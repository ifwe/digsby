import optparse
import sys

# TODO: switch to argparse? optparse is deprecated in later versions of python
# and the switch to argparse is very straightforward.

class NonExitingOptionParser(optparse.OptionParser):
    def exit(self, code = None, message = None):
        if code is None and message is None:
            # --help calls exit() with no arguments
            return optparse.OptionParser.exit(self, code, message)

        print >>sys.stderr, "Error processing options: code = %r, message = %r" % (code, message)

parser = NonExitingOptionParser(prog="Digsby",
                                version="%%prog r%s" %
                                getattr(sys, "REVISION", 'dev'))
parser.add_option('--noautologin',
                  action="store_false",
                  dest='autologin',
                  help="Disable autologin of Digsby")

parser.add_option('--noautologin-accounts',
                  '--noautologin_accounts',
                  action="store_false",
                  dest='autologin_accounts',
                  help="Disable autologin of accounts")

parser.add_option('--measure', type='string', help='Measure timings of certain actions')

parser.add_option('--register',
                  action='store_true',
                  help = 'Show the register page on startup')

# This is an override for dev mode. non-dev will always attempt to load portable settings.
parser.add_option('--portable',
                  action='store_true',
                  dest = 'allow_portable',
                  help = 'Allows the program to load info for "portable" mode')

parser.add_option('--username', help = 'Username to login with')
parser.add_option('--password', help = 'Password to login with')
parser.add_option('--resource', help = 'Resource to login with')

parser.add_option('--lang',
                  '--language',
                  dest = 'lang',
                  help = 'Language code (i.e., es_DO) to show interface in')

parser.set_defaults(autologin=True,
                    autologin_accounts=True,
                    register = False,
                    allow_portable = False)

parser.add_option('--action')

#===============================================================================
# Behavioral
#===============================================================================
behave_group = optparse.OptionGroup(parser, 'Behavioral Options')
behave_group.add_option('--multi',
                        action = 'store_false',
                        dest = 'single_instance',
                        help = 'disable single-instance checker')
behave_group.add_option('--single',
                        action = 'store_true',
                        dest = 'single_instance',
                        help = 'enable single-instance checker on dev')
behave_group.add_option('--start-offline', '--offline',
                        action = 'store_true',
                        dest = 'start_offline',
                        help = 'forces the initial login to be an offline one. (only works in DEV mode)')
behave_group.add_option('--server',
                        help = 'adds a server to the start login sequence')
behave_group.add_option('--loadbalancer',
                        help = 'forces digsby to use a specific load balancer')

parser.set_defaults(start_offline = False)
#===============================================================================
# Debugging
#===============================================================================
debug_group = optparse.OptionGroup(parser, 'Debugging Options')
debug_group.add_option('--profile',
                       type='int',
                       help="profiling level [default: %default]")
debug_group.add_option('--profile1',
                       action='store_const',
                       const=1,
                       dest='profile',
                       help="profiling level 1")
debug_group.add_option('--profile2',
                       action='store_const',
                       const=2,
                       dest='profile',
                       help="profiling level 2")
debug_group.add_option('--nocpuwatch', '--no-cpuwatch',
                       action="store_false",
                       dest='cpuwatch',
                       help="disable CPUWatch")
debug_group.add_option('--no-force-exit',
                       action='store_false',
                       dest='force_exit',
                       help='disable forceful exit if Digsby hangs on quit')
debug_group.add_option('--quickexit',
                       action='store_true',
                       help='always exit forcefully')
debug_group.add_option('--full-crashdump',
                        action = 'store_true',
                        dest = 'full_crashdump',
                        help = 'enable full crash dumps')
debug_group.add_option('--crashdump-dir',
                       dest = 'crashdump_dir',
                       help = 'specify the directory crash dumps will be saved to')
debug_group.add_option('--no-crashsubmit',
                       action = 'store_false',
                       dest = 'submit_crashdump',
                       help = 'disable crash minidump submission')
debug_group.add_option('--color',
                       action='store_true',
                       dest='console_color',
                       help='enable color console output')
debug_group.add_option('--no-plugins','--no_plugins',
                       action='store_false',
                       dest='load_plugins',
                       help='disable plugin loading')
debug_group.add_option('--no-traceback-dialog',
                       action='store_false',
                       dest='traceback_dialog',
                       help='disables the traceback dialog')
debug_group.add_option('--heapy',
                       action='store_true',
                       dest='heapy',
                       help='enables Heapy on the console')
debug_group.add_option('--track-windowids',
                       action='store_true',
                       dest='track_windowids',
                       help='sends window id allocation locations in bug reports')
debug_group.add_option('--debugads',
                       action='store_true',
                       help='logs more information about ads being loaded')


parser.set_defaults(profile=0,
                    cpuwatch=True,
                    force_exit=True,
                    submit_crashdump=True,
                    console_color=False,
                    load_plugins=True,
                    traceback_dialog=True,
                    heapy=False,
                    track_windowids=False,
                    debugads=False)

#===============================================================================
# Logging
#===============================================================================
logging_group = optparse.OptionGroup(parser, 'Logging Options')

logging_group.add_option('-v', '--verbose',
                       '--full-log',
                       '--full_log',
                       dest='full_log',
                       action='store_true',
                       help='Tells the logger to log everything.  '
                            'Disables the hiding (from the logger) of many '
                            'possibly sensitive pieces of information, '
                            'such as IM messages and the contents of streams to the server.  '
                            'WARNING: increases CPU and disk activity.  '
                            '[default: %default]')

logging_group.add_option('--no-log',
                       dest = 'no_log',
                       action= 'store_true',
                       help = 'Tells the logger to log nothing.')

logging_group.add_option('--no-log-limit',
                         dest='limit_log',
                         action='store_false',
                         help='The log will not be rate limited on stdout.')

logging_group.add_option('--release-logging',
                         dest='release_logging',
                         action='store_true')

logging_group.add_option('--log-buffer',
                         type='int',
                         dest='log_buffer',
                         help='The number of log messages to keep in memory before writing to disk')

parser.set_defaults(full_log=False,
                    limit_log=True,
                    release_logging=False,
                    log_buffer=0)

#===============================================================================
# Update
#===============================================================================
update_group = optparse.OptionGroup(parser,
                                    'Update Options',
                                    "Options dealing with behavior "
                                    "after an update.")

update_group.add_option('--force-update',
                        action = 'store_true',
                        dest = 'force_update',
                        help = 'Force an update & integrity check of application files')
update_group.add_option('--updated',
                        action="store_true",
                        help="Update Successful")

update_group.add_option('--norestart', '--no-restart', '--no_restart',
                        action="store_false",
                        dest="do_restart",
                        help="disable restart after an update")
update_group.add_option('--noupdate',
                        '--no-update',
                        '--no_update',
                        action='store_false',
                        dest='allow_update',
                        help='disable update check')

update_group.add_option('--update_failed',
                        action = 'store_true',
                        dest = 'update_failed',
                        help = 'signifies an update has failed to be installed')

update_group.add_option('--updatetag')

parser.set_defaults(updated=False,
                    do_restart=True,
                    force_update = False,
                    allow_update = True,
                    update_failed = False,
                    updatetag = None)

#===============================================================================
# Reflexive
#===============================================================================
reflexive_group = optparse.OptionGroup(parser, 'Reflexive Options',
                    "Options designed for Digsby to call itself with.  "
                    "It is believed that some of them bite.")
reflexive_group.add_option('--crashreport', type="string")
reflexive_group.add_option('--crashuser', type='string')
reflexive_group.add_option('--crashuniquekey', type='string')
reflexive_group.add_option('--no-crashreport', action = 'store_false', dest = 'crashreporting')

parser.set_defaults(crashreporting = True)

#===============================================================================
# plura
#===============================================================================
plura_group = optparse.OptionGroup(parser, 'Plura options',
                                   "These options are to cause the app to set/unset plura processing. "
                                   "Pretty much only used for the installer to pass in the user's choice.")
plura_group.add_option('--set-plura-enabled', action = 'store_true', dest = 'set_plura_option')
plura_group.add_option('--set-plura-disabled', action = 'store_false', dest = 'set_plura_option')

parser.set_defaults(set_plura_option = None)

#===============================================================================
# twitter
#===============================================================================
twitter_group = optparse.OptionGroup(parser, 'Twitter Options')
twitter_group.add_option('--dbsnapshot', type='string')
twitter_group.add_option('--savesnapshots', action='store_true')

parser.set_defaults(twitter_offline=False,
                    dnsnapshot='',
                    savesnapshots=False)

#===============================================================================
# no-op
#===============================================================================

noop_group = optparse.OptionGroup(parser, 'No-ops',
                                  description =
                                  "quiets some problems when running unit tests")

noop_group.add_option('--verbosity', action='store')

#===============================================================================
# Option group ordering
#===============================================================================
parser.add_option_group(behave_group)
parser.add_option_group(debug_group)
parser.add_option_group(logging_group)
parser.add_option_group(update_group)
parser.add_option_group(reflexive_group)
parser.add_option_group(plura_group)
parser.add_option_group(twitter_group)
parser.add_option_group(noop_group)

if __name__=="__main__":
    parser.print_help()
    print parser.parse_args()

