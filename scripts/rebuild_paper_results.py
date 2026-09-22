from __future__ import annotations
import argparse, csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "artifacts" / "paper_revised_core10" / "scores" / "main_pool_scores.csv"
DATASETS = ["BBC News Sport","Leukemia","Caltech101-20","Leukemia2","Chameleon","Amazon Photo","ORL","ACM","Iris","Mushroom"]
METHODS = ["MCLA","HBGF","CEHM","YACHT","RANGE","GPEC","PSF-CE"]
METRICS = ["ACC","NMI","ARI","F1"]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", required=True); args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    rows=list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    keys={(r["dataset"],int(r["pool"]),r["method"]) for r in rows}
    expected={(d,p,m) for d in DATASETS for p in range(3) for m in METHODS}
    if len(rows)!=210 or keys!=expected: raise SystemExit(f"coverage failure: rows={len(rows)}, missing={len(expected-keys)}, extra={len(keys-expected)}")
    buckets=defaultdict(list)
    for r in rows: buckets[(r["dataset"],r["method"])].append(r)
    ds=[]
    for d in DATASETS:
      for m in METHODS:
        rs=buckets[(d,m)]; item={"dataset":d,"method":m}
        for metric in METRICS: item[metric]=sum(float(x[metric]) for x in rs)/3
        ds.append(item)
    with (out/"main_results_dataset_means.csv").open("w",encoding="utf-8",newline="") as f:
      w=csv.DictWriter(f,fieldnames=["dataset","method"]+METRICS); w.writeheader(); w.writerows(ds)
    summary=[]
    for m in METHODS:
      rs=[r for r in ds if r["method"]==m]; item={"method":m}
      for metric in METRICS: item[metric]=sum(float(x[metric]) for x in rs)/10
      summary.append(item)
    for metric in METRICS:
      order=sorted(summary,key=lambda x:-x[metric]); rank={r["method"]:i+1 for i,r in enumerate(order)}
      for r in summary:r[metric+"_rank"]=rank[r["method"]]
    fields=["method"]+sum(([m,m+"_rank"] for m in METRICS),[])
    with (out/"main_results_method_summary.csv").open("w",encoding="utf-8",newline="") as f:
      w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(summary)
    print("PASS: rebuilt revised Core-10 summaries from 210 archived pool rows")
if __name__=="__main__": main()
