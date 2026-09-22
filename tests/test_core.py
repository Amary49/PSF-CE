import numpy as np
from sklearn.datasets import make_blobs
from psfce.generate import generate_base_partitions
from psfce.pair_spectrum import PairSpectrumFamily
from psfce.models import run_psfce, discrete_objective_reduced


def fam(seed=7):
    X,y=make_blobs(n_samples=120,centers=4,n_features=8,cluster_std=1.7,random_state=seed)
    parts,_=generate_base_partitions(X,4,n_base=8,seed=seed)
    return y,parts,PairSpectrumFamily(parts)


def test_energy_preservation():
    _,_,f=fam()
    for q in [0.5,1.0,2.0,6.0]: assert f.filter_energy_errors(q).max(initial=0.0)<1e-9


def test_q1_raw_collapse():
    _,_,f=fam(); assert f.q1_raw_collapse_error()<1e-9


def test_norm_calibration():
    _,_,f=fam()
    for q in [0.5,1.0,2.0,6.0]: assert f.calibration_error(q)<1e-9


def test_label_permutation_invariance():
    _,parts,f=fam(); rng=np.random.default_rng(3); p2=[]
    for z in parts:
        u=np.unique(z); perm=rng.permutation(len(u))+100; mp={a:perm[i] for i,a in enumerate(u)}; p2.append(np.array([mp[v] for v in z]))
    f2=PairSpectrumFamily(p2)
    g1=f.dense_operator(1.2,2.0); g2=f2.dense_operator(1.2,2.0)
    assert np.linalg.norm(g1-g2)/np.linalg.norm(g1)<1e-10


def test_spectral_rounding_returns_all_clusters_and_objective():
    _,_,f=fam(); z,info=run_psfce(f,4,1.0,2.0,seed=2,kmeans_n_init=5,rounding='strong')
    assert len(np.unique(z))==4
    K=f.reduced_operator(1.0,2.0)
    val=discrete_objective_reduced(f,K,z,4)
    assert np.isfinite(val) and abs(val-info['rounding_objective'])<1e-8
