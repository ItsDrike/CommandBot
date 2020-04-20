import logging
import random
import textwrap
from datetime import datetime

from dateutil.relativedelta import relativedelta
from discord import Colour, Embed, Member
from discord.errors import Forbidden
from discord.ext import commands
from discord.ext.commands import Context, command
from discord.ext.commands.errors import BotMissingPermissions

from bot import constants
from bot.bot import Bot
from bot.constants import Event
from bot.decorators import with_role
from bot.utils import infractions
from bot.utils.checks import has_higher_role_check
from bot.utils.converters import Expiry, FetchedMember
from bot.utils.time import humanize_delta

from .modlog import ModLog

log = logging.getLogger(__name__)


class Infractions(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

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

    @with_role(*constants.STAFF_ROLES)
    @command()
    async def warn(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Warn a user for a given reason"""
        if await self.check_bot(ctx, user, 'warn'):
            return
        if not await self.check_role(ctx, user, 'warn'):
            return

        infractions.Infraction(
            user.id, 'warn', reason, ctx.author.id, datetime.now(), 0, write_to_db=True)

        await ctx.send(f':exclamation:Warned {user.mention} ({reason})')

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def kick(self, ctx: Context, user: Member, *, reason: str = None) -> None:
        """Kick a user for a given reason"""

        if await self.check_bot(ctx, user, 'kick'):
            return
        if not await self.check_role(ctx, user, 'kick'):
            return

        infractions.Infraction(
            user.id, 'kick', reason, ctx.author.id, datetime.now(), 0, write_to_db=True)

        self.mod_log.ignore(Event.member_remove, user.id)

        try:
            await ctx.guild.kick(user, reason=reason)
            await ctx.send(f':exclamation:User {user.mention} has been kicked ({reason})')
        except Forbidden:
            raise BotMissingPermissions('kick')

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def ban(self, ctx: Context, user: FetchedMember, *, reason: str = None) -> None:
        """Permanently ban a user for the given reason"""

        if await self.check_bot(ctx, user, 'ban'):
            return
        if not await self.check_role(ctx, user, 'ban'):
            return

        infs = infractions.get_active_infractions(
            user, inf_type='ban')

        for infraction in infs:
            if infraction.duration == 1_000_000_000:
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description='This user is already banned',
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return

        self.mod_log.ignore(Event.member_remove, user.id)

        try:
            # Give ban infraction with 1000000000 seconds time (can't use infinity)
            infractions.Infraction(
                user.id, 'ban', reason, ctx.author.id, datetime.now(), 1_000_000_000, write_to_db=True)
            await ctx.guild.ban(user, reason=reason)
            await ctx.send(f':exclamation:User {user.mention} has been permanently banned ({reason})')
        except Forbidden:
            raise BotMissingPermissions('ban')

    @command()
    async def tempban(self, ctx: Context, user: FetchedMember, duration: Expiry, *, reason: str = None) -> None:
        """Temporarily ban a user for the given time and reason"""

        if await self.check_bot(ctx, user, 'ban'):
            return
        if not await self.check_role(ctx, user, 'ban'):
            return

        infs = infractions.get_active_infractions(
            user, inf_type='ban')

        for infraction in infs:
            if infraction.stop > (datetime.now() + relativedelta(seconds=duration)):
                embed = Embed(
                    title=random.choice(constants.NEGATIVE_REPLIES),
                    description=f"This user is already banned\n(Currents ban ends at: {infraction.stop})",
                    color=constants.Colours.soft_red
                )
                await ctx.send(embed=embed)
                return

        self.mod_log.ignore(Event.member_remove, user.id)

        try:
            # Give ban infraction with 1000000000 seconds time (can't use infinity)
            infractions.Infraction(
                user.id, 'ban', reason, ctx.author.id, datetime.now(), duration, write_to_db=True)
            await ctx.guild.ban(user, reason=reason)
            duration_str = humanize_delta(relativedelta(seconds=duration))
            await ctx.send(f':exclamation:User {user.mention} has been banned for {duration_str} ({reason})')
        except Forbidden:
            raise BotMissingPermissions('ban')

    # TODO: Add mute & unmute

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def unban(self, ctx: Context, user: FetchedMember) -> None:
        """Prematurely end the active ban infraction for the user."""
        infs = infractions.get_active_infractions(user, inf_type='ban')
        if len(infs) >= 1:
            log.info(f'User {user} was unbanned by {ctx.author}')

            force = False
            for infraction in infs:
                await infraction.pardon(ctx.guild, self.bot, force=force)
                # Make force pardon in case there are more infractions (discord logs only 1 ban)
                force = True

            await ctx.send(f'User {user} ({user.id}) was unbanned successfully')

        else:
            # Build an embed
            embed = Embed(
                title=random.choice(constants.NEGATIVE_REPLIES),
                description=f"This user is not banned",
                colour=constants.Colours.soft_red
            )
            await ctx.send(embed=embed)

    @with_role(constants.Roles.owners)
    @command()
    async def pardon(self, ctx: Context, infraction_id: int) -> None:
        """Pardon any infraction by its ID"""
        inf = await infractions.remove_infraction(ctx.guild, self.bot, infraction_id)

        if inf:
            user = ctx.guild.get_member(inf.user_id)
            if not user:
                user = inf.user_id

            actor = ctx.guild.get_member(inf.actor_id)
            if not actor:
                actor = inf.actor_id

            description = textwrap.dedent(f"""
            **Infraction Removed**
            ID: {infraction_id}
            Given to: {user}
            Type: {inf.type}
            Reason: {inf.reason}
            Actor: {actor}
            Duration: {inf.str_duration}
            Given: {inf.str_start}
            Active: {inf.is_active}
            """).strip()

            embed = Embed(
                title=random.choice(constants.POSITIVE_REPLIES),
                description=description,
                colour=Colour.blurple()
            )
        else:
            embed = Embed(
                title=random.choice(constants.NEGATIVE_REPLIES),
                description=f'Infraction not found',
                colour=constants.Colours.soft_red
            )

        await ctx.send(embed=embed)
