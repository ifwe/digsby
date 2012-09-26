#protocols.aim = S(
#       warnings = (
#                   dict(critical = False,
#                        checker = lambda info: '@aim.com' not in info.name and '@aol.com' not in info.name,
#                        text = _('Screen name should not include "@aol.com" or "@aim.com".')),
#                   ),
#   )

#protocols.icq = S(
#       warnings = (
#                   dict(critical = False, checker = lambda info: info.password_len <= 8,
#                        text = _("Password should be 8 characters or less.")),
#                   ),
#   )
