"""PSF-CE: norm-calibrated pairwise spectral filtering before fusion."""
__version__='1.0.0'
from .pair_spectrum import PairSpectrumFamily
from .models import run_psfce
__all__=['PairSpectrumFamily','run_psfce']
