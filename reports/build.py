import json, datetime as dt
from collections import defaultdict

P = json.load(open('punches.json'))
f = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M:%S') if s else None

# Button-lunch records from tc_day_flags: (employee_id, date) -> lunch taken
DAY_LUNCH = {('msf3nu2tij3pcv04md','2026-08-05'): True,
             ('msf3nu2tij3pcv04md','2026-08-13'): False,
             ('msryihzikzvq0wuzugm','2026-08-14'): True}

REVIEW_HRS = 16          # a span longer than this is treated as a missed clock-out
MEAL_GAP   = dt.timedelta(minutes=30)

segs = []
for pid, eid, name, role, loc, i, o, lunch_out in P:
    i, o = f(i), f(o)
    hrs = (o - i).total_seconds()/3600 if o else None
    segs.append(dict(id=pid, eid=eid, name=name, role=role, loc=loc, i=i, o=o,
                     lunch_out=lunch_out, hrs=hrs,
                     bad=(o is None) or hrs > REVIEW_HRS,
                     why='Never clocked out' if o is None else
                         (f'{hrs:.1f} hour span — clock-out almost certainly missed' if hrs > REVIEW_HRS else '')))

# Group by employee and the calendar day the shift STARTED on.
days = defaultdict(list)
for s in segs:
    days[(s['name'], s['eid'], s['i'].date())].append(s)

rows = []
for (name, eid, d), ss in sorted(days.items()):
    ss.sort(key=lambda s: s['i'])
    bad = [s for s in ss if s['bad']]
    r = dict(name=name, eid=eid, date=d, segs=ss, nseg=len(ss), review=bool(bad),
             why='; '.join(dict.fromkeys(s['why'] for s in bad)) if bad else '',
             clock_in=ss[0]['i'], clock_out=ss[-1]['o'],
             meal_out=None, meal_in=None, note='')
    # Meal = an explicit lunch clock-out, else any gap of 30 min or more.
    for a, b in zip(ss, ss[1:]):
        if a['o'] and (a['lunch_out'] or (b['i'] - a['o']) >= MEAL_GAP):
            r['meal_out'], r['meal_in'] = a['o'], b['i']
            break
    r['button_lunch'] = DAY_LUNCH.get((eid, d.isoformat()), False)
    if not r['review']:
        r['gross'] = sum(s['hrs'] for s in ss)
        if len(ss) > 2:
            r['note'] = f"{len(ss)} separate punches this day"
    else:
        r['gross'] = None
    rows.append(r)

# Pay periods run Tuesday -> Monday.
def period_start(d):
    return d - dt.timedelta(days=(d.weekday() - 1) % 7)   # Monday=0, so Tuesday=1

periods = defaultdict(list)
for r in rows:
    periods[period_start(r['date'])].append(r)

print(f"{len(rows)} employee-days across {len(periods)} pay periods\n")
for ps in sorted(periods):
    rs = periods[ps]
    ok  = [r for r in rs if not r['review']]
    rev = [r for r in rs if r['review']]
    tot = sum(r['gross'] - (0.5 if r['button_lunch'] else 0) for r in ok)
    print(f"  {ps:%b %d} - {ps+dt.timedelta(days=6):%b %d}  "
          f"{len(rs):2} days ({len(rev)} held) {len(set(r['name'] for r in rs))} staff  {tot:6.2f} net hrs")
mx = max(r['nseg'] for r in rows if not r['review'])
print(f"\nmax punches in a single payable day: {mx}")
json.dump([{**r, 'date': r['date'].isoformat(),
            'clock_in': r['clock_in'].isoformat(),
            'clock_out': r['clock_out'].isoformat() if r['clock_out'] else None,
            'meal_out': r['meal_out'].isoformat() if r['meal_out'] else None,
            'meal_in': r['meal_in'].isoformat() if r['meal_in'] else None,
            'segs': [{**s, 'i': s['i'].isoformat(), 'o': s['o'].isoformat() if s['o'] else None} for s in r['segs']]}
           for r in rows], open('days.json','w'), indent=0)
