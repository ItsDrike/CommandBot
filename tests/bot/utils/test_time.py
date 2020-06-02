import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from dateutil.relativedelta import relativedelta

from bot.utils import time


class TimeTests(unittest.TestCase):
    """Test helper functions in bot.utils.time."""

    def test_humanize_delta_handle_unknown_units(self):
        """humanize_delta should be able to handle unknown units, and will not abort."""
        # Does not abort for unknown units, as the unit name is checked
        # against the attribute of the relativedelta instance.
        self.assertEqual(time.humanize_delta(relativedelta(
            days=2, hours=2), "elephants", 2), "2 days and 2 hours")

    def test_humanize_delta_handle_high_units(self):
        """humanize_delta should be able to handle very high units."""
        # Very high maximum units, but it only ever iterates over
        # each value the relativedelta might have.
        self.assertEqual(time.humanize_delta(relativedelta(
            days=2, hours=2), "hours", 20), "2 days and 2 hours")

    def test_humanize_delta_should_normal_usage(self):
        """Testing humanize delta."""
        test_cases = (
            (relativedelta(days=2), "seconds", 1, "2 days"),
            (relativedelta(days=2, hours=2), "seconds", 2, "2 days and 2 hours"),
            (relativedelta(days=2, hours=2), "seconds", 1, "2 days"),
            (relativedelta(days=2, hours=2), "days", 2, "2 days"),
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
                    days=2, hours=2), "hours", max_units)
            self.assertEqual(str(error.exception),
                             "max_units must be positive")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_wait_until(self, mock):
        """Testing wait_until."""
        start = datetime(2019, 1, 1, 0, 0)
        then = datetime(2019, 1, 1, 0, 10)

        # No return value
        self.assertIs(asyncio.run(time.wait_until(then, start)), None)

        mock.assert_called_once_with(10 * 60)

    def test_until_expiration_with_duration_none_expiry(self):
        """until_expiration should work for None expiry."""
        test_cases = (
            (None, None, None, None),

            # To make sure that now and max_units are not touched
            (None, "Why hello there!", None, None),
            (None, None, float("inf"), None),
            (None, "Why hello there!", float("inf"), None),
        )

        for expiry, now, max_units, expected in test_cases:
            with self.subTest(expiry=expiry, now=now, max_units=max_units, expected=expected):
                self.assertEqual(time.until_expiration(
                    expiry, now, max_units), expected)

    def test_until_expiration_with_duration_custom_units(self):
        """until_expiration should work for custom max_units."""
        test_cases = (
            ("2019-12-12T00:01:00Z", datetime(2019, 12, 11, 12, 5, 5),
             6, "11 hours, 55 minutes and 55 seconds"),
            ("2019-11-23T20:09:00Z", datetime(2019, 4, 25, 20, 15),
             20, "6 months, 28 days, 23 hours and 54 minutes")
        )

        for expiry, now, max_units, expected in test_cases:
            with self.subTest(expiry=expiry, now=now, max_units=max_units, expected=expected):
                self.assertEqual(time.until_expiration(
                    expiry, now, max_units), expected)

    def test_until_expiration_normal_usage(self):
        """until_expiration should work for normal usage, across various durations."""
        test_cases = (
            ("2019-12-12T00:01:00Z", datetime(2019, 12,
                                              11, 12, 0, 5), 2, "12 hours and 55 seconds"),
            ("2019-12-12T00:01:00Z", datetime(2019, 12, 11, 12, 0, 5), 1, "12 hours"),
            ("2019-12-12T00:00:00Z", datetime(2019, 12, 11, 23, 59), 2, "1 minute"),
            ("2019-11-23T20:09:00Z", datetime(2019, 11,
                                              15, 20, 15), 2, "7 days and 23 hours"),
            ("2019-11-23T20:09:00Z", datetime(2019, 4,
                                              25, 20, 15), 2, "6 months and 28 days"),
            ("2019-11-23T20:58:00Z", datetime(2019, 11, 23, 20, 53), 2, "5 minutes"),
            ("2019-11-24T00:00:00Z", datetime(2019, 11, 23, 23, 59, 0), 2, "1 minute"),
            ("2019-11-23T23:59:00Z", datetime(2017, 7,
                                              21, 23, 0), 2, "2 years and 4 months"),
            ("2019-11-23T23:59:00Z", datetime(2019, 11, 23,
                                              23, 49, 5), 2, "9 minutes and 55 seconds"),
            (None, datetime(2019, 11, 23, 23, 49, 5), 2, None),
        )

        for expiry, now, max_units, expected in test_cases:
            with self.subTest(expiry=expiry, now=now, max_units=max_units, expected=expected):
                self.assertEqual(time.until_expiration(
                    expiry, now, max_units), expected)
