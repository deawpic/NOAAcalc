"""
Unit test wrapper for the evaluation benchmark suite
"""

import unittest
from noaaharness.evaluation import run_eval_suite


class TestBenchmarkSuite(unittest.TestCase):

    def test_run_full_benchmark(self):
        result = run_eval_suite(verbose=False)
        self.assertEqual(result["passed_cases"], result["total_cases"],
                         f"Benchmark failed cases: {[c for c in result['cases'] if not c['passed']]}")
        self.assertEqual(result["pass_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
