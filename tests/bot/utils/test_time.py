import unittest

from dateutil.relativedelta import relativedelta

from bot.utils import time


class TimeTests(unittest.TestCase):
    """Test helper functions in bot.utils.time."""

    def test_humanize_delta_handle_unknown_units(self):
        """humanize_delta should be able to handle unknown units, and will not abort."""
        # Does not abort for unknown units, as the unit name is checked
        # against the attribute of the relativedelta instance.
        self.assertEqual(time.humanize_delta(relativedelta(
            days=2, hours=2), 'elephants', 2), '2 days and 2 hours')

    def test_humanize_delta_handle_high_units(self):
        """humanize_delta should be able to handle very high units."""
        # Very high maximum units, but it only ever iterates over
        # each value the relativedelta might have.
        self.assertEqual(time.humanize_delta(relativedelta(
            days=2, hours=2), 'hours', 20), '2 days and 2 hours')

    def test_humanize_delta_should_normal_usage(self):
        """Testing humanize delta."""
        test_cases = (
            (relativedelta(days=2), 'seconds', 1, '2 days'),
            (relativedelta(days=2, hours=2), 'seconds', 2, '2 days and 2 hours'),
            (relativedelta(days=2, hours=2), 'seconds', 1, '2 days'),
            (relativedelta(days=2, hours=2), 'days', 2, '2 days'),
        )

        for delta, precision, max_units, expected in test_cases:
            with self.subTest(delta=delta, precision=precision, max_units=max_units, expected=expected):
                self.assertEqual(time.humanize_delta(
                    delta, precision, max_units), expected)

    def test_humanize_delta_raises_for_invalid_max_units(self):
        """humanize_delta should raises ValueError('max_units must be positive') for invalid max_units."""
        test_cases = (-1, 0)

        for max_units in test_cases:
            with self.subTest(max_units=max_units), self.assertRaises(ValueError) as error:
                time.humanize_delta(relativedelta(
                    days=2, hours=2), 'hours', max_units)
            self.assertEqual(str(error.exception),
                             'max_units must be positive')
