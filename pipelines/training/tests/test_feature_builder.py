import unittest

import pandas as pd

from feature_builder import FEATURE_COLUMNS, preprocess_features, time_based_train_test_split


class FeatureBuilderTest(unittest.TestCase):
    def test_preprocess_features_fills_missing_numeric_values(self):
        dataset = pd.DataFrame(
            [
                {
                    **{column: 1 for column in FEATURE_COLUMNS},
                    "amount_stddev_7d": None,
                    "is_fraud": 1,
                }
            ]
        )

        features, labels = preprocess_features(dataset)

        self.assertEqual(0, features.loc[0, "amount_stddev_7d"])
        self.assertEqual(1, labels.iloc[0])

    def test_preprocess_features_requires_expected_columns(self):
        dataset = pd.DataFrame([{"amount": 1, "is_fraud": 0}])

        with self.assertRaises(ValueError):
            preprocess_features(dataset)

    def test_time_based_split_orders_by_event_timestamp(self):
        dataset = pd.DataFrame(
            [
                {"event_timestamp": "2026-06-25T10:02:00Z", "value": 3},
                {"event_timestamp": "2026-06-25T10:00:00Z", "value": 1},
                {"event_timestamp": "2026-06-25T10:01:00Z", "value": 2},
                {"event_timestamp": "2026-06-25T10:03:00Z", "value": 4},
            ]
        )

        train_df, test_df = time_based_train_test_split(dataset, test_fraction=0.25)

        self.assertEqual([1, 2, 3], train_df["value"].tolist())
        self.assertEqual([4], test_df["value"].tolist())


if __name__ == "__main__":
    unittest.main()

