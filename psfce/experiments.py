from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from itertools import product
from pathlib import Path
import json, time, traceback
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .cache import load_or_build_family
from .dataio import DatasetRecord, load_pool_npz
from .metrics import evaluate_clustering
from .models import (run_psfce,run_ca,run_poly2,
                     run_aggregate_power,run_psfce_relocation)
from .native_baselines import cspa,eac,hbgf,mcla
from .solver import RelocationConfig
from .utils import atomic_json_dump,safe_name,stable_hash


def _row_base(record,method,params,status="ok"):
    return {"dataset":record.name,"pool":record.pool,"group":record.group,"task_family":record.task_family,
            "split":record.split,"source_id":record.source_id,"method":method,
            "params":json.dumps(params,sort_keys=True),"status":status}


def _evaluate(record,y,pred,method,params,info,c,n,M):
    row=_row_base(record,method,params); row.update({"n":n,"c":c,"M":M,**evaluate_clustering(y,pred)})
    for key in ["runtime_seconds","spectral_seconds","objective","rounding_objective","eig_max","eig_min_topc",
                "commutator_ratio","interaction_scale"]:
        row[key]=float(info.get(key,np.nan))
    row.update({"solver":str(info.get("solver","")),"rounding":str(info.get("rounding","")),
                "sweeps":int(info.get("sweeps",0)),"moves":int(info.get("moves",0)),
                "history_json":json.dumps(info.get("history") or []),
                "rounding_candidates_json":json.dumps(info.get("rounding_candidates") or {},sort_keys=True),
                "skip_reason":str(info.get("skip_reason",""))})
    return row


def _dispatch(family,y,parts,c,method,params,options,rounding=None):
    seed=int(options.get("seed",2027)); n_init=int(options.get("kmeans_n_init",20))
    rounding=rounding or options.get("rounding","strong"); cal=options.get("calibration","fro_centered")
    if method=="PSF-CE": return run_psfce(family,c,float(params["lambda"]),float(params["q"]),seed,n_init,rounding,cal)
    if method=="LinearPair": return run_psfce(family,c,float(params["lambda"]),1.0,seed,n_init,rounding,cal)
    if method=="CA": return run_ca(family,c,seed,rounding,n_init)
    if method=="Poly2": return run_poly2(family,c,float(params.get("eta",0.25)),seed,rounding,n_init,True)
    if method=="AggregatePower": return run_aggregate_power(family,c,float(params.get("q_after",params.get("q",2.0))),seed,rounding,n_init)
    if method=="PSF-CE+Relocation":
        cfg=RelocationConfig(**options.get("relocation",{}))
        return run_psfce_relocation(family,c,float(params["lambda"]),float(params["q"]),seed,n_init,cal,cfg)
    if method=="CSPA":
        t=time.perf_counter(); z=cspa(parts,c,seed=seed,n_init=n_init); return z,{"runtime_seconds":time.perf_counter()-t,"solver":"native"}
    if method=="EAC":
        t=time.perf_counter(); z=eac(parts,c); return z,{"runtime_seconds":time.perf_counter()-t,"solver":"native"}
    if method=="HBGF":
        t=time.perf_counter(); z=hbgf(parts,c,seed=seed,n_init=n_init); return z,{"runtime_seconds":time.perf_counter()-t,"solver":"native"}
    if method=="MCLA":
        t=time.perf_counter(); z=mcla(parts,c); return z,{"runtime_seconds":time.perf_counter()-t,"solver":"native"}
    raise KeyError(method)


def expand_search_specs(search:dict):
    settings=[]
    for method,spec in search.items():
        if method=="CA" or not spec:
            settings.append({"name":method,"params":{}}); continue
        keys=list(spec.keys()); vals=[spec[k] if isinstance(spec[k],list) else [spec[k]] for k in keys]
        for combo in product(*vals): settings.append({"name":method,"params":dict(zip(keys,combo))})
    return settings


def _load_family(record,options):
    y,parts=load_pool_npz(record.path); c=len(np.unique(y))
    fam=load_or_build_family(parts,options.get("cache_dir"),options.get("svd_tol",1e-11))
    return y,parts,c,fam


def run_settings_for_record(record_dict,settings,options,rounding=None):
    record=DatasetRecord(**record_dict)
    with threadpool_limits(limits=int(options.get("blas_threads",1))):
        y,parts,c,family=_load_family(record,options); n=len(y); M=len(parts); rows=[]
        for spec in settings:
            method=spec["name"]; params=dict(spec.get("params",{}))
            try:
                pred,info=_dispatch(family,y,parts,c,method,params,options,rounding)
                rows.append(_evaluate(record,y,pred,method,params,info,c,n,M))
            except Exception as exc:
                row=_row_base(record,method,params,"error"); row.update({"n":n,"c":c,"M":M,"error":repr(exc),"traceback":traceback.format_exc()}); rows.append(row)
        return rows


def run_search_for_record(record_dict,search,options,rounding="qr"):
    return run_settings_for_record(record_dict,expand_search_specs(search),options,rounding)


def run_frozen_for_record(record_dict,frozen_methods,options):
    settings=[{"name":m,"params":p} for m,p in frozen_methods.items()]
    return run_settings_for_record(record_dict,settings,options,options.get("rounding_main","strong"))


def run_solver_ablation_for_record(record_dict,psf_params,options):
    settings=[{"name":"PSF-CE","params":psf_params},{"name":"PSF-CE+Relocation","params":psf_params}]
    return run_settings_for_record(record_dict,settings,options,"strong")


def run_formal_oracle_for_record(record_dict,psf_search,frozen_psf,options):
    """Two-stage solver-matched formal oracle diagnostic.

    Stage 1: full broad grid with cheap deterministic cluster_qr.
    Stage 2: label-selected top-K QR settings + frozen setting, all rerun with the
    same strong spectral rounding used by frozen main. The strong oracle therefore
    contains the frozen setting by construction and cannot be below it.
    """
    record=DatasetRecord(**record_dict)
    with threadpool_limits(limits=int(options.get("blas_threads",1))):
        y,parts,c,family=_load_family(record,options); n=len(y); M=len(parts)
        settings=expand_search_specs({"PSF-CE":psf_search})
        qr_rows=[]
        for spec in settings:
            params=spec["params"]
            try:
                pred,info=_dispatch(family,y,parts,c,"PSF-CE",params,options,"qr")
                qr_rows.append(_evaluate(record,y,pred,"PSF_ORACLE_QR",params,info,c,n,M))
            except Exception as exc:
                row=_row_base(record,"PSF_ORACLE_QR",params,"error"); row.update({"error":repr(exc)}); qr_rows.append(row)
        good=[r for r in qr_rows if r["status"]=="ok"]
        good=sorted(good,key=lambda r:(r["ACC"],r["NMI"],r["ARI"]),reverse=True)
        topk=int(options.get("formal_oracle_topk",10)); chosen=[]; seen=set()
        for r in good[:topk]:
            p=json.loads(r["params"]); key=(float(p["q"]),float(p["lambda"]))
            if key not in seen: chosen.append({"name":"PSF-CE","params":p}); seen.add(key)
        fp={"q":float(frozen_psf["q"]),"lambda":float(frozen_psf["lambda"])}; key=(fp["q"],fp["lambda"])
        if key not in seen: chosen.append({"name":"PSF-CE","params":fp})
        strong=[]
        for spec in chosen:
            p=spec["params"]
            pred,info=_dispatch(family,y,parts,c,"PSF-CE",p,options,"strong")
            strong.append(_evaluate(record,y,pred,"PSF_ORACLE_STRONG_TOPK",p,info,c,n,M))
        return qr_rows+strong


def run_parallel(records,worker,worker_args,output_dir,experiment_name,max_workers=1,force=False):
    output_dir=Path(output_dir); shard_dir=output_dir/"shards"/experiment_name; shard_dir.mkdir(parents=True,exist_ok=True)
    sig=stable_hash({"experiment":experiment_name,"args":worker_args}); all_rows=[]; pending=[]
    for record in records:
        shard=shard_dir/f"{safe_name(record.name)}__{safe_name(record.pool)}__{sig}.json"
        if shard.exists() and not force:
            all_rows.extend(json.loads(shard.read_text(encoding="utf-8"))["rows"])
        else: pending.append((record,shard))
    def consume(record,shard,result):
        rows=result[0] if isinstance(result,tuple) else result
        extra=result[1] if isinstance(result,tuple) else {}
        atomic_json_dump({"record":asdict(record),"config_sig":sig,"rows":rows,"extra":extra},shard); all_rows.extend(rows)
    if max_workers<=1:
        for r,s in pending: consume(r,s,worker(asdict(r),*worker_args))
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as ex:
            fs={ex.submit(worker,asdict(r),*worker_args):(r,s) for r,s in pending}
            for f in as_completed(fs): r,s=fs[f]; consume(r,s,f.result())
    df=pd.DataFrame(all_rows); out=output_dir/f"{experiment_name}.csv"; df.to_csv(out,index=False); return df,out
