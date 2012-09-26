'''
Created on Aug 20, 2009

@author: Christopher
'''
def get_birthdays(bdays, now):
    import datetime
    today = datetime.date.fromtimestamp(now)
    new = {}
    for uid, d_ in bdays.items():
        bd = d_.get('birthday_date')
        if bd is not None:
            mdy = [None]*3
            vals = [int(i) for i in bd.split('/')]
            mdy[:len(vals)] = vals
            m, d, y = mdy
            bd_date_this = datetime.date(today.year, m, d)
            bd_date_next = datetime.date(today.year + 1, m, d)
            keep = False
            if -1 < (bd_date_this-today).days <= 7:
                keep = True
                bd_date = bd_date_this
            elif -1 < (bd_date_next-today).days <= 7:
                keep = True
                bd_date = bd_date_next
            if keep:
                new[uid] = dict(d_)
                new[uid]['bday'] = bd_date
                if y is not None:
                    born_on = datetime.date(y,m,d)
                    #I figure leap-year shouldn't matter, who d'you know that has been around the sun 1460+ times?
                    new[uid]['age'] = int(((bd_date - born_on).days + 1) / 365)

    return sorted(new.items(), key=lambda foo: foo[1]['bday'])
