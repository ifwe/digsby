This directory holds any third-party modules that have C/C++ extensions
or platform-specific components and thus can't be shared across
platforms. Nothing should be put into this root dir, and you should
never put platlib itself on the PYTHONPATH, only the subdirs matching
your platform.
