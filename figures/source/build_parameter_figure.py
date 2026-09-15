from pathlib import Path
import json, hashlib, subprocess, argparse
args=argparse.ArgumentParser()
args.add_argument("--mode",choices=["reference","9pt"],default="reference")
args.add_argument("--raw-csv",type=Path,default=None)
args=args.parse_args()
IS9=args.mode=="9pt"
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
if args.raw_csv is not None:
    raw=pd.read_csv(args.raw_csv)
    d=raw[(raw['method']=='PSF_ORACLE_QR')&(raw['status']=='ok')].copy()
    p=d.params.map(json.loads)
    d['q']=p.map(lambda x:float(x['q'])); d['lambda']=p.map(lambda x:float(x['lambda']))
    assert len(d)==53*3*14*16
    assert not d.duplicated(['dataset','pool','q','lambda']).any()
    assert (d.groupby(['q','lambda']).size()==159).all()
    assert (d.groupby(['dataset','q','lambda']).size()==3).all()
    assert d[['ACC','NMI']].apply(lambda s:s.between(0,1).all()).all()
    dm=d.groupby(['dataset','q','lambda'],as_index=False)[['ACC','NMI']].mean()
    grid=dm.groupby(['q','lambda'],as_index=False)[['ACC','NMI']].mean()
else:
    grid=pd.read_csv(ROOT/'data'/'full_grid_acc_nmi.csv')
qs=[0.3,1.0,6.0,12.0]; ls=[0.1,0.5,1.0,4.0,12.0]
selected=grid[grid.q.isin(qs)&grid['lambda'].isin(ls)].copy().sort_values(['q','lambda'])
grid.to_csv(ROOT/'data'/'full_grid_acc_nmi.csv',index=False,float_format='%.14g')
selected.to_csv(ROOT/'data'/'plotted_grid_acc_nmi.csv',index=False,float_format='%.14g')
lookup=selected.set_index(['q','lambda'])
# Orthographic projection; x = lambda, y = q, z = metric (absolute score).
SX=np.array([2.86,1.30]); SY=np.array([2.72,-1.75]); SZ=np.array([0.0,20.4])
O=np.array([9.20,22.5]); ZMAX=.5

def vec(x,y,z,shift=0):
    return O+np.array([shift,0.])+x*SX+y*SY+z*SZ

def pt(x,y,z,shift=0):
    a=vec(x,y,z,shift); return f'({a[0]:.6f},{a[1]:.6f})'

def poly(coords,opts,shift=0):
    return r'\path['+opts+'] '+' -- '.join(pt(*p,shift) for p in coords)+r' -- cycle;'

def line(a,b,opts='gridline',shift=0):
    return r'\draw['+opts+'] '+pt(*a,shift)+' -- '+pt(*b,shift)+';'

def node(x,y,text,opts='',font=None):
    if font: opts=opts+(', ' if opts else '')+'font={'+font+'}'
    return rf'\node[{opts}] at ({x:.6f},{y:.6f}) {{{text}}};'

out=[r'% Data-driven paths generated from plotted_grid_acc_nmi.csv.',
 r'\begin{tikzpicture}[x=1mm,y=1mm,',
 (r'font=\fontsize{9.2}{10.5}\selectfont,' if IS9 else r'font=\fontsize{4.6}{5.4}\selectfont,'),
 r'line join=miter,line cap=butt,',
 r'gridline/.style={draw=black!12,line width=0.15pt},',
 r'axisline/.style={draw=black!55,line width=0.23pt},',
 r'barline/.style={draw=black!75,line width=0.19pt}]',
 r'\path[use as bounding box] (0,5.0) rectangle (86,46);']
colors=[(0.24,.12,.68),(.14,.46,.86),(.02,.70,.75),(.62,.82,.22),(.97,.92,.03)]
for j,(rr,gg,bb) in enumerate(colors):
    out.append(rf'\definecolor{{series{j}}}{{rgb}}{{{rr},{gg},{bb}}}')
for shift,metric in [(0.,'ACC'),(41.5,'NMI')]:
    # Walls, base, and faint grid lines, as in the supplied reference.
    out.append(poly([(0,0,0),(5,0,0),(5,0,ZMAX),(0,0,ZMAX)],'fill=white,gridline',shift))
    out.append(poly([(5,0,0),(5,4,0),(5,4,ZMAX),(5,0,ZMAX)],'fill=white,gridline',shift))
    for x in range(6):
        out.append(line((x,0,0),(x,4,0),shift=shift))
        out.append(line((x,0,0),(x,0,ZMAX),shift=shift))
    for y in range(5):
        out.append(line((0,y,0),(5,y,0),shift=shift))
        out.append(line((5,y,0),(5,y,ZMAX),shift=shift))
    for z in [0,.25,.5]:
        out.append(line((0,0,z),(5,0,z),shift=shift))
        out.append(line((5,0,z),(5,4,z),shift=shift))
    # Far-to-near order is determined by the fixed camera, never by metric height.
    bars=[(j,i) for j in range(5) for i in range(4)]
    bars.sort(key=lambda ji:(ji[0]-.7*ji[1]),reverse=True)
    for j,i in bars:
        h=float(lookup.loc[(qs[i],ls[j]),metric]); x=j+.10;y=i+.10; dx=.8;dy=.8
        col=f'series{j}'
        out.append(poly([(x,y,0),(x,y+dy,0),(x,y+dy,h),(x,y,h)],f'barline,fill={col}!76!black',shift))
        out.append(poly([(x,y+dy,0),(x+dx,y+dy,0),(x+dx,y+dy,h),(x,y+dy,h)],f'barline,fill={col}!88!black',shift))
        out.append(poly([(x,y,h),(x+dx,y,h),(x+dx,y+dy,h),(x,y+dy,h)],f'barline,fill={col}!91!white',shift))
    for a,b in [((0,0,0),(0,0,ZMAX)),((0,0,0),(0,4,0)),((0,4,0),(5,4,0))]:
        out.append(line(a,b,'axisline',shift))
    for z,label in ([(0,'0'),(.5,'0.5')] if IS9 else [(0,'0'),(.25,'0.25'),(.5,'0.5')]):
        v=vec(0,0,z,shift); out.append(rf'\draw[axisline] ({v[0]:.5f},{v[1]:.5f}) -- ++(-.6,0);')
        out.append(node(v[0]-.95,v[1],label,'anchor=east,inner sep=0'))
    # Keep numeric tick labels level, not diagonally rotated.
    for j,lam in enumerate(ls):
        if IS9 and j not in [0,2,4]: continue
        v=vec(j+.5,4,0,shift);out.append(rf'\draw[axisline] ({v[0]:.5f},{v[1]:.5f}) -- ++(0,-.5);')
        out.append(node(v[0],v[1]-.9,f'{lam:g}','anchor=north,inner sep=0'))
    for i,q in enumerate(qs):
        if IS9 and i not in [0,3]: continue
        v=vec(0,i+.5,0,shift);out.append(rf'\draw[axisline] ({v[0]:.5f},{v[1]:.5f}) -- ++(-.5,-.2);')
        out.append(node(v[0]-.85,v[1]-(1.7 if IS9 else 1.0),f'{q:g}','anchor=east,inner sep=0'))
    v=vec(2.5,4,0,shift); out.append(node(v[0],v[1]-(6.3 if IS9 else 3.3),r'$\lambda$','inner sep=0'))
    v=vec(0,2,0,shift); out.append(node(v[0]-(6.0 if IS9 else 3.6),v[1]-(4.4 if IS9 else 3.0),r'$q$','inner sep=0'))
    out.append(node(shift+(3.0 if IS9 else 4.2),27.5,metric,'rotate=90,inner sep=0'))
    out.append(node(shift+21.8,8.5,'(a) Mean ACC' if metric=='ACC' else '(b) Mean NMI','inner sep=0',r'\normalfont\rmfamily\mdseries\upshape\fontsize{9.2}{10.5}\selectfont'))
out.append(r'\end{tikzpicture}')
(ROOT/'plot_tikz.tex').write_text('\n'.join(out)+'\n')
(ROOT/'figure_standalone.tex').write_text(r'''\documentclass[border=0pt]{standalone}
\usepackage{newtxtext,newtxmath}
\usepackage{tikz}
\begin{document}
\input{plot_tikz.tex}
\end{document}
''')
(ROOT/'preview_with_caption.tex').write_text(r'''\documentclass[border=0pt]{standalone}
\usepackage{newtxtext,newtxmath}
\usepackage{graphicx}
\begin{document}
\begin{minipage}{86mm}
\centering
\includegraphics[width=\linewidth]{figures/psf_acc_nmi_reference.pdf}\par
\vspace{0.2mm}
{\fontsize{9.2}{10.6}\selectfont Fig. 1: Clustering ACC and NMI of PSF-CE.\par}
\end{minipage}
\end{document}
''')
(ROOT/'data'/'DATA_AUDIT.json').write_text(json.dumps({
 'source':'results.zip/results/formal_oracle.csv',
 'source_archive_sha256':'4d536e1adb00e83cdfc86904bcfb046b3e4e2ef5f3e2864a3ff211a33bf07fbb',
 'method':'PSF_ORACLE_QR','solver':'spectral/cluster_qr',
 'full_grid_rows':35616,'n_datasets':53,'pools_per_dataset':3,
 'selected_q':qs,'selected_lambda':ls,'bars_per_panel':20,
 'aggregation':'mean over 3 pools within each dataset, then unweighted mean over 53 datasets',
 'selection_rule':'re-use previously displayed parameter-only subgrid for legibility; no outcome-based selection',
 'metric_units':'absolute ACC/NMI, not percent; bars start at zero',
 'z_axis_range':[0,.5],
 'plot_mode':args.mode,
 'no_synthetic_values':True,'no_interpolation':True
},indent=2))
print(selected.to_string(index=False))
