'''

Actions - callables with names, bitmaps, shortcuts, and preconditions.

'''
from __future__ import with_statement
from functools import partial
from types import FunctionType as function
from util.observe import Observable, ObservableMeta
import logging
import util.data_importer as importer
import util.introspect as introspect
import util.merge
import util.primitives.funcs as funcs
import util.primitives.mapping as mapping
import util.primitives.strings as strings

log = logging.getLogger('actions')
__author__ = 'dotSyntax'


_actions_cached = None
_actions_imported = False

def _actions():

    global _actions_cached
    global _actions_imported

    if _actions_imported:
        return _actions_cached

    from gui import skin
    try:
        actions = importer.yaml_import('actions', loadpath = [skin.resourcedir()])
    except ImportError:
        actions = {}
    finally:
        _actions_imported = True

    add_actions(actions)
    return _actions_cached

def add_actions(actionsdict):
    the_actions = _actions()
    if the_actions is None:
        the_actions = {}
    the_actions = util.merge.merge(the_actions, actionsdict)

    global _actions_cached
    _actions_cached = the_actions

def forclass(cls, search_bases = True):
    'Returns YAML action descriptions for a given class (and subclasses).'

    if not isinstance(cls, type) and \
        hasattr(cls, '__class__'): cls = cls.__class__

    if search_bases:
        classes = list(reversed(cls.__mro__))
    else:
        classes = [cls]

    return funcs.flatten(_actions().get(c.__name__, []) for c in classes)

class Action( Observable ):
    def __init__( self, name, callable ):
        Observable.__init__(self)
        funcs.autoassign( self, locals() )

    def __call__( self, *args, **kws ):
        return self.callable( *args, **kws )

    def __repr__( self ):
        return '<Action %s for %r>' % ( self.name, self.callable )


def menu(parent, obj, menu = None, cls = None, search_bases = True, filter = lambda func: True):
    'Builds or adds to an existing menu with actions for the specified object.'

    from gui.uberwidgets.umenu import UMenu

    actions = forclass(cls if cls is not None else obj, search_bases)
    menu    = menu if menu is not None else UMenu(parent)

    # For each action defined in the YAML
    names = set()
    for action in actions:

        #
        # ---- means separator
        #
        if isinstance(action, basestring) and action.startswith('--'):
            menu.AddSep()
            continue
        #
        # method: a function to call
        #
        elif 'method' in action:
            introspect.import_function(action['method'])(menu, obj)
            continue

        name = action['call']
        if name in names: continue
        else: names.add(name)


        # the actual function
        func = getattr(obj, name, None)
        if func is None: continue

        gui_name = action['name']

        try:
            # read precondition lambda and "needs" from the @action annotations
            precondition, needslist = getattr(obj, '_actions')[name]
        except KeyError, _e:
            # ...if there is no @action annotating the method, just call it
            precondition, needslist = lambda v: True, []


        if needslist:
            import gui.userform as userform
            callback = partial(userform.getinput, obj, parent, needslist,
                               func, title = gui_name.replace('&',''))
        elif 'gui' in action:
            gui = introspect.import_function(action['gui'])

            if not hasattr(gui, 'Prompt'):
                callback = lambda gui=gui, func=func: gui(obj, func)
            else:
                def callback(gui=gui, func=func): gui(None, obj).Prompt(func)

        else:
            callback = func

        # Preconditions
        # - None:  Don't show menu item
        # - False: Show disabled menu item
        # - True:  Show menu item

        result = precondition( obj ) if precondition is not None else True

        if filter(func) and (precondition is None or result is not None):
            name = action_name(obj, gui_name)
            menu.AddItem(name, callback = callback).Enable(bool(result))

    if menu.GetMenuItemCount() == 0:
        menu.AddItem(_('No actions')).Enable(False)

    while menu[-1].IsSeparator():
        menu.RemoveItem(menu[len(menu)-1])

    return menu

def action_name(obj, name):
    if name.find('$') != -1:
        name = strings.curly(name, source = {'obj': obj})

    return name

_actioncalls = dict()

class ActionMeta(type):
    '''
    When a class with ActionMeta as a metaclass is compiled, all functions
    that have an @action decorator are collected into a class variable called
    _actions.
    '''

    action_prefix = '__ACTION__'
    class_action_attr = '_actions'

    def __init__(cls, name, bases, dict):
        global _actioncalls
        super(ActionMeta, cls).__init__(name, bases, dict)

        # Inherit actions from base classes.
        superactions = mapping.odict()

        if 'inherited_actions' in dict:
            bases = bases + tuple(dict['inherited_actions'])

        funcs.do(superactions.update(c._actions) for c in bases if hasattr(c, '_actions'))
        setattr(cls, ActionMeta.class_action_attr, superactions)

        actions = getattr(cls, ActionMeta.class_action_attr)
        prefix = ActionMeta.action_prefix

        for v in dict.itervalues():
            # for each method in the classdict:
            # if it's a function and it starts with our magic action prefix,
            # remove the prefix and add it to our list of actions, along with
            # the callable "predicate" determining the action's validity at any
            # point in time
            if isinstance(v, function) and v.__name__.startswith(prefix):
                v.__name__ = v.__name__[len(prefix):]
                val = _actioncalls.pop(v)
                actions[v.__name__] = val

class ActionType(object):
    __metaclass__ = ActionMeta

class ObservableActionMeta(ObservableMeta, ActionMeta): pass


class ActionError(Exception): pass

def _action_err_info(callable_predicate):
    'Grabs error information and context for an ActionError.'

    code = callable_predicate.func_code
    fn = code.co_filename
    ln = code.co_firstlineno

    from linecache import getline
    line = getline(fn,ln) or '<UNKNOWN>'

    return fn,ln,line

#
# action decorator
#

def action( callable_predicate = None, needs = None ):
    'Marks a class method as an action.'

    global _actioncalls # not threadsafe, but all @action decorators should be run at "compile" time anyways

    if callable_predicate is not None and not callable(callable_predicate):
        raise TypeError("action decorator needs a callable or None as it's "
                        "only argument (you gave a %s)" % type(callable_predicate))

    def action_dec( meth ):
        def func( *args, **kws ):

            # Do runtime check of the predicate. The GUI should have done this
            # already, but for command-line usage a nice exception will be
            # shown.
            if callable_predicate:
                filename, line, line_text = _action_err_info(callable_predicate)
                err_msg = \
'''%s is not allowed, %%s
File "%s", line %d, in %s
%s''' % \
                (meth.__name__, filename, line, callable_predicate.__name__, line_text)

                try:
                    allow = callable_predicate(*args, **kws)
                except TypeError, e:
                    raise ActionError, err_msg % \
                        'error in precondition function: ' + str(e)

                # Did we fail the precondition?
                if not allow:
                    log.warning(str(ActionError(err_msg % 'precondition not met for')))

            return meth( *args, **kws )

        # tag the method so the metaclass can add it into a list
        func.__name__ = ActionMeta.action_prefix + meth.__name__
        func.__doc__  =  meth.__doc__

        def allowed(obj):
            if hasattr(obj, '_disallow_actions'):
                return False

            if callable_predicate:
                return callable_predicate(obj)

            return True

        func.action_allowed = allowed

        # If any needs were specified, make sure they are in the right format.
        tneeds = needs

        # Store for the metaclass to pick up when the class is defined.
        _actioncalls[func] = (allowed, tneeds)

        return func
    return action_dec
