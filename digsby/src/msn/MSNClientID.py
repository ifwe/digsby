class MSNCapabilities(object):
    CLIENT_MOBILE     = 0x00000001
    MSN_EXPLORER8     = 0x00000002
    INK_GIF           = 0x00000004
    INK_ISF           = 0x00000008
    WEBCAM            = 0x00000010
    MULTIPACKET_MSG   = 0x00000020
    CLIENT_MSNMOBILE  = 0x00000040
    CLIENT_MSNDIRECT  = 0x00000080
    CLIENT_WEB        = 0x00000200
    CLIENT_INTERNAL   = 0x00000800
    SPACES            = 0x00001000
    CLIENT_WINXPMCE   = 0x00002000
    DIRECT_IM         = 0x00004000
    WINKS             = 0x00008000
    MSN_SEARCH        = 0x00010000
    IS_BOT            = 0x00020000
    VOICE_CLIPS       = 0x00040000
    SECURE_IM         = 0x00080000
    SIP_INVITES       = 0x00100000
    SIP_TUNNEL        = 0x00200000
    FILE_SHARING      = 0x00400000
    ONE_CARE          = 0x01000000
    P2P_TURN          = 0x02000000
    P2P_UUN           = 0x04000000
    MSNC1             = 0x10000000
    MSNC2             = 0x20000000
    MSNC3             = 0x30000000
    MSNC4             = 0x40000000
    MSNC5             = 0x50000000
    MSNC6             = 0x60000000
    MSNC7             = 0x70000000
    MSNC8             = 0x80000000
    MSNC9             = 0x90000000
    MSNC10            = 0xA0000000
    MSNC11            = 0xB0000000
    MSNC12            = 0xC0000000
    MSNC13            = 0xD0000000
    MSNC14            = 0xE0000000

    num_to_str = {
                  0x00000001 : 'mobile',
                  0x00000002 : 'msn explorer 8',
                  0x00000004 : 'ink gif support',
                  0x00000008 : 'ink isf support',
                  0x00000010 : 'shared webcam',
                  0x00000020 : 'multipacket messaging',
                  0x00000040 : 'msn mobile device',
                  0x00000080 : 'msn direct',
                  0x00000200 : 'web based client',
                  0x00000800 : 'office live client',
                  0x00001000 : 'msn space',
                  0x00002000 : 'windows xp media center',
                  0x00004000 : 'direct im',
                  0x00008000 : 'recv winks',
                  0x00010000 : 'msn search',
                  0x00020000 : 'is bot',
                  0x00040000 : 'recv voice clips',
                  0x00080000 : 'secure channel communications',
                  0x00100000 : 'SIP invitations',
                  0x00200000 : 'sip tunnel',
                  0x00400000 : 'file sharing',
                  0x01000000 : 'one care',
                  0x02000000 : 'p2p turn',
                  0x04000000 : 'p2p uun',
                  0x10000000 : 'msnc1',
                  0x20000000 : 'msnc2',
                  0x30000000 : 'msnc3',
                  0x40000000 : 'msnc4',
                  0x50000000 : 'msnc5',
                  0x60000000 : 'msnc6',
                  0x70000000 : 'msnc7',
                  0x80000000 : 'msnc8',
                  0x90000000 : 'msnc9',
                  0xa0000000 : 'msnc10',
                  0xb0000000 : 'msnc11',
                  0xc0000000 : 'msnc12',
                  0xd0000000 : 'msnc13',
                  0xe0000000 : 'msnc14',
    }


class MSNCapabilitiesEx(object):
        NONE = 0x00
        IsSmsOnly = 0x01
        SupportsVoiceOverMsnp = 0x02
        SupportsUucpSipStack = 0x04
        SupportsApplicationMessages = 0x08
        RTCVideoEnabled = 0x10
        SupportsPeerToPeerV2 = 0x20
        IsAuthenticatedWebIMUser = 0x40
        Supports1On1ViaGroup = 0x80
        SupportsOfflineIM = 0x100
        SupportsSharingVideo = 0x200
        SupportsNudges = 0x400
        CircleVoiceIMEnabled = 0x800
        SharingEnabled = 0x1000
        MobileSuspendIMFanoutDisable = 0x2000
        _0x4000 = 0x4000
        SupportsPeerToPeerMixerRelay = 0x8000
        _0x10000 = 0x10000
        ConvWindowFileTransfer = 0x20000
        VideoCallSupports16x9 = 0x40000
        SupportsPeerToPeerEnveloping = 0x80000
        _0x100000 = 0x100000
        _0x200000 = 0x200000
        YahooIMDisabled = 0x400000
        SIPTunnelVersion2 = 0x800000
        VoiceClipSupportsWMAFormat = 0x1000000
        VoiceClipSupportsCircleIM = 0x2000000
        SupportsSocialNewsObjectTypes = 0x4000000
        CustomEmoticonsCapable = 0x8000000
        SupportsUTF8MoodMessages = 0x10000000
        FTURNCapable = 0x20000000
        SupportsP4Activity = 0x40000000
        SupportsMultipartyConversations = 0x80000000

        num_to_str = {0x00000001: 'IsSmsOnly',
                      0x00000002: 'SupportsVoiceOverMsnp',
                      0x00000004: 'SupportsUucpSipStack',
                      0x00000008: 'SupportsApplicationMessages',
                      0x00000010: 'RTCVideoEnabled',
                      0x00000020: 'SupportsPeerToPeerV2',
                      0x00000040: 'IsAuthenticatedWebIMUser',
                      0x00000080: 'Supports1On1ViaGroup',
                      0x00000100: 'SupportsOfflineIM',
                      0x00000200: 'SupportsSharingVideo',
                      0x00000400: 'SupportsNudges',
                      0x00000800: 'CircleVoiceIMEnabled',
                      0x00001000: 'SharingEnabled',
                      0x00002000: 'MobileSuspendIMFanoutDisable',
                      0x00004000: '_0x4000',
                      0x00008000: 'SupportsPeerToPeerMixerRelay',
                      0x00010000: '_0x10000',
                      0x00020000: 'ConvWindowFileTransfer',
                      0x00040000: 'VideoCallSupports16x9',
                      0x00080000: 'SupportsPeerToPeerEnveloping',
                      0x00100000: '_0x100000',
                      0x00200000: '_0x200000',
                      0x00400000: 'YahooIMDisabled',
                      0x00800000: 'SIPTunnelVersion2',
                      0x01000000: 'VoiceClipSupportsWMAFormat',
                      0x02000000: 'VoiceClipSupportsCircleIM',
                      0x04000000: 'SupportsSocialNewsObjectTypes',
                      0x08000000: 'CustomEmoticonsCapable',
                      0x10000000: 'SupportsUTF8MoodMessages',
                      0x20000000: 'FTURNCapable',
                      0x40000000: 'SupportsP4Activity',
                      0x80000000: 'SupportsMultipartyConversations'}

def parse_client_id(num):
    '''
    Take the stupid msn client id and turn it into a string

    @param num:    the client id to parse.
    @returns:      a string containing all of the properties based on the above
                   dictionary.
    '''

    try:
        caps_basic = int(num)
        caps_ex = 0
    except ValueError:
        caps_basic, caps_ex = map(int, str(num).split(':', 1))

    to_str = lambda i, cls: ', '.join(cls.num_to_str[k] for k in cls.num_to_str if k & i == k)
    basic_str = to_str(caps_basic, MSNCapabilities)
    ex_str = to_str(caps_ex, MSNCapabilitiesEx)

    return ' : '.join(filter(None, [basic_str, ex_str]))

IM_DEFAULT_CAPABILITIES = (MSNCapabilities.MSNC11 |
                           MSNCapabilities.SIP_INVITES |
                           MSNCapabilities.DIRECT_IM |
                           MSNCapabilities.MULTIPACKET_MSG |
                           MSNCapabilities.WINKS |
                           0
                           )
IM_DEFAULT_CAPABILITIES_EX = (
                              MSNCapabilitiesEx.Supports1On1ViaGroup |
#                              MSNCapabilitiesEx.ConvWindowFileTransfer |
                              MSNCapabilitiesEx.SupportsOfflineIM |
                              MSNCapabilitiesEx.SupportsNudges |
                              MSNCapabilitiesEx.SupportsUTF8MoodMessages |
                              MSNCapabilitiesEx.SupportsMultipartyConversations |
                              MSNCapabilitiesEx.SupportsSocialNewsObjectTypes |
#                              MSNCapabilitiesEx._0x10000 |
#                              MSNCapabilitiesEx._0x4000 |
#                              MSNCapabilitiesEx._0x100000
                              MSNCapabilitiesEx.ConvWindowFileTransfer |
                              0
                              )

PE_DEFAULT_CAPABILITIES = 0
PE_DEFAULT_CAPABILITIES_EX = (MSNCapabilitiesEx.SupportsP4Activity |
                              MSNCapabilitiesEx.SupportsPeerToPeerEnveloping |
                              MSNCapabilitiesEx.SupportsPeerToPeerMixerRelay |
                              MSNCapabilitiesEx.SupportsPeerToPeerV2 |
                              MSNCapabilitiesEx.ConvWindowFileTransfer |
                              0
                              )

