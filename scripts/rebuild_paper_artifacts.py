#!/usr/bin/env python3
"""Rebuild paper-v1 tables/statistics and a vector verification figure.

This script reads recorded scores only. It does not execute clustering and does
not recompute metrics from raw labels or predictions.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
METRICS = ["ACC", "NMI", "ARI", "F1"]
METHODS = ["CA", "Poly2", "LinearPair", "AggregatePower", "CEHM", "YACHT", "RANGE", "PSF-CE"]
ABLATION = ["w/o interaction", "PSF-CE w/o nonlinear filtering", "PSF-CE"]

def holm(values):
    p=np.asarray(values,float); order=np.argsort(p)
    adj=np.minimum(1.,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    out=np.empty_like(p); out[order]=adj; return out

def validate_frame(frame, methods):
    assert set(frame.method)==set(methods)
    assert frame.status.eq("ok").all()
    assert not frame.duplicated(["dataset","pool","method"]).any()
    assert frame.groupby("method").size().eq(159).all()
    assert frame.groupby("method").dataset.nunique().eq(53).all()
    assert frame.groupby(["method","dataset"]).size().eq(3).all()
    assert frame.M.eq(20).all() and np.isfinite(frame[METRICS]).all().all()

def paired(scores, baselines, rng_seed=2027):
    rows=[]; rng=np.random.default_rng(rng_seed)
    for b in baselines:
        d=scores["PSF-CE"]-scores[b]; pp=100*d
        p=1.0 if np.all(np.abs(d)<1e-15) else float(wilcoxon(d,alternative="two-sided",zero_method="wilcox").pvalue)
        boot=rng.choice(pp.to_numpy(),size=(20000,len(pp)),replace=True).mean(axis=1)
        rows.append({"baseline":b,"datasets":len(pp),"W":int((pp>.05).sum()),"T":int((np.abs(pp)<=.05).sum()),"L":int((pp<-.05).sum()),"mean_delta_pp":float(pp.mean()),"median_delta_pp":float(pp.median()),"p_two_sided":p,"ci95_lower_pp":float(np.quantile(boot,.025)),"ci95_upper_pp":float(np.quantile(boot,.975))})
    out=pd.DataFrame(rows); out["p_holm"]=holm(out.p_two_sided); return out

def tex_summary(summary, path):
    lines=[r"\begin{tabular}{lrrrrr}",r"\toprule",r"Method & ACC & NMI & ARI & F1 & ACC rank \\",r"\midrule"]
    for m,row in summary.iterrows():
        label=r"\textbf{PSF-CE}" if m=="PSF-CE" else m
        lines.append(f"{label} & {row.ACC:.2f} & {row.NMI:.2f} & {row.ARI:.2f} & {row.F1:.2f} & {row.ACC_avg_rank:.2f} \\\\")
    lines += [r"\bottomrule",r"\end{tabular}"]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=ROOT/"rebuild_output"); a=ap.parse_args()
    out=a.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    art=ROOT/"artifacts"/"paper_v1"
    internal=pd.read_csv(art/"scores"/"main_five_methods_pool_scores.csv")
    recent=pd.read_csv(art/"scores"/"recent_three_methods_pool_scores.csv")
    validate_frame(internal,METHODS[:4]+["PSF-CE"]); validate_frame(recent,METHODS[4:7])
    raw=pd.concat([internal,recent],ignore_index=True,sort=False)
    validate_frame(raw,METHODS)
    dm=raw.groupby(["dataset","method"])[METRICS].mean()
    scores=dm.ACC.unstack("method").reindex(columns=METHODS)
    summary=(100*dm).groupby("method").mean().reindex(METHODS)
    summary["ACC_avg_rank"]=scores.rank(axis=1,ascending=False,method="average").mean().reindex(METHODS)
    summary.to_csv(out/"main_summary_53datasets.csv",float_format="%.17g")
    dm.reset_index().to_csv(out/"main_dataset_means_53x8.csv",index=False,float_format="%.17g")
    tests=paired(scores,[m for m in METHODS if m!="PSF-CE"])
    tests.to_csv(out/"main_paired_acc_recomputed_current_env.csv",index=False,float_format="%.17g")
    tex_summary(summary,out/"main_summary.tex")

    selection=json.loads((ROOT/"configs"/"examples"/"main_table_selection.json").read_text(encoding="utf-8"))["datasets"]
    names=[x["name"] for x in selection]; ids=[x["id"] for x in selection]
    values=100*dm
    lines=[r"\begin{tabular}{l"+"r"*(2*len(names))+"}",r"\toprule", "Method & "+" & ".join(ids+ids)+r" \\",r"\midrule"]
    for m in METHODS:
        cells=[]
        for metric in ["ACC","NMI"]:
            for n in names: cells.append(f"{values.loc[(n,m),metric]:.2f}")
        lines.append(m+" & "+" & ".join(cells)+r" \\")
    lines += [r"\bottomrule",r"\end{tabular}"]
    (out/"main_selected10_acc_nmi.tex").write_text("\n".join(lines)+"\n",encoding="utf-8")

    abl=pd.read_csv(art/"scores"/"fixed_strength_ablation_pool_scores.csv")
    assert set(abl.variant)==set(ABLATION) and len(abl)==477 and abl.status.eq("ok").all()
    assert not abl.duplicated(["dataset","pool","variant"]).any()
    assert abl.groupby(["variant","dataset"]).size().eq(3).all()
    adm=abl.groupby(["variant","dataset"])[METRICS].mean()
    asum=(100*adm).groupby("variant").mean().reindex(ABLATION)
    asum.to_csv(out/"ablation_summary.csv",float_format="%.17g")
    ascores=adm.ACC.unstack("variant")
    atests=paired(ascores,["w/o interaction","PSF-CE w/o nonlinear filtering"],rng_seed=2027)
    atests.to_csv(out/"ablation_paired_acc_recomputed_current_env.csv",index=False,float_format="%.17g")
    lines=[r"\begin{tabular}{lrrr}",r"\toprule",r"Variant & ACC & NMI & ARI \\",r"\midrule"]
    for v,row in asum.iterrows(): lines.append(f"{v} & {row.ACC:.2f} & {row.NMI:.2f} & {row.ARI:.2f} \\\\")
    lines += [r"\bottomrule",r"\end{tabular}"]
    (out/"fixed_strength_ablation.tex").write_text("\n".join(lines)+"\n",encoding="utf-8")

    grid=pd.read_csv(ROOT/"figures"/"data"/"plotted_grid_acc_nmi.csv")
    assert len(grid)==20 and not grid.duplicated(["q","lambda"]).any()
    qs=sorted(grid.q.unique()); ls=sorted(grid["lambda"].unique())
    fig=plt.figure(figsize=(7.16,3.25)); colors=plt.cm.viridis(np.linspace(.15,.95,len(ls)))
    for k,metric in enumerate(["ACC","NMI"],1):
        ax=fig.add_subplot(1,2,k,projection="3d")
        for j,lam in enumerate(ls):
            g=grid[grid["lambda"].eq(lam)].set_index("q").reindex(qs)
            ax.bar3d(np.full(len(qs),j)-.32,np.arange(len(qs))-.32,np.zeros(len(qs)),.64,.64,g[metric].to_numpy(),color=colors[j],edgecolor="0.25",linewidth=.25,shade=True)
        ax.set_xticks(range(len(ls)),[f"{x:g}" for x in ls]); ax.set_yticks(range(len(qs)),[f"{x:g}" for x in qs])
        ax.set_xlabel(r"$\lambda$"); ax.set_ylabel(r"$q$"); ax.set_zlabel(metric); ax.set_zlim(0,.5)
        ax.set_title(f"({'a' if k==1 else 'b'}) Mean {metric}",fontweight="normal",fontsize=9)
        ax.tick_params(labelsize=7); ax.view_init(elev=24,azim=-56)
    fig.tight_layout(); fig.savefig(out/"psf_acc_nmi_rebuilt.pdf",format="pdf",bbox_inches="tight"); plt.close(fig)
    report={"schema":"psfce-paper-v1-rebuild-v1","main_rows":len(raw),"methods":METHODS,"datasets":53,"pools_per_method":159,"ablation_rows":len(abl),"figure_grid_rows":len(grid),"statistics_unit":"dataset after three-pool mean","statistical_note":"Recomputed statistics are explicitly named current_env; archived historical statistics are never overwritten.","scores_recomputed_from_labels":False,"algorithm_executed":False}
    (out/"REBUILD_REPORT.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
