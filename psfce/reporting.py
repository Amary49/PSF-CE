from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .metrics import paired_wilcoxon, holm_adjust, bootstrap_mean_ci


def parse_params(df):
    out=df.copy(); vals=[]
    for s in out["params"].fillna("{}").astype(str):
        try: vals.append(json.loads(s))
        except Exception: vals.append({})
    keys=sorted({k for d in vals for k in d})
    for k in keys: out[k]=[d.get(k,np.nan) for d in vals]
    return out


def dataset_method_means(df):
    ok=df[df["status"].eq("ok")].copy() if "status" in df else df.copy()
    metrics=[m for m in ["ACC","NMI","ARI","F1","runtime_seconds"] if m in ok]
    # Dataset/method is the statistical unit; group metadata are merged back only when informative.
    dm=ok.groupby(["dataset","method"],as_index=False,dropna=False)[metrics].mean(numeric_only=True)
    for meta in ["group","task_family"]:
        if meta in ok.columns and ok[meta].fillna("").astype(str).str.len().gt(0).any():
            mm=ok[["dataset",meta]].copy(); mm[meta]=mm[meta].fillna("").astype(str)
            mm=mm[mm[meta].str.len()>0].drop_duplicates("dataset")
            dm=dm.merge(mm,on="dataset",how="left")
    return dm


def add_average_ranks(dm,metric="ACC"):
    p=dm.pivot(index="dataset",columns="method",values=metric)
    ranks=p.rank(axis=1,ascending=False,method="average")
    return ranks.mean(axis=0).sort_values()


def comparison_summary(df,primary="PSF-CE",tie_pp=0.05):
    dm=dataset_method_means(df); p=dm[dm.method.eq(primary)].set_index("dataset")
    rows=[]; raw=[]
    for method in sorted(m for m in dm.method.unique() if m!=primary):
        b=dm[dm.method.eq(method)].set_index("dataset"); common=p.index.intersection(b.index)
        if not len(common): continue
        d=(p.loc[common,"ACC"]-b.loc[common,"ACC"])*100
        pv=paired_wilcoxon(p.loc[common,"ACC"],b.loc[common,"ACC"]); lo,hi=bootstrap_mean_ci(d.values,n_boot=5000)
        rows.append({"baseline":method,"n":len(common),"W":int(np.sum(d>tie_pp)),"T":int(np.sum(np.abs(d)<=tie_pp)),"L":int(np.sum(d<-tie_pp)),
                     "mean_delta_pp":float(d.mean()),"median_delta_pp":float(d.median()),"ci95_lo_pp":lo,"ci95_hi_pp":hi,"p":pv})
        raw.append(pv)
    if rows:
        for r,a in zip(rows,holm_adjust(raw)): r["p_holm"]=float(a)
    return pd.DataFrame(rows)


def _setting_table(df,method):
    g=parse_params(df[(df.status=="ok") & (df.method==method)].copy())
    if len(g)==0: return g
    param_cols=[c for c in ["q","lambda","eta","alpha","gamma","q_after"] if c in g.columns and g[c].notna().any()]
    per=g.groupby(["dataset",*param_cols],as_index=False)[["ACC","NMI","ARI","F1"]].mean(numeric_only=True)
    return per,param_cols


def freeze_all(dev_strong_csv,output_json,policy="family_robust",epsilon_pp=0.15):
    df=parse_params(pd.read_csv(dev_strong_csv)); methods=sorted(df[df.status.eq("ok")].method.unique())
    frozen={}; diagnostics={}
    for method in methods:
        g=df[(df.status=="ok") & (df.method==method)].copy()
        param_cols=[c for c in ["q","lambda","eta","alpha","gamma","q_after"] if c in g.columns and g[c].notna().any()]
        if not param_cols:
            frozen[method]={}; continue
        per=g.groupby(["dataset",*param_cols],as_index=False)[["ACC","NMI","ARI","F1"]].mean(numeric_only=True)
        if "task_family" in g.columns:
            mp=g[["dataset","task_family"]].copy(); mp["task_family"]=mp.task_family.fillna("").astype(str); mp=mp.drop_duplicates("dataset")
            per=per.merge(mp,on="dataset",how="left")
        else: per["task_family"]=""
        use_family=policy=="family_robust" and per.task_family.fillna("").str.len().gt(0).any()
        rows=[]
        for key,sg in per.groupby(param_cols,dropna=False):
            if not isinstance(key,tuple): key=(key,)
            score=float(sg.groupby("task_family").ACC.mean().mean()) if use_family else float(sg.ACC.mean())
            row={k:float(v) for k,v in zip(param_cols,key)}
            row.update({"selection_ACC":score,"mean_ACC":float(sg.ACC.mean()),"q25_ACC":float(sg.ACC.quantile(.25)),
                        "median_ACC":float(sg.ACC.median()),"mean_NMI":float(sg.NMI.mean()),"mean_ARI":float(sg.ARI.mean()),
                        "datasets":int(sg.dataset.nunique()),"families":int(sg.task_family.replace('',np.nan).nunique())})
            rows.append(row)
        tab=pd.DataFrame(rows); best=float(tab.selection_ACC.max())
        if policy=="mean": cand=tab[np.isclose(tab.selection_ACC,best)]
        else: cand=tab[tab.selection_ACC>=best-float(epsilon_pp)/100.0]
        cand=cand.sort_values(["q25_ACC","median_ACC","selection_ACC","mean_NMI","mean_ARI"],ascending=False); b=cand.iloc[0]
        frozen[method]={k:float(b[k]) for k in param_cols}
        diagnostics[method]={"selection_score_ACC":float(b.selection_ACC),"best_selection_ACC":best,"selected_mean_ACC":float(b.mean_ACC),
                             "q25_ACC":float(b.q25_ACC),"median_ACC":float(b.median_ACC),"datasets":int(b.datasets),
                             "families":int(b.families),"family_balanced":bool(use_family),"candidates_within_epsilon":int(len(cand))}
    payload={"policy":policy,"epsilon_pp":float(epsilon_pp),"methods":frozen,"diagnostics":diagnostics}
    payload["development_csv_sha256"]=hashlib.sha256(Path(dev_strong_csv).read_bytes()).hexdigest()
    Path(output_json).parent.mkdir(parents=True,exist_ok=True); Path(output_json).write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    return payload

def oracle_capacity_table(oracle_csv):
    df=parse_params(pd.read_csv(oracle_csv)); qr=df[(df.status=="ok") & df.method.eq("PSF_ORACLE_QR")].copy()
    rows=[]
    for (ds,pool),g in qr.groupby(["dataset","pool"]):
        a=g[np.isclose(g["lambda"].astype(float),0.0)].sort_values(["ACC","NMI","ARI"],ascending=False).iloc[0]
        lin=g[np.isclose(g["q"].astype(float),1.0)].sort_values(["ACC","NMI","ARI"],ascending=False).iloc[0]
        full=g.sort_values(["ACC","NMI","ARI"],ascending=False).iloc[0]
        for stage,r in [("A",a),("Best linear q=1",lin),("Full PSF",full)]:
            rows.append({"dataset":ds,"pool":pool,"stage":stage,"ACC":r.ACC,"NMI":r.NMI,"ARI":r.ARI,
                         "q":float(r.get("q",np.nan)),"lambda":float(r.get("lambda",np.nan))})
    return pd.DataFrame(rows)


def transfer_gap_table(main_csv,oracle_csv):
    main=parse_params(pd.read_csv(main_csv)); main=main[(main.status=="ok") & main.method.eq("PSF-CE")]
    oracle=parse_params(pd.read_csv(oracle_csv)); oracle=oracle[(oracle.status=="ok") & oracle.method.eq("PSF_ORACLE_STRONG_TOPK")]
    # Pool-matched same strong spectral solver. Formal oracle contains frozen setting by construction.
    best=oracle.sort_values(["ACC","NMI","ARI"],ascending=False).groupby(["dataset","pool"],as_index=False).first()
    f=main.groupby(["dataset","pool"],as_index=False)[["ACC","NMI","ARI"]].mean(numeric_only=True)
    x=best.merge(f,on=["dataset","pool"],suffixes=("_oracle","_frozen"))
    x["gap_ACC_pp"]=(x.ACC_oracle-x.ACC_frozen)*100
    return x


def _tex(s):
    return str(s).replace('\\','\\textbackslash{}').replace('_','\\_').replace('&','\\&').replace('%','\\%').replace('#','\\#')


def write_latex(main_csv=None,oracle_csv=None,solver_csv=None,output_dir="results/report/latex",primary="PSF-CE"):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    if main_csv and Path(main_csv).exists():
        df=pd.read_csv(main_csv); dm=dataset_method_means(df); ranks=add_average_ranks(dm)
        summ=dm.groupby("method")[["ACC","NMI","ARI","F1"]].mean()*100
        lines=[r"\begin{table}[t]",r"\centering",r"\caption{Frozen held-out performance averaged over datasets.}",r"\small",
               r"\begin{tabular}{lrrrrr}",r"\toprule",r"Method & ACC & NMI & ARI & F1 & Rank \\",r"\midrule"]
        for m,row in summ.sort_values("ACC",ascending=False).iterrows():
            lines.append("{} & {:.2f} & {:.2f} & {:.2f} & {:.2f} & {:.2f} \\".format(_tex(m),row.ACC,row.NMI,row.ARI,row.F1,ranks.get(m,np.nan)))
        lines += [r"\bottomrule",r"\end{tabular}",r"\label{tab:main_compact}",r"\end{table}"]
        (out/"main_compact.tex").write_text("\n".join(lines),encoding="utf-8")
        comp=comparison_summary(df,primary); comp.to_csv(out/"comparison_summary.csv",index=False)
        lines=[r"\begin{table}[t]",r"\centering",r"\caption{Paired ACC comparison against PSF-CE.}",r"\small",r"\begin{tabular}{lrrrr}",r"\toprule",r"Baseline & W/T/L & $\Delta$ (pp) & 95\% CI & $p_{Holm}$ \\",r"\midrule"]
        for _,r in comp.iterrows():
            lines.append("{} & {}/{}/{} & {:.2f} & [{:.2f},{:.2f}] & {:.3g} \\".format(_tex(r.baseline),int(r["W"]),int(r["T"]),int(r["L"]),r.mean_delta_pp,r.ci95_lo_pp,r.ci95_hi_pp,r.p_holm))
        lines += [r"\bottomrule",r"\end{tabular}",r"\label{tab:paired}",r"\end{table}"]
        (out/"paired_comparison.tex").write_text("\n".join(lines),encoding="utf-8")
        piv=dm.pivot(index="dataset",columns="method",values="ACC")*100; piv.to_csv(out/"main_dataset_acc.csv")
    if oracle_csv and Path(oracle_csv).exists():
        cap=oracle_capacity_table(oracle_csv); cap.to_csv(out/"oracle_capacity.csv",index=False)
        st=cap.groupby("stage")[["ACC","NMI","ARI"]].mean()*100
        order=[x for x in ["A","Best linear q=1","Full PSF"] if x in st.index]
        lines=[r"\begin{table}[t]",r"\centering",r"\caption{Nested formal oracle capacity under the same QR spectral solver.}",r"\small",r"\begin{tabular}{lrrr}",r"\toprule",r"Model family & ACC & NMI & ARI \\",r"\midrule"]
        for stage in order:
            rr=st.loc[stage]; lines.append("{} & {:.2f} & {:.2f} & {:.2f} \\".format(_tex(stage),rr.ACC,rr.NMI,rr.ARI))
        lines += [r"\bottomrule",r"\end{tabular}",r"\label{tab:capacity}",r"\end{table}"]
        (out/"oracle_capacity.tex").write_text("\n".join(lines),encoding="utf-8")
        if main_csv and Path(main_csv).exists():
            gap=transfer_gap_table(main_csv,oracle_csv); gap.to_csv(out/"transfer_gap.csv",index=False)
            summary={"mean_gap_pp":float(gap.gap_ACC_pp.mean()),"median_gap_pp":float(gap.gap_ACC_pp.median()),
                     "max_gap_pp":float(gap.gap_ACC_pp.max()),"negative_gap_count":int(np.sum(gap.gap_ACC_pp<-1e-9))}
            (out/"transfer_gap_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    if solver_csv and Path(solver_csv).exists():
        pd.read_csv(solver_csv).to_csv(out/"solver_ablation.csv",index=False)

def plot_surface(search_csv,output_pdf,method="PSF-CE",metric="ACC"):
    df=parse_params(pd.read_csv(search_csv)); g=df[(df.status=="ok") & df.method.eq(method)]
    if not {"q","lambda"}.issubset(g.columns): return False
    d=g.groupby(["dataset","q","lambda"],as_index=False)[metric].mean(numeric_only=True)
    m=d.groupby(["q","lambda"],as_index=False)[metric].mean(numeric_only=True)
    p=m.pivot(index="q",columns="lambda",values=metric).sort_index().sort_index(axis=1)
    fig,ax=plt.subplots(figsize=(6.4,4.0)); im=ax.imshow(p.values,aspect="auto",origin="lower")
    ax.set_xticks(range(len(p.columns))); ax.set_xticklabels([f"{v:g}" for v in p.columns],rotation=45,ha="right")
    ax.set_yticks(range(len(p.index))); ax.set_yticklabels([f"{v:g}" for v in p.index]); ax.set_xlabel(r"$\lambda$"); ax.set_ylabel(r"$q$")
    ax.set_title(f"{method}: mean {metric}"); fig.colorbar(im,ax=ax,label=metric); fig.tight_layout()
    Path(output_pdf).parent.mkdir(parents=True,exist_ok=True); fig.savefig(output_pdf,bbox_inches="tight"); plt.close(fig); return True


def plot_solver_convergence(solver_csv,output_pdf,max_curves=12):
    df=pd.read_csv(solver_csv); g=df[(df.status=="ok") & df.method.eq("PSF-CE+Relocation") & df.history_json.fillna("").ne("")].head(max_curves)
    if len(g)==0: return False
    fig,ax=plt.subplots(figsize=(6.0,3.8))
    for _,r in g.iterrows():
        h=np.asarray(json.loads(r.history_json),dtype=float)
        if len(h)>1: ax.plot(np.arange(len(h)),h-h[0],linewidth=1.2,label=f"{r.dataset}/{r.pool}")
    ax.set_xlabel("Relocation sweep"); ax.set_ylabel("Objective increase"); ax.set_title("Optional relocation convergence")
    if len(g)<=8: ax.legend(fontsize=7)
    fig.tight_layout(); Path(output_pdf).parent.mkdir(parents=True,exist_ok=True); fig.savefig(output_pdf,bbox_inches="tight"); plt.close(fig); return True



def write_results_text(main_csv,oracle_csv,output_path,primary="PSF-CE"):
    parts=[]
    if main_csv and Path(main_csv).exists():
        df=pd.read_csv(main_csv); dm=dataset_method_means(df); means=dm.groupby("method")[["ACC","NMI","ARI","F1"]].mean()
        if primary in means.index:
            p=means.loc[primary]; others=means.drop(index=primary,errors="ignore")
            if len(others):
                best_name=others.ACC.idxmax(); b=others.loc[best_name]; delta=(p.ACC-b.ACC)*100
                comp=comparison_summary(df,primary); cr=comp[comp.baseline.eq(best_name)]
                pair=""
                if len(cr):
                    r=cr.iloc[0]; pair=f" The paired ACC comparison is {int(r['W'])}/{int(r['T'])}/{int(r['L'])} (W/T/L), with a Holm-adjusted $p$-value of {r.p_holm:.3g}."
                parts.append(f"\\paragraph{{Frozen evaluation.}} { _tex(primary) } obtains mean ACC/NMI/ARI of {p.ACC*100:.2f}/{p.NMI*100:.2f}/{p.ARI*100:.2f}\\%, compared with {b.ACC*100:.2f}/{b.NMI*100:.2f}/{b.ARI*100:.2f}\\% for the strongest non-PSF control ({_tex(best_name)}), an ACC difference of {delta:.2f} percentage points.{pair}")
    if oracle_csv and Path(oracle_csv).exists():
        cap=oracle_capacity_table(oracle_csv).groupby("stage")[["ACC","NMI","ARI"]].mean()
        if all(x in cap.index for x in ["A","Best linear q=1","Full PSF"]):
            a,lin,full=cap.loc["A"],cap.loc["Best linear q=1"],cap.loc["Full PSF"]
            parts.append(f"\\paragraph{{Mechanism capacity.}} Under the solver-matched formal oracle diagnostic, ACC increases from {a.ACC*100:.2f}\\% for first-order consensus to {lin.ACC*100:.2f}\\% for the best linear pair interaction and {full.ACC*100:.2f}\\% for the full nonlinear pair-mode family. The nonlinear stage therefore contributes {(full.ACC-lin.ACC)*100:.2f} additional percentage points beyond the best $q=1$ response.")
        if main_csv and Path(main_csv).exists():
            gap=transfer_gap_table(main_csv,oracle_csv)
            parts.append(f"\\paragraph{{Parameter transfer.}} The screened strong oracle exceeds the frozen PSF-CE setting by {gap.gap_ACC_pp.mean():.2f} percentage points on average (median {gap.gap_ACC_pp.median():.2f}), using the same strong spectral solver in both cases.")
    Path(output_path).parent.mkdir(parents=True,exist_ok=True); Path(output_path).write_text("\n\n".join(parts),encoding="utf-8")

def build_report(main_csv=None,dev_csv=None,oracle_csv=None,solver_csv=None,output_dir="results/report"):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); lines=["# PSF-CE V2 Experiment Report",""]
    if dev_csv and Path(dev_csv).exists():
        d=parse_params(pd.read_csv(dev_csv)); p=d[(d.status=="ok") & d.method.eq("PSF-CE")]
        if len(p):
            t=p.groupby(["dataset","q","lambda"],as_index=False)[["ACC","NMI","ARI"]].mean(numeric_only=True)
            g=t.groupby(["q","lambda"],as_index=False)[["ACC","NMI","ARI"]].mean(numeric_only=True).sort_values(["ACC","NMI","ARI"],ascending=False)
            b=g.iloc[0]; lines += ["## Development strong search",f"Top global setting in evaluated strong candidates: q={b.q:g}, lambda={b['lambda']:g}, ACC={b.ACC:.4f}.",""]
    if main_csv and Path(main_csv).exists():
        df=pd.read_csv(main_csv); dm=dataset_method_means(df); means=dm.groupby("method")[["ACC","NMI","ARI","F1"]].mean().sort_values("ACC",ascending=False)
        lines += ["## Frozen formal main"]
        for m,r in means.iterrows(): lines.append(f"- {m}: ACC={r.ACC:.4f}, NMI={r.NMI:.4f}, ARI={r.ARI:.4f}, F1={r.F1:.4f}")
        comp=comparison_summary(df); lines += ["","### PSF-CE paired ACC"]
        for _,r in comp.iterrows(): lines.append(f"- vs {r.baseline}: W/T/L={int(r["W"])}/{int(r["T"])}/{int(r["L"])}, mean Δ={r.mean_delta_pp:.3f} pp, Holm p={r.p_holm:.4g}")
        lines.append("")
    if oracle_csv and Path(oracle_csv).exists():
        cap=oracle_capacity_table(oracle_csv); s=cap.groupby("stage")[["ACC","NMI","ARI"]].mean()
        lines += ["## Formal oracle capacity (diagnostic; not frozen claim)"]
        for stage,r in s.iterrows(): lines.append(f"- {stage}: ACC={r.ACC:.4f}, NMI={r.NMI:.4f}, ARI={r.ARI:.4f}")
        if main_csv and Path(main_csv).exists():
            gap=transfer_gap_table(main_csv,oracle_csv); lines += ["",f"Strong-solver screened oracle minus frozen PSF-CE: mean {gap.gap_ACC_pp.mean():.3f} pp; median {gap.gap_ACC_pp.median():.3f} pp; negative gaps={int(np.sum(gap.gap_ACC_pp<-1e-9))}."]
    if solver_csv and Path(solver_csv).exists():
        s=pd.read_csv(solver_csv); dm=dataset_method_means(s); m=dm.groupby("method")[["ACC","NMI","ARI"]].mean(); lines += ["","## Solver ablation"]
        for method,r in m.iterrows(): lines.append(f"- {method}: ACC={r.ACC:.4f}, NMI={r.NMI:.4f}, ARI={r.ARI:.4f}")
    (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    write_latex(main_csv,oracle_csv,solver_csv,out/"latex")
    write_results_text(main_csv,oracle_csv,out/"latex"/"results_text.tex")
    if dev_csv and Path(dev_csv).exists(): plot_surface(dev_csv,out/"dev_surface.pdf")
    if oracle_csv and Path(oracle_csv).exists(): plot_surface(oracle_csv,out/"formal_oracle_surface.pdf",method="PSF_ORACLE_QR")
    if solver_csv and Path(solver_csv).exists(): plot_solver_convergence(solver_csv,out/"relocation_convergence.pdf")
