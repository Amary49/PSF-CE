#!/usr/bin/env python
from __future__ import annotations
import argparse,json
from pathlib import Path
from psfce.dataio import load_manifest,validate_manifest
from psfce.recent_baseline_experiments import run_parallel


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--registry',default='configs/frozen/recent_baselines_registry.json')
    ap.add_argument('--frozen',default='configs/frozen/recent_baselines.json'); ap.add_argument('--output',default='runtime_results/recent'); ap.add_argument('--workers',type=int,default=2); ap.add_argument('--force',action='store_true')
    a=ap.parse_args(); fr=json.loads(Path(a.frozen).read_text()); settings=[{'name':m,'params':p} for m,p in fr['methods'].items()]
    rec=load_manifest(a.manifest); validate_manifest(rec,require_disjoint=True,expected_M=20); formal=[r for r in rec if r.split.lower() in {'formal','test','heldout'}]
    if len(formal)!=159 or len({r.name for r in formal})!=53 or any(sum(x.name==r.name for x in formal)!=3 for r in formal):
        raise SystemExit('formal manifest must contain exactly 53 datasets x 3 pools')
    options={'seed':2027,'cache_dir':str(Path(a.output)/'cache'),'package_root':str(Path(__file__).resolve().parents[1])}
    df,path=run_parallel(formal,settings,a.registry,options,a.output,'recent_main_frozen',a.workers,a.force); print(path); print(f'rows={len(df)}')
if __name__=='__main__': main()
