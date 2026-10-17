import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'evals' / 'measure_deployed_assistant.py'
spec = importlib.util.spec_from_file_location('measurement', path)
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


class MeasurementTest(unittest.TestCase):
    def test_percentiles_use_nearest_rank(self):
        self.assertEqual(measurement.percentile([10, 20, 30, 40], .5), 20)
        self.assertEqual(measurement.percentile([10, 20, 30, 40], .95), 40)
        self.assertIsNone(measurement.percentile([], .95))

    def test_wrong_tool_arguments_do_not_pass(self):
        case = {'expected_tool': 'get_transaction_audit', 'transaction_id': 'tx-right'}
        body = {'tool_calls': [{'name': 'get_transaction_audit', 'arguments': {'transaction_id': 'tx-wrong'}}]}
        self.assertFalse(measurement.evaluate(case, body)['tool_selection_check'])

    def test_failure_counts_in_check_denominator(self):
        record = {'success': False, 'guardrail_case': False, 'checks': {'expected_source_coverage': False}}
        summary = measurement.summarize([record])
        self.assertEqual(summary['checks']['expected_source_coverage'], {'passed': 0, 'total': 1, 'percent': 0.})
        self.assertEqual(summary['success_rate_pct'], 0.)

    def test_comparison_rejects_different_workload(self):
        current = {'run': {'workload_hash': 'a', 'target': 'https://a', 'repeats': 3, 'delay_seconds': 2, 'warmup_requests': 1}}
        baseline = {'run': dict(current['run'], workload_hash='b')}
        with self.assertRaises(ValueError):
            measurement.compare(current, baseline)

if __name__ == '__main__':
    unittest.main()
