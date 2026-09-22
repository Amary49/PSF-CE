from __future__ import annotations

import time
import numpy as np
from scipy import linalg, sparse
from sklearn.cluster import KMeans, MiniBatchKMeans

from .pair_spectrum import PairSpectrumFamily


def _cluster_qr(vectors: np.ndarray) -> np.ndarray:
    """Public reimplementation of the Damle-Minden-Ying cluster_qr rounding."""
    from scipy.linalg import qr, svd
    X=np.asarray(vectors,dtype=np.float64); k=X.shape[1]
    _,_,piv=qr(X.T,pivoting=True,mode="economic")
    ut,_,v=svd(X[piv[:k],:].T,full_matrices=False)
    scores=np.abs(X@(ut@v))
    return scores.argmax(axis=1).astype(np.int32)


def _repair_empty(labels: np.ndarray, emb: np.ndarray, c: int) -> np.ndarray:
    z=np.asarray(labels,dtype=np.int32).copy(); counts=np.bincount(z,minlength=c)
    if np.all(counts>0): return z
    # Move the least-confident points from the largest clusters into missing clusters.
    centers=np.zeros((c,emb.shape[1]),dtype=np.float64)
    for k in range(c):
        idx=np.flatnonzero(z==k)
        if len(idx): centers[k]=emb[idx].mean(axis=0)
    for missing in np.flatnonzero(counts==0):
        src=int(np.argmax(counts)); idx=np.flatnonzero(z==src)
        if len(idx)<=1: continue
        d=np.linalg.norm(emb[idx]-centers[src],axis=1)
        pick=int(idx[np.argmax(d)]); z[pick]=missing; counts[src]-=1; counts[missing]+=1
    return z


def discrete_objective_reduced(family: PairSpectrumFamily, K: np.ndarray, labels, c: int) -> float:
    z=np.asarray(labels,dtype=np.int32); n=len(z)
    Z=sparse.csr_matrix((np.ones(n),(np.arange(n),z)),shape=(n,c))
    T=np.asarray(family.H.T@Z.toarray(),dtype=np.float64)
    QTZ=family._ensure_reduced_basis()["T"].T@T
    sizes=np.bincount(z,minlength=c).astype(np.float64)
    vals=np.sum(QTZ*(K@QTZ),axis=0)
    return float(np.sum(vals/np.maximum(sizes,1.0)))


def _embedding_from_K(family: PairSpectrumFamily,K:np.ndarray,c:int,row_normalize=False):
    r=family._ensure_reduced_basis(); rr=K.shape[0]
    if rr<c: raise ValueError(f"operator rank {rr} < c={c}")
    vals,U=linalg.eigh(K,subset_by_index=[rr-c,rr-1],check_finite=False,driver="evr")
    order=np.argsort(vals)[::-1]; vals,U=vals[order],U[:,order]
    emb=np.asarray(family.H@(r["T"]@U),dtype=np.float64)
    if row_normalize:
        emb/=np.maximum(np.linalg.norm(emb,axis=1,keepdims=True),1e-12)
    return vals,emb


def _round_embedding(family,K,emb,c,seed=0,mode="strong",kmeans_n_init=20,large_n_threshold=30000):
    raw=np.asarray(emb,dtype=np.float64)
    norm=raw/np.maximum(np.linalg.norm(raw,axis=1,keepdims=True),1e-12)
    candidates=[]
    zqr=_repair_empty(_cluster_qr(norm),norm,c)
    candidates.append(("cluster_qr",zqr,discrete_objective_reduced(family,K,zqr,c)))
    if mode=="strong":
        if len(raw)>large_n_threshold:
            km=MiniBatchKMeans(n_clusters=c,n_init=max(3,min(10,kmeans_n_init)),batch_size=2048,random_state=seed)
        else:
            km=KMeans(n_clusters=c,n_init=kmeans_n_init,random_state=seed,algorithm="lloyd")
        zk=km.fit_predict(norm).astype(np.int32); zk=_repair_empty(zk,norm,c)
        candidates.append(("kmeans_norm",zk,discrete_objective_reduced(family,K,zk,c)))
        # Raw embedding is sometimes better when eigenvector norms carry useful confidence.
        if len(raw)<=large_n_threshold:
            kr=KMeans(n_clusters=c,n_init=max(10,kmeans_n_init//2),random_state=seed+104729,algorithm="lloyd")
            zr=kr.fit_predict(raw).astype(np.int32); zr=_repair_empty(zr,raw,c)
            candidates.append(("kmeans_raw",zr,discrete_objective_reduced(family,K,zr,c)))
    best=max(candidates,key=lambda x:x[2])
    return best[1],{"rounding":best[0],"rounding_objective":float(best[2]),
                    "rounding_candidates":{name:float(obj) for name,_,obj in candidates}}


def _run_reduced_model(family,K,c,seed=0,rounding="strong",kmeans_n_init=20):
    t0=time.perf_counter(); vals,emb=_embedding_from_K(family,K,c,row_normalize=False)
    t_eig=time.perf_counter()-t0
    z,rinfo=_round_embedding(family,K,emb,c,seed,rounding,kmeans_n_init)
    return z,{**rinfo,"solver":"spectral","eig_max":float(vals[0]),"eig_min_topc":float(vals[-1]),
              "spectral_seconds":float(t_eig),"runtime_seconds":float(time.perf_counter()-t0),
              "refined":False,"sweeps":0,"moves":0,"history":None,"moves_history":None,"skip_reason":""}


def run_psfce(family,c,lam,q,seed=0,kmeans_n_init=20,rounding="strong",calibration="fro_centered",energy_preserve=True):
    K=family.reduced_operator(float(lam),float(q),energy_preserve,calibration)
    z,info=_run_reduced_model(family,K,c,seed,rounding,kmeans_n_init)
    info.update({"q":float(q),"lambda":float(lam),"calibration":calibration,
                 "interaction_scale":float(family.interaction_scale(q,energy_preserve,calibration)),
                 "commutator_ratio":float(family.commutator_ratio(q,energy_preserve,calibration))})
    return z,info


def run_ca(family,c,seed=0,rounding="strong",kmeans_n_init=20):
    return _run_reduced_model(family,family._ensure_reduced_basis()["K0"],c,seed,rounding,kmeans_n_init)


def run_poly2(family,c,eta=0.25,seed=0,rounding="strong",kmeans_n_init=20,centered=True):
    r=family._ensure_reduced_basis(); K0=r["K0"]
    base=r["K0c"] if centered else K0
    K=K0+float(eta)*(base@base); K=0.5*(K+K.T)
    z,info=_run_reduced_model(family,K,c,seed,rounding,kmeans_n_init); info["eta"]=float(eta)
    return z,info


def run_dckl(family,c,alpha=0.1,seed=0,rounding="strong",kmeans_n_init=20):
    r=family._ensure_reduced_basis(); vals,U=linalg.eigh(r["K0"],check_finite=False,driver="evd")
    h=(1.0-float(alpha))*vals/np.maximum(1.0-float(alpha)*vals*vals,1e-10)
    K=(U*h[None,:])@U.T; K=0.5*(K+K.T)
    z,info=_run_reduced_model(family,K,c,seed,rounding,kmeans_n_init); info["alpha"]=float(alpha)
    return z,info


def _old_sacsi_reduced(family,lam=1.0,gamma=4.0):
    energies=np.asarray([p.energy for p in family.pairs],dtype=np.float64)
    if float(gamma)==0 or np.all(energies<=1e-14): weights=np.ones_like(energies)/len(energies)
    else:
        raw=np.maximum(energies,1e-14)**float(gamma); weights=raw/raw.sum()
    Wq=np.zeros((family.d,family.d),dtype=np.float64)
    for weight,p in zip(weights,family.pairs):
        cnt=(p.U*p.s[None,:])@p.Vt if p.s.size else np.zeros((p.k_left,p.k_right))
        al,bl=family.offsets[p.left],family.offsets[p.left+1]; ar,br=family.offsets[p.right],family.offsets[p.right+1]
        Wq[al:bl,ar:br]+=0.5*weight*cnt; Wq[ar:br,al:bl]+=0.5*weight*cnt.T
    r=family._ensure_reduced_basis(); Kq=r["B"].T@Wq@r["B"]; Kq=0.5*(Kq+Kq.T)
    return 0.5*((r["K0"]+float(lam)*Kq)+(r["K0"]+float(lam)*Kq).T)


def run_old_sacsi(family,c,lam=1.0,gamma=4.0,seed=0,rounding="strong",kmeans_n_init=20):
    K=_old_sacsi_reduced(family,lam,gamma)
    z,info=_run_reduced_model(family,K,c,seed,rounding,kmeans_n_init); info.update({"lambda":float(lam),"gamma":float(gamma)})
    return z,info


def run_aggregate_power(family,c,q=2.0,seed=0,rounding="strong",kmeans_n_init=20):
    """Aggregate first then power-filter A's centered spectrum.

    This preserves A's eigenvectors and therefore is a direct order-of-operations control.
    """
    r=family._ensure_reduced_basis(); vals,U=linalg.eigh(r["K0"],check_finite=False,driver="evd")
    # identify constant mode by maximum overlap with stored constant coordinate
    const=r["const"]; overlaps=np.abs(U.T@const); j=int(np.argmax(overlaps))
    filt=vals.copy(); idx=np.arange(len(vals))!=j; non=np.clip(vals[idx],0.0,None); raw=non**float(q)
    if np.linalg.norm(raw)>1e-15: raw*=np.linalg.norm(non)/np.linalg.norm(raw)
    filt[idx]=raw; K=(U*filt[None,:])@U.T; K=0.5*(K+K.T)
    z,info=_run_reduced_model(family,K,c,seed,rounding,kmeans_n_init); info["q_after"]=float(q)
    return z,info


def run_psfce_relocation(family,c,lam,q,seed=0,kmeans_n_init=20,calibration="fro_centered",relocation=None):
    """Optional solver ablation only; not the V2 main solver."""
    from .solver import RelocationConfig, FactorOperator, exact_relocation
    z0,base=run_psfce(family,c,lam,q,seed,kmeans_n_init,rounding="strong",calibration=calibration)
    cfg=relocation or RelocationConfig(); W=family.total_W(lam,q,calibration=calibration)
    op=FactorOperator(family.H,W,fb_dtype=cfg.fb_dtype,max_fb_bytes=cfg.max_fb_bytes)
    best=None
    for r in range(max(1,cfg.order_restarts)):
        z,info=exact_relocation(op,z0,c,max_sweeps=cfg.max_sweeps,tolerance=cfg.tolerance,
                                order_seed=seed+7919*r,record_history=True)
        if best is None or info["objective"]>best[1]["objective"]: best=(z,info)
    z,info=best; info.update({"runtime_seconds":base["runtime_seconds"],"solver":"spectral+relocation",
                              "q":float(q),"lambda":float(lam),"calibration":calibration,
                              "commutator_ratio":float(family.commutator_ratio(q,calibration=calibration))})
    return z,info
