#protocols.msn = S(
#       warnings = (
#                   dict(critical = False,
#                        checker = lambda info: info.password_len <= 16,
#                        text = _("Password should be 16 characters or less.")),
#                   dict(critical = True,
#                        checker = lambda info: info.remote_alias != info.plain_password if info.remote_alias else True,
#                        text = _("You can't have your password as your display name.")),
#                   ),
#   )
