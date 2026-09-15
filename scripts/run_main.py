#!/usr/bin/env python
from __future__ import annotations
import argparse,json
from pathlib import Path
from psfce.dataio import load_manifest,validate_manifest
from psfce.experiments import run_parallel,run_frozen_for_record


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--frozen',default='configs/frozen/main_methods.json'); ap.add_argument('--config',default='configs/frozen/formal_main.json'); ap.add_argument('--output',default='runtime_results/main'); ap.add_argument('--workers',type=int,default=1); ap.add_argument('--force',action='store_true')
    a=ap.parse_args(); cfg=json.loads(Path(a.config).read_text()); fr=json.loads(Path(a.frozen).read_text())['methods']
    for m in cfg.get('exclude_methods',[]): fr.pop(m,None)
    for m in cfg.get('native_methods',[]): fr.setdefault(m,{})
    allr=load_manifest(a.manifest); validate_manifest(allr,require_disjoint=True,expected_M=cfg.get('expected_M')); r=[x for x in allr if x.split.lower() in {'formal','test','heldout'}]
    if not r: raise SystemExit('no formal rows')
    df,path=run_parallel(r,run_frozen_for_record,(fr,cfg['options']),a.output,'main_frozen',a.workers,a.force); print(path,len(df))
if __name__=='__main__': main()
