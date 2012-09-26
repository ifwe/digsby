from string import digits
digits_set = frozenset(digits)

SMS_MAX_LENGTH = 135

def normalize_sms(sms_number):
    '''
    Returns a consistent form for an SMS number.

    Raises ValueError if the sms number is not valid.
    '''

    sms_number = str(sms_number).translate(None, ' ()-.+')

    if not all(s in digits_set for s in sms_number):
        raise ValueError('invalid sms number: ' + repr(sms_number))

    if len(sms_number) == 10:
        sms_number = '1' + sms_number

    elif len(sms_number) != 11:
        raise ValueError('invalid sms number: ' + repr(sms_number))

    return sms_number

def validate_sms(n):
    try:
        normalize_sms(n)
    except ValueError:
        return False
    else:
        return True

