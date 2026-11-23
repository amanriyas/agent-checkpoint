# Builds the system diagram as SVG, then renders PNG with Playwright.
import html
NAVY="#073e67"; INK="#1f2933"; MUTED="#52606d"; AI="#7a3e9d"; PLAN="#9aa5b1"
boxes={
 # id: x,y,w,h,title,lines,status  (status: impl|sim|plan|ai)
 'scen':(40,110,300,96,"Scripted task files",["3 tasks, 30 approval points,","9 seeded harmful actions"],'sim'),
 'llm': (40,250,300,96,"Live LLM (Groq / OpenAI)",["proposes one action as JSON;","never executes (dry run)"],'ai'),
 'schema':(40,390,300,80,"Schema check",["bad JSON or tool: session stops"],'impl'),
 'seed':(40,510,300,80,"Seeded harmful actions",["mixed into live runs for ground truth"],'impl'),

 'engine':(430,110,360,80,"Session engine",["one proposed step at a time"],'impl'),
 'gate':(430,230,360,96,"Contract gate",["reads + test runs: run, then report","'don't ask again' classes: auto-approve"],'impl'),
 'an':(430,366,360,80,"Consequence analyser",["fixed rules, not AI; 'unknown' if no rule"],'impl'),
 'prompt':(430,486,360,80,"Prompt builder",["raw: command only  |  card: + consequences"],'impl'),
 'log':(430,620,360,80,"Decision log (JSON Lines)",["action, label, decision, time, auto?"],'impl'),
 'sdt':(430,750,170,96,"Scoring",["hits, false alarms,","d′, c, per block"],'impl'),
 'report':(620,750,170,96,"Report builder",["agent claim vs","log + return values"],'impl'),

 'trans':(880,110,320,80,"Transcript",["what ran, and who approved it"],'impl'),
 'ask':(880,486,320,80,"Approval prompt",["Approve / Refuse / Don't ask again"],'impl'),
 'person':(880,620,320,80,"Participant",["reads, decides (time logged)"],'person'),
 'rep':(880,750,150,96,"After-run report",["Done, Refused,","Assumed, Can't undo"],'impl'),
 'res':(1050,750,150,96,"Results page",["by condition,","by block, CSV"],'impl'),

 'p1':(40,920,360,70,"Sandbox that really runs approved actions",[],'plan'),
 'p2':(430,920,360,70,"Multi-day sessions, same participants",[],'plan'),
 'p3':(840,920,360,70,"Varied card designs against habituation",[],'plan'),
}
groups=[(20,60,340,560,"AGENT: PROPOSES"),(410,60,400,810,"CHECKPOINT SERVER (FastAPI): DISPOSES"),(860,60,360,810,"PARTICIPANT'S BROWSER (HTML/JS)"),(20,890,1200,120,"PLANNED, NOT BUILT")]
def anchor(b,side,off=0.5):
    x,y,w,h=boxes[b][:4]
    return {'l':(x,y+h*off),'r':(x+w,y+h*off),'t':(x+w*off,y),'b':(x+w*off,y+h)}[side]
# from,side,to,side,label,kind(info|control|ai), label offset
arrows=[
 ('scen','r','engine','l',"next scripted step",'info',None),
 ('llm','b','schema','t',"JSON proposal",'ai',None),
 ('schema','r','engine','l',"valid action",'info',None),
 ('seed','r','engine','l',"",'info',None),
 ('engine','b','gate','t',"",'info',None),
 ('gate','r','trans','l',"auto-run: shown, not asked",'info',None),
 ('gate','b','an','t',"needs approval",'control',None),
 ('an','b','prompt','t',"",'info',None),
 ('prompt','r','ask','l',"",'info',None),
 ('ask','b','person','t',"",'info',None),
 ('person','l','log','r',"decision",'control',None),
 ('log','b','report','t',"",'info',None),
 ('log','b','sdt','t',"",'info',None),
 ('report','r','rep','l',"",'info',None),
 ('sdt','b','res','b',"",'info',None),
 ('log','t','engine','t',"",'skip',None),
]
st={'impl':("#ffffff",NAVY,"0","2"),'sim':("#fffaf0","#b7791f","8 5","2"),'ai':("#f7f0fb",AI,"0","2.5"),'plan':("#f5f7fa",PLAN,"3 4","2"),'person':("#e8f0f7",NAVY,"0","2")}
tag={'impl':("IMPLEMENTED",NAVY),'sim':("SIMULATED",'#b7791f'),'ai':("IMPLEMENTED · AI",AI),'plan':("PLANNED",'#7b8794'),'person':("HUMAN",NAVY)}
W,H=1240,1030
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, sans-serif">',
'<defs>'+''.join(f'<marker id="m{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k,c in [('info',MUTED),('control','#c0392b'),('ai',AI)])+'</defs>',
f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
f'<text x="20" y="34" font-size="22" font-weight="700" fill="{INK}">Agent Checkpoint: components and flows</text>']
for x,y,w,h,t in groups:
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#f8fafc" stroke="#d9e2ec"/>')
    o.append(f'<text x="{x+14}" y="{y+24}" font-size="12.5" font-weight="700" letter-spacing="1" fill="{MUTED}">{html.escape(t)}</text>')
def line(a,b,kind,label):
    (x1,y1),(x2,y2)=a,b
    col={'info':MUTED,'control':'#c0392b','ai':AI}[kind]
    dash=' stroke-dasharray="6 4"' if kind=='control' else ''
    if abs(y1-y2)<2 or abs(x1-x2)<2: d=f'M{x1},{y1} L{x2},{y2}'
    elif a[0]!=b[0] and kind!='vert':
        mx=(x1+x2)/2; d=f'M{x1},{y1} L{mx},{y1} L{mx},{y2} L{x2},{y2}'
    o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2"{dash} marker-end="url(#m{kind})"/>')
    if label:
        lx=(x1+x2)/2; ly=(y1+y2)/2
        if abs(y1-y2)<2: ly=y1-8; anc='middle'
        elif abs(x1-x2)<2: lx=x1+10; anc='start'
        else: lx=(x1+x2)/2+8; ly=min(y1,y2)+(abs(y2-y1))/2; anc='start'
        o.append(f'<text x="{lx}" y="{ly}" font-size="12" fill="{col}" text-anchor="{anc}" font-weight="600">{html.escape(label)}</text>')
def P(d,kind):
    col={'info':MUTED,'control':'#c0392b','ai':AI}[kind]; dash=' stroke-dasharray="6 4"' if kind=='control' else ''
    o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2"{dash} marker-end="url(#m{kind})"/>')
def T(x,y,t,kind,anc='start',rot=None):
    col={'info':MUTED,'control':'#c0392b','ai':AI}[kind]; r=f' transform="rotate({rot} {x} {y})"' if rot else ''
    o.append(f'<text x="{x}" y="{y}" font-size="12" fill="{col}" text-anchor="{anc}" font-weight="600"{r}>{html.escape(t)}</text>')
# left bus into engine
for b in ('scen','schema','seed'):
    x,y=anchor(b,'r'); o.append(f'<path d="M{x},{y} L385,{y}" fill="none" stroke="{MUTED}" stroke-width="2"/>')
o.append(f'<path d="M385,550 L385,150" fill="none" stroke="{MUTED}" stroke-width="2"/>')
P("M385,150 L430,150",'info')
T(398,350,"proposed action, one at a time",'info','middle',90)
P("M190,346 L190,390",'ai'); T(200,374,"JSON proposal",'ai')
P("M610,190 L610,230",'info')
P("M790,262 L1040,262 L1040,190",'info'); T(880,254,"auto-run: shown, not asked",'info')
P("M610,326 L610,366",'control'); T(620,352,"needs approval",'control')
P("M610,446 L610,486",'info')
P("M790,526 L880,526",'info')
P("M1040,566 L1040,620",'info')
P("M880,660 L790,660",'control'); T(835,652,"decision",'control','middle')
P("M515,700 L515,750",'info'); P("M705,700 L705,750",'info')
P("M790,798 L880,798",'info')
P("M515,846 L515,862 L1125,862 L1125,846",'info')
for k,(x,y,w,h,t,lines,s) in boxes.items():
    fill,stroke,dash,sw=st[s]
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-dasharray="{dash}"/>')
    tg,tc=tag[s]
    if s=='plan':
        o.append(f'<text x="{x+14}" y="{y+28}" font-size="11" font-weight="700" letter-spacing=".8" fill="{tc}">{tg}</text>')
        o.append(f'<text x="{x+14}" y="{y+50}" font-size="15" font-weight="600" fill="{MUTED}">{html.escape(t)}</text>'); continue
    o.append(f'<text x="{x+14}" y="{y+22}" font-size="10.5" font-weight="700" letter-spacing=".8" fill="{tc}">{tg}</text>')
    o.append(f'<text x="{x+14}" y="{y+44}" font-size="16" font-weight="700" fill="{INK}">{html.escape(t)}</text>')
    for i,l in enumerate(lines):
        o.append(f'<text x="{x+14}" y="{y+64+i*17}" font-size="13" fill="{MUTED}">{html.escape(l)}</text>')
# loop-back: decision feeds engine (control)
o.append('<path d="M790,640 L822,640 L822,140 L790,140" fill="none" stroke="#c0392b" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#mcontrol)"/>')
o.append('<text x="834" y="420" font-size="12" fill="#c0392b" font-weight="600" transform="rotate(90 834 420)" text-anchor="middle">approved: scripted result, agent continues · refused: skipped</text>')
# legend
lx=40; ly=660
o.append(f'<rect x="{lx}" y="{ly-10}" width="300" height="190" rx="8" fill="#ffffff" stroke="#d9e2ec"/>')
o.append(f'<text x="{lx+14}" y="{ly+14}" font-size="12.5" font-weight="700" letter-spacing="1" fill="{MUTED}">KEY</text>')
items=[('box',NAVY,'0',"Implemented"),('box','#b7791f','8 5',"Simulated (scripted agent)"),('box',AI,'0',"AI component (only proposes)"),('box',PLAN,'3 4',"Planned"),('ln',MUTED,'0',"Information flow"),('ln','#c0392b','6 4',"Control: the person's decision")]
for i,(k,c,d,t) in enumerate(items):
    yy=ly+38+i*24
    if k=='box': o.append(f'<rect x="{lx+14}" y="{yy-12}" width="28" height="16" rx="3" fill="#fff" stroke="{c}" stroke-width="2" stroke-dasharray="{d}"/>')
    else: o.append(f'<line x1="{lx+14}" y1="{yy-4}" x2="{lx+42}" y2="{yy-4}" stroke="{c}" stroke-width="2" stroke-dasharray="{d}"/>')
    o.append(f'<text x="{lx+54}" y="{yy}" font-size="13" fill="{INK}">{t}</text>')
o.append('</svg>')
open('docs/figures/system_diagram.svg','w').write('\n'.join(o))
