import asyncio
import logging
from typing import Optional, NamedTuple

from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Context

from bot.bot import Bot
from bot.cogs.moderation.modlog import ModLog
from bot.constants import (STAFF_ROLES, Channels, Colours, Emojis, Guild,
                           Icons, Roles)
from bot.converters import SilenceDurationConverter
from bot.utils.checks import with_role_check
from bot.utils.scheduling import Scheduler

log = logging.getLogger(__name__)

SilencedChannel = NamedTuple(
    "SilencedChannel", [("ctx", Context), ("delay", int)]
)


class Silence(Scheduler, commands.Cog):
    """Commands for stopping channel messages for `Guest` role in a channel."""

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.muted_channels = set()
        self._get_instance_var_task = self.bot.loop.create_task(
            self._get_instance_vars())
        self._get_instance_vars_event = asyncio.Event()

    @property
    def mod_log(self) -> ModLog:
        """Get the currently loaded ModLog cog instance"""
        return self.bot.get_cog("ModLog")

    async def _get_instance_vars(self) -> None:
        """Get instance variables after they're aviable to get from the guild"""
        await self.bot.wait_until_guild_available()
        guild = self.bot.get_guild(Guild.id)
        self._guests_role = guild.get_role(Roles.guests)
        self._mod_log_channel = self.bot.get_channel(Channels.mod_log)
        self._get_instance_vars_event.set()

    async def _scheduled_task(self, channel: SilencedChannel) -> None:
        """Calls `self.unsilence` on expired silenced channel to unsilence it."""
        await asyncio.sleep(channel.delay)
        log.info("Unsilencing channel after set delay.")

        # Because `self.unsilence` explicitly cancels this scheduled task, it is shielded
        # to avoid prematurely cancelling itself
        await asyncio.shield(channel.ctx.invoke(self.unsilence))

    @commands.command(aliases=("hush", "mutechat"))
    async def silence(self, ctx: Context, duration: SilenceDurationConverter = 10) -> None:
        """
        Silence the current channel for `duration` minutes or `forever`

        Duration is capped at 15 minutes for non-moderators.
        """
        if not ctx.channel.permissions_for(ctx.author).manage_messages:
            await ctx.send(
                f"{Emojis.cross_mark} sorry, you can't manage messages here")
            log.debug(
                f"{ctx.author} tried to silence #{ctx.channel} without manage messages permission")
            return
        await self._get_instance_vars_event.wait()
        log.debug(f"{ctx.author} is silencing channel #{ctx.channel}")

        if not await self._silence(ctx.channel, duration=duration):
            await ctx.send(f"{Emojis.cross_mark} current channel is already silenced.")
            return

        # Log this to #mod_log channel
        response = (
            f"**Channel:** {ctx.channel.mention} (`{ctx.channel.id}`)\n"
            f"**Actor:** {ctx.author.mention} (`{ctx.author.mention}`)\n"
            f"**Duration:** {f'{duration} minute(s)' if duration is not None else 'forever'}"
        )
        await self.mod_log.send_log_message(
            Icons.message_delete, Colours.soft_red,
            "Channel silenced",
            response,
            channel_id=Channels.mod_log
        )

        if duration is None:
            await ctx.send(f"{Emojis.check_mark} silenced current channel indefinitely.")
            return
        await ctx.send(f"{Emojis.check_mark} silenced current channel for {duration} minute(s).")

        channel = SilencedChannel(
            ctx=ctx,
            delay=duration*60
        )

        self.schedule_task(ctx.channel.id, channel)

    @commands.command(aliases=("unhush", "unmutechat"))
    async def unsilence(self, ctx: Context) -> None:
        """Unsiilence the current channel."""
        if not ctx.channel.permissions_for(ctx.author).manage_messages:
            await ctx.send(
                f"{Emojis.cross_mark} sorry, you can't manage messages here")
            log.debug(
                f"{ctx.author} tried to unsilence #{ctx.channel} without manage messages permission")
            return

        await self._get_instance_vars_event.wait()
        log.debug(
            f"Unsilencing channel #{ctx.channel} from {ctx.author}'s command.")

        if not await self._unsilence(ctx.channel):
            await ctx.send(f"{Emojis.cross_mark} current channel is not silenced")
            return

        await ctx.send(f"{Emojis.check_mark} unsilenced current channel.")

        # Log this to #mod_log channel
        response = (
            f"**Channel:** {ctx.channel.mention} (`{ctx.channel.id}`)\n"
            f"**Actor:** {ctx.author.mention} (`{ctx.author.mention}`)\n"
        )
        await self.mod_log.send_log_message(
            Icons.message_edit, Colours.soft_green,
            "Channel unsilenced",
            response,
            channel_id=Channels.mod_log
        )

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
            self.cancel_task(channel.id)
            return True
        log.info(
            f"Tried to unsilence channel ${channel} ({channel.id}) but the channel was not silenced.")
        return False

    def cog_check(self, ctx: Context) -> bool:
        """Only allow moderators to invoke the commands in this cog."""
        return with_role_check(ctx, *STAFF_ROLES)
