import unittest
from resolve_batch import decide_count


class ResolveBatchTests(unittest.TestCase):
    def test_catch_up_rechecks_actual_deliveries(self):
        self.assertEqual(decide_count([{'status': 'sent'}] * 10, 108), 98)
        self.assertEqual(decide_count([{'status': 'sent'}] * 20, 108), 88)
        self.assertEqual(decide_count([{'status': 'sent'}] * 110, 108), 0)

    def test_normal_batch_is_ten(self):
        self.assertEqual(decide_count([{'status': 'sent'}] * 10, 0), 10)

    def test_ambiguous_delivery_blocks_catch_up(self):
        with self.assertRaises(ValueError):
            decide_count([{'status': 'attempted'}], 108)

    def test_large_or_negative_targets_are_rejected(self):
        for target in [-1, 1001, 1_000_001]:
            with self.assertRaises(ValueError):
                decide_count([], target)


if __name__ == '__main__':
    unittest.main()
