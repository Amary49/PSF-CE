from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans, MiniBatchKMeans, AgglomerativeClustering, Birch
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.random_projection import GaussianRandomProjection
from sklearn.preprocessing import StandardScaler


def clean_scale(X):
    X=np.asarray(X,dtype=np.float64)
    if X.ndim!=2: raise ValueError("X must be 2D")
    finite=np.isfinite(X)
    if not finite.all():
        med=np.nanmedian(np.where(finite,X,np.nan),axis=0)
        med=np.where(np.isfinite(med),med,0.0)
        ii=np.where(~finite); X=X.copy(); X[ii]=med[ii[1]]
    var=np.var(X,axis=0)
    keep=var>1e-14
    if not np.any(keep): raise ValueError("all features are constant")
    X=X[:,keep]
    return StandardScaler().fit_transform(X)


def _safe_k(c, ratio, n):
    return min(n-1,max(2,int(round(c*ratio))))


def generate_base_partitions(X,c,n_base=20,seed=2027):
    """Audited student schedule, hardened for reproducible development pools.

    Diversifies algorithm, cluster count, and representation. This generator is for
    development/smoke data; formal experiments should reuse prespecified BP pools.
    """
    X=clean_scale(X); rng=np.random.default_rng(seed)
    methods=["kmeans","minibatch","ward","birch","gmm"]
    ratios=[0.8,1.0,1.2,1.5,2.0]
    transforms=["full","subspace","pca","projection"]
    parts=[]; meta=[]
    for m in range(n_base):
        rs=seed+97*m
        requested=methods[m%5]
        ratio=ratios[((m//5)+2*(m%5))%5]
        k=_safe_k(c,ratio,len(X))
        transform=transforms[((m//5)+(m%5))%4]
        Xm=X
        if transform=="subspace" and X.shape[1]>4:
            keep=max(3,int(np.ceil(X.shape[1]*(0.55+0.1*(m%4)))))
            idx=rng.choice(X.shape[1],size=min(keep,X.shape[1]),replace=False); Xm=X[:,idx]
        if transform=="pca" and Xm.shape[1]>8:
            nc=min(max(4,Xm.shape[1]//2),50,len(X)-1)
            Xm=PCA(n_components=nc,svd_solver="randomized",random_state=rs).fit_transform(Xm)
        elif transform=="projection" and Xm.shape[1]>6:
            nc=min(max(4,Xm.shape[1]//2),50,Xm.shape[1])
            Xm=GaussianRandomProjection(n_components=nc,random_state=rs).fit_transform(Xm)
        method=requested
        if requested=="ward" and len(X)>3000: method="minibatch_ward_fallback"
        if method=="kmeans":
            z=KMeans(n_clusters=k,n_init=12,random_state=rs).fit_predict(Xm)
        elif method in {"minibatch","minibatch_ward_fallback"}:
            z=MiniBatchKMeans(n_clusters=k,n_init=6,batch_size=min(512,len(X)),random_state=rs).fit_predict(Xm)
        elif method=="ward":
            z=AgglomerativeClustering(n_clusters=k,linkage="ward").fit_predict(Xm)
        elif method=="birch":
            z=Birch(n_clusters=k,threshold=0.8).fit_predict(Xm)
        else:
            z=GaussianMixture(n_components=k,covariance_type="diag",reg_covar=1e-5,random_state=rs,max_iter=150).fit_predict(Xm)
        parts.append(np.asarray(z,dtype=np.int32))
        meta.append({"id":m,"method_requested":requested,"method":method,"k_ratio":ratio,
                     "k":int(len(np.unique(z))),"feature_transform":transform,"feature_dim":int(Xm.shape[1])})
    return parts,meta
