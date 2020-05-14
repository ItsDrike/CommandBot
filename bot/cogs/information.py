import colorsys
import logging
import random
import textwrap
from collections import Counter, defaultdict
from string import Template
from typing import Union

from discord import Colour, Embed, Guild, Member, Role, Status, utils
from discord.ext.commands import Cog, Context, command
from discord.utils import escape_markdown

import bot.utils.infractions as infractions
from bot import constants
from bot.bot import Bot
from bot.decorators import InChannelCheckFailure, with_role
from bot.pagination import LinePaginator
from bot.utils.checks import has_higher_role_check, with_role_check
from bot.utils.converters import FetchedMember
from bot.utils.time import time_since

log = logging.getLogger(__name__)


class Information(Cog):
    """A cog with commands for generating embeds with server info, such as server stats and user info."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @with_role(*constants.MODERATION_ROLES)
    @command(name="roles")
    async def roles_info(self, ctx: Context) -> None:
        """Returns a list of all roles and their corresponding IDs."""
        # Sort the roles alphabetically and remove the @everyone role
        roles = sorted(ctx.guild.roles[1:], key=lambda role: role.name)

        # Build a list
        role_list = []
        for role in roles:
            role_list.append(f"`{role.id}` - {role.mention}")

        # Build an embed
        embed = Embed(
            title=f"Role information (Total {len(roles)} role{'s' * (len(role_list) > 1)})",
            colour=Colour.blurple()
        )

        await LinePaginator.paginate(role_list, ctx, embed, empty=False)

    @with_role(*constants.MODERATION_ROLES)
    @command(name="role")
    async def role_info(self, ctx: Context, *roles: Union[Role, str]) -> None:
        """
        Return information on a role or list of roles.

        To specify multiple roles just add to the arguments, delimit roles with spaces in them using quotation marks.
        """
        parsed_roles = []
        failed_roles = []

        for role_name in roles:
            if isinstance(role_name, Role):
                # Role conversion has already succeeded
                parsed_roles.append(role_name)
                continue

            role = utils.find(
                lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)

            if not role:
                failed_roles.append(role_name)
                continue

            parsed_roles.append(role)

        if failed_roles:
            msg = ':x: I could not convert the following role names to a role: \n-'
            msg += '\n-'.join(failed_roles)
            await ctx.send(msg)

        for role in parsed_roles:
            h, s, v = colorsys.rgb_to_hsv(*role.colour.to_rgb())

            embed = Embed(
                title=f"{role.name} info",
                colour=role.colour,
            )
            embed.add_field(name="ID", value=role.id, inline=True)
            embed.add_field(name="Colour (RGB)",
                            value=f"#{role.colour.value:0>6x}", inline=True)
            embed.add_field(name="Colour (HSV)",
                            value=f"{h:.2f} {s:.2f} {v}", inline=True)
            embed.add_field(name="Member count", value=len(
                role.members), inline=True)
            embed.add_field(name="Position", value=role.position)
            embed.add_field(name="Permission code",
                            value=role.permissions.value, inline=True)

            await ctx.send(embed=embed)

    @command(name="server", aliases=["server_info", "guild", "guild_info"])
    async def server_info(self, ctx: Context) -> None:
        """Returns an embed full of server information."""
        created = time_since(ctx.guild.created_at, precision="days")
        features = ", ".join(ctx.guild.features)
        region = ctx.guild.region

        roles = len(ctx.guild.roles)
        member_count = ctx.guild.member_count

        # How many of each type of channel?
        channels = Counter(c.type for c in ctx.guild.channels)
        channel_counts = "".join(sorted(
            f"{str(ch).title()} channels: {channels[ch]}\n" for ch in channels)).strip()

        # How many of each user status?
        statuses = Counter(member.status for member in ctx.guild.members)
        embed = Embed(colour=Colour.blurple())

        # Because channel_counts lacks leading whitespace, it breaks the dedent if it's inserted directly by the
        # f-string. While this is correctly formated by Discord, it makes unit testing difficult. To keep the formatting
        # without joining a tuple of strings we can use a Template string to insert the already-formatted channel_counts
        # after the dedent is made.
        embed.description = Template(
            textwrap.dedent(f"""
                **Server information**
                Created: {created}
                Voice region: {region}
                Features: {features}

                **Counts**
                Members: {member_count:,}
                Roles: {roles}
                $channel_counts

                **Members**
                {constants.Emojis.status_online} {statuses[Status.online]:,}
                {constants.Emojis.status_idle} {statuses[Status.idle]:,}
                {constants.Emojis.status_dnd} {statuses[Status.dnd]:,}
                {constants.Emojis.status_offline} {statuses[Status.offline]:,}
            """)
        ).substitute({"channel_counts": channel_counts})
        embed.set_thumbnail(url=ctx.guild.icon_url)

        await ctx.send(embed=embed)

    @command(name="user", aliases=["user_info", "member", "member_info"])
    async def user_info(self, ctx: Context, user: FetchedMember = None) -> None:
        """Returns info about a user."""
        if user is None:
            user = ctx.author

        # Do a role check if this is being executed on someone other than the caller
        elif user != ctx.author and not with_role_check(ctx, *constants.STAFF_ROLES):
            await ctx.send("You may not use this command on users other than yourself.")
            return

        # Non-staff may only do this in #bot-commands
        if not with_role_check(ctx, *constants.STAFF_ROLES):
            if not ctx.channel.id == constants.Channels.commands:
                raise InChannelCheckFailure(constants.Channels.commands)

        embed = await self.create_user_embed(ctx, user)

        await ctx.send(embed=embed)

    @command(name="infractions", aliases=["show_infractions"])
    async def infractions(self, ctx: Context, user: FetchedMember = None) -> None:
        '''Return user's infractions'''

        # TODO: Handle too long message

        if user is None:
            user = ctx.author

        # Do a role check if this is being executed on someone other than the caller
        elif user != ctx.author and not with_role_check(ctx, *constants.STAFF_ROLES):
            await ctx.send("You may not use this command on users other than yourself.")
            return

        # Prevent usage on someone with higher role
        if not has_higher_role_check(ctx, user):
            embed = Embed(
                color=constants.Colours.soft_red,
                title=random.choice(constants.NEGATIVE_REPLIES),
                description=f'You may not use this command on users with higher role than yours'
            )
            await ctx.send(embed=embed)
            return

        # Non-staff may only do this in #bot-commands
        if not with_role_check(ctx, *constants.STAFF_ROLES):
            if not ctx.channel.id == constants.Channels.commands:
                raise InChannelCheckFailure(constants.Channels.commands)

        embed = await self.create_infractions_embed(ctx, user)

        # Send infractions as DM, if user has any (bypass for staff members)
        if not with_role_check(ctx, *constants.STAFF_ROLES) and not len(infractions.get_infractions(user)) == 0:
            msg = f'Your infraction list was sent to you by DM, {user.mention}'
            await user.send(embed=embed)
            await ctx.send(msg)
        else:
            await ctx.send(embed=embed)

    @with_role(*constants.STAFF_ROLES)
    @command()
    async def infraction(self, ctx: Context, infraction_id: int) -> None:
        """Provide detailed info about single infraction"""
        infraction = infractions.get_infraction_by_row(infraction_id)

        if infraction:
            user = ctx.guild.get_member(infraction.user_id)
            if not user:
                user = infraction.user_id
            else:
                # Preform a role check if the user is found
                if not has_higher_role_check(ctx, user):
                    embed = Embed(
                        title=random.choice(constants.NEGATIVE_REPLIES),
                        description="You don't have permission to access this infraction",
                        colour=constants.Colours.soft_red
                    )
                    await ctx.send(embed=embed)
                    return

            actor = ctx.guild.get_member(infraction.actor_id)
            if not actor:
                actor = infraction.actor_id

            description = textwrap.dedent(f"""
            **Infraction Details**
            ID: {infraction_id}
            Given to: {user}
            Type: {infraction.type}
            Reason: {infraction.reason}
            Actor: {actor}
            Duration: {infraction.str_duration}
            Given: {infraction.str_start}
            Active: {infraction.is_active}
            """).strip()

            embed = Embed(
                title=random.choice(constants.POSITIVE_REPLIES),
                description=description,
                colour=Colour.blurple()
            )
        else:
            embed = Embed(
                title=random.choice(constants.NEGATIVE_REPLIES),
                description="No such infraction",
                colour=constants.Colours.soft_red
            )

        await ctx.send(embed=embed)

    @command()
    async def rules(self, ctx: Context) -> None:
        rules_channel = ctx.guild.get_channel(constants.Channels.rules)
        await ctx.send(f'Please read the server rules at: {rules_channel.mention}')

    @command()
    async def rule(self, ctx: Context, number: int):
        rules = constants.Rules.rules
        try:
            rule = rules[number]
        except KeyError:
            await ctx.send(f":x: No such rule ({number})")
            return

        embed = Embed(
            title=f"#{number}: {rule['title']}",
            description=rule['description'],
            color=Colour.blurple()
        )
        await ctx.send(embed=embed)
    # region: Infractions sub-functions

    async def create_user_embed(self, ctx: Context, user: FetchedMember) -> Embed:
        """Creates an embed containing information on the `user`."""
        created = time_since(user.created_at, max_units=3)

        name = str(user)
        custom_status = ''
        if isinstance(user, Member):
            if user.nick:
                name = f"{user.nick} ({name})"

            mention = user.mention

            joined = time_since(user.joined_at, precision="days")
            roles = ", ".join(role.mention for role in user.roles[1:])

            for activity in user.activities:
                # Check activity.state for None value if user has a custom status set
                # This guards against a custom status with an emoji but no text, which will cause
                # escape_markdown to raise an exception
                # This can be reworked after a move to d.py 1.3.0+, which adds a CustomActivity class
                if activity.name == 'Custom Status' and activity.state:
                    state = escape_markdown(activity.state)
                    custom_status = f'Status: {state}\n'
        else:
            roles = None
            mention = f'{user.name}#{user.discriminator}'

        description = [
            textwrap.dedent(f"""
                **User Information**
                Created: {created}
                Profile: {mention}
                ID: {user.id}
                {custom_status}
            """).strip()
        ]
        if isinstance(user, Member):
            description[0] += '\n'
            description[0] += textwrap.dedent(f"""
                **Member Information**
                Joined: {joined}
                Roles: {roles or None}
            """).strip()

        if has_higher_role_check(ctx, user):
            # Show more verbose output in staff channels for infractions
            if ctx.channel.id in constants.STAFF_CHANNELS and with_role_check(ctx, *constants.STAFF_ROLES):
                description.append(await self.expanded_user_infraction_counts(user))
            else:
                description.append(await self.basic_user_infraction_counts(user))

        # Let's build the embed now
        embed = Embed(
            title=name,
            description="\n\n".join(description)
        )

        embed.set_thumbnail(url=user.avatar_url_as(format="png"))
        embed.colour = user.top_role.colour if roles else Colour.blurple()

        return embed

    async def create_infractions_embed(self, ctx: Context, user: FetchedMember) -> Embed:
        """Create an embed containing information on user's infractions"""

        name = str(user)
        if isinstance(user, Member):
            if user.nick:
                name = f'{user.nick} ({name})'

            roles = user.roles[1:]
        else:
            roles = []

        description = await self.full_user_infraction_counts(ctx, user)

        embed = Embed(
            title=name,
            description=description
        )

        embed.set_thumbnail(url=user.avatar_url_as(format="png"))
        embed.colour = user.top_role.colour if roles else Colour.blurple()

        return embed

    async def basic_user_infraction_counts(self, member: FetchedMember) -> str:
        """Gets the total and active infraction counts for the given `member`."""
        infs = infractions.get_infractions(member)
        active_infs = infractions.get_active_infractions(member)

        total_infractions = len(infs)
        active_infractions = len(active_infs)

        infraction_output = f"**Infractions**\nTotal: {total_infractions}\nActive: {active_infractions}"

        return infraction_output

    async def expanded_user_infraction_counts(self, member: FetchedMember) -> str:
        """
        Gets expanded infraction counts for the given `member`.

        The counts will be split by infraction type and the number of active infractions for each type will indicated
        in the output as well.
        """
        infs = infractions.get_infractions(member)

        infraction_output = ["**Infractions**"]
        if not infs:
            infraction_output.append(
                "This user has never received an infraction.")
        else:
            # Count infractions split by `type` and `active` status for this user
            infraction_types = set()
            infraction_counter = defaultdict(int)
            for infraction in infs:
                infraction_type = infraction.type
                infraction_active = 'active' if infraction.is_active else 'inactive'

                infraction_types.add(infraction_type)
                infraction_counter[f"{infraction_active} {infraction_type}"] += 1

            # Format the output of the infraction counts
            for infraction_type in sorted(infraction_types):
                active_count = infraction_counter[f"active {infraction_type}"]
                total_count = active_count + \
                    infraction_counter[f"inactive {infraction_type}"]

                line = f"{infraction_type.capitalize()}s: {total_count}"
                if active_count:
                    line += f" ({active_count} active)"

                infraction_output.append(line)

        return "\n".join(infraction_output)

    async def full_user_infraction_counts(self, ctx: Context, member: FetchedMember) -> str:
        """
        Gets full infraction info with descriptions for the given member

        The counts will be split by `active` status and infraction `type`
        """

        def get_infractions_by_type(guild: Guild, all_infractions: list) -> dict:
            infraction_types = set()
            infractions_dict = defaultdict(list)

            # Loop through all given infractions
            for infraction in all_infractions:
                # Add infraction type to infraction_types set
                infraction_type = infraction.type
                infraction_types.add(infraction_type)
                # Append the infraction to infractions_dict with type as key
                infractions_dict[infraction_type].append(infraction)

            line = '```yaml\n'
            for infraction_type in sorted(infraction_types):
                # Get total infraction amount
                infractions_amt = len(infractions_dict[infraction_type])
                line += f'{infraction_type}s: {infractions_amt}\n'
                # Print details about infractions with current type
                for infraction in infractions_dict[infraction_type]:
                    # Get actors name if possible
                    actor = guild.get_member(infraction.actor_id)
                    if not isinstance(actor, Member):
                        actor = infraction.actor_id
                    else:
                        actor = f'{actor.name}#{actor.discriminator}'

                    line += f'  - {(infraction.reason)}\n'
                    line += f'      ID: {infraction.id}\n'
                    line += f'      duration: {infraction.str_duration}\n'
                    line += f'      given: {infraction.time_since_start}\n'
                    line += f'      actor: {actor}\n'
            line = line[:-1]
            line += '```'

            return line

        active_infs = infractions.get_active_infractions(member)
        inactive_infs = infractions.get_inactive_infractions(member)
        guild = ctx.guild

        if not active_infs and not inactive_infs:
            infraction_output = ["**Infractions**"]
            infraction_output.append(
                "This user has never received an infraction.")
        else:
            infraction_output = ["**Active Infractions**"]
            if not active_infs:
                infraction_output.append(
                    "This user has no active infractions.")
            else:
                infraction_output.append(f'TOTAL: {len(active_infs)}')
                infraction_output.append(
                    get_infractions_by_type(guild, active_infs))
            infraction_output.append("**Inactive Infractions**")
            if not inactive_infs:
                infraction_output.append(
                    "This user has no inactive infractions.")
            else:
                infraction_output.append(f'TOTAL: {len(inactive_infs)}')
                infraction_output.append(
                    get_infractions_by_type(guild, inactive_infs))

        return '\n'.join(infraction_output)

    # endregion: Infractions sub-functions


def setup(bot: Bot) -> None:
    """Load the Information cog."""
    bot.add_cog(Information(bot))
