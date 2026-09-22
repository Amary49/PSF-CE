from __future__ import annotations

import unittest
import importlib.util

import numpy as np
from sklearn.metrics import adjusted_rand_score

from baseline_adapters.python.classic_baselines import canonical_membership, hbgf_graph, hbgf_metis, jaccard_meta_graph, mcla_metis


class ClassicBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        truth = np.repeat(np.arange(3), 20)
        self.parts = np.column_stack([
            truth,
            np.array([10, 30, 20], dtype=np.int32)[truth],
            truth,
            np.array([7, 5, 9], dtype=np.int32)[truth],
        ]).astype(np.int32)
        self.truth = truth

    def test_membership_contract(self) -> None:
        membership = canonical_membership(self.parts)
        self.assertEqual(membership.shape, (12, 60))
        self.assertTrue(np.all(np.asarray(membership.sum(axis=0)).ravel() == 4))

    def test_jaccard_bounds_and_symmetry(self) -> None:
        graph = jaccard_meta_graph(canonical_membership(self.parts))
        self.assertTrue(np.allclose(graph, graph.T))
        self.assertTrue(np.all((graph >= 0) & (graph <= 1)))
        self.assertTrue(np.allclose(np.diag(graph), 1))

    def test_hbgf_graph_contract(self) -> None:
        graph, d = hbgf_graph(self.parts)
        self.assertEqual(graph.shape, (60 + d, 60 + d))
        self.assertEqual(graph.nnz, 2 * 60 * 4)
        self.assertEqual((graph - graph.T).nnz, 0)

    @unittest.skipUnless(importlib.util.find_spec('pymetis'), 'requires frozen pymetis==2025.2.2')
    def test_methods_are_deterministic_and_relabel_invariant(self) -> None:
        relabeled = self.parts.copy()
        for column in range(relabeled.shape[1]):
            unique = np.unique(relabeled[:, column])
            mapping = {value: 1000 + 17 * index for index, value in enumerate(unique[::-1])}
            relabeled[:, column] = np.asarray([mapping[value] for value in relabeled[:, column]])
        for method in (mcla_metis, hbgf_metis):
            first = method(self.parts, 3, seed=0)
            second = method(self.parts, 3, seed=0)
            permuted = method(relabeled, 3, seed=0)
            self.assertEqual(first.status, "COMPLETED")
            self.assertTrue(np.array_equal(first.labels, second.labels))
            self.assertEqual(adjusted_rand_score(first.labels, permuted.labels), 1.0)
            self.assertEqual(adjusted_rand_score(self.truth, first.labels), 1.0)


if __name__ == "__main__":
    unittest.main()
