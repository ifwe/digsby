#__LICENSE_GOES_HERE__
from collections import defaultdict
def mkdict(lines):
    d = defaultdict(list)
    state = 0
    for line in lines:
        if line.startswith("#: "):
            d['file'].append(line)
        elif line.startswith("#"):
            d['comments'].append(line)
        elif line.startswith("msgid"):
            d["msgid"].append(line)
            state = "msgid"
        elif line.startswith("msgstr"):
            d["msgstr"].append(line)
            state = "msgstr"
        elif state=="msgid":
            d["msgid"].append(line)
        else:
            assert state=="msgstr"
            d["msgstr"].append(line)
    return dict(d)

def build(lines):
    r = []
    cur = []
    for line in lines:
        if line == '\n':
            r.append(mkdict(cur))
            cur = []
        else:
            cur.append(line)
    return r

def run(filename):
    with open(filename, 'r') as f:
        r = build(f.readlines())
        r = [d for d in r if d.get('comments') and d.get('comments') != ["#, fuzzy\n"]]
    return sorted(r, key=lambda d: d.get('file'))

if __name__ == "__main__":
    r = run('digsby_en_LT.po')
    with open('commented.po', 'w') as f:
        def p(l):
            f.write(l)
        for d in r:
            for k in ('comments', 'file', 'msgid', 'msgstr'):
                if d.get(k):
                    for line in d[k]:
                        p(line)
            p('\n')

