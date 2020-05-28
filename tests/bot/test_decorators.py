import collections
import unittest
import unittest.mock

from bot import constants
from bot.decorators import InWhitelistCheckFailure, in_whitelist
from tests import helpers

InWhitelistTestCase = collections.namedtuple(
    "WhitelistedContextTestCase", ("kwargs", "ctx", "description"))


class InChannelTests(unittest.TestCase):
    """Tests for the `in_channel` check"""

    @classmethod
    def setUpClass(cls):
        """Set up helpers so that they only need to be defined once"""
        cls.commands_channel = helpers.MockTextChannel(id=123456789)
        cls.non_whitelisted_channel = helpers.MockTextChannel(
            id=666666, category_id=123456)
        cls.general_channel = helpers.MockTextChannel(
            id=987654321, category_id=987654)
        cls.dm_channel = helpers.MockDMChannel()

        cls.non_staff_member = helpers.MockMember()
        cls.staff_role = helpers.MockRole(id=121212)
        cls.staff_member = helpers.MockMember(roles=(cls.staff_role, ))

        cls.channels = (cls.commands_channel.id, )
        cls.categories = (cls.general_channel.category_id, )
        cls.roles = (cls.staff_role.id, )

    def test_predicate_returns_true_for_whitelisted_context(self):
        """The predicate should return `True` if a whitelisted context was passed to it"""
        test_cases = (
            InWhitelistTestCase(
                kwargs={"channels": self.channels},
                ctx=helpers.MockContext(
                    channel=self.commands_channel, author=self.non_staff_member),
                description="In whitelisted channels by members without whitelisted roles",
            ),
            InWhitelistTestCase(
                kwargs={"redirect": self.commands_channel.id},
                ctx=helpers.MockContext(
                    channel=self.commands_channel, author=self.non_staff_member),
                description="`redirect` should be implicitly added to `channels`",
            ),
            InWhitelistTestCase(
                kwargs={"categories": self.categories},
                ctx=helpers.MockContext(
                    channel=self.general_channel, author=self.non_staff_member),
                description="In whitelisted category without whitelisted role",
            ),
            InWhitelistTestCase(
                kwargs={"roles": self.roles},
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.staff_member),
                description="Whitelisted role outside of whitelisted channel/category"
            ),
            InWhitelistTestCase(
                kwargs={
                    "channels": self.channels,
                    "categories": self.categories,
                    "roles": self.roles,
                    "redirect": self.commands_channel,
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
                predicate = in_whitelist(**test_case.kwargs)

            with self.subTest(test_description=test_case.description):
                self.assertTrue(predicate(test_case.ctx))

    def test_predicate_raises_exception_for_non_whitelisted_context(self):
        """The predicate should raise `InChannelCheckFailure` for a non-whitelisted member"""
        test_cases = (
            InWhitelistTestCase(
                kwargs={
                    "categories": self.categories,
                    "channels": self.channels,
                    "roles": self.roles,
                    "redirect": self.commands_channel,
                },
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="Failing check with an explicit redirect channel",
            ),
            InWhitelistTestCase(
                kwargs={
                    "categories": self.categories,
                    "channels": self.channels,
                    "roles": self.roles,
                },
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="Failing check with an implicit redirect channel",
            ),
            InWhitelistTestCase(
                kwargs={
                    "categories": self.categories,
                    "channels": self.channels,
                    "roles": self.roles,
                    "redirect": None,
                },
                ctx=helpers.MockContext(
                    channel=self.non_whitelisted_channel, author=self.non_staff_member),
                description="Failing check without a redirect channel",
            ),
            InWhitelistTestCase(
                kwargs={
                    "categories": self.categories,
                    "channels": self.channels,
                    "roles": self.roles,
                    "redirect": None,
                },
                ctx=helpers.MockContext(
                    channel=self.dm_channel, author=self.dm_channel.me),
                description="Commands issued in DM channel should be rejected",
            ),
        )

        for test_case in test_cases:
            if "redirect" not in test_case.kwargs or test_case.kwargs["redirect"] is not None:
                # There are two cases in which we have a redirect channel:
                #   1. No redirect channel was passed: the default value of `commands` is used
                #   2. An explicit `redirect` is set that is "not None"
                redirect_channel = test_case.kwargs.get(
                    "redirect", constants.Channels.commands)
                redirect_message = f" here. Please use the <#{redirect_channel}> channel instead"
            else:
                # If an explicit `None` was passed for `redirect`, there is no redirect channel
                redirect_message = ""

            exception_message = f"You are not allowed to use that command{redirect_message}."

            # patch `command.check` with a no-op lambda that just returns the predicate passed to it
            # so we can test the predicate that was generated from the specified args&kwargs
            with unittest.mock.patch("bot.decorators.commands.check", new=lambda predicate: predicate):
                predicate = in_whitelist(**test_case.kwargs)

            with self.subTest(test_description=test_case.description):
                with self.assertRaisesRegex(InWhitelistCheckFailure, exception_message):
                    predicate(test_case.ctx)
