from __future__ import annotations

from pathlib import Path
import hashlib, os, pickle, tempfile
import numpy as np

from .pair_spectrum import PairSpectrumFamily

CACHE_SCHEMA = "psfce-v2-family-1"


def parts_fingerprint(parts) -> str:
    h=hashlib.sha256(CACHE_SCHEMA.encode())
    for p in parts:
        z=np.asarray(p,dtype=np.int32).ravel()
        h.update(np.asarray(z.shape,dtype=np.int64).tobytes()); h.update(z.tobytes())
    return h.hexdigest()


def load_or_build_family(parts, cache_dir=None, svd_tol=1e-11):
    if not cache_dir:
        return PairSpectrumFamily(parts, svd_tol=svd_tol)
    root=Path(cache_dir); root.mkdir(parents=True,exist_ok=True)
    fp=parts_fingerprint(parts); path=root/f"{fp}.pkl"
    if path.exists():
        try:
            with open(path,"rb") as f:
                obj=pickle.load(f)
            if getattr(obj,"cache_schema",None)==CACHE_SCHEMA:
                return obj
        except Exception:
            pass
    obj=PairSpectrumFamily(parts,svd_tol=svd_tol); obj.cache_schema=CACHE_SCHEMA
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(root))
    try:
        with os.fdopen(fd,"wb") as f: pickle.dump(obj,f,protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return obj
