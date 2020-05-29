import asyncio
import logging
from typing import Optional

from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Context

from bot.bot import Bot
from bot.constants import STAFF_ROLES, Channels, Emojis, Guild, Roles
from bot.converters import SilenceDurationConverter
from bot.utils.checks import with_role_check

log = logging.getLogger(__name__)


class Silence(commands.Cog):
    """Commands for stopping channel messages for `Guest` role in a channel."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.muted_channels = set()
        self._get_instance_var_task = self.bot.loop.create_task(
            self._get_instance_vars())
        self._get_instance_vars_event = asyncio.Event()

    async def _get_instance_vars(self) -> None:
        """Get instance variables after they're aviable to get from the guild"""
        await self.bot.wait_until_guild_available()
        guild = self.bot.get_guild(Guild.id)
        self._guests_role = guild.get_role(Roles.guests)
        self._mod_log_channel = self.bot.get_channel(Channels.mod_log)
        self._get_instance_vars_event.set()

    @commands.command(aliases=("hush",))
    async def silence(self, ctx: Context, duration: SilenceDurationConverter = 10) -> None:
        """
        Silence the current channel for `duration` minutes or `forever`

        Duration is capped at 15 minutes for non-moderators.
        """
        await self._get_instance_vars_event.wait()
        log.debug(f"{ctx.author} is silencing channel #{ctx.channel}")
        if not await self._silence(ctx.channel, duration=duration):
            await ctx.send(f"{Emojis.cross_mark} current channel is already silenced.")
            return
        if duration is None:
            await ctx.send(f"{Emojis.check_mark} silenced current channel indefinitely.")
            return

        await ctx.send(f"{Emojis.check_mark} silenced current channel for {duration} minute(s).")
        await asyncio.sleep(duration*60)

        log.info("Unsilencing channel after set delay.")
        await ctx.invoke(self.unsilence)

    @commands.command(aliases=("unhush",))
    async def unsilence(self, ctx: Context) -> None:
        """Unsiilence the current channel."""
        await self._get_instance_vars_event.wait()
        log.debug(
            f"Unsilencing channel #{ctx.channel} from {ctx.author}'s command.")
        if await self._unsilence(ctx.channel):
            await ctx.send(f"{Emojis.check_mark} unsilenced current channel.")

    async def _silence(self, channel: TextChannel, duration: Optional[int]) -> bool:
        """Silence `channel` for `self._guests_role`"""
        current_overwrite = channel.overwrites_for(self._guests_role)
        if current_overwrite.send_messages is False:
            log.info(
                f"Tried to silence channel #{channel} ({channel.id}) but the channel was already silenced.")
            return False
        await channel.set_permissions(self._guests_role, **dict(current_overwrite, send_messages=False))
        self.muted_channels.add(channel)
        if not duration:
            log.info(f"Silenced #{channel} ({channel.id}) indefinitely.")
            return True

        log.info(
            f"Silenced #{channel} ({channel.id}) for {duration} minute(s).")
        return True

    async def _unsilence(self, channel: TextChannel) -> bool:
        """
        Unsilence `channel`

        Check if `channel` is silenced through `PermissionOverwrite`, if it is, unsilence it.
        Return `True` if channel permissions were changed, `False` otherwise
        """
        current_overwrite = channel.overwrites_for(self._guests_role)
        if current_overwrite.send_messages is False:
            await channel.set_permissions(self._guests_role, **dict(current_overwrite, send_messages=None))
            log.info(f"Unsilenced channel #{channel} ({channel.id}).")
            self.muted_channels.discard(channel)
            return True
        log.info(
            f"Tried to unsilence channel ${channel} ({channel.id}) but the channel was not silenced.")
        return False

    def cog_check(self, ctx: Context) -> bool:
        """Only allow moderators to invoke the commands in this cog."""
        return with_role_check(ctx, *STAFF_ROLES)
