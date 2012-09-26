import os
pathname = r'c:\workspace\Digsby'

# XXX: this isn't part of the program. it should get axed.
filecount = 0

from hashlib import md5

in3quotes = False

from time import clock
clock()

filesizes={}

bytecount = 0
for root, dirs, files in os.walk(pathname):
    if '.svn' in root:
        continue

    for file in files:

        if file.endswith('.py'):
            fname = os.path.join(root,file)
            filesizes[fname] = 0
            f = open(fname)
            for line in f:
                filesizes[fname] += 1
                continue
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                s1 = line.count('"""')
                s2 = line.count("'''")
                m1 = s1 % 2
                m2 = s2 % 2

                if s1 and m1 or s2 and m2:
                    in3quotes = not in3quotes

                if not in3quotes:
                    filesizes[fname] += 1
                else:
                    pass
            f.close()

duration = clock()
filesizes = sorted(filesizes.items(), key=lambda x:x[1])
sizes = [x[1] for x in filesizes]
files = [x[0] for x in filesizes]
total = sum(sizes)
max = sizes[-1]
min = sizes[0]
avg = total/len(sizes)
median = sizes[len(sizes)//2]

print 'Total   = %d' % (total,)
print 'Max     = %d (%s)' % (max, files[-1])
print 'Min     = %d (%s)' % (min, files[0])
print 'Avg     = %d' % (avg,)
print 'Med     = %d' % (median,)

print '=' * 80
n = 10
print 'Top %d files:' % n
for f,s in reversed(filesizes[-n:]):
    print '%4d lines\t\t%s' % (s,f)


