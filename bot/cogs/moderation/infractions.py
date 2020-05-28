import logging
import random
import typing as t
from datetime import datetime

import discord
from dateutil.relativedelta import relativedelta
from discord import Embed, Member, Object
from discord.ext import commands
from discord.ext.commands import Context, command

from bot import constants
from bot.bot import Bot
from bot.constants import Event
from bot.decorators import respect_role_hierarchy, with_role
from bot.utils import infractions
from bot.utils.checks import has_higher_role_check
from bot.converters import Expiry, FetchedMember

from . import utils
from .modlog import ModLog
from .scheduler import InfractionScheduler
from .utils import UserSnowflake

log = logging.getLogger(__name__)


class Infractions(InfractionScheduler, commands.Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

    # region: Checks

    async def check_bot(self, ctx: Context, user: Member, command: str) -> bool:
        """Check user is not a bot"""
        if user.bot:
            # Build an embed
            embed = Embed(
                title=random.choice(constants.NEGATIVE_REPLIES),
                description=f"You can't use {command} on bot users",
                colour=constants.Colours.soft_red
            )
            await ctx.send(embed=embed)
            return True
        else:
            return False

    async def check_role(self, ctx: Context, user: Member, command: str) -> bool:
        """Check if author can use this command to specified user"""
        if not has_higher_role_check(ctx, user):
            # Build an embed
            embed = Embed(
                title=random.choice(constants.NEGATIVE_REPLIES),
                description=f"You can't use {command} on this user",
                colour=constants.Colours.soft_red
            )
            await ctx.send(embed=embed)
            return False
        else:
            return True

    # endregion
    # region: Permanent infractions

    @with_role(*constants.STAFF_ROLES)
    @command()
    async def warn(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Warn a user for a given reason"""

        await self.apply_warn(ctx, user, reason)

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def kick(self, ctx: Context, user: Member, *, reason: str = None) -> None:
        """Kick a user for a given reason"""

        await self.apply_kick(ctx, user, reason)

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def ban(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Permanently ban a user for the given reason"""

        # Pass 1_000_000_000 as duration (can't pass infinity)
        await self.apply_ban(ctx, user, reason)

    # endregion
    # region: Temporary infractions

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def tempban(self, ctx: Context, user: FetchedMember, duration: Expiry, *, reason: str = None) -> None:
        """Temporarily ban a user for the given time and reason"""

        await self.apply_ban(ctx, user, reason, duration)

    @with_role(*constants.STAFF_ROLES)
    @command(aliases=['mute'])
    async def tempmute(self, ctx: Context, user: Member, duration: Expiry, *, reason: str = None) -> None:
        """Temporarily mute a user for the given reason and duration."""

        await self.apply_mute(ctx, user, reason, duration)

    # endregion
    # region: Permanent shadow infractions

    @with_role(*constants.MODERATION_ROLES)
    @command(hidden=True, aliases=['shadowkick', 'skick'])
    async def shadow_kick(self, ctx: Context, user: Member, *, reason: str = None) -> None:
        """Kick a user for the given reason without notifying the user."""

        await self.apply_kick(ctx, user, reason, hidden=True)

    @with_role(*constants.MODERATION_ROLES)
    @command(hidden=True, aliases=['shadowban', 'sban'])
    async def shadow_ban(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Permanently ban a user for the given reason without notifying the user."""

        await self.apply_ban(ctx, user, reason, hidden=True)

    # endregion
    # region: Temporary shadow infractions

    @with_role(*constants.MODERATION_ROLES)
    @command(hidden=True, aliases=['shadowtempban', 'stempban'])
    async def shadow_tempban(self, ctx: Context, user: FetchedMember, duration: Expiry, *, reason: str = None) -> None:
        """Temporarily ban a user for the given reason and duration without notifying the user."""

        await self.apply_ban(ctx, user, reason, duration, hidden=True)

    @with_role(*constants.MODERATION_ROLES)
    @command(hidden=True, aliases=['shadowtempmute', 'stempmute', 'shadowmute', 'smute'])
    async def shadow_tempmute(self, ctx: Context, user: Member, duration: Expiry, *, reason: str = None) -> None:
        """Temporarily mute a user for the given reason and duration without notifying the user."""

        await self.apply_mute(ctx, user, reason, duration, hidden=True)

    # endregion
    # region: Pardon infractions

    @with_role(*constants.STAFF_ROLES)
    @command()
    async def unmute(self, ctx: Context, user: Member, *, reason: str = None) -> None:
        """Prematurely end the active mute infraction for the user."""

        infraction_list = infractions.get_active_infractions(user, "mute")
        infraction = max(infraction_list, key=lambda o: o.stop)
        await self.pardon_infraction(ctx, infraction)

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def unban(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Prematurely end the active ban infraction for the user."""

        infraction_list = infractions.get_active_infractions(user, "ban")
        infraction = max(infraction_list, key=lambda o: o.stop)
        await self.pardon_infraction(ctx, infraction)

    @with_role(constants.Roles.owners)
    @command()
    async def pardon(self, ctx: Context, infraction_id: int) -> None:
        """Pardon any infraction by its ID"""

        infraction = infractions.get_infraction_by_row(infraction_id)

        await self.pardon_infraction(ctx, infraction)

    @with_role(constants.Roles.owners)
    @command(hidden=True, aliases=["delinf", "infdel", "remove_infraction"])
    async def delete_infraction(self, ctx: Context, infraction_id: int) -> None:
        """Remove infraction by its ID"""

        infraction = infractions.get_infraction_by_row(infraction_id)

        await self.remove_infraction(ctx, infraction)

    # endregion
    # region: Infraction apply functions

    @respect_role_hierarchy()
    async def apply_ban(self, ctx: Context, user: UserSnowflake, reason: str = None, duration: int = 1_000_000_000, hidden: bool = False) -> None:
        """Apply a ban infraction"""

        infraction = infractions.Infraction(
            user.id, "ban", reason, ctx.author.id, datetime.now(), duration)

        # Get current user's active bans
        infs = infractions.get_active_infractions(
            user, inf_type='ban')

        # Determine if the user has any active ban infractions that override the current one
        for inf in infs:
            if inf.duration == 1_000_000_000:
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description="This user is already banned permanently",
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return
            if inf.stop > (datetime.now() + relativedelta(seconds=duration)):
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description=f"This user is already banned\n(Currents ban ends at: {inf.stop})",
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return

        # Do not send member_remove message to mod_log in case the user is member
        if ctx.guild.get_member(user.id):
            self.mod_log.ignore(Event.member_remove, user.id)

        action = ctx.guild.ban(user, reason=reason)
        infraction.add_to_database()
        await self.apply_infraction(ctx, infraction, user, action, hidden)

    @respect_role_hierarchy()
    async def apply_kick(self, ctx: Context, user: Member, reason: str = None, hidden: bool = False) -> None:
        """Apply a kick infraction"""

        infraction = infractions.Infraction(
            user.id, 'kick', reason, ctx.author.id, datetime.now(), 0)

        # Do not send member_remove message to mod_log
        self.mod_log.ignore(Event.member_remove, user.id)

        action = user.kick(reason=reason)
        infraction.add_to_database()
        await self.apply_infraction(ctx, infraction, user, action, hidden)

    @respect_role_hierarchy()
    async def apply_mute(self, ctx: Context, user: Member, reason: str = None, duration: int = 1_000_000_000, hidden: bool = False) -> None:
        """Apply a mute infraction"""

        infraction = infractions.Infraction(
            user.id, 'mute', reason, ctx.author.id, datetime.now(), duration)

        # Get current user's active mutes
        infs = infractions.get_active_infractions(
            user, inf_type='mute')

        # Determine if the user has any active mute infractions that override the current one
        for inf in infs:
            if inf.duration == 1_000_000_000:
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description="This user is already muted permanently",
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return
            if inf.stop > (datetime.now() + relativedelta(seconds=duration)):
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description=f"This user is already muted\n(Currents mute ends at: {inf.stop})",
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return

        # Do not send member_update message to mod_log
        self.mod_log.ignore(Event.member_update, user.id)

        async def action() -> None:
            await user.add_roles(discord.Object(constants.Roles.muted), reason=reason)
            await user.move_to(None, reason=reason)
        infraction.add_to_database()

        await self.apply_infraction(ctx, infraction, user, action(), hidden)

    @respect_role_hierarchy()
    async def apply_warn(self, ctx: Context, user: UserSnowflake, reason: str = None, hidden: bool = False) -> None:
        """Apply a warn infraction"""

        infraction = infractions.Infraction(
            user.id, 'warn', reason, ctx.author.id, datetime.now(), 0)

        infraction.add_to_database()
        await self.apply_infraction(ctx, infraction, user, hidden=hidden)

    # endregion
    # region: Infraction pardon functions

    async def pardon_mute(self, user_id: int, guild: discord.Guild, reason: str) -> t.Dict[str, str]:
        """Remove a user's muted role, DM them a notification, and return a log dict."""

        user = guild.get_member(user_id)
        log_text = {}

        if user:
            self.mod_log.ignore(Event.member_update, user.id)
            await user.remove_roles(Object(constants.Roles.muted), reason=reason)

            # DM the user about the expiration
            notified = await utils.notify_pardon(
                user=user,
                title="You have been unmuted",
                content="You may now send messages in the server",
                icon_url=utils.INFRACTION_ICONS["mute"][1]
            )

            log_text["Member"] = f'User {user.mention} (`{user.id}`)'
            log_text["DM"] = "Sent" if notified else "**Failed**"
        else:
            log.info(f"Failed to unmute user {user_id}: user not found")
            log_text["Failure"] = "User was not found in the guild"

        return log_text

    async def pardon_ban(self, user_id: int, guild: discord.Guild, reason: str) -> t.Dict[str, str]:
        """Remove a user's ban on the Discord guild and return a log dict."""

        user = discord.Object(user_id)
        log_text = {}

        self.mod_log.ignore(Event.member_unban, user_id)

        try:
            await guild.unban(user, reason=reason)
        except discord.NotFound:
            log.info(
                f"Failed to unban user {user_id} no active ban found on Discord")
            log_text["Note"] = "No active ban found on Discord"

        return log_text

    async def _pardon_action(self, infraction: infractions.Infraction) -> t.Optional[t.Dict[str, str]]:
        """
        Execute deactivation steps specific to the infraction's type and return a log dict.

        If an infraction type is unsupported, return None instead.
        """
        guild = self.bot.get_guild(constants.Guild.id)
        user_id = infraction.user_id
        reason = f"Infraction #{infraction.id} expired or was pardoned."

        if infraction.type == "mute":
            return await self.pardon_mute(user_id, guild, reason)
        elif infraction.type == "ban":
            return await self.pardon_ban(user_id, guild, reason)

    # endregion
