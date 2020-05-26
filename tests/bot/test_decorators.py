import unittest
import unittest.mock
import collections

from bot.decorators import InChannelCheckFailure, in_channel
from tests import helpers

InWhitelistTestCase = collections.namedtuple(
    "WhitelistedContextTestCase", ("args", "kwargs", "ctx", "description"))


class InChannelTests(unittest.TestCase):
    """Tests for the `in_channel` check"""

    @classmethod
    def setUpClass(cls):
        """Set up helpers so that they only need to be defined once"""
        cls.commands_channel = helpers.MockTextChannel(id=123456789)
        cls.non_whitelisted_channel = helpers.MockTextChannel(id=666666)
        cls.hidden_channel = helpers.MockTextChannel(id=88888888)
        cls.general_channel = helpers.MockTextChannel(id=987654321)
        # cls.dm_channel = helpers.MockDMChannel()

        cls.non_staff_member = helpers.MockMember()
        cls.staff_role = helpers.MockRole(id=121212)
        cls.staff_member = helpers.MockMember(roles=(cls.staff_role, ))

        cls.channels = (cls.commands_channel.id, )
        cls.hidden_channels = (cls.hidden_channel.id, )
        cls.roles = (cls.staff_role.id, )

    def test_predicate_returns_true_for_whitelisted_context(self):
        """The predicate should return `True` if a whitelisted context was passed to it"""
        test_cases = (
            InWhitelistTestCase(
                args=self.channels,
                kwargs={},
                ctx=helpers.MockContext(
                    channel=self.commands_channel, author=self.non_staff_member),
                description="In whitelisted channels by members without whitelisted roles",
            ),
            InWhitelistTestCase(
                args=self.channels,
                kwargs={"bypass_roles": self.roles},
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.staff_member),
                description="Bypass role outside of whitelisted channel",
            ),
            InWhitelistTestCase(
                args=self.channels,
                kwargs={"hidden_channels": self.hidden_channels},
                ctx=helpers.MockContext(
                    channel=self.hidden_channel, author=self.non_staff_member),
                description="In hidden channel by members without whitelisted roles",
            ),
            InWhitelistTestCase(
                args=self.channels,
                kwargs={
                    "bypass_roles": self.roles,
                    "hidden_channels": self.hidden_channels
                },
                ctx=helpers.MockContext(
                    channel=self.general_channel, author=self.staff_member),
                description="Case with all whitelist kwargs used",
            ),
        )

        for test_case in test_cases:
            # patch `commands.check` with a no-op lambda that just returns the predicate passed to it
            # so we can test the predicate that was generated from the specified args&kwargs
            with unittest.mock.patch("bot.decorators.commands.check", new=lambda predicate: predicate):
                predicate = in_channel(*test_case.args, **test_case.kwargs)

            with self.subTest(test_description=test_case.description):
                self.assertTrue(predicate(test_case.ctx))

    def test_predicate_raises_exception_for_non_whitelisted_context(self):
        """The predicate should raise `InChannelCheckFailure` for a non-whitelisted member"""
        test_cases = (
            InWhitelistTestCase(
                args=self.channels,
                kwargs={},
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="In non-whitelisted channels by members without whitelisted roles",
            ),
            InWhitelistTestCase(
                args=self.channels,
                kwargs={"bypass_roles": self.roles},
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="Non-Bypass role outside of whitelisted channel",
            ),
            InWhitelistTestCase(
                args=self.channels,
                kwargs={"hidden_channels": self.hidden_channels},
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="In non-hidden, non-whitelisted channel by members without whitelisted roles",
            ),
            # InWhitelistTestCase(
            #     args=self.channels,
            #     kwargs={
            #         "bypass_roles": self.roles,
            #         "hidden_channels": self.hidden_channels
            #     },
            #     ctx=helpers.MockContext(
            #         channel=self.dm_channel, author=self.dm_channel.me),
            #     description="Commands issued in DM channel should be rejected",
            # ),
        )

        for test_case in test_cases:
            channels_str = ', '.join(f"<#{c_id}>" for c_id in test_case.args)
            redirect_message = f"Sorry, but you may only use this command within {channels_str}."

            # patch `command.check` with a no-op lambda that just returns the predicate passed to it
            # so we can test the predicate that was generated from the specified args&kwargs
            with unittest.mock.patch("bot.decorators.commands.check", new=lambda predicate: predicate):
                predicate = in_channel(*test_case.args, **test_case.kwargs)

            with self.subTest(test_description=test_case.description):
                with self.assertRaisesRegex(InChannelCheckFailure, redirect_message):
                    predicate(test_case.ctx)
