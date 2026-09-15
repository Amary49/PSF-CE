#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import pandas as pd
from sklearn.datasets import load_iris,load_wine,load_breast_cancer,load_digits,make_blobs
from psfce.generate import generate_base_partitions
from psfce.dataio import save_pool_npz


def main():
    root=Path("demo_data"); root.mkdir(exist_ok=True)
    datasets=[]
    for name,loader in [("iris",load_iris),("wine",load_wine),("breast_cancer",load_breast_cancer)]:
        b=loader(); datasets.append((name,b.data,b.target))
    d=load_digits(); datasets.append(("digits_1000",d.data[:1000],d.target[:1000]))
    X,y=make_blobs(n_samples=900,centers=8,cluster_std=2.0,n_features=18,random_state=7); datasets.append(("synthetic8",X,y))
    rows=[]
    for j,(name,X,y) in enumerate(datasets):
        parts,_=generate_base_partitions(X,len(set(y)),n_base=20,seed=2027+j)
        p=root/f"{name}__pool0.npz"; save_pool_npz(p,y,parts)
        split="dev" if j < 3 else "formal"
        family = "classic_tabular" if name in {"iris","wine"} else ("medical_tabular" if name=="breast_cancer" else ("image" if name.startswith("digits") else "synthetic"))
        rows.append({"name":name,"pool":"0","path":p.name,"group":"demo","split":split,"source_id":name,"task_family":family})
    pd.DataFrame(rows).to_csv(root/"manifest.csv",index=False); print(root/"manifest.csv")
if __name__=="__main__": main()
