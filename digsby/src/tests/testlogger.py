from __future__ import with_statement
from util import Storage as S
from path import path
from calendar import Calendar
from random import randrange, shuffle
from datetime import datetime

def generate_random():
    'Generates a years worth of random logs.'

    p = path('c:\\test')

    words = 'foo bar to be or not the and apple orange banana cherry futon proleptic gregorian ordinal'.split()

    cal = Calendar()

    for month in xrange(1, 12):
        for day in cal.itermonthdates(2007, month):

            messages = []
            for x in xrange(2, randrange(20, 50)):
                shuffle(words)

                messages.append(
                    S(buddy     = S(name = 'digsby0%d' % randrange(1, 3)),
                      timestamp = random_time_in_day(day),
                      message   = ' '.join(words[:randrange(1, len(words)+1)])))

            messages.sort(key = lambda mobj: mobj['timestamp'])

            daylog = p / (day.isoformat() + '.html')

            with daylog.open('w') as f:
                f.write(html_header % dict(title = 'IM Logs with %s on %s' % ('digsby0%d' % randrange(1, 3), day.isoformat())))

                for mobj in messages:
                    f.write(generate_output_html(mobj))

def random_time_in_day(day):
    return datetime(day.year, day.month, day.day, randrange(0, 24), randrange(0, 60), randrange(0, 60))
