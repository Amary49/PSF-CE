from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy import linalg

from .indicators import stacked_indicator


@dataclass
class PairSpectrum:
    left: int
    right: int
    U: np.ndarray
    s: np.ndarray
    Vt: np.ndarray
    energy: float
    k_left: int
    k_right: int


class PairSpectrumFamily:
    """Cached geometry for norm-calibrated PSF-CE.

    Raw model:
        A = H W0 H^T,
        R_q = H Wq H^T.

    V2 main model:
        G_{lambda,q} = A + lambda * s_q * R_q,
        s_q = ||A-J||_F / ||R_q||_F when ||R_q||_F > eps, and 1 otherwise.

    Because R_q annihilates the complete-partition constant direction, this
    calibration only matches branch scale; it does not change pair-mode shape.
    """

    def __init__(self, parts, svd_tol=1e-11, dtype=np.float64):
        self.parts, self.Hs, self.H, self.offsets = stacked_indicator(parts, dtype=dtype)
        self.n, self.d = self.H.shape
        self.M = len(self.Hs)
        self.P = self.M * (self.M - 1) // 2
        self.svd_tol = float(svd_tol)
        self.dtype = np.dtype(dtype)
        self.W0 = np.zeros((self.d, self.d), dtype=np.float64)
        for m in range(self.M):
            a,b=self.offsets[m],self.offsets[m+1]
            self.W0[a:b,a:b]=np.eye(b-a,dtype=np.float64)/self.M
        self.pairs:list[PairSpectrum]=[]
        self._wq_cache={}
        self._kq_cache={}
        self._scale_cache={}
        self._gram=None
        self._reduced=None
        self._build_pair_spectra()

    def _build_pair_spectra(self):
        u0=np.full(self.n,1.0/math.sqrt(self.n),dtype=np.float64)
        a=[np.asarray(h.T@u0).ravel() for h in self.Hs]
        for m in range(self.M):
            for l in range(m+1,self.M):
                c=(self.Hs[m].T@self.Hs[l]).toarray().astype(np.float64,copy=False)
                cnt=c-np.outer(a[m],a[l])
                if not np.any(np.abs(cnt)>self.svd_tol):
                    u=np.zeros((cnt.shape[0],0)); s=np.zeros(0); vt=np.zeros((0,cnt.shape[1]))
                else:
                    u,s,vt=np.linalg.svd(cnt,full_matrices=False)
                    keep=s>self.svd_tol; u,s,vt=u[:,keep],s[keep],vt[keep]
                self.pairs.append(PairSpectrum(m,l,u,s,vt,float(np.dot(s,s)),cnt.shape[0],cnt.shape[1]))

    @property
    def gram(self):
        if self._gram is None:
            self._gram=(self.H.T@self.H).toarray().astype(np.float64,copy=False)
            self._gram=0.5*(self._gram+self._gram.T)
        return self._gram

    @staticmethod
    def _filtered_cross(pair:PairSpectrum,q:float,energy_preserve=True):
        if q<=0: raise ValueError("q must be positive")
        if pair.s.size==0:
            return np.zeros((pair.k_left,pair.k_right),dtype=np.float64)
        raw=np.power(pair.s,float(q))
        if energy_preserve:
            den=float(np.linalg.norm(raw))
            filt=np.zeros_like(raw) if den<=1e-15 else raw*(float(np.linalg.norm(pair.s))/den)
        else:
            filt=raw
        return (pair.U*filt[None,:])@pair.Vt

    def pair_table(self):
        return [{"m":p.left,"l":p.right,"k_m":p.k_left,"k_l":p.k_right,
                 "rank":len(p.s),"energy":p.energy,
                 "sigma_max":float(p.s[0]) if len(p.s) else 0.0,
                 "sigma_min_nonzero":float(p.s[-1]) if len(p.s) else 0.0} for p in self.pairs]

    def interaction_W(self,q:float,energy_preserve=True):
        key=(round(float(q),12),bool(energy_preserve))
        if key in self._wq_cache: return self._wq_cache[key]
        w=np.zeros((self.d,self.d),dtype=np.float64); scale=1.0/(2.0*self.P)
        for p in self.pairs:
            ct=self._filtered_cross(p,q,energy_preserve)
            al,bl=self.offsets[p.left],self.offsets[p.left+1]
            ar,br=self.offsets[p.right],self.offsets[p.right+1]
            w[al:bl,ar:br]+=scale*ct; w[ar:br,al:bl]+=scale*ct.T
        self._wq_cache[key]=w
        return w

    def _ensure_reduced_basis(self,rank_tol=1e-10):
        if self._reduced is not None: return self._reduced
        vals,vecs=linalg.eigh(self.gram,check_finite=False,driver="evd")
        vmax=float(np.max(vals)) if len(vals) else 1.0
        keep=vals>max(rank_tol,rank_tol*max(vmax,1.0)); vals,vecs=vals[keep],vecs[:,keep]
        order=np.argsort(vals)[::-1]; vals,vecs=vals[order],vecs[:,order]
        sq=np.sqrt(vals); B=vecs*sq[None,:]; T=vecs*(1.0/sq)[None,:]
        K0=B.T@self.W0@B; K0=0.5*(K0+K0.T)
        u0=np.full(self.n,1.0/math.sqrt(self.n),dtype=np.float64)
        z=T.T@np.asarray(self.H.T@u0).ravel(); z=z/max(np.linalg.norm(z),1e-15)
        Jred=np.outer(z,z)
        K0c=0.5*((K0-Jred)+(K0-Jred).T)
        self._reduced={"vals":vals,"V":vecs,"B":B,"T":T,"K0":K0,"Jred":Jred,"K0c":K0c,"const":z}
        return self._reduced

    def reduced_interaction(self,q:float,energy_preserve=True):
        key=(round(float(q),12),bool(energy_preserve))
        if key in self._kq_cache: return self._kq_cache[key]
        r=self._ensure_reduced_basis(); wq=self.interaction_W(q,energy_preserve)
        kq=r["B"].T@wq@r["B"]; kq=0.5*(kq+kq.T)
        # Numerical centering: exact model is centered, this removes only roundoff.
        P0=np.eye(kq.shape[0])-r["Jred"]
        kq=P0@kq@P0; kq=0.5*(kq+kq.T)
        self._kq_cache[key]=kq
        return kq

    def interaction_scale(self,q:float,energy_preserve=True,mode="fro_centered",eps=1e-12):
        if mode in {None,"none","raw"}: return 1.0
        if mode!="fro_centered": raise ValueError(f"unknown calibration mode {mode}")
        key=(round(float(q),12),bool(energy_preserve),mode)
        if key in self._scale_cache: return self._scale_cache[key]
        r=self._ensure_reduced_basis(); nr=float(np.linalg.norm(self.reduced_interaction(q,energy_preserve),"fro"))
        na=float(np.linalg.norm(r["K0c"],"fro"))
        s=1.0 if nr<=eps else na/nr
        self._scale_cache[key]=float(s); return float(s)

    def reduced_operator(self,lam:float,q:float,energy_preserve=True,calibration="fro_centered"):
        r=self._ensure_reduced_basis(); scale=self.interaction_scale(q,energy_preserve,calibration)
        k=r["K0"]+float(lam)*scale*self.reduced_interaction(q,energy_preserve)
        return 0.5*(k+k.T)

    def total_W(self,lam:float,q:float,energy_preserve=True,calibration="fro_centered"):
        scale=self.interaction_scale(q,energy_preserve,calibration)
        return self.W0+float(lam)*scale*self.interaction_W(q,energy_preserve)

    def spectral_embedding(self,c:int,lam:float,q:float,energy_preserve=True,calibration="fro_centered",row_normalize=True):
        r=self._ensure_reduced_basis(); k=self.reduced_operator(lam,q,energy_preserve,calibration); rr=k.shape[0]
        if rr<c: raise ValueError(f"operator rank {rr} < c={c}")
        vals,u=linalg.eigh(k,subset_by_index=[rr-c,rr-1],check_finite=False,driver="evr")
        order=np.argsort(vals)[::-1]; vals,u=vals[order],u[:,order]
        emb=np.asarray(self.H@(r["T"]@u),dtype=np.float64)
        if row_normalize:
            emb/=np.maximum(np.linalg.norm(emb,axis=1,keepdims=True),1e-12)
        return vals,emb

    def dense_operator(self,lam,q,energy_preserve=True,calibration="fro_centered"):
        w=self.total_W(lam,q,energy_preserve,calibration)
        return np.asarray(self.H@w@self.H.T,dtype=np.float64)

    def operator_fro_norm(self,W):
        s=self.gram; val=float(np.trace(W.T@s@W@s)); return math.sqrt(max(val,0.0))

    def commutator_ratio(self,q,energy_preserve=True,calibration="fro_centered"):
        r=self._ensure_reduced_basis(); kq=self.reduced_interaction(q,energy_preserve)*self.interaction_scale(q,energy_preserve,calibration)
        c=r["K0"]@kq-kq@r["K0"]
        den=max(float(np.linalg.norm(r["K0c"],"fro"))*float(np.linalg.norm(kq,"fro")),1e-15)
        return float(np.linalg.norm(c,"fro")/den)

    def q1_raw_collapse_error(self):
        r1=self.dense_operator(1.0,1.0,calibration="none")-self.dense_operator(0.0,1.0,calibration="none")
        a=self.dense_operator(0.0,1.0,calibration="none"); j=np.full((self.n,self.n),1.0/self.n)
        rhs=(self.M*(a@a)-a)/(self.M-1.0)-j
        return float(np.linalg.norm(r1-rhs,"fro")/max(np.linalg.norm(rhs,"fro"),1e-15))

    def calibration_error(self,q):
        r=self._ensure_reduced_basis(); kq=self.reduced_interaction(q); sc=self.interaction_scale(q)
        return abs(float(np.linalg.norm(r["K0c"],"fro"))-float(np.linalg.norm(sc*kq,"fro")))

    def filter_energy_errors(self,q):
        errs=[]
        for p in self.pairs:
            ct=self._filtered_cross(p,q,True); errs.append(abs(float(np.linalg.norm(ct,"fro"))-math.sqrt(p.energy)))
        return np.asarray(errs)
