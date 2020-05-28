import asyncio
import unittest
from unittest.mock import MagicMock

import datetime

from discord.ext.commands import BadArgument

from bot.converters import (
    DiceThrow,
    Duration,
    ISODelta,
)


class ConverterTests(unittest.TestCase):
    """Tests our custom argument converters."""

    @classmethod
    def setUpClass(cls):
        cls.context = MagicMock
        cls.context.author = 'bob'

    def test_dicethrow_converter_for_valid(self):
        test_values = (
            ('1d5', (1, 5)),
            ('110D300', (110, 300)),
            ('d100', (1, 100)),
            ('01d1', (1, 1)),
            ('00000025D0035', (25, 35))
        )

        converter = DiceThrow()

        for dicethrow_str, expected_tuple in test_values:
            with self.subTest(dicethrow_str=dicethrow_str, expected_tuple=expected_tuple):
                converted_dicethrow = asyncio.run(
                    converter.convert(self.context, dicethrow_str)
                )
                self.assertEqual(converted_dicethrow, expected_tuple)

    def test_dicethrow_converter_for_invalid(self):
        test_values = (
            # Values of 0
            ('0d8'),
            ('1d00'),
            ('0d0'),

            # Negative values
            ('-1d8'),
            ('5D-5'),

            # No values
            ('d'),
            ('D'),

            # Non-number values
            ('XdY'),
            ('1dU'),
            ('lD8'),

            # Invalid values
            ('Hello There!'),
            ('just no'),
            ('d' * 20),
        )

        converter = DiceThrow()

        for invalid_dicethrow in test_values:
            with self.subTest(invalid_dicethrow=invalid_dicethrow):
                exception_message = f'`{invalid_dicethrow}` is not a valid dice throw string.'
                with self.assertRaises(BadArgument, msg=exception_message):
                    asyncio.run(converter.convert(
                        self.context, invalid_dicethrow))

    def test_duration_converter_for_valid(self):
        """Duration returns the correct `datetime` for valid duration strings."""
        test_values = (
            # Simple duration strings
            ('1Y', 31_536_000),
            ('1y', 31_536_000),
            ('1year', 31_536_000),
            ('1years', 31_536_000),
            ('1mo', 2_678_400),
            ('1month', 2_678_400),
            ('1months', 2_678_400),
            ('1w', 604_800),
            ('1W', 604_800),
            ('1week', 604_800),
            ('1weeks', 604_800),
            ('1d', 86_400),
            ('1D', 86_400),
            ('1day', 86_400),
            ('1days', 86_400),
            ('1h', 3_600),
            ('1H', 3_600),
            ('1hour', 3_600),
            ('1hours', 3_600),
            ('1m', 60),
            ('1minute', 60),
            ('1minutes', 60),
            ('1s', 1),
            ('1S', 1),
            ('1second', 1),
            ('1seconds', 1),

            # Complex duration strings
            (
                '1y1mo1w1d1h1m1s',
                34_909_261
            ),
            ('5y100S', 157_766_500),
            ('2w28H', 1_310_400),

            # Duration strings with spaces
            ('1 year 2 months', 36_806_400),
            ('1d 2H', 93_600),
            ('1 week2 days', 777_600),
        )

        converter = Duration()

        for duration, expected_duration in test_values:
            with self.subTest(duration=duration, expected_duration=expected_duration):
                converted_duration = asyncio.run(
                    converter.convert(self.context, duration)
                )
                self.assertEqual(converted_duration, expected_duration)

    def test_duration_converter_for_invalid(self):
        """Duration raises the right exception for invalid duration strings."""
        test_values = (
            # Units in wrong order
            ('1d1w'),
            ('1s1y'),

            # Duplicated units
            ('1 year 2 years'),
            ('1 M 10 minutes'),

            # Unknown substrings
            ('1MVes'),
            ('1y3breads'),

            # Missing amount
            ('ym'),

            # Incorrect whitespace
            (" 1y"),
            ("1S "),
            ("1y  1m"),

            # Garbage
            ('this means nothing'),
            ('ItsDrike ItsDrike ItsDrike ItsDrike ItsDrike'),
        )

        converter = Duration()

        for invalid_duration in test_values:
            with self.subTest(invalid_duration=invalid_duration):
                exception_message = f'`{invalid_duration}` is not a valid duration string.'
                with self.assertRaises(BadArgument, msg=exception_message):
                    asyncio.run(converter.convert(
                        self.context, invalid_duration))

    def test_isodelta_converter_for_valid(self):
        """
        ISODelta converter returns correct datetime for valid datetime string. (`get_datetime`)

        While verification of `get_datetime` is easy, verifying `convert` is harder since
        it uses `datetime.datetime.now()` to get timedelta which is different from when this
        check will get current time. There is a workaround to test that the difference is less
        than 0.01 seconds.
        """
        test_values = (
            # `YYYY-mm-ddTHH:MM:SSZ` | `YYYY-mm-dd HH:MM:SSZ`
            ('2019-09-02T02:03:05Z', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 02:03:05Z', datetime.datetime(2019, 9, 2, 2, 3, 5)),

            # `YYYY-mm-ddTHH:MM:SS±HH:MM` | `YYYY-mm-dd HH:MM:SS±HH:MM`
            ('2019-09-02T03:18:05+01:15', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 03:18:05+01:15', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02T00:48:05-01:15', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 00:48:05-01:15', datetime.datetime(2019, 9, 2, 2, 3, 5)),

            # `YYYY-mm-ddTHH:MM:SS±HHMM` | `YYYY-mm-dd HH:MM:SS±HHMM`
            ('2019-09-02T03:18:05+0115', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 03:18:05+0115', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02T00:48:05-0115', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 00:48:05-0115', datetime.datetime(2019, 9, 2, 2, 3, 5)),

            # `YYYY-mm-ddTHH:MM:SS±HH` | `YYYY-mm-dd HH:MM:SS±HH`
            ('2019-09-02 03:03:05+01', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02T01:03:05-01', datetime.datetime(2019, 9, 2, 2, 3, 5)),

            # `YYYY-mm-ddTHH:MM:SS` | `YYYY-mm-dd HH:MM:SS`
            ('2019-09-02T02:03:05', datetime.datetime(2019, 9, 2, 2, 3, 5)),
            ('2019-09-02 02:03:05', datetime.datetime(2019, 9, 2, 2, 3, 5)),

            # `YYYY-mm-ddTHH:MM` | `YYYY-mm-dd HH:MM`
            ('2019-11-12T09:15', datetime.datetime(2019, 11, 12, 9, 15)),
            ('2019-11-12 09:15', datetime.datetime(2019, 11, 12, 9, 15)),

            # `YYYY-mm-dd`
            ('2019-04-01', datetime.datetime(2019, 4, 1)),

            # `YYYY-mm`
            ('2019-02-01', datetime.datetime(2019, 2, 1)),

            # `YYYY`
            ('2025', datetime.datetime(2025, 1, 1)),
        )

        converter = ISODelta()

        for datetime_string, corresponding_dt in test_values:
            with self.subTest(datetime_string=datetime_string, corresponding_dt=corresponding_dt):
                converted_dt = asyncio.run(
                    converter.get_datetime(datetime_string))

                self.assertEqual(converted_dt, corresponding_dt)

                converted_delta = asyncio.run(
                    converter.convert(self.context, datetime_string))

                now = datetime.datetime.now()
                expected_delta = (corresponding_dt - now).total_seconds()

                self.assertLessEqual(
                    abs(converted_delta - expected_delta), 0.01)

    def test_isodelta_converter_for_invalid(self):
        """ISODelta converter raises the correct exception for invalid datetime strings."""
        test_values = (
            # Make sure it doesn't interfere with the Duration converter
            ('1Y'),
            ('1d'),
            ('1H'),

            # Check if it fails when only providing the optional time part
            ('10:10:10'),
            ('10:00'),

            # Invalid date format
            ('19-01-01'),

            # Other non-valid strings
            ('Fish the omnipotent'),
        )

        converter = ISODelta()
        for datetime_string in test_values:
            with self.subTest(datetime_string=datetime_string):
                exception_message = f"`{datetime_string}` is not a valid ISO-8601 datetime string"
                with self.assertRaises(BadArgument, msg=exception_message):
                    asyncio.run(converter.convert(
                        self.context, datetime_string))
