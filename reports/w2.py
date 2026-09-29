import json, re, zipfile, shutil, datetime as dt
from collections import defaultdict, OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter as L

D=json.load(open('w2.json'))
f=lambda s: dt.datetime.strptime(s,'%Y-%m-%d %H:%M:%S')
P0,P1=[dt.date.fromisoformat(x) for x in D['period']]
LOC=D['location']; LUNCH={tuple(x) for x in D['day_lunch']}
MEAL_ROLE_ORDER=['Actor','Crowd Control','Lines/Crowd Control']
MEAL_MIN=30       # a gap at least this long can count as a meal
SPLIT_MIN=120     # a gap this long is going home and coming back, not a break

A='Arial'
HDR_F=PatternFill('solid',fgColor='1F3864'); TOT_F=PatternFill('solid',fgColor='D9E2F3')
ROLE_F=PatternFill('solid',fgColor='EAF3DE'); ODD_F=PatternFill('solid',fgColor='FFF2CC')
EDGE_F=PatternFill('solid',fgColor='FFE08A'); GRAND=PatternFill('solid',fgColor='1F3864')
TITLE=Font(name=A,size=14,bold=True); HDR=Font(name=A,size=10,bold=True,color='FFFFFF')
BASE=Font(name=A,size=10); BOLD=Font(name=A,size=10,bold=True)
INPUT=Font(name=A,size=10,color='0000FF'); MUTED=Font(name=A,size=9,color='808080')
RED=Font(name=A,size=10,bold=True,color='C00000'); AMB=Font(name=A,size=10,bold=True,color='9A6700')
WHITE=Font(name=A,size=11,bold=True,color='FFFFFF')
thin=Side(style='thin',color='BFBFBF'); BOX=Border(left=thin,right=thin,top=thin,bottom=thin)
CALC={}

# ── shape the week ────────────────────────────────────────────
days=defaultdict(list)
for eid,name,role,i,o,src in D['punches']:
    days[(name,eid,f(i).date())].append(dict(role=role,i=f(i),o=f(o),src=src))
ROLES=sorted({p[2] for p in D['punches']})

rows=[]
for (name,eid,day),ss in sorted(days.items()):
    ss.sort(key=lambda s:s['i'])
    gaps=[(a['o'],b['i'],(b['i']-a['o']).total_seconds()/60) for a,b in zip(ss,ss[1:])]
    split=[g for g in gaps if g[2]>=SPLIT_MIN]
    meals=[g for g in gaps if MEAL_MIN<=g[2]<SPLIT_MIN]
    meal=meals[0] if meals else None
    # Gross is the sum of the stints, so every gap is unpaid however long it ran.
    gross=sum((s['o']-s['i']).total_seconds()/3600 for s in ss)
    ded=0.5 if (eid,day.isoformat()) in LUNCH else 0
    net=gross-ded
    per={r:0.0 for r in ROLES}
    for s in ss: per[s['role']]+=(s['o']-s['i']).total_seconds()/3600
    left=ded
    for rl in MEAL_ROLE_ORDER:
        if left<=0 or rl not in per: continue
        take=min(per[rl],left); per[rl]-=take; left-=take
    if left>1e-9:
        rest=sum(v for v in per.values() if v>0)
        if rest>0:
            for r in list(per):
                if per[r]>0: per[r]-=left*(per[r]/rest)
    srcs={s['src'] for s in ss}
    rows.append(dict(name=name,eid=eid,day=day,segs=ss,gross=gross,ded=ded,net=net,per=per,
        cin=ss[0]['i'],cout=ss[-1]['o'],meal=meal,split=split,
        src='Clocked' if srcs=={'clocked'} else ('Hand-entered' if 'clocked' not in srcs else 'Mixed')))

# ── columns ───────────────────────────────────────────────────
C={}; n=1
for key,title,w in ([('name','Employee',17),('date','Date',11),('dow','Day',6),('stints','Stints',7),
                     ('cin','First In',11),('cout','Last Out',11),
                     ('gross','Gross Hrs',10),('ded','Meal Deduct',9),('net','Net Hrs',9)]
                    +[(f'role{i}',r,14) for i,r in enumerate(ROLES)]
                    +[('mmin','Meal Mins',9),('mbeg','Meal Began\n(hrs in)',11),
                      ('comp','Meal Break Compliance (CA)',44),('pen','Penalty Hrs',9),
                      ('over','Over By\n(minutes)',10),('ot','OT DAY',8),('src','Source',13)]):
    C[key]=(n,title,w); n+=1
col=lambda k:C[k][0]; ltr=lambda k:L(C[k][0]); NCOL=n-1

wb=Workbook(); wb.remove(wb.active)
def put(ws,row,key,value,cached=None,font=BASE,fmt=None,align=None,fill=None):
    c=ws.cell(row,col(key),value); c.font=font
    if fmt: c.number_format=fmt
    if align: c.alignment=Alignment(horizontal=align)
    if fill: c.fill=fill
    c.border=BOX
    if cached is not None: CALC[(ws.title,f'{ltr(key)}{row}')]=cached
    return c

# ── All Punches first: the week sheet sums from it ────────────
ap=wb.create_sheet('All Punches')
ap['A1']=f'Every stint recorded at {LOC} · {P0:%B %d} – {P1:%B %d, %Y}'; ap['A1'].font=TITLE
for i,(t,w) in enumerate([('Employee',17),('Date',11),('Day',6),('Role',20),
                          ('In',20),('Out',20),('Hours',9),('Source',13)],1):
    c=ap.cell(3,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center'); ap.column_dimensions[L(i)].width=w
ap.freeze_panes='A4'; r=4
for x in rows:
    for s in x['segs']:
        ap.cell(r,1,x['name']).font=BASE
        c=ap.cell(r,2,x['day']); c.number_format='mm/dd/yyyy'
        ap.cell(r,3,f"{x['day']:%a}").alignment=Alignment(horizontal='center')
        ap.cell(r,4,s['role']).font=BASE
        for cc,v in ((5,s['i']),(6,s['o'])):
            cell=ap.cell(r,cc,v); cell.font=INPUT; cell.number_format='mm/dd/yyyy h:mm AM/PM'
        c=ap.cell(r,7,f'=(F{r}-E{r})*24'); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
        CALC[('All Punches',f'G{r}')]=(s['o']-s['i']).total_seconds()/3600
        c=ap.cell(r,8,'Clocked' if s['src']=='clocked' else 'Hand-entered')
        c.font=BASE if s['src']=='clocked' else AMB; c.alignment=Alignment(horizontal='center')
        for cc in range(1,9): ap.cell(r,cc).border=BOX
        r+=1
ap.sheet_view.showGridLines=False
APEND=r-1

# ── the week ──────────────────────────────────────────────────
ws=wb.create_sheet(f'Week ending {P1:%b %d}')
ws['A1']=f'{LOC} · {P0:%B %d} – {P1:%B %d, %Y}'; ws['A1'].font=TITLE
for k in C:
    i,t,w=C[k]
    c=ws.cell(3,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    ws.column_dimensions[L(i)].width=w
ws.row_dimensions[3].height=32; ws.freeze_panes='A4'
row=4; by=OrderedDict()
for x in rows: by.setdefault(x['name'],[]).append(x)
for name,recs in by.items():
    first=row
    for x in recs:
        put(ws,row,'name',name)
        put(ws,row,'date',x['day'],fmt='mm/dd/yyyy')
        put(ws,row,'dow',f"{x['day']:%a}",align='center')
        put(ws,row,'stints',len(x['segs']),align='center')
        put(ws,row,'cin',x['cin'],font=INPUT,fmt='h:mm AM/PM')
        put(ws,row,'cout',x['cout'],font=INPUT,
            fmt='mm/dd h:mm AM/PM' if x['cout'].date()!=x['day'] else 'h:mm AM/PM')
        # Summed from the stints, so any number of them is handled and every gap
        # between them stays unpaid.
        put(ws,row,'gross',
            f"=SUMIFS('All Punches'!$G$4:$G${APEND},'All Punches'!$A$4:$A${APEND},{ltr('name')}{row},"
            f"'All Punches'!$B$4:$B${APEND},{ltr('date')}{row})",
            x['gross'],fmt='0.00',align='center')
        put(ws,row,'ded',x['ded'],font=INPUT,fmt='0.00',align='center')
        gr,dd,nt=ltr('gross'),ltr('ded'),ltr('net')
        put(ws,row,'net',f'={gr}{row}-{dd}{row}',x['net'],font=BOLD,fmt='0.00',align='center')
        for i,rl in enumerate(ROLES):
            v=x['per'][rl]
            put(ws,row,f'role{i}',round(v,4) if v>1e-9 else None,fmt='0.00',align='center',fill=ROLE_F)
        mins = x['meal'][2] if x['meal'] else None
        began = (x['meal'][0]-x['cin']).total_seconds()/3600 if x['meal'] else None
        put(ws,row,'mmin',round(mins,1) if mins is not None else None,font=INPUT,fmt='0.0',align='center')
        put(ws,row,'mbeg',round(began,2) if began is not None else None,font=INPUT,fmt='0.00',align='center')
        mm,mb=ltr('mmin'),ltr('mbeg')
        # A day split by a long absence is two work periods, which the single-meal
        # test cannot judge — it is sent to a human rather than guessed at.
        if x['split']: txt='SPLIT SHIFT - review manually'
        elif x['net']<=5: txt=''
        elif mins is None and x['ded']==0: txt='' if x['net']<=6 else 'VIOLATION - no meal taken, over 6 hrs'
        elif mins is None: txt='REVIEW - lunch button, no times recorded'
        elif began>5: txt='VIOLATION - meal began after 5th hour'
        elif x['net']>12: txt='VIOLATION - no 2nd meal, over 12 hrs'
        else: txt=''
        put(ws,row,'comp',
            f'=IF({ltr("stints")}{row}=0,"",'
            f'IF({nt}{row}<=5,"",'
            f'IF(AND({mm}{row}="",{dd}{row}=0),IF({nt}{row}<=6,"","VIOLATION - no meal taken, over 6 hrs"),'
            f'IF({mm}{row}="","REVIEW - lunch button, no times recorded",'
            f'IF({mb}{row}>5,"VIOLATION - meal began after 5th hour",'
            f'IF({nt}{row}>12,"VIOLATION - no 2nd meal, over 12 hrs",""))))))',
            txt, font=RED if txt.startswith('VIOLATION') else (AMB if txt else BASE))
        pen=1 if txt.startswith('VIOLATION') else 0
        cp,pn=ltr('comp'),ltr('pen')
        put(ws,row,'pen',f'=IF(LEFT({cp}{row},9)="VIOLATION",1,0)',pen,font=RED,fmt='0',align='center')
        marg=''
        if pen:
            if 'over 6 hrs' in txt: marg=(x['net']-6)*60
            elif 'after 5th' in txt: marg=(began-5)*60
        put(ws,row,'over',
            f'=IF({pn}{row}=0,"",'
            f'IF({cp}{row}="VIOLATION - no meal taken, over 6 hrs",({nt}{row}-6)*60,'
            f'IF({cp}{row}="VIOLATION - meal began after 5th hour",({mb}{row}-5)*60,"")))',
            marg,fmt='0.0',align='center')
        put(ws,row,'ot',f'=IF({nt}{row}>8,"OT","")','OT' if x['net']>8 else '',font=RED,align='center')
        put(ws,row,'src',x['src'],font=BASE if x['src']=='Clocked' else AMB,align='center')
        row+=1
    put(ws,row,'name',f'TOTAL — {name}',font=BOLD)
    for k in ['gross','ded','net','pen']+[f'role{i}' for i in range(len(ROLES))]:
        vals=[CALC.get((ws.title,f'{ltr(k)}{rr}')) for rr in range(first,row)]
        s=sum(v for v in vals if isinstance(v,(int,float)))
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
wb.move_sheet('All Punches',offset=len(wb.sheetnames))

# ── By Role ───────────────────────────────────────────────────
br=wb.create_sheet('By Role',1)
br['A1']=f'Hours by role · {LOC} · week ending {P1:%B %d, %Y}'; br['A1'].font=TITLE
br['A2']='Net hours, after any meal deduction.'; br['A2'].font=MUTED
people=list(by); br.column_dimensions['A'].width=24
for i,_ in enumerate(people): br.column_dimensions[L(2+i)].width=15
br.column_dimensions[L(2+len(people))].width=13
for i,t in enumerate(['Role']+people+['TOTAL'],1):
    c=br.cell(4,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
br.row_dimensions[4].height=30; rr=5
for rl in ROLES:
    br.cell(rr,1,rl).font=BOLD; br.cell(rr,1).border=BOX
    for i,p_ in enumerate(people):
        v=sum(x['per'][rl] for x in by[p_])
        c=br.cell(rr,2+i,round(v,2) if v>1e-9 else None); c.number_format='0.00'
        c.alignment=Alignment(horizontal='center'); c.border=BOX
    c=br.cell(rr,2+len(people),round(sum(x['per'][rl] for x in rows),2))
    c.font=BOLD; c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    c.border=BOX; c.fill=TOT_F
    rr+=1
br.cell(rr,1,'TOTAL').font=WHITE; br.cell(rr,1).fill=GRAND; br.cell(rr,1).border=BOX
for i,p_ in enumerate(people):
    c=br.cell(rr,2+i,round(sum(x['net'] for x in by[p_]),2))
    c.font=WHITE; c.fill=GRAND; c.number_format='0.00'
    c.alignment=Alignment(horizontal='center'); c.border=BOX
c=br.cell(rr,2+len(people),round(sum(x['net'] for x in rows),2))
c.font=WHITE; c.fill=GRAND; c.number_format='0.00'
c.alignment=Alignment(horizontal='center'); c.border=BOX
br.sheet_view.showGridLines=False

# ── Check These ───────────────────────────────────────────────
ck=wb.create_sheet('Check These',2)
ck['A1']='Days that need your eye'; ck['A1'].font=TITLE
for i,(t,w) in enumerate([('Employee',17),('Date',12),('Net Hrs',10),('What stands out',82)],1):
    c=ck.cell(3,i,t); c.font=HDR; c.fill=HDR_F; c.border=BOX
    c.alignment=Alignment(horizontal='center'); ck.column_dimensions[L(i)].width=w
rr=4; nodd=0
for x in rows:
    why=None
    if x['split']:
        g=max(s[2] for s in x['split'])
        why=(f"Left and came back — {g/60:.1f} hour gap. Counted as two work periods, so the hours are "
             f"right, but the meal rule cannot be judged automatically across a break that long.")
    elif x['gross']<0.5:
        why=f"{x['gross']*60:.0f} minutes on the clock — looks like a test punch."
    if not why: continue
    nodd+=1
    ck.cell(rr,1,x['name']).font=BASE
    c=ck.cell(rr,2,x['day']); c.number_format='mm/dd/yyyy'
    c=ck.cell(rr,3,round(x['net'],2)); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    c=ck.cell(rr,4,why); c.font=BASE; c.alignment=Alignment(wrap_text=True,vertical='top')
    ck.row_dimensions[rr].height=28
    for i in range(1,5): ck.cell(rr,i).border=BOX; ck.cell(rr,i).fill=ODD_F
    rr+=1
if nodd==0: ck.cell(4,1,'Nothing flagged this week.').font=BASE
ck.sheet_view.showGridLines=False

# ── Read Me ───────────────────────────────────────────────────
rm=wb.create_sheet('Read Me',0)
rm.column_dimensions['A'].width=3; rm.column_dimensions['B'].width=30; rm.column_dimensions['C'].width=90
rm['B2']=f'{LOC} — Hours for the week ending {P1:%B %d, %Y}'; rm['B2'].font=TITLE
rm['B3']=f'Pay period {P0:%A, %B %d} through {P1:%A, %B %d} · generated {dt.date.today():%B %d, %Y}'
rm['B3'].font=MUTED
r=5
def note(l,t,fo=BASE):
    global r
    rm.cell(r,2,l).font=BOLD
    c=rm.cell(r,3,t); c.font=fo; c.alignment=Alignment(wrap_text=True,vertical='top')
    rm.row_dimensions[r].height=max(14,13*(len(t)//99+1)); r+=1
note('Scope',f'{LOC} only. Hours worked at other locations this period are not included.')
note('Hours format','Decimal, two places. 7.50 means seven hours thirty minutes.')
note('Gross Hrs','The stints added together, so every gap between them is unpaid however long it ran. '
     'Stints shows how many separate periods made up the day; All Punches lists each one.')
note('Hours by role','One column per role. They add up to Net Hrs on every row. An unpaid meal is charged '
     'against Actor, then Crowd Control, then Lines/Crowd Control.')
note('Source','Whether the day was punched by the employee or typed in from a paper card.')
r+=1
rm.cell(r,2,'MEAL BREAKS').font=Font(name=A,size=11,bold=True); r+=1
note('The rule','California Labor Code 512. A meal must be at least 30 uninterrupted minutes and must BEGIN '
     'before the end of the 5th hour of work.')
note('  Over 6 hours','Required and not waivable. None taken is a violation.')
note('  5 to 6 hours','Covered by the signed waiver every employee has, so it is not flagged.')
note('What counts as a meal','A gap of 30 minutes up to 2 hours. Anything longer is someone leaving and '
     'coming back, not a break.')
note('SPLIT SHIFT','A day broken by a gap of 2 hours or more is two separate work periods. The hours are '
     'correct, but a single meal test cannot fairly judge a day like that, so it is sent to you rather than '
     'guessed at. See Check These.',RED)
note('Penalty Hrs','One hour of pay per workday under Labor Code 226.7, capped at one per day.')
rm.sheet_view.showGridLines=False

OUT=f'HauntedTrail-Week-Ending-{P1}.xlsx'
wb.save(OUT)

# ── cache results ─────────────────────────────────────────────
shutil.copy(OUT,'tmp.xlsx')
zin=zipfile.ZipFile('tmp.xlsx'); zout=zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED)
names={i+1:s.title for i,s in enumerate(wb)}; nc=0
for it in zin.infolist():
    data=zin.read(it.filename)
    m=re.fullmatch(r'xl/worksheets/sheet(\d+)\.xml',it.filename)
    if m:
        title=names.get(int(m.group(1))); xml=data.decode()
        def fix(cm):
            global nc
            ref,attrs,ftag=cm.group(1),cm.group(2),cm.group(3)
            v=CALC.get((title,ref))
            if v is None or v=='': return cm.group(0)
            nc+=1; attrs=re.sub(r'\s+t="[^"]*"','',attrs)
            if isinstance(v,str):
                e=v.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                return f'<c r="{ref}"{attrs} t="str">{ftag}<v>{e}</v></c>'
            return f'<c r="{ref}"{attrs}>{ftag}<v>{v!r}</v></c>'
        xml=re.sub(r'<c r="([A-Z]+\d+)"([^>]*)>(<f>.*?</f>)(?:<v\s*/>|<v>.*?</v>)?</c>',fix,xml,flags=re.S)
        data=xml.encode()
    zout.writestr(it,data)
zout.close(); zin.close()
print('roles  :',ROLES)
print('sheets :',wb.sheetnames)
print('flagged:',nodd,'| cached',nc,'formula results ->',OUT)
