import numpy as np
from psfce.metrics import clustering_accuracy,evaluate_clustering

def test_acc_permutation_invariant():
    y=np.array([0,0,1,1,2,2]); z=np.array([2,2,0,0,1,1])
    assert clustering_accuracy(y,z)==1.0 and evaluate_clustering(y,z)['ARI']==1.0
