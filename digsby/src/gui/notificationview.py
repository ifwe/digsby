'''
GUI for editing notification events.

NotificationView is the main TreeList control which lists notifications.
'''

from __future__ import with_statement

import wx
from copy import deepcopy
from util import dictadd
from gui.treelist import TreeList, TreeListModel
from gui.toolbox import build_button_sizer
from util import autoassign, pythonize, dictsub, InstanceTracker
from gui import skin
from common import profile
from common.notifications import reactions
from gettext import ngettext

from logging import getLogger; log = getLogger('notificationview'); info = log.info

from common.notifications import get_notification_info

from wx import Rect
#notification_info = get_notification_info()

def get_notifications(testdict = {}):
    "Returns user notifications in the form {'dotted.name': Reaction}"

    try:
        from common import profile
        return profile.notifications
    except ImportError:
        return testdict


class EventPanel(wx.Panel):
    'Popup for editing a single event.'

    def __init__(self, parent, event_desc, event = None):
        wx.Panel.__init__(self, parent)
        if not isinstance(event_desc, basestring):
            raise TypeError

        # "who" is a string describing who's doing the eventings
        aContact = _('a Contact')
        if event is None:
            replace_str = aContact
        else:
            if 'contact' in event:
                replace_str = event['contact'].split('/')[-1]
            else:
                replace_str = aContact

        self.event_desc = _('When ') + event_desc.replace(_('Contact'), replace_str)

        self.action_ctrls = {}

        self.construct(event)
        self.layout()

        # If we're editing an existing event, populate
        if event: self.populate(event)

    def info(self):
        details = dict()
        for name, (ctrl, ex) in self.action_ctrls.iteritems():
            details[name] = getattr(ctrl, ex)

        details['reaction'] = reactions[self.action_choice.GetSelection()]
        return details

    def populate(self, event):
        with self.Frozen():
            for name, (c, ex) in self.action_ctrls.iteritems():
                setattr(c, ex, event[name])

    def construct(self, event = None):
        'Constructs common event GUI elements.'

        # Top header: the description of the event.
        self.event_header = Text(self, self.event_desc)
        font = self.event_header.Font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.event_header.Font = font

        self.action_text = Text(self, _('&Action:'))
        self.action_choice = self.build_action_choice(event)
        self.action_choice.Bind(wx.EVT_CHOICE, self.on_action_choice)

        # Add and Cancel buttons
        self.ok = wx.Button(self, wx.ID_OK, _('&OK'))
        self.ok.SetDefault()
        self.cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))

    def on_action_choice(self, e = None):
        '''
        Invoked when the "action" choice is changed. Controls under the choice
        need to be updated.'
        '''

        i = self.action_choice.GetSelection()
        if i == -1: return

        with self.Frozen():
            f = self.flex

            [c.Window.Destroy() for c in f.Children
             if c.Window not in (self.action_text, self.action_choice)]

            self.action_ctrls.clear()

            f.Clear() # does not Destroy child windows
            f.Add(self.action_text, 0, wx.EXPAND | wx.ALL, 10)
            f.Add(self.action_choice, 0, wx.EXPAND | wx.ALL, 10)

            # Call build_controls_XXX where XXX is the pythonized name of
            # the Reaction class (see notifications.py for possible
            # Reactions)
            name = pythonize(reactions[i].__name__)
            getattr(self, 'build_controls_%s' % name,
                    lambda s: None)(self.flex)

            self.Layout()

    def layout(self):
        'Initial sizer layout.'

        self.Sizer = sz = wx.BoxSizer(wx.VERTICAL)

        # The flex grid sizer is where controls are subbed in and out depending
        # on the action.
        self.flex = f = wx.FlexGridSizer(-1, 2, 6, 6)

        # define some shortcuts for adding controls to the flex grid for
        # consistent spacing

        AddFlexControl = lambda c: self.flex.Add(c, 0, wx.EXPAND | wx.ALL, 5)

        def AddHeader(header):
            AddFlexControl(wx.StaticText(self, -1, _(header)))

        def AddControl(name, ctrl, data_extractor = 'Value'):
            self.action_ctrls[name] = (ctrl, data_extractor)
            AddFlexControl(ctrl)

        self.flex.AddHeader  = AddHeader
        self.flex.AddControl = AddControl

        self.on_action_choice()

        sz.Add(self.event_header, 0, wx.EXPAND | wx.ALL, 10)
        sz.Add(f, 1, wx.EXPAND)

        # OK/Cancel
        sz.Add(build_button_sizer(save=self.ok, cancel=self.cancel),
               0, wx.EXPAND | wx.SOUTH | wx.EAST | wx.WEST, 4)

    def build_action_choice(self, event = None):
        'Returns the action choice control.'

        choice_ctrl = wx.Choice(self, -1, choices = [r.__doc__ for r in reactions])

        i = 0 if event is None else reactions.index(event['reaction'])
        choice_ctrl.SetSelection(i)
        return choice_ctrl

    ##
    ## these methods define which controls appear for each action type.
    ## if the method is missing, no controls are used.
    ##

    def build_controls_alert(self, sz):
        sz.AddHeader('&Alert Text:')
        txt = wx.TextCtrl(self, -1, '', style = wx.TE_MULTILINE)
        txt.Size = (300, 300)
        sz.AddControl('msg', txt)

    def build_controls_sound(self, sz):
        sz.AddHeader('&Sound:')
        sz.AddControl('filename', wx.FilePickerCtrl(self, -1), 'Path')

    def build_controls_showcontactlist(self, sz):
        sz.AddHeader('&Seconds:')
        sz.AddControl('duration', wx.TextCtrl(self, -1, ''))

    def build_controls_startcommand(self, sz):
        sz.AddHeader('&Command:')
        txt = wx.TextCtrl(self, -1, '')
        sz.AddControl('path', txt)

class EventDialog(wx.Dialog):
    'Shows the event edit panel.'

    def __init__(self, parent, event_desc, event = None):

        if event is not None:
            title = _('Edit Event for "{desc}"').format(desc=event_desc)
        else:
            title = _('Add Event for "{desc}"').format(desc=event_desc)

        wx.Dialog.__init__(self, parent, title = title)
        self.Sizer = sz = wx.BoxSizer(wx.VERTICAL)

        self.eventpanel = EventPanel(self, event_desc, event = event)
        self.info = self.eventpanel.info

        sz.Add(self.eventpanel, 1, wx.EXPAND)
        self.Bind(wx.EVT_BUTTON, self.on_button)

    def on_button(self, e):
        self.EndModal(e.EventObject.Id)


class NotificationEntry(object):
    'A row in the Notifications VListBox.'

    def OnDrawBackground(self, dc, rect, n, selected):
        from gui.anylists import bgcolors

        # alternate colors
        bgcol = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT) if selected else bgcolors[n % len(bgcolors)]
        dc.Brush = wx.Brush(bgcol)
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangle(*rect)

class EventEntry(NotificationEntry):
    def __init__(self, event):
        if not isinstance(event, dict) and 'reaction' in event:
            raise TypeError('event should be a dict, got a %s' % type(event))

        self.event = event
        self.name = str(id(self.event))

    def __repr__(self):
        event = self.event
        reac = event['reaction']

        # If this event dict has a contact associated with it, add
        # "for CONTACT" on the end of the description string.
        if 'contact' in event:
            contact_str = _(' for %s') % event['contact'].split('/')[-1]
        else:
            contact_str = ''

        try:
            desc = reac.desc
        except AttributeError:
            desc = reac
            #raise AssertionError('Reaction objects must have a desc attribute')


        if callable(desc):
            return desc(self.event) + contact_str
        else:
            try:
                return (desc % self.event) + contact_str
            except:
                log.warning('illegal format string or mismatched')
                log.warning('event: %r', self.event)
                log.warning(desc)
                return self.event['reaction'].__doc__ + contact_str

    def __hash__(self):
        return id(self)




class ActionEntry(NotificationEntry, list):
    def __init__(self, topic, events = [], description = '', icon_skinpath = None):
        autoassign(self, locals())
        self.name = topic
        if self.icon_skinpath is None:
            self.icon_skinpath = 'AppDefaults.Notificationicons.%s' % self.topic.split('.', 1)[0]

        list.__init__(self, [EventEntry(event) for event in events])

    def __repr__(self):
        return self.description

    def __hash__(self):
        return hash(unicode(self.topic) + ''.join(unicode(c.__hash__()) for c in self))

    def expandable(self):
        return bool(len(self))

    @property
    def icon(self):
        icon = skin.get(self.icon_skinpath, None)
        if icon is not None:
            if len(self) > 0:
                return icon.Resized(32)
            else:
                return icon.Resized(20)

    @property
    def ItemHeight(self):
        if len(self) > 0:
            return 40
        else:
            return 25




class NotificationView(TreeList, InstanceTracker):
    'Displays notifications for all contacts or for an individual contact in a tree list.'

    def __init__(self, parent, notifications, for_contact = None, plusminus_buttons = None):
        TreeList.__init__(self, parent, TreeListModel(), style = wx.NO_BORDER)
        InstanceTracker.track(self)

        if for_contact is not None and not hasattr(for_contact, 'idstr'):
            raise TypeError('for_contact must be a contact, a metacontact, or None')

        # if for_contact is None we'll show both global ztnotifications and
        # notifications for each contact
        info('showing notifications for %s', 'everybody' if for_contact is None else for_contact.idstr())
        self.for_contact = for_contact
        self.notifications = notifications

        if plusminus_buttons is not None:
            plus, minus = plusminus_buttons
            plus.Bind(wx.EVT_BUTTON, self.on_add)
            minus.Bind(wx.EVT_BUTTON, self.on_remove)
            #TODO: disable add/deleted when no not. is selected

        self.update_view()

        self.BBind(LEFT_DCLICK = self.on_add_or_edit,
                   LEFT_DOWN   = self.on_left_down,
                   LISTBOX     = self.on_selection)

        self.SetDrawCallback(self.cskin_drawcallback)

    def cskin_drawcallback(self, dc, rect, n):
        self.OnDrawBackground(dc, Rect(*rect), n)
        self.OnDrawItem(dc, Rect(*rect), n)
        #self.OnDrawSeparator(dc, Rect(*rect), n)


    def on_selection(self, e):
        'When an event is selected, "preview" it.'

        sel = self.GetSelection()
        if sel != -1:
            obj = self[sel]
            if isinstance(obj, EventEntry):
                obj.event['reaction'](**dictsub(obj.event, {'reaction': None})).preview()

    def on_left_down(self, e):
        if e.Position.x < 20:
            i, percent = self.hit_test_ex(e.Position)
            if i != -1: self.toggle_expand(self.model[i])
            e.Skip(False)
        else:
            e.Skip(True)

    @classmethod
    def update_all(cls):
        cls.CallAll(NotificationView.update_view)

    def update_view(self):

        #from common.notifications import set_active
        #set_active(get_notifications())

        notifications, contact = self.notifications, self.for_contact
        if contact is not None:
            contact = contact.idstr()
            contactobj = contact

        showing_contacts = True
        already_added, root = [], []

        gnots = {} if None not in notifications else notifications[None]

        for topic, notif in get_notification_info().iteritems():
            events, desc = [], notif['description']

            if contact is None:
                if topic in gnots:
                    p = deepcopy(gnots[topic])
                    events.extend(p)

                # Grab events for contacts (maybe)
                if showing_contacts:
                    for subcontact in (set(notifications.keys()) - set([None])):
                        if subcontact in self.notifications:
                            if topic in self.notifications[subcontact]:
                                c_events = deepcopy(notifications[subcontact][topic])
                                if c_events:
                                    events.extend([(dictadd({'contact': subcontact}, e))
                                                   for e in c_events])

                if events:
                    already_added += [topic]
                    root.append(ActionEntry(topic, events,
                                            description = desc,
                                            icon_skinpath = notif.get('notification_icon', None)))
            else:
                if contact in notifications:
                    if topic in notifications[contact]:
                        events = deepcopy(notifications[contact][topic])
                        if events:
                            already_added += [topic]
                            root.append(ActionEntry(topic, events,
                                                    description = desc,
                                                    icon_skinpath = notif.get('notification_icon', None)))



        # Add event categories with no events set
        for topic, notif in get_notification_info().iteritems():
            if not topic in already_added:
                root.append(ActionEntry(topic,
                                        description = notif['description'],
                                        icon_skinpath = notif.get('notification_icon', None)))
        self.set_root(root)

    def on_add_or_edit(self, e = None):
        i = self.GetSelection()
        if i == -1: return
        obj = self[i]
        if isinstance(obj, ActionEntry):
            return self.on_add(e)
        else:
            parent = self.model.parent_of(obj)
            description = get_notification_info()[parent.topic]['description']
            diag = EventDialog(self, description, event = obj.event)
            res = diag.ShowModal()
            if res == wx.ID_OK:
                contact = None if self.for_contact is None else self.for_contact.idstr()
                if 'contact' in obj.event:
                    contact = obj.event['contact']
                nots = self.notifications[contact]
                notif = nots[parent.topic]
                notif.insert(notif.index(obj.event), deepcopy(diag.info()))
                notif.remove(obj.event)

                self.CallAll(NotificationView.update_view)

            diag.Destroy()

    def on_add(self, e):

        i = self.GetSelection()
        if i != -1:
            if isinstance(self[i], EventEntry):
                i = self.model.index_of(self.GetParent(self[i]))

            topic = self[i].topic
            assert isinstance(topic, basestring), 'topic is a %s' % type(topic)

            # Display the event edit dialog.
            diag = EventDialog(self, get_notification_info()[topic]['description'])
            res = diag.ShowModal()
            if res == wx.ID_OK:
                contact = self.for_contact.idstr() if self.for_contact else None

                if contact not in self.notifications:
                    self.notifications[contact] = dict()

                if topic not in self.notifications[contact]:
                    self.notifications[contact][topic] = list()

                self.notifications[contact][topic].append(deepcopy(diag.info()))

            diag.Destroy()

            self.CallAll(NotificationView.update_view)

    def on_remove(self, e):
        i = self.GetSelection()
        if i == -1: return

        obj = self[i]

        if isinstance(obj, ActionEntry):
            return

        contact = obj.event.get('contact', # buddy specific
                                None if self.for_contact is None # global
                                else self.for_contact.idstr())   # buddy specific window

        if 'contact' in obj.event:
            contact = obj.event['contact']

        if isinstance(obj, EventEntry):
            parent = self.GetParent(obj)
            parent.remove(obj)

            topic = self.notifications[contact][parent.topic]
            topic.remove(dictsub(obj.event, {'contact':None}))
            if len(topic) == 0:
                del self.notifications[contact][parent.topic]
            self.CallAll(NotificationView.update_view)

        elif isinstance(obj, NotificationEntry):
            n = len(obj.events)
            msg = ngettext(_('Are you sure you want to remove %d event?') % n,
                           _('Are you sure you want to remove %d events?') % n,
                           n)
            if wx.YES == wx.MessageBox(msg, _('Remove Events: {notification_desc}').format(notification_desc=obj.description),
                          style = wx.YES_NO):
                del self.notifications[contact][obj.topic]
                self.update_view()

class ContactAlertDialog(wx.Dialog):
    def __init__(self, parent, contact):

        from contacts import MetaContact
        name = contact.alias if isinstance(contact, MetaContact) else contact.name

        wx.Dialog.__init__(self, parent, title = _('Editing Alerts for {name}').format(name=name))
        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)

        self.contact = contact

        add_button = wx.Button(self, -1, '+')
        add_button.Size = (15, 15)
        remove_button = wx.Button(self, -1, '-')
        remove_button.Size = (15, 15)
        h = wx.BoxSizer(wx.HORIZONTAL)
        h.AddStretchSpacer(1)
        h.Add(add_button)
        h.Add(remove_button)
        s.Add(h, 0, wx.EXPAND | wx.ALL, 3)

        self.notview = NotificationView(self, deepcopy(dict(get_notifications())), contact,
                                        (add_button, remove_button))

        s.Add(self.notview, 1, wx.EXPAND)

        # Save and cancel buttons
        save = wx.Button(self, wx.ID_SAVE, _('&Save'))
        cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))
        button_sizer = build_button_sizer(save, cancel)

        save.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_SAVE))

        s.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 7)


    def Prompt(self, callback):
        if wx.ID_SAVE == self.ShowModal():
            callback(notifications = self.notview.notifications)
            self.notview.update_all()

def edit_contact_alerts(parent, contact):
    diag = ContactAlertDialog(parent, contact)

    def callback(notifications):
        idstr = contact.idstr()
        profile.notifications[idstr] = notifications[idstr]

    diag.Prompt(callback)




Text = lambda self, txt: wx.StaticText(self, -1, txt)



