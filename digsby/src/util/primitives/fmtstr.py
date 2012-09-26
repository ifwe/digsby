from collections import defaultdict
from util import Storage

class FormattingException(Exception): pass

class fmtstr(object):
    '''
    Holds formatted text, and converts between different formats.
    '''

    least_lossy = ['rtf', 'singleformat', 'plaintext']

    @staticmethod
    def plaintext(txt):
        assert isinstance(txt, basestring)
        return fmtstr(plaintext=txt)

    @staticmethod
    def singleformat(s, format):
        assert isinstance(s, basestring)
        return fmtstr(singleformat=dict(text=s, format=format))

    def __init__(self, **string_values):
        assert string_values

        # pop any None values
        for k, v in string_values.items():
            if v is None:
                string_values.pop(k)
            else:
                string_values[k] = getattr(self, '_transform_' + k, lambda v: v)(v)

        self.string_values = string_values # {mime-type: value}

    def _transform_singleformat(self, val):
        '''
        turn any wxColors in format storages into tuples
        '''
        import wx
        format = val.get('format')
        if format is None:
            return

        format_primitive = {}
        for k, v in format.items():
            format_primitive[k] = tuple(v) if isinstance(v, wx.Color) else v

        val['format'] = format_primitive
        return val

    def __add__(self, text):
        rtf = self.string_values.get('rtf')
        if rtf is not None:
            return fmtstr(rtf=rtf_append(rtf, text))

        singleformat = self.string_values.get('singleformat')
        if singleformat is not None:
            return fmtstr.singleformat(singleformat['text'] + text, format=singleformat['format'])

        return fmtstr.plainttext(self.format_as('plaintext') + text)

    @property
    def bestFormat(self):
        for fmt in self.least_lossy:
            if fmt in self.string_values:
                return fmt

        return None

    def asDict(self):
        serialized_dict = {}
        for fmt in self.least_lossy:
            try:
                val = self.string_values[fmt]
            except KeyError:
                pass
            else:
                serialized_dict[fmt] = val
                break

        assert serialized_dict
        return serialized_dict

    @staticmethod
    def fromDict(dict):
        return fmtstr(**dict)

    def __repr__(self):
        try:
            r = self.string_values['plaintext']
        except KeyError:
            r = repr(self.string_values)[:40]

        return '<fmtstr %r>' % r

    def format_as(self, type):
        try:
            return self.string_values[type]
        except KeyError:
            for encoder in self._encoder_types[type]:
                try:
                    val = encoder(self)
                except FormattingException:
                    val = None
                if val is not None:
                    self.string_values[type] = val # memoize
                    return val

            raise FormattingException('cannot format as %r' % type)

    _encoder_types = defaultdict(list)

try:
    from cgui import RTFToX
except ImportError:
    pass
else:
    # register RTF -> types
    import cgui

    def register_encoder(output_type, encoder):
        fmtstr._encoder_types[output_type].append(encoder)

    def register_rtf_encoder(fmt):
        def encoder(fmtstr):
            rtf = fmtstr.format_as('rtf')
            if rtf is not None:
                return RTFToX().Convert(rtf, fmt, 'rtf')
        encoder.__name__ = 'rtf_to_%s_encoder' % fmt

        register_encoder(fmt, encoder)

    def register_plaintext_encoder(fmt):
        def encoder(fmtstr):
            plaintext = fmtstr.format_as('plaintext')
            if plaintext is not None:
                return RTFToX().Convert(plaintext, fmt, 'plaintext')
        encoder.__name__ = 'plaintext_to_%s_encoder' % fmt

        register_encoder(fmt, encoder)


    def register_singleformat_encoder(fmt):
        def encoder(fmtstr):
            singleformat = fmtstr.format_as('singleformat')
            if singleformat is not None:
                from gui.uberwidgets.formattedinput2.fontutil import StorageToStyle
                formatstorage = singleformat['format']
                if not isinstance(formatstorage, Storage):
                    formatstorage = Storage(formatstorage)
                textattr = StorageToStyle(formatstorage)
                return RTFToX().Convert(singleformat['text'], fmt, 'plaintext', textattr)
        encoder.__name__ = 'singleformat_to_%s_encoder' % fmt

        register_encoder(fmt, encoder)

    def singleformat_to_plaintext(fmtstr):
        return fmtstr.format_as('singleformat')['text']

    register_encoder('plaintext', singleformat_to_plaintext)

    for fmt in cgui.RTFToX.EncoderTypes():
        register_rtf_encoder(fmt)
        register_singleformat_encoder(fmt)
        register_plaintext_encoder(fmt)


def rtf_append(rtf, text):
    'Appends plaintext to an RTF string.'

    # This is a hack until RTFToX supports appending text to its formatting tree.
    i = rtf.rfind('\\par')
    i = rtf.rfind(' ', 0, i)
    i = rtf.find('\\',i)

    return ''.join((rtf[:i], text, rtf[i:]))

