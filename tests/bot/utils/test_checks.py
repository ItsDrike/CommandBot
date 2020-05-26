import unittest

from bot.utils import checks
from tests.helpers import MockContext, MockRole


class ChecksTests(unittest.TestCase):
    """Tests the check functions defined in `bot.checks`."""

    def setUp(self):
        self.ctx = MockContext()

    def test_with_role_check_without_guild(self):
        """`with_role_check` returns `False` if `Context.guild` is None."""
        self.ctx.guild = None
        self.assertFalse(checks.with_role_check(self.ctx))

    def test_with_role_check_without_required_roles(self):
        """`with_role_check` returns `False` if `Context.author` lacks the required role."""
        self.ctx.author.roles = []
        self.assertFalse(checks.with_role_check(self.ctx))

    def test_with_role_check_with_guild_and_required_role(self):
        """`with_role_check` returns `True` if `Context.author` has the required role."""
        self.ctx.author.roles.append(MockRole(id=10))
        self.assertTrue(checks.with_role_check(self.ctx, 10))
