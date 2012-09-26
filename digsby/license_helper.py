import sys
import path
import logging
log = logging.getLogger()


class QuitException(Exception):
    pass


def parse_extensions(ext_string):
    try:
        exts = map(str.strip, ext_string.split(','))
    except ValueError as e:
        log.error('Error parsing extensions %r: %r', ext_string, e)
        exts = []

    if len(exts) == 0:
        log.info('No extensions provided.')
        exts = None

    return exts


def prompt_extensions():
    extensions = raw_input("Enter comma-separated list of extensions to use. (e.g., py,js): ")
    return parse_extensions(extensions)


def parse_license_file(license_filename):
    license_path = path.path(license_filename)

    if not license_path.isfile():
        log.error('File not found: %s', license_path)
        return None
    return license_path


def prompt_license_file():
    return parse_license_file(raw_input("Enter path to license file: "))


def parse_directory(dir_str):
    dir_path = path.path(dir_str).abspath()
    if not dir_path.isdir():
        log.error('Directory not found: %s', dir_path)
        dir_path = None

    return dir_path


def prompt_directory():
    return parse_directory(raw_input("Enter directory path to walk: "))


def get_file_options():
    return [x[0] for x in get_file_options_help()]


def get_file_options_help():
    return [
        'y      Yes - Add license to file',
        'n      No - Do not add license to file',
        'm      More - print more file content',
        'q      Quit - Stop looking at files and exit',
        '?      Help - Print this help message',
    ]


def prompt_file(fname, fcontent):
    print 'file: %s' % fname
    lines = fcontent.splitlines()
    lines_offset = 0
    line_count = 5

    print_lines = True
    while True:
        if print_lines:
            if lines_offset == 0:
                print 'First %d lines:' % line_count
            print '\n'.join(lines[lines_offset:lines_offset + line_count])
            lines_offset += line_count
            print_lines = False

        response = raw_input(
            "Add license to the top of this file? [%s]: "
            % ','.join(get_file_options())
        )

        if response in ('y', 'n', 'q'):
            return response

        if response == 'm':
            print_lines = True
            continue

        if response == '?':
            print '\n'.join(get_file_options_help())

        # unknown input, we'll loop around again


def write_license_to_file(license, filename):
    file_content = filename.text()
    with open(filename, 'w') as f:
        f.write(license)
        if not license.endswith('\n'):
            f.write('\n')
        f.write(file_content)


def do_extension(directory, ext, license_content):
    pattern = '*.' + ext

    for source_file in directory.walk(pattern):
        source_content = source_file.text()
        if len(source_content.strip()) == 0:
            log.info('Skipping file, empty content (file = %s)', source_file)
            continue

        if source_content.startswith(license_content.strip()):
            log.info('Skipping file, already has license header (file = %s)', source_file)
            continue

        response = None
        while not response:
            response = prompt_file(source_file, source_content)

        if response == 'y':
            write_license_to_file(license_content, source_file)
        elif response == 'n':
            continue
        elif response == 'q':
            raise QuitException
    log.info("Done with %r files in %s", ext, directory)


def main(directory='', license_file=None, extensions='', verbose=False):
    if verbose:
        log.setLevel(1)

    if extensions:
        extensions = parse_extensions(extensions)
    while not extensions:
        extensions = prompt_extensions()

    if license_file:
        license_file = parse_license_file(license_file)

    while not license_file:
        license_file = prompt_license_file()

    license_content = license_file.text()
    log.debug("Using license content:")
    log.debug(license_content)

    if not directory:
        directory = '.'

    directory = parse_directory(directory)
    while not directory:
        directory = prompt_directory()

    for ext in extensions:
        try:
            do_extension(directory, ext, license_content)
        except QuitException:
            break


if __name__ == '__main__':
    logging.basicConfig()
    import argparse
    parser = argparse.ArgumentParser("License header helper")
    parser.add_argument('--license', dest='license_file', default='LICENSE', help='The content to be placed in each approved file')
    parser.add_argument('--ext', dest='extensions', default='py', help='Comma-separated list of extensions to use. e.g.: py,js')
    parser.add_argument('--dir', dest='directory', default='.', help='Directory to walk')
    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False)
    args = parser.parse_args(sys.argv[1:])
    main(**vars(args))
