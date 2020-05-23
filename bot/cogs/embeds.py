import logging
import textwrap
import typing as t
from collections import defaultdict

from discord import Colour, Embed, TextChannel
from discord.ext.commands import Cog, ColourConverter, Context, command, group

from bot.bot import Bot
from bot.cogs.moderation.modlog import ModLog
from bot.constants import MODERATION_ROLES
from bot.constants import Bot as BotConstant
from bot.constants import Icons
from bot.decorators import with_role
from bot.utils.converters import FetchedMember

prefix = BotConstant.prefix

log = logging.getLogger(__name__)


# Global variable needed for the `has_active_embed` decorator to work
embeds = {}


class Embeds(Cog):
    """
    A cog which allows user to send messages using the bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.embed_field_id = defaultdict(lambda: -1)

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

    # region: embed mode

    @command(aliases=["embedcreate"])
    @with_role(*MODERATION_ROLES)
    async def embedbuild(self, ctx: Context) -> None:
        """Enter embed creation mode"""
        if ctx.author not in embeds:
            await ctx.send(f"{ctx.author.mention} You are now in embed creation mode, use `{prefix}help Embed` for more info")
            embeds[ctx.author] = Embed()
        else:
            await ctx.send(f":x: {ctx.author.mention} You are already in embed creation mode, use `{prefix}help Embed` for more info")

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedquit(self, ctx: Context) -> None:
        """Leave embed creation mode"""
        if ctx.author in embeds:
            await ctx.send(f"{ctx.author.mention} You are no longer in embed creation mode, your embed was cleared")
            del embeds[ctx.author]
        else:
            await ctx.send(f":x: {ctx.author.mention} You aren't in embed mode")

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedshow(self, ctx: Context) -> None:
        """Take a look at the embed"""
        if not await Embeds.has_active_embed(ctx):
            return

        await ctx.send(embed=embeds[ctx.author])

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedsend(self, ctx: Context, channel: TextChannel) -> None:
        """Send the Embed to specified channel"""
        if not await Embeds.has_active_embed(ctx):
            return

        channel_perms = channel.permissions_for(ctx.author)
        if channel_perms.send_messages:
            embed_msg = await channel.send(embed=embeds[ctx.author])

            await self.mod_log.send_log_message(
                icon_url=Icons.message_edit,
                colour=Colour.blurple(),
                title="Embed message sent",
                thumbnail=ctx.author.avatar_url_as(static_format="png"),
                text=textwrap.dedent(f"""
                    Actor: {ctx.author.mention} (`{ctx.author.id}`)
                    Channel: {channel.mention}
                    Message jump link: {embed_msg.jump_url}
                """),
            )
            log.info(f"User {ctx.author} sent embed message to #{channel}")
            await ctx.send(":white_check_mark: Embed sent")
        else:
            await ctx.send(f":x: {ctx.author.mention} Sorry but you don't have permission to send messages to this channel")

    # endregion
    # region: embed build
    @group(invoke_without_command=True, name='embed', aliases=["embedset"])
    @with_role(*MODERATION_ROLES)
    async def embed_group(self, ctx: Context) -> None:
        """Commands for configuring the Embed message"""
        await ctx.invoke(self.bot.get_command('help'), 'embed')

    @embed_group.command(name="title")
    @with_role(*MODERATION_ROLES)
    async def embed_title(self, ctx: Context, *, title: str) -> None:
        """Set embeds title"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].title = title
        await ctx.send("Embeds title updated")

    @embed_group.command(name="description")
    @with_role(*MODERATION_ROLES)
    async def embed_description(self, ctx: Context, *, description: str) -> None:
        """Set embeds title"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].description = description
        await ctx.send("Embeds description updated")

    @embed_group.command(name="footer")
    @with_role(*MODERATION_ROLES)
    async def embed_footer(self, ctx: Context, *, footer: str) -> None:
        """Set embeds footer"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].set_footer(text=footer)
        await ctx.send("Embeds footer updated")

    @embed_group.command(name="image", aliases=["img"])
    @with_role(*MODERATION_ROLES)
    async def embed_image(self, ctx: Context, *, url: str) -> None:
        """Set embeds image"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].set_image(url=url)
        await ctx.send("Embeds Image URL updated")

    @embed_group.command(name="color", aliases=["colour"])
    @with_role(*MODERATION_ROLES)
    async def embed_color(self, ctx: Context, *, color: ColourConverter) -> None:
        """Set embeds title, `color` can be HEX color or some of standard colors (red, blue, ...)"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].colour = color
        await ctx.send("Embeds color updated")

    # region: author
    @embed_group.command(name="author", aliases=["setauthor", "authorname"])
    @with_role(*MODERATION_ROLES)
    async def embed_author_name(self, ctx: Context, *, author_name: str) -> None:
        """Set authors name in embed"""
        if not await Embeds.has_active_embed(ctx):
            return

        embed = embeds[ctx.author]
        embed.set_author(
            name=author_name,
            url=embed.author.url,
            icon_url=embed.author.icon_url
        )
        await ctx.send("Embeds author updated")

    @embed_group.command(name="authorurl", aliases=["setauthorurl"])
    @with_role(*MODERATION_ROLES)
    async def embed_author_url(self, ctx: Context, *, author_url: str) -> None:
        """Set authors URL in embed"""
        if not await Embeds.has_active_embed(ctx):
            return

        embed = embeds[ctx.author]
        embed.set_author(
            name=embed.author.name,
            url=author_url,
            icon_url=embed.author.icon_url
        )
        await ctx.send("Embeds author URL updated")

    @embed_group.command(name="authoricon", aliases=[
        "setauthoricon", "authoriconurl", "setauthoriconurl"
    ])
    @with_role(*MODERATION_ROLES)
    async def embed_author_icon(self, ctx: Context, *, icon_url: t.Union[FetchedMember, str]) -> None:
        """Set authors icon in embed (You can also mention user to get his avatar)"""
        if not await Embeds.has_active_embed(ctx):
            return

        embed = embeds[ctx.author]
        if type(icon_url) != str:
            icon_url = icon_url.avatar_url_as(format="png")
        embed.set_author(
            name=embed.author.name,
            url=embed.author.url,
            icon_url=icon_url
        )
        await ctx.send("Embeds authors image updated")

    # endregion

    # region: fields
    @embed_group.command(name="createfield", aliases=[
        "newfield", "makefield", "addfield",
        "fieldadd", "fieldcreate", "fieldmake", "field"
    ])
    @with_role(*MODERATION_ROLES)
    async def embed_field_create(self, ctx: Context, *, title: str = "None") -> None:
        """Create new field in embed"""
        if not await Embeds.has_active_embed(ctx):
            return

        embeds[ctx.author].add_field(name=title, value="None")
        self.embed_field_id[ctx.author] += 1
        await ctx.send(f"Embed field with ID **{self.embed_field_id[ctx.author]}** created")

    @embed_group.command(name="fielddescription", aliases=["fieldvalue"])
    @with_role(*MODERATION_ROLES)
    async def embed_field_description(self, ctx: Context, ID: int, *, description: str) -> None:
        """Set description of embeds field"""
        if not await Embeds.has_active_embed(ctx):
            return
        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed = embeds[ctx.author]
        embed.set_field_at(
            ID,
            name=embed.fields[ID].name,
            value=description
        )
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="fieldtitle", aliases=["fieldname"])
    @with_role(*MODERATION_ROLES)
    async def embed_field_title(self, ctx: Context, ID: int, *, title: str) -> None:
        """Set title of embeds field"""
        if not await Embeds.has_active_embed(ctx):
            return
        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed = embeds[ctx.author]
        embed.set_field_at(
            ID,
            name=title,
            value=embed.fields[ID].value
        )
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="fieldinline")
    @with_role(*MODERATION_ROLES)
    async def embed_field_inline(self, ctx: Context, ID: int, inline: bool) -> None:
        """Choose if embed should be inline or not"""
        if not await Embeds.has_active_embed(ctx):
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed = embeds[ctx.author]
        embed.set_field_at(
            ID,
            name=embed.fields[ID].name,
            value=embed.fields[ID].value,
            inline=inline
        )
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="removefield", aliases=[
        "deletefield", "fieldremove", "fieldrem",
        "fielddel", "delfield", "remfield"
    ])
    @with_role(*MODERATION_ROLES)
    async def embed_field_remove(self, ctx: Context, ID: int) -> None:
        """Remove field in embed"""
        if not await Embeds.has_active_embed(ctx):
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embeds[ctx.author].remove_field(ID)
        self.embed_field_id[ctx.author] -= 1
        await ctx.send(f"Embed field with ID: **{ID}** removed (all other IDs were renumbered accordingly)")
    # endregion
    # endregion

    @staticmethod
    async def has_active_embed(ctx):
        if ctx.author in embeds:
            return True
        else:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{Bot.prefix}help Embeds`)")
            return False


def setup(bot: Bot) -> None:
    '''Load the Embeds cog.'''
    bot.add_cog(Embeds(bot))
