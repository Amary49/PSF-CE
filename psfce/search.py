from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .reporting import parse_params


def rank_settings(csv_path,method):
    df=parse_params(pd.read_csv(csv_path)); g=df[(df.status=="ok") & df.method.eq(method)].copy()
    param_cols=[c for c in ["q","lambda","eta","alpha","gamma","q_after"] if c in g.columns and g[c].notna().any()]
    if not param_cols:
        return pd.DataFrame([{"mean_ACC":g.groupby("dataset").ACC.mean().mean()}]),[]
    per=g.groupby(["dataset",*param_cols],as_index=False)[["ACC","NMI","ARI","F1"]].mean(numeric_only=True)
    tab=per.groupby(param_cols,as_index=False)[["ACC","NMI","ARI","F1"]].mean(numeric_only=True)
    tab=tab.rename(columns={"ACC":"mean_ACC","NMI":"mean_NMI","ARI":"mean_ARI","F1":"mean_F1"})
    tab=tab.sort_values(["mean_ACC","mean_NMI","mean_ARI"],ascending=False).reset_index(drop=True)
    return tab,param_cols


def _unique_settings(settings):
    seen=set(); out=[]
    for s in settings:
        key=(s["name"],json.dumps(s.get("params",{}),sort_keys=True))
        if key not in seen: seen.add(key); out.append(s)
    return out


def propose_strong_candidates(broad_csv,topk=12,psf_neighborhood=True):
    df=pd.read_csv(broad_csv); methods=sorted(df[df.status.eq("ok")].method.unique()); settings=[]
    for method in methods:
        tab,cols=rank_settings(broad_csv,method)
        if not cols:
            settings.append({"name":method,"params":{}}); continue
        for _,r in tab.head(topk).iterrows():
            settings.append({"name":method,"params":{c:float(r[c]) for c in cols}})
        if method=="PSF-CE" and psf_neighborhood and {"q","lambda"}.issubset(cols):
            for _,r in tab.head(min(4,topk)).iterrows():
                q=float(r.q); lam=float(r["lambda"])
                qvals=sorted(set([q,max(0.2,q*0.8),q*0.9,q*1.1,q*1.25]))
                if lam==0: lvals=[0.0,0.05,0.1]
                else: lvals=sorted(set([lam,lam*0.75,lam*0.9,lam*1.1,lam*1.33]))
                for qq in qvals:
                    for ll in lvals: settings.append({"name":"PSF-CE","params":{"q":round(qq,8),"lambda":round(ll,8)}})
        if method=="LinearPair":
            # Make sure q=1 linear family is densely represented around its broad optimum.
            for _,r in tab.head(min(3,topk)).iterrows():
                lam=float(r["lambda"]); vals=[lam] if lam==0 else [lam*0.75,lam*0.9,lam,lam*1.1,lam*1.33]
                for ll in vals: settings.append({"name":"LinearPair","params":{"lambda":round(float(ll),8)}})
    return _unique_settings(settings)
