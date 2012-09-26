import time
from random import randint

def main():

    from threading import Thread, currentThread

    def foo():
        for i in xrange(1000):
            time.sleep(randint(100,1000) / 1000)
            t = currentThread()
            t._mycount += 1
            print t.getName(), t._mycount

    threads = []

    for x in xrange(5):
        t = Thread(target = foo)
        t._mycount = 0
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()