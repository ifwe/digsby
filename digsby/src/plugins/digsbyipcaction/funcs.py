import sys
import simplejson

IPC_HOOK = 'digsby.ipcaction'

def quote_escape(s):
    return s.replace('"', '\\"')

def quote_unescape(s):
    return s.replace('\\"', '"')

def register_ipc_handlers():
    '''Registers an IPC handler for --action commands.'''

    import config as digsbyconfig
    if digsbyconfig.platformName != 'win':
        return

    import wx, hooks
    from .ipc import listen

    def on_ipc(msg):
        try:
            method, kwargs = msg.split(':', 1)
        except ValueError:
            method, kwargs = msg, '{}'

        kwargs = simplejson.loads(quote_unescape(kwargs))
        wx.CallAfter(hooks.notify, IPC_HOOK, impl=method, **kwargs)

    listen(on_ipc)

def funccall(method, **kwargs):
    if kwargs:
        argstring = quote_escape(simplejson.dumps(kwargs))
        return '"%s"' % ':'.join([method, argstring])
    else:
        return method

def handle_ipc_action():
    '''Looks for --action=foo on the command line, and sends an IPC message to
    a running Digsby instance.'''
    if sys.opts.action:
        import ipc
        ipc.send_message(sys.opts.action)
        return True

