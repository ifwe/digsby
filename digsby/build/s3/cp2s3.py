#__LICENSE_GOES_HERE__
'''
copies files and directories to an S3 bucket
'''

from time import time, mktime
from threading import Thread
from cStringIO import StringIO
from traceback import print_exc
from datetime import datetime
from gzip import GzipFile
from optparse import OptionParser
from Queue import Queue

import mimetypes
import os
import os.path

import S3

mimetypes.add_type("application/x-xpinstall", ".xpi")

DEFAULT_NUM_THREADS = 30

# Note: On Unix platforms, sockets are also file handles,
# so we'll end up getting a 'too many open file handles' error
# if the number of threads is set to high
if not os.name == 'nt':
    DEFAULT_NUM_THREADS = 5

def options_parser():
    parser = OptionParser()
    opt = parser.add_option

    opt('-v', '--verbose', action = 'store_true')
    opt('-y', '--dry-run', action = 'store_true')

    opt('-d', '--digest', action = 'store_true', dest = 'save_hash')
    opt('-k', '--key')
    opt('-s', '--secret')
    opt('-b', '--bucket')

    opt('-c', '--compress', action = 'append')
    opt('-a', '--compress-all', action = 'store_true')
    opt('-m', '--mimetypes', action = 'store_true')
    opt('-p', '--public-read', action = 'store_true')
    opt('-z', '--size', action = 'store_true', dest = 'save_size')
    opt('-t', '--time', action = 'store_true', dest = 'save_time')
    opt('-r', '--recursive', action = 'store_true')

    opt('--threads', type = 'int')

    parser.set_defaults(threads = DEFAULT_NUM_THREADS)
    return parser

def check_opts(parser, opts, args):
    if opts.bucket is None:
        parser.error('please specify a bucket with -b or --bucket')
    if opts.key is None:
        parser.error('please specify an API key with -k or --key')
    if opts.secret is None:
        parser.error('please specify an API secret with -s or --secret')

    # rest of the args are paths to files or directories to upload
    if not args:
        parser.error('please specify one or more files or directories to upload')
    else:
        for filepath in args:
            if not os.path.exists(filepath):
                parser.error('file or directory does not exist: %s' % filepath)

def utc_mtime(filename):
    file_mtime = os.path.getmtime(filename)
    return int(mktime(datetime.utcfromtimestamp(file_mtime).timetuple()))

def should_compress(filename):
    '''With --compress-all, --compress "extension" means "don't compress."'''

    filepart, extension = os.path.splitext(filename)
    if extension.startswith('.'):
        extension = extension[1:]

    return bool(opts.compress_all) ^ (extension in opts.compress)

def _upload_file(conn, bucket, filename):
    filedata = open(filename, 'rb').read()
    headers = {}

    if opts.save_size:
        headers.update({'x-amz-meta-size': str(os.path.getsize(filename))})

    if opts.save_hash:
        headers.update({'x-amz-meta-sha1_hash': hashlib.sha1(filedata).hexdigest()})

    if opts.public_read:
        headers.update({'x-amz-acl': 'public-read'})

    if opts.save_time:
        headers.update({'x-amz-meta-mtime': str(utc_mtime(filename))})

    if opts.mimetypes:
        mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype is not None:
            headers.update({'Content-Type': mimetype})

    compressed = should_compress(filename)
    if compressed:
        headers.update({'Content-Encoding': 'gzip'})
        origdata, filedata = filedata, gzip(filedata)

    compressed_info = (' compressed from %d bytes' % len(origdata)) if compressed else ''
    log(' -> %s (%d bytes%s)' % (filename, len(filedata), compressed_info))

    if not opts.dry_run:
        for x in xrange(5):
            try:
                resp = conn.put(bucket, filename, filedata, headers)
            except Exception, e:
                log(' Error on %r: %r' % (filename, e))
                continue

            log(' <- %s %s' % (filename, resp.message))
            if resp.http_response.status == 200:
                break
        else:
            raise AssertionError('could not upload %r' % filename)

def enqueue(queue, filename):
    count = 0
    if os.path.isdir(filename):
        if opts.recursive:
            for f in os.listdir(filename):
                count += enqueue(queue, os.path.join(filename, f).replace('\\', '/'))
    elif os.path.isfile(filename):
        queue.put(filename)
        count += 1
    else:
        raise AssertionError('not a file and not a dir: %r' % filename)

    return count

def log(msg):
    if opts.verbose:
        print msg

def gzip(s):
    f = StringIO()
    g = GzipFile(mode='wb', fileobj=f)
    g.write(s)
    g.close()
    return f.getvalue()

def handle_options():
    global opts
    parser = options_parser()
    opts, args = parser.parse_args()

    check_opts(parser, opts, args)
    opts.compress = set(opts.compress or [])
    return args

class S3UploadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue
        self.error = None

    @property
    def conn(self):
        try:
            return self._conn
        except AttributeError:
            self._conn = S3.AWSAuthConnection(opts.key, opts.secret)
            return self._conn

    def run(self):
        try:
            while True:
                filepath = self.queue.get()
                try:
                    _upload_file(self.conn, opts.bucket, filepath)
                finally:
                    self.queue.task_done()
        except Exception, e:
            print repr(e)
            print_exc()
            os._exit(1) # quit on any errors

def upload_file(file):
    return upload_files([file])

def upload_files(files):
    requests = Queue()

    num_files = sum(enqueue(requests, filepath) for filepath in files)
    log('uploading %d files' % num_files)
    S3UploadWorker.total = num_files

    pool = []
    for x in xrange(min(requests.qsize(), opts.threads)):
        t = S3UploadWorker(requests)
        t.setDaemon(True)
        pool.append(t)

    for t in pool:
        t.start()

    requests.join()

def main():
    args = handle_options()
    timetook = timeit(lambda: upload_files(args))
    print 'took %ss' % timetook

def timeit(func):
    before = time()
    func()
    return time() - before

if __name__ == '__main__':
    main()
