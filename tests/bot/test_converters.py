import asyncio
import unittest
from unittest.mock import MagicMock

from discord.ext.commands import BadArgument

from bot.utils.converters import (
    DiceThrow,
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
