from peak.util.plugins import Hook
from util.threads import threaded
from logging import getLogger; _log = log = getLogger('plugin_hub')
import traceback

# call each hook method async
def asyn(identifier, *args, **kwargs):
    threaded(syn)(identifier, *args, **kwargs)

# call each method sync
def syn(identifier, *args, **kwargs):
    ret = True

    for hook in Hook(identifier):
        #_log.info('HOOK: %s',repr(hook))
        try:
            ret = hook(*args, **kwargs)
            if not ret:
                ret = False
        except Exception:
            traceback.print_exc()
    return ret


    #return all(try_this(lambda: hook(*args, **kwargs), False) for hook in Hook(identifier))

# call to a hook with the specified ID and args
def act(id, *args, **kwargs):
    #_log.info('ACT: %s',id)
    #log.info('%s',repr(args))


    if id.endswith('.async'):
        asyn(id, *args, **kwargs)
    else:
        ret = syn(id, *args, **kwargs)

        #_log.info('%s',repr(ret))
        return ret


hooks = \
'''
im:
  filetransfer: syn, buddy, file, state
  alert:
    pre: syn, proto, type, param
  msg:
    pre: syn, message, type
    async: syn, msg, type
  my_status_change:
    pre: syn, msg
    async: syn, msg
  setprofile:
    pre: syn, proto, profile
    async: syn, proto, profile
  status_change:
    pre: syn, proto, buddy
    async: syn, proto, buddy
  info:
    pre: syn, proto, buddy, info
    async: syn, proto, buddy, info
  conversation:
    start:
      pre: syn, proto, buddy
      async: syn, proto, buddy
    end:
      async: syn, proto, buddy
  addcontact:
    pre: syn, proto, name, alias
    async: syn, proto, name, alias
  addaccount:
    async: syn, proto_name, acct_name
updateaccount:
  async: syn, account
social:
  addaccount:
    async: syn, proto_name, acct_name
  alert: syn, proto, type, msg
protocol:
  statechange:
    async: syn, state
plugin:
  load:
    async: syn
  unload:
    async: syn
goidle:
  pre: syn
  async: syn
unidle:
  pre: syn
  async: syn
email:
  newmail:
    pre: syn, proto, address, count, msg
    async: syn, proto, address, count, msg
  addaccount:
    async: syn, proto_name, acct_name
popup:
  pre: syn
'''

functemp = \
'''def %(func_name)s(%(def_args)s):
    return %(type)s('%(func_id)s'%(func_args)s)
'''

from prefs import flatten
from syck import load
funcs = flatten(load(hooks))

for func_id, args in funcs:
    func_id = 'digsby.' + func_id
    args = args.split(', ')
    type, func_args = args[0], args[1:]
    def_args = ', '.join(func_args)
    if func_args:
        func_args = ', ' + def_args
    else:
        func_args = ''
    func_name = func_id.replace('.', '_')
    exec(functemp % locals(), globals(), locals())

