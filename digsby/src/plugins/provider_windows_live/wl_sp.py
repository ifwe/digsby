import hooks
import util.net as net

import services.service_provider as SP

#TODO: trac ticket #5018
class WindowsLiveServiceProvider(SP.EmailPasswordServiceProvider):
    pass


def validate(info, MSP, is_new):
    '''
    If user enters more than 16 characters for password, show a warning. Microsoft doesn't currently allow more than 16 chars for passwords,
    but legacy passwords may exist, so users must be allowed to enter them.

    For user safety, we also make sure they have not entered the same thing in their password and remote alias fields.
    '''
    valid = hooks.first('digsby.services.validate', info, MSP, is_new,
                        impl = "digsby_service_editor", raise_hook_exceptions = True)

    password = info.get('_real_password_')
    if password is not None:
        if len(password) > 16:
            raise SP.AccountException(_("Password should be 16 characters or less."), fatal = False)

    remote_alias = info.get('remote_alias')
    if remote_alias is not None:
        if password == remote_alias:
            raise SP.AccountException(_("You can't have your password as your display name."))

    return valid
