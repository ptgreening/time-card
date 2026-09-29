import json, datetime as dt
from collections import defaultdict, OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

D=json.load(open('wk.json'))
f=lambda s: dt.datetime.strptime(s,'%Y-%m-%d %H:%M:%S')
P0,P1=[dt.date.fromisoformat(x) for x in D['period']]
LOC=D['location']
LUNCH={tuple(x) for x in D['day_lunch']}
CLOCKOUT=set(D['lunch_clockout_roles'])

A='Arial'
HDR_F=PatternFill('solid',fgColor='1F3864'); TOT_F=PatternFill('solid',fgColor='D9E2F3')
ODD_F=PatternFill('solid',fgColor='FFF2CC'); EDGE_F=PatternFill('solid',fgColor='FFE08A')
TITLE=Font(name=A,size=14,bold=True); HDR=Font(name=A,size=10,bold=True,color='FFFFFF')
BASE=Font(name=A,size=10); BOLD=Font(name=A,size=10,bold=True)
INPUT=Font(name=A,size=10,color='0000FF'); MUTED=Font(name=A,size=9,color='808080')
RED=Font(name=A,size=10,bold=True,color='C00000')
thin=Side(style='thin',color='BFBFBF'); BOX=Border(left=thin,right=thin,top=thin,bottom=thin)

wb=Workbook(); wb.remove(wb.active)
def head(ws,cols,row,widths):
    for c,(t,w) in enumerate(zip(cols,widths),1):
        x=ws.cell(row,c,t); x.font=HDR; x.fill=HDR_F; x.border=BOX
        x.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width=w
    ws.row_dimensions[row].height=30

# ── group into employee-days ──
days=defaultdict(list)
for eid,name,role,i,o,lo in D['punches']:
    days[(name,eid,f(i).date())].append(dict(role=role,i=f(i),o=f(o),lo=lo))
rows=[]
for (name,eid,day),ss in sorted(days.items()):
    ss.sort(key=lambda s:s['i'])
    gaps=[(a['o'],b['i']) for a,b in zip(ss,ss[1:]) if b['i']>a['o']]
    meal=max(gaps,key=lambda g:g[1]-g[0]) if gaps else None
    rows.append(dict(name=name,eid=eid,day=day,segs=ss,
        cin=ss[0]['i'],cout=ss[-1]['o'],mo=meal[0] if meal else None,mi=meal[1] if meal else None,
        button=(eid,day.isoformat()) in LUNCH,
        roles=' / '.join(OrderedDict.fromkeys(s['role'] for s in ss))))

# ── Read Me ──
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
note('Net hours','Time on the clock minus any unpaid break. Break Out and Break In show the longest gap between '
     'punches that day. Any gap is unpaid — the Meal? column says whether it was long enough to count as a meal '
     'under the 30-minute rule.')
note('Day assignment','A shift belongs to the day it STARTED. One running past midnight stays on the day it began.')
r+=1
ws.cell(r,2,'MEAL BREAKS').font=Font(name=A,size=11,bold=True); r+=1
note('The rule','California Labor Code 512. A meal must be at least 30 uninterrupted minutes and must BEGIN before the '
     'end of the 5th hour of work.')
note('  Over 6 hours','Required and not waivable. None taken is a violation.')
note('  5 to 6 hours','Covered by the signed waiver every employee has, so it is not flagged.')
note('Penalty Hrs','One hour of pay per workday under Labor Code 226.7, capped at one per day.')
note('Over By (minutes)','How far past the line a violation is. Anything within 15 minutes is shaded amber and worth '
     'reading the punches before paying.')
r+=1
note('Nothing to hold back','No open punches and no shift over 16 hours this period, so every day below is counted. '
     'Compare with August, where most recorded time was forgotten clock-outs.')
note('Two rows to look at','See the Check These tab. Neither is a compliance problem — both look like test entries.',RED)
ws.sheet_view.showGridLines=False

# ── the week ──
COLS=['Employee','Date','Day','Roles worked','Clock In','Break Out','Break In','Clock Out',
      'Gross Hrs','Meal Deduct','Net Hrs','Meal?','Break Mins','Break Began\n(hrs in)',
      'Meal Break Compliance (CA)','Penalty Hrs','Over By\n(minutes)','OT DAY']
W=[18,11,6,26,11,11,11,11,9,9,9,7,9,11,40,9,10,8]
ws=wb.create_sheet(f'Week ending {P1:%b %d}')
ws['A1']=f'{LOC} · {P0:%B %d} – {P1:%B %d, %Y}'; ws['A1'].font=TITLE
head(ws,COLS,3,W); ws.freeze_panes='A4'
row=4
by=OrderedDict()
for x in rows: by.setdefault(x['name'],[]).append(x)
for name,recs in by.items():
    first=row
    for x in recs:
        ws.cell(row,1,name).font=BASE
        c=ws.cell(row,2,x['day']); c.font=BASE; c.number_format='mm/dd/yyyy'
        ws.cell(row,3,f"{x['day']:%a}").font=BASE
        ws.cell(row,4,x['roles']).font=BASE
        for col,v in ((5,x['cin']),(6,x['mo']),(7,x['mi']),(8,x['cout'])):
            if v:
                c=ws.cell(row,col,v); c.font=INPUT
                c.number_format='mm/dd h:mm AM/PM' if v.date()!=x['day'] else 'h:mm AM/PM'
        ws.cell(row,9,f'=IF(F{row}="",(H{row}-E{row})*24,(F{row}-E{row})*24+(H{row}-G{row})*24)').font=BASE
        ws.cell(row,10,0.5 if x['button'] else 0).font=INPUT
        ws.cell(row,11,f'=I{row}-J{row}').font=BOLD
        qualifies = 1 if (x['mo'] and (x['mi']-x['mo'])>=dt.timedelta(minutes=30)) else 0
        ws.cell(row,12,qualifies).font=INPUT
        ws.cell(row,13,f'=IF(F{row}="","",(G{row}-F{row})*1440)').font=BASE
        ws.cell(row,14,f'=IF(F{row}="","",(F{row}-E{row})*24)').font=BASE
        ws.cell(row,15,
            f'=IF(K{row}<=5,"",'
            f'IF(AND(L{row}=0,J{row}=0),IF(K{row}<=6,"","VIOLATION - no meal taken, over 6 hrs"),'
            f'IF(AND(L{row}=0,J{row}>0),"REVIEW - lunch button, no times recorded",'
            f'IF(M{row}<30,IF(K{row}<=6,"","VIOLATION - longest break under 30 min, no qualifying meal"),'
            f'IF(N{row}>5,"VIOLATION - meal began after 5th hour",'
            f'IF(AND(K{row}>12,L{row}<2),"VIOLATION - no 2nd meal, over 12 hrs",""))))))').font=BASE
        ws.cell(row,16,f'=IF(LEFT(O{row},9)="VIOLATION",1,0)').font=RED
        ws.cell(row,17,
            f'=IF(P{row}=0,"",'
            f'IF(O{row}="VIOLATION - no meal taken, over 6 hrs",(K{row}-6)*60,'
            f'IF(O{row}="VIOLATION - meal began after 5th hour",(N{row}-5)*60,'
            f'IF(O{row}="VIOLATION - longest break under 30 min, no qualifying meal",30-M{row},""))))').font=BASE
        ws.cell(row,18,f'=IF(K{row}>8,"OT","")').font=RED
        for col in (9,10,11,13,14,16,17):
            ws.cell(row,col).number_format='0.0' if col==17 else '0.00'
            ws.cell(row,col).alignment=Alignment(horizontal='center')
        for col in (3,12,18): ws.cell(row,col).alignment=Alignment(horizontal='center')
        for col in range(1,19): ws.cell(row,col).border=BOX
        row+=1
    ws.cell(row,1,f'TOTAL — {name}').font=BOLD
    for col,rng in ((9,'I'),(10,'J'),(11,'K'),(16,'P')):
        c=ws.cell(row,col,f'=SUM({rng}{first}:{rng}{row-1})')
        c.font=BOLD if col==11 else (RED if col==16 else BASE)
        c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    ws.cell(row,15,'Meal penalty hours owed ->').font=BOLD
    ws.cell(row,18,f'=IF(K{row}>40,"OVER 40","")').font=RED
    ws.cell(row,18).alignment=Alignment(horizontal='center')
    for col in range(1,19): ws.cell(row,col).fill=TOT_F; ws.cell(row,col).border=BOX
    row+=2
ws.conditional_formatting.add(f'Q4:Q{row}',
    CellIsRule(operator='between',formula=['0.0001','15'],fill=EDGE_F))
ws.sheet_view.showGridLines=False

# ── oddities ──
ws=wb.create_sheet('Check These')
ws['A1']='Worth a look — not compliance problems'; ws['A1'].font=TITLE
head(ws,['Employee','Date','Net Hrs','What stands out'],3,[18,12,10,74]); ws.freeze_panes='A4'
odd=[]
for x in rows:
    g=sum((s['o']-s['i']).total_seconds()/3600 for s in x['segs']); n=g-(0.5 if x['button'] else 0)
    if g<0.5: odd.append((x,n,f'{g*60:.0f} minutes on the clock — looks like a test punch, not a shift.'))
    elif x['button'] and g<2: odd.append((x,n,f'A 30-minute lunch was deducted from a {g*60:.0f}-minute shift, leaving {n:.2f} hrs. Check this was meant.'))
r2=4
for x,n,why in odd:
    ws.cell(r2,1,x['name']).font=BASE
    c=ws.cell(r2,2,x['day']); c.font=BASE; c.number_format='mm/dd/yyyy'
    c=ws.cell(r2,3,round(n,2)); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    ws.cell(r2,4,why).font=BASE
    for col in range(1,5): ws.cell(r2,col).border=BOX; ws.cell(r2,col).fill=ODD_F
    r2+=1
ws.sheet_view.showGridLines=False

# ── raw punches ──
ws=wb.create_sheet('All Punches')
ws['A1']=f'Every punch recorded at {LOC} this period'; ws['A1'].font=TITLE
head(ws,['Employee','Role','Clock In','Clock Out','Span (hrs)'],3,[18,16,22,22,11]); ws.freeze_panes='A4'
r3=4
for eid,name,role,i,o,lo in sorted(D['punches'],key=lambda p:(p[1],p[3])):
    ws.cell(r3,1,name).font=BASE; ws.cell(r3,2,role).font=BASE
    for col,v in ((3,f(i)),(4,f(o))):
        c=ws.cell(r3,col,v); c.font=INPUT; c.number_format='mm/dd/yyyy h:mm AM/PM'
    c=ws.cell(r3,5,f'=(D{r3}-C{r3})*24'); c.number_format='0.00'; c.alignment=Alignment(horizontal='center')
    for col in range(1,6): ws.cell(r3,col).border=BOX
    r3+=1
ws.sheet_view.showGridLines=False
wb.save('HauntedTrail-Week-Ending-2026-09-28.xlsx')
print('sheets:', wb.sheetnames)
print('oddities flagged:', len(odd))
