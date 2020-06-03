import logging

from discord.ext import commands
from discord.ext.commands import Context, command

from bot.bot import Bot
from bot.constants import STAFF_ROLES
from bot.constants import Bot as BotConstant
from bot.constants import Channels, Emojis, Roles
from bot.decorators import in_whitelist
from bot.utils.checks import with_role_check, without_role_check

log = logging.getLogger(__name__)


class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @in_whitelist(redirect=Channels.commands, roles=STAFF_ROLES)
    @command()
    async def subscribe(self, ctx: Context) -> None:
        """Get notified on new announcements"""
        if without_role_check(ctx, Roles.announcements):
            author = ctx.author
            role = ctx.guild.get_role(Roles.announcements)

            await author.add_roles(role)
            log.debug(f"User {author} has subscribed to notifications")
            await ctx.send(f"{Emojis.check_mark}You will now be notified on new announcements {author.mention}")
        else:
            await ctx.send(f"{Emojis.cross_mark}You are already subscribed (use `{BotConstant.prefix}unsubscribe` to unsubscribe)")

    @in_whitelist(redirect=Channels.commands, roles=STAFF_ROLES)
    @command()
    async def unsubscribe(self, ctx: Context) -> None:
        """Stop receiving new announcements"""
        if with_role_check(ctx, Roles.announcements):
            author = ctx.author
            role = ctx.guild.get_role(Roles.announcements)

            await author.remove_roles(role)
            log.debug(f"User {author} has unsubscribed to notifications")
            await ctx.send(f"{Emojis.check_mark}You will no longer be notified on new announcements {author.mention}")
        else:
            await ctx.send(f"{Emojis.cross_mark}You are already unsubscribed (use `{BotConstant.prefix}subscribe` to subscribe)")


def setup(bot: Bot) -> None:
    """Load the ErrorHandler cog."""
    bot.add_cog(Announcements(bot))
