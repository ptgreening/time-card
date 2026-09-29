import json, re, zipfile, shutil, datetime as dt
from collections import defaultdict, OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter as L

D=json.load(open('wk.json'))
f=lambda s: dt.datetime.strptime(s,'%Y-%m-%d %H:%M:%S')
P0,P1=[dt.date.fromisoformat(x) for x in D['period']]
LOC=D['location']; LUNCH={tuple(x) for x in D['day_lunch']}
# Which role an unpaid meal is charged against, in order of preference.
MEAL_ROLE_ORDER=['Actor','Crowd Control']
OUT=f'HauntedTrail-Week-Ending-{P1}.xlsx'

A='Arial'
HDR_F=PatternFill('solid',fgColor='1F3864'); TOT_F=PatternFill('solid',fgColor='D9E2F3')
ROLE_F=PatternFill('solid',fgColor='EAF3DE'); ODD_F=PatternFill('solid',fgColor='FFF2CC')
EDGE_F=PatternFill('solid',fgColor='FFE08A'); GRAND_F=PatternFill('solid',fgColor='1F3864')
TITLE=Font(name=A,size=14,bold=True); HDR=Font(name=A,size=10,bold=True,color='FFFFFF')
BASE=Font(name=A,size=10); BOLD=Font(name=A,size=10,bold=True)
INPUT=Font(name=A,size=10,color='0000FF'); MUTED=Font(name=A,size=9,color='808080')
RED=Font(name=A,size=10,bold=True,color='C00000'); WHITE=Font(name=A,size=11,bold=True,color='FFFFFF')
thin=Side(style='thin',color='BFBFBF'); BOX=Border(left=thin,right=thin,top=thin,bottom=thin)

# ── employee-days ─────────────────────────────────────────────
days=defaultdict(list)
for eid,name,role,i,o,lo in D['punches']:
    days[(name,eid,f(i).date())].append(dict(role=role,i=f(i),o=f(o)))
ROLES=sorted({p[2] for p in D['punches']})

rows=[]
for (name,eid,day),ss in sorted(days.items()):
    ss.sort(key=lambda s:s['i'])
    gaps=[(a['o'],b['i']) for a,b in zip(ss,ss[1:]) if b['i']>a['o']]
    brk=max(gaps,key=lambda g:g[1]-g[0]) if gaps else None
    gross=sum((s['o']-s['i']).total_seconds()/3600 for s in ss)
    ded=0.5 if (eid,day.isoformat()) in LUNCH else 0
    net=gross-ded
    # The unpaid meal comes off Actor, or Crowd Control where there is no Actor.
    # If that role is too short to absorb the whole break the remainder falls to
    # the next one, and anything still left is spread across the rest — so the
    # role columns always add up to what is actually paid.
    per={r:0.0 for r in ROLES}
    for s in ss: per[s['role']]+=(s['o']-s['i']).total_seconds()/3600
    left=ded
    for rl in MEAL_ROLE_ORDER:
        if left<=0: break
        if rl not in per: continue          # that role was not worked this day
        take=min(per[rl],left); per[rl]-=take; left-=take
    if left>1e-9:
        rest=sum(v for r,v in per.items() if v>0)
        if rest>0:
            for r in list(per):
                if per[r]>0: per[r]-=left*(per[r]/rest)
    rows.append(dict(name=name,eid=eid,day=day,segs=ss,gross=gross,ded=ded,net=net,per=per,
        cin=ss[0]['i'],cout=ss[-1]['o'],bo=brk[0] if brk else None,bi=brk[1] if brk else None,
        meal=1 if brk and (brk[1]-brk[0])>=dt.timedelta(minutes=30) else 0))

# ── column layout ─────────────────────────────────────────────
C={}; n=1
for key,title,w in ([('name','Employee',18),('date','Date',11),('dow','Day',6),
                     ('cin','Clock In',11),('bo','Break Out',11),('bi','Break In',11),('cout','Clock Out',11),
                     ('gross','Gross Hrs',9),('ded','Meal Deduct',9),('net','Net Hrs',9)]
                    +[(f'role{i}',r,13) for i,r in enumerate(ROLES)]
                    +[('meal','Meal?',7),('bmin','Break Mins',9),('bbeg','Break Began\n(hrs in)',11),
                      ('comp','Meal Break Compliance (CA)',40),('pen','Penalty Hrs',9),
                      ('over','Over By\n(minutes)',10),('ot','OT DAY',8)]):
    C[key]=(n,title,w); n+=1
col=lambda k: C[k][0]
ltr=lambda k: L(C[k][0])
NCOL=n-1
CALC={}
def put(ws,row,key,value,cached=None,font=BASE,fmt=None,align=None):
    c=ws.cell(row,col(key),value); c.font=font
    if fmt: c.number_format=fmt
    if align: c.alignment=Alignment(horizontal=align)
    c.border=BOX
    if cached is not None: CALC[(ws.title,f'{ltr(key)}{row}')]=cached
    return c

wb=Workbook(); wb.remove(wb.active)
def head(ws,row,keys):
    for k in keys:
        i,t,w=C[k]
        x=ws.cell(row,i,t); x.font=HDR; x.fill=HDR_F; x.border=BOX
        x.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        ws.column_dimensions[L(i)].width=w
    ws.row_dimensions[row].height=32

# ── Read Me ───────────────────────────────────────────────────
ws=wb.create_sheet('Read Me')
ws.column_dimensions['A'].width=3; ws.column_dimensions['B'].width=30; ws.column_dimensions['C'].width=88
ws['B2']=f'{LOC} — Hours for the week ending {P1:%B %d, %Y}'; ws['B2'].font=TITLE
ws['B3']=f'Pay period {P0:%A, %B %d} through {P1:%A, %B %d} · generated {dt.date.today():%B %d, %Y}'
ws['B3'].font=MUTED
r=5
def note(l,t,fo=BASE):
    global r
    ws.cell(r,2,l).font=BOLD
    c=ws.cell(r,3,t); c.font=fo; c.alignment=Alignment(wrap_text=True,vertical='top')
    ws.row_dimensions[r].height=max(14,13*(len(t)//97+1)); r+=1
note('Scope',f'{LOC} only. Shifts worked at other locations in this period are not included.')
note('Hours format','Decimal, two places. 7.50 means seven hours thirty minutes.')
note('Hours by role',f'One column per role worked: {", ".join(ROLES)}. They add up to Net Hrs on every row.')
note('By Role tab','The same hours the other way round — each role down the side, each person across, '
     'with a total per role at the bottom.')
note('Where a meal deduction lands','The unpaid half hour is charged against Actor, or against Crowd Control '
     'where there is no Actor time that day. If that role is too short to absorb it the remainder falls to the '
     'next, so the role columns always total what is actually paid. On a day with no deduction the role hours '
     'are exactly the time clocked in that role.')
note('Net hours','Time on the clock minus any unpaid break. Break Out and Break In show the longest gap between '
     'punches that day. Any gap is unpaid — the Meal? column says whether it was long enough to count as a meal.')
note('Day assignment','A shift belongs to the day it STARTED. One running past midnight stays on the day it began.')
r+=1
ws.cell(r,2,'MEAL BREAKS').font=Font(name=A,size=11,bold=True); r+=1
note('The rule','California Labor Code 512. A meal must be at least 30 uninterrupted minutes and must BEGIN '
     'before the end of the 5th hour of work.')
note('  Over 6 hours','Required and not waivable. None taken is a violation.')
note('  5 to 6 hours','Covered by the signed waiver every employee has, so it is not flagged.')
note('Penalty Hrs','One hour of pay per workday under Labor Code 226.7, capped at one per day.')
note('Over By (minutes)','How far past the line a violation is. Anything within 15 minutes is shaded amber.')
r+=1
note('Nothing held back','No open punches and no shift over 16 hours this period, so every day below is counted.')
note('Two rows to look at','See the Check These tab. Neither is a compliance problem — both look like test entries.',RED)
ws.sheet_view.showGridLines=False

# ── the week ──────────────────────────────────────────────────
ws=wb.create_sheet(f'Week ending {P1:%b %d}')
ws['A1']=f'{LOC} · {P0:%B %d} – {P1:%B %d, %Y}'; ws['A1'].font=TITLE
head(ws,3,list(C)); ws.freeze_panes='A4'
row=4; by=OrderedDict()
for x in rows: by.setdefault(x['name'],[]).append(x)
for name,recs in by.items():
    first=row
    for x in recs:
        put(ws,row,'name',name)
        put(ws,row,'date',x['day'],fmt='mm/dd/yyyy')
        put(ws,row,'dow',f"{x['day']:%a}",align='center')
        for k,v in (('cin',x['cin']),('bo',x['bo']),('bi',x['bi']),('cout',x['cout'])):
            if v: put(ws,row,k,v,font=INPUT,
                      fmt='mm/dd h:mm AM/PM' if v.date()!=x['day'] else 'h:mm AM/PM')
            else: put(ws,row,k,None)
        E,F,G,H=(ltr(k) for k in ('cin','bo','bi','cout'))
        put(ws,row,'gross',f'=IF({F}{row}="",({H}{row}-{E}{row})*24,({F}{row}-{E}{row})*24+({H}{row}-{G}{row})*24)',
            x['gross'],fmt='0.00',align='center')
        put(ws,row,'ded',x['ded'],font=INPUT,fmt='0.00',align='center')
        gr,dd=ltr('gross'),ltr('ded'); nt=ltr('net')
        put(ws,row,'net',f'={gr}{row}-{dd}{row}',x['net'],font=BOLD,fmt='0.00',align='center')
        for i,rl in enumerate(ROLES):
            v=x['per'][rl]
            c=put(ws,row,f'role{i}',round(v,4) if v else None,fmt='0.00',align='center')
            c.fill=ROLE_F
        put(ws,row,'meal',x['meal'],font=INPUT,align='center')
        bm,bb=ltr('bmin'),ltr('bbeg')
        put(ws,row,'bmin',f'=IF({F}{row}="","",({G}{row}-{F}{row})*1440)',
            '' if x['bo'] is None else (x['bi']-x['bo']).total_seconds()/60,fmt='0.00',align='center')
        put(ws,row,'bbeg',f'=IF({F}{row}="","",({F}{row}-{E}{row})*24)',
            '' if x['bo'] is None else (x['bo']-x['cin']).total_seconds()/3600,fmt='0.00',align='center')
        ml,cp,pn,ov=ltr('meal'),ltr('comp'),ltr('pen'),ltr('over')
        # Labor Code 512, applied in order: no break at all, button with no times,
        # a break too short to qualify, a qualifying break taken too late.
        mins=None if x['bo'] is None else (x['bi']-x['bo']).total_seconds()/60
        began=None if x['bo'] is None else (x['bo']-x['cin']).total_seconds()/3600
        if x['net']<=5: txt=''
        elif mins is None and x['ded']==0: txt='' if x['net']<=6 else 'VIOLATION - no meal taken, over 6 hrs'
        elif mins is None: txt='REVIEW - lunch button, no times recorded'
        elif mins<30: txt='' if x['net']<=6 else 'VIOLATION - longest break under 30 min, no qualifying meal'
        elif began>5: txt='VIOLATION - meal began after 5th hour'
        elif x['net']>12 and x['meal']<2: txt='VIOLATION - no 2nd meal, over 12 hrs'
        else: txt=''
        put(ws,row,'comp',
            f'=IF({nt}{row}<=5,"",'
            f'IF(AND({bm}{row}="",{dd}{row}=0),IF({nt}{row}<=6,"","VIOLATION - no meal taken, over 6 hrs"),'
            f'IF({bm}{row}="","REVIEW - lunch button, no times recorded",'
            f'IF({bm}{row}<30,IF({nt}{row}<=6,"","VIOLATION - longest break under 30 min, no qualifying meal"),'
            f'IF({bb}{row}>5,"VIOLATION - meal began after 5th hour",'
            f'IF(AND({nt}{row}>12,{ml}{row}<2),"VIOLATION - no 2nd meal, over 12 hrs",""))))))', txt)
        pen=1 if txt.startswith('VIOLATION') else 0
        put(ws,row,'pen',f'=IF(LEFT({cp}{row},9)="VIOLATION",1,0)',pen,font=RED,fmt='0',align='center')
        marg=''
        if pen:
            if 'over 6 hrs' in txt: marg=(x['net']-6)*60
            elif 'after 5th' in txt: marg=(began-5)*60
            elif 'under 30 min' in txt: marg=30-mins
        put(ws,row,'over',
            f'=IF({pn}{row}=0,"",'
            f'IF({cp}{row}="VIOLATION - no meal taken, over 6 hrs",({nt}{row}-6)*60,'
            f'IF({cp}{row}="VIOLATION - meal began after 5th hour",({bb}{row}-5)*60,'
            f'IF({cp}{row}="VIOLATION - longest break under 30 min, no qualifying meal",30-{bm}{row},""))))',
            marg,fmt='0.0',align='center')
        put(ws,row,'ot',f'=IF({nt}{row}>8,"OT","")','OT' if x['net']>8 else '',font=RED,align='center')
        row+=1
    put(ws,row,'name',f'TOTAL — {name}',font=BOLD)
    for k in ['gross','ded','net']+[f'role{i}' for i in range(len(ROLES))]+['pen']:
        s=sum(CALC.get((ws.title,f'{ltr(k)}{rr}'),0) or 0 for rr in range(first,row)) if k!='pen' else \
          sum(CALC.get((ws.title,f'{ltr("pen")}{rr}'),0) or 0 for rr in range(first,row))
        if k.startswith('role'):
            s=sum(ws.cell(rr,col(k)).value or 0 for rr in range(first,row))
        put(ws,row,k,f'=SUM({ltr(k)}{first}:{ltr(k)}{row-1})',s,
            font=BOLD if k=='net' else (RED if k=='pen' else BASE),
            fmt='0' if k=='pen' else '0.00',align='center')
    put(ws,row,'comp','Meal penalty hours owed ->',font=BOLD)
    put(ws,row,'ot',f'=IF({ltr("net")}{row}>40,"OVER 40","")',
        'OVER 40' if CALC[(ws.title,f'{ltr("net")}{row}')]>40 else '',font=RED,align='center')
    for i in range(1,NCOL+1):
        c=ws.cell(row,i); c.fill=TOT_F; c.border=BOX
    row+=2
ws.conditional_formatting.add(f'{ltr("over")}4:{ltr("over")}{row}',
    CellIsRule(operator='between',formula=['0.0001','15'],fill=EDGE_F))
ws.sheet_view.showGridLines=False
WEEK=ws.title

# ── By Role ───────────────────────────────────────────────────
ws=wb.create_sheet('By Role')
ws['A1']=f'Hours by role · {LOC} · week ending {P1:%B %d, %Y}'; ws['A1'].font=TITLE
ws['A2']='Net hours, after any meal deduction. Same numbers as the week sheet, grouped the other way.'
ws['A2'].font=MUTED
people=list(by)
ws.column_dimensions['A'].width=24
for i,_ in enumerate(people): ws.column_dimensions[L(2+i)].width=16
ws.column_dimensions[L(2+len(people))].width=14
hdr=['Role']+people+['TOTAL']
for i,t in enumerate(hdr,1):
    c=ws.cell(4,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
ws.row_dimensions[4].height=30
rr=5
for rl in ROLES:
    ws.cell(rr,1,rl).font=BOLD; ws.cell(rr,1).border=BOX
    for i,pn_ in enumerate(people):
        v=sum(x['per'][rl] for x in by[pn_])
        c=ws.cell(rr,2+i,round(v,2) if v else None); c.font=BASE
        c.number_format='0.00'; c.alignment=Alignment(horizontal='center'); c.border=BOX
    c=ws.cell(rr,2+len(people),round(sum(sum(x['per'][rl] for x in by[p]) for p in people),2))
    c.font=BOLD; c.number_format='0.00'; c.alignment=Alignment(horizontal='center'); c.border=BOX; c.fill=TOT_F
    rr+=1
ws.cell(rr,1,'TOTAL').font=WHITE; ws.cell(rr,1).fill=GRAND_F; ws.cell(rr,1).border=BOX
for i,pn_ in enumerate(people):
    c=ws.cell(rr,2+i,round(sum(x['net'] for x in by[pn_]),2))
    c.font=WHITE; c.fill=GRAND_F; c.number_format='0.00'
    c.alignment=Alignment(horizontal='center'); c.border=BOX
c=ws.cell(rr,2+len(people),round(sum(x['net'] for x in rows),2))
c.font=WHITE; c.fill=GRAND_F; c.number_format='0.00'
c.alignment=Alignment(horizontal='center'); c.border=BOX
ws.sheet_view.showGridLines=False

# ── Check These ───────────────────────────────────────────────
ws=wb.create_sheet('Check These')
ws['A1']='Worth a look — not compliance problems'; ws['A1'].font=TITLE
for i,(t,w) in enumerate([('Employee',18),('Date',12),('Net Hrs',10),('What stands out',74)],1):
    c=ws.cell(3,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center'); ws.column_dimensions[L(i)].width=w
rr=4
for x in rows:
    why=None
    if x['gross']<0.5: why=f"{x['gross']*60:.0f} minutes on the clock — looks like a test punch, not a shift."
    elif x['ded'] and x['gross']<2:
        why=(f"A 30-minute lunch was deducted from a {x['gross']*60:.0f}-minute shift, "
             f"leaving {x['net']:.2f} hrs. Check this was meant.")
    if not why: continue
    ws.cell(rr,1,x['name']).font=BASE
    c=ws.cell(rr,2,x['day']); c.number_format='mm/dd/yyyy'
    c=ws.cell(rr,3,round(x['net'],2)); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    ws.cell(rr,4,why).font=BASE
    for i in range(1,5): ws.cell(rr,i).border=BOX; ws.cell(rr,i).fill=ODD_F
    rr+=1
ws.sheet_view.showGridLines=False

# ── All Punches ───────────────────────────────────────────────
ws=wb.create_sheet('All Punches')
ws['A1']=f'Every punch recorded at {LOC} this period'; ws['A1'].font=TITLE
for i,(t,w) in enumerate([('Employee',18),('Role',16),('Clock In',22),('Clock Out',22),('Hours',10)],1):
    c=ws.cell(3,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center'); ws.column_dimensions[L(i)].width=w
ws.freeze_panes='A4'; rr=4
for eid,name,role,i_,o_,lo in sorted(D['punches'],key=lambda p:(p[1],p[3])):
    ws.cell(rr,1,name).font=BASE; ws.cell(rr,2,role).font=BASE
    for cc,v in ((3,f(i_)),(4,f(o_))):
        c=ws.cell(rr,cc,v); c.font=INPUT; c.number_format='mm/dd/yyyy h:mm AM/PM'
    c=ws.cell(rr,5,f'=(D{rr}-C{rr})*24'); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    CALC[(ws.title,f'E{rr}')]=(f(o_)-f(i_)).total_seconds()/3600
    for cc in range(1,6): ws.cell(rr,cc).border=BOX
    rr+=1
ws.sheet_view.showGridLines=False
wb.save(OUT)

# ── cache every formula result ────────────────────────────────
shutil.copy(OUT,'tmp.xlsx')
zin=zipfile.ZipFile('tmp.xlsx'); zout=zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED)
names={i+1:s.title for i,s in enumerate(wb)}; cached=0
for it in zin.infolist():
    data=zin.read(it.filename)
    m=re.fullmatch(r'xl/worksheets/sheet(\d+)\.xml',it.filename)
    if m:
        title=names.get(int(m.group(1))); xml=data.decode()
        def fix(cm):
            global cached
            ref,attrs,ftag=cm.group(1),cm.group(2),cm.group(3)
            v=CALC.get((title,ref))
            if v is None or v=='': return cm.group(0)
            cached+=1; attrs=re.sub(r'\s+t="[^"]*"','',attrs)
            if isinstance(v,str):
                e=v.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                return f'<c r="{ref}"{attrs} t="str">{ftag}<v>{e}</v></c>'
            return f'<c r="{ref}"{attrs}>{ftag}<v>{v!r}</v></c>'
        xml=re.sub(r'<c r="([A-Z]+\d+)"([^>]*)>(<f>.*?</f>)(?:<v\s*/>|<v>.*?</v>)?</c>',fix,xml,flags=re.S)
        data=xml.encode()
    zout.writestr(it,data)
zout.close(); zin.close()
print('roles :',ROLES)
print('sheets:',wb.sheetnames)
print('cached',cached,'formula results ->',OUT)
