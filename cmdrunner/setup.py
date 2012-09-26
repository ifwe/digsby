from setuptools import setup

setup(
    name = "cmdrunner",
    entry_points = {'zc.buildout': ['default = cmdrunner:Cmd', 'py = cmdrunner:Python'],
                    'zc.buildout.uninstall': ['default = cmdrunner:uninstallCmd']}
)
