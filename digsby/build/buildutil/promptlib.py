#__LICENSE_GOES_HERE__
_pre_functions = []
_post_functions = []

def register_pre_handler(pred, pre):
    _pre_functions.insert(0, (pred, pre))

def register_post_handler(pred, post):
    _post_functions.insert(0, (pred, post))

def register_prompt_handler(f):
    funcs = f()
    pred = funcs.get('pred')
    pre = funcs.get('pre')
    post = funcs.get('post')
    if pred is None:
        raise Exception('%r doesn\'t seem to be the right sort of function for a prompt handler', f)

    if pre is not None:
        register_pre_handler(pred, pre)
    if post is not None:
        register_post_handler(pred, post)

    return f

@register_prompt_handler
def bool_type():
    def pred(o, d):
        return o is bool

    def pre(o,d):
        if d is True:
            return '', '(Y/n)'
        elif d is False:
            return '', '(y/N)'
        else:
            return '', '(y/n)'

    def post(t, o, d):
        t = t.lower()
        if t in ('y', 'n'):
            return True if t == 'y' else False
        return d

    return locals()

@register_prompt_handler
def confirm_type():
    def pred(o, d):
        return o == 'confirm' and d is not None
    def pre(o, d):
        return '', ': type "%s" (or "CANCEL" to cancel)' % d
    def post(t, o, d):
        if t == d:          return True
        elif t == 'CANCEL': return False
        else:               return None
    return locals()

@register_prompt_handler
def str_type():
    def pred(o, d):
        return o is str
    def pre(o, d):
        return ('(default = %r)' % (d,)), ''
    def post(t, o, d):
        return t or d
    return locals()

@register_prompt_handler
def strlist_type():
    def pred(o, d):
        return o is list
    def pre(o, d):
        return ('(default = %r)' % (d,)), '(comma-separated)'
    def post(t, o, d):
        if t:
            return map(str.strip, t.strip(',').split(','))
        else:
            return d
    return locals()

@register_prompt_handler
def list_type():
    def pred(o, d):
        return type(o) is list
    def pre(o, d):
        options_str = '\n\t' + '\n\t'.join('(%d) %s' % (i+1, s) for i,s in enumerate(o))
        default_str = '\n(default = %r)' % d
        return default_str, options_str
    def post(t, o, d):
        if not t:
            return d
        try:
            idx = int(t)
        except Exception:
            return None
        else:
            if idx == 0:
                return None
            try:
                return o[idx-1]
            except IndexError:
                return None
    return locals()

def pre_prompt(prompt_str, options, default):
    pre_func = find_pre_function(options, default)
    if pre_func is None:
        raise NotImplementedError("Don't know what to do for options = %r, default = %r", options, default)

    default_str, options_str = pre_func(options, default)

    full_prompt_str = ("%s %s %s" % (prompt_str, options_str, default_str)).strip() + ": "
    return full_prompt_str, options, default

def prompt(prompt_str, options = None, default = None, input_func = raw_input):
    prompt_str, options, default = pre_prompt(prompt_str, options, default)
    result = None
    while result is None:
        try:
            text = input_func(prompt_str).strip()
        except Exception, e:
            raise e
        else:
            result = post_prompt(text, options, default)
            if default is None and result is None:
                break

    return result

def find_match_for(pred_func_list, *args):
    for pred, func in pred_func_list:
        if pred(*args):
            return func

def find_pre_function(options, default):
    return find_match_for(_pre_functions, options, default)

def find_post_function(options, default):
    return find_match_for(_post_functions, options, default)

def post_prompt(text, options, default):
    post_func = find_post_function(options, default)
    if post_func is None:
        raise NotImplementedError("Don't know what to do for options = %r, default = %r", options, default)

    return post_func(text, options, default)


def _main():
    'bool confirm str strlist list'
    booltests = (
     (bool, True, ['n'], False),
     (bool, False, ['y'], True),
     (bool, None, ['', 'y'], True),
     (bool, True, [''], True),
     (bool, False, [''], False),
     )
    confirmtests = (
     ('confirm', 'b', ['b'], True),
     ('confirm', 'b', ['CANCEL'], False),
     ('confirm', 'b', ['a', 'CANCEL'], False),
     ('confirm', 'b', ['a', 'b'], True),
     )
    strtests = (
     (str, 'a', ['b'], 'b'),
     (str, 'a', [''], 'a'),
     (str, None, ['b'], 'b'),
     (str, None, ['', 'a'], 'a'),
     )
    strlisttests = (
     (list('abcd'), 'a', [''], 'a'),
     (list('abcd'), 'a', [''], 'a'),
     (list('abcd'), 'a', [''], 'a'),
     (list('abcd'), 'a', [''], 'a'),
     )
    listtests = (
     #(),
     )

    for tests in (booltests, confirmtests, strtests, strlisttests, listtests):
        for opts, default, inputs, expected in tests:
            def input():
                yield None
                for input in inputs:
                    yield input
                while True:
                    yield ''

            input_gen = input()
            input_gen.next()
            result = prompt(repr(opts), opts, default, input_gen.send)
            input_gen.close()
            if result == expected:
                print ' O'
            else:
                print ' X (%r != %r)' % (result, expected)

if __name__ == '__main__':
    _main()
