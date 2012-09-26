def form_builder(parts):
    global _mimifiers
    form_mime = mimify('multipart', _subtype = 'form-data')
    for props in parts:
        _name = props.get('name')
        _type = props.get('type')
        _val  = props.get('value')
        _kws  = props.get('kws', {})
        disp_kws = props.get('disposition', {})
        
        mime_part = _mimifiers.get(_type)(_val, **_kws)
        mime_part.add_header('Content-Disposition', 'form-data', name = _name, **disp_kws)
        
        form_mime.attach(mime_part)
        
    return form_mime

_mimifiers = {}

def mimifier(name):
    def registerer(f):
        global _mimifiers
        _mimifiers[name] = f
        return f
    return registerer

_cap_names = {'nonmultipart' : 'NonMultipart'}        
def mimify(type, **kwargs):
    cap_name = _cap_names.get(type, type.capitalize())
    mime_mod = getattr(__import__('email.mime.%s' % type).mime, type)
    mime_type = getattr(mime_mod, 'MIME%s' % cap_name)
    return mime_type(**kwargs)

@mimifier('text')
def mime_text(text, encoding = 'utf8'):
    return mimify('text', _text = text.encode(encoding), _charset = encoding)

@mimifier('text-noenc')
def mime_text_noenc(text, encoding = 'ascii'):
    mimeobj = mimify('nonmultipart', _maintype = 'text', _subtype = 'plain',)
    mimeobj.set_payload(text.encode(encoding))
    mimeobj.set_charset(encoding)
    return mimeobj

@mimifier('application')
def mime_app(data):
    return mimify('application', _data = data)

def subtype_for_image(data):
    import imghdr, os.path
    if hasattr(data, 'read') or os.path.exists(data):
        return imghdr.what(data)
    else:
        return imghdr.what(None, data)
    
@mimifier('image')
def mime_image(data):
    subtype = subtype_for_image(data)
    return mimify('image', _imagedata = data, _subtype = subtype)

@mimifier('image-noenc')
def mime_image_noenc(data, filename = None):
    import email.encoders as encoders
    subtype = subtype_for_image(data)
    mimeobj = mimify('image', _imagedata = data, _subtype = subtype, _encoder = encoders.encode_noop)
    if filename is not None:
        pass
    return mimeobj

@mimifier('data')
def mime_data(data):
    import email.encoders as encoders
    mimeobj = mimify('nonmultipart', _maintype = '', _subtype = '')
    mimeobj._headers[:] = []
    mimeobj.set_payload(data)
    return mimeobj
