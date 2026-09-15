#!/usr/bin/env python
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
from sklearn.datasets import make_blobs
from psfce.generate import generate_base_partitions
from psfce.pair_spectrum import PairSpectrumFamily


def main():
    root=Path(__file__).resolve().parents[1]
    cp=subprocess.run([sys.executable,'-m','pytest','-q',str(root/'tests')],cwd=root,text=True,capture_output=True)
    X,y=make_blobs(n_samples=140,centers=5,n_features=9,cluster_std=1.8,random_state=23)
    parts,_=generate_base_partitions(X,5,n_base=8,seed=23); f=PairSpectrumFamily(parts)
    payload={'pytest_returncode':cp.returncode,'pytest_stdout':cp.stdout.strip(),
             'q1_raw_collapse_error':f.q1_raw_collapse_error(),
             'max_energy_error_q2':float(f.filter_energy_errors(2).max(initial=0.0)),
             'calibration_error_q2':f.calibration_error(2),
             'commutator_q2':f.commutator_ratio(2),
             'passed':bool(cp.returncode==0 and f.q1_raw_collapse_error()<1e-8 and f.calibration_error(2)<1e-8)}
    out=root/'runtime_results'/'core_validation.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2)); raise SystemExit(0 if payload['passed'] else 1)
if __name__=='__main__': main()
