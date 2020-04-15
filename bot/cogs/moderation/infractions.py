import logging
import random
from datetime import datetime

from discord import Embed, Member
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
from bot.utils.converters import FetchedMember

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
    @command(name='warn', aliases=['infraction'])
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

        self.mod_log.ignore(Event.member_remove, user.id)

        try:
            await ctx.guild.ban(user, reason=reason)

            # Give ban infraction with 100 years time (can't use infinity)
            infractions.Infraction(
                user.id, 'ban', reason, ctx.author.id, datetime.now(), 1_000_000_000, write_to_db=True)

            await ctx.send(f':exclamation:User {user.mention} has been permanently banned ({reason})')
        except Forbidden:
            raise BotMissingPermissions('ban')

    @with_role(*constants.MODERATION_ROLES)
    @command()
    async def unban(self, ctx: Context, user: FetchedMember) -> None:
        infs = infractions.get_active_infractions(user, inf_type='ban')
        if len(infs) >= 1:
            log.info(f'User {user} was unbanned by {ctx.author}')

            force = False
            for infraction in infs:
                await infraction.pardon(ctx.guild, user, force=force)
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
