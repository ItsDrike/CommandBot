import logging
import textwrap
from collections import defaultdict

from discord import Colour, Embed, TextChannel
from discord.ext.commands import Cog, ColourConverter, Context, command, group

from bot.bot import Bot
from bot.cogs.moderation.modlog import ModLog
from bot.constants import MODERATION_ROLES
from bot.constants import Bot as BotConstant
from bot.constants import Icons
from bot.decorators import with_role

prefix = BotConstant.prefix

log = logging.getLogger(__name__)


class Embeds(Cog):
    """
    A cog which allows user to send messages using the bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.embed_mode = defaultdict(bool)
        self.embed = {}
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
        if not self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are now in embed creation mode, use `{prefix}help Embed` for more info")
            self.embed_mode[ctx.author] = True
            self.embed[ctx.author] = Embed()
        else:
            await ctx.send(f":x: {ctx.author.mention} You are already in embed creation mode, use `{prefix}help Embed` for more info")

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedquit(self, ctx: Context) -> None:
        """Leave embed creation mode"""
        if self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are no longer in embed creation mode, your embed was cleared")
            self.embed_mode[ctx.author] = False
            del self.embed[ctx.author]
        else:
            await ctx.send(f":x: {ctx.author.mention} You aren't in embed mode")

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedshow(self, ctx: Context) -> None:
        """Take a look at the embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        await ctx.send(embed=embed)

    @command()
    @with_role(*MODERATION_ROLES)
    async def embedsend(self, ctx: Context, channel: TextChannel) -> None:
        """Send the Embed to specified channel"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        channel_perms = channel.permissions_for(ctx.author)
        if channel_perms.send_messages:
            embed_msg = await channel.send(embed=embed)

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
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.title = title
        self.embed[ctx.author] = embed
        await ctx.send("Embeds title updated")

    @embed_group.command(name="description")
    @with_role(*MODERATION_ROLES)
    async def embed_description(self, ctx: Context, *, description: str) -> None:
        """Set embeds title"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.description = description
        self.embed[ctx.author] = embed
        await ctx.send("Embeds description updated")

    @embed_group.command(name="footer")
    @with_role(*MODERATION_ROLES)
    async def embed_footer(self, ctx: Context, *, footer: str) -> None:
        """Set embeds footer"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_footer(text=footer)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds footer updated")

    @embed_group.command(name="image", aliases=["img"])
    @with_role(*MODERATION_ROLES)
    async def embed_image(self, ctx: Context, *, url: str) -> None:
        """Set embeds image"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_image(url=url)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds Image URL updated")

    @embed_group.command(name="color", aliases=["colour"])
    @with_role(*MODERATION_ROLES)
    async def embed_color(self, ctx: Context, *, color: ColourConverter) -> None:
        """Set embeds title, `color` can be HEX color or some of standard colors (red, blue, ...)"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.colour = color
        self.embed[ctx.author] = embed
        await ctx.send("Embeds color updated")

    # region: author
    @embed_group.command(name="author", aliases=["setauthor", "authorname"])
    @with_role(*MODERATION_ROLES)
    async def embed_author_name(self, ctx: Context, *, author_name: str) -> None:
        """Set authors name in embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_author(name=author_name, url=embed.author.url,
                         icon_url=embed.author.icon_url)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds author updated")

    @embed_group.command(name="authorurl", aliases=["setauthorurl"])
    @with_role(*MODERATION_ROLES)
    async def embed_author_url(self, ctx: Context, *, author_url: str) -> None:
        """Set authors URL in embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_author(name=embed.author.name, url=author_url,
                         icon_url=embed.author.icon_url)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds author URL updated")

    @embed_group.command(name="authoricon", aliases=[
        "setauthoricon", "authoriconurl", "setauthoriconurl"
    ])
    @with_role(*MODERATION_ROLES)
    async def embed_author_icon(self, ctx: Context, *, icon_url: str) -> None:
        """Set authors image in embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_author(name=embed.author.name, url=embed.author.url,
                         icon_url=icon_url)
        self.embed[ctx.author] = embed
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
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.add_field(name=title, value="None")

        self.embed_field_id[ctx.author] += 1
        self.embed[ctx.author] = embed
        await ctx.send(f"Embed field with ID **{self.embed_field_id[ctx.author]}** created")

    @embed_group.command(name="fielddescription", aliases=["fieldvalue"])
    @with_role(*MODERATION_ROLES)
    async def embed_field_description(self, ctx: Context, ID: int, *, description: str) -> None:
        """Set description of embeds field"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed.set_field_at(
            ID, name=embed.fields[ID].name, value=description)

        self.embed[ctx.author] = embed
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="fieldtitle", aliases=["fieldname"])
    @with_role(*MODERATION_ROLES)
    async def embed_field_title(self, ctx: Context, ID: int, *, title: str) -> None:
        """Set title of embeds field"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed.set_field_at(
            ID, name=title, value=embed.fields[ID].value)

        self.embed[ctx.author] = embed
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="fieldinline")
    @with_role(*MODERATION_ROLES)
    async def embed_field_inline(self, ctx: Context, ID: int, inline: bool) -> None:
        """Choose if embed should be inline or not"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed.set_field_at(
            ID, name=embed.fields[ID].name, value=embed.fields[ID].value, inline=inline)

        self.embed[ctx.author] = embed
        await ctx.send(f"Embed field with ID: **{ID}** updated")

    @embed_group.command(name="removefield", aliases=[
        "deletefield", "fieldremove", "fieldrem",
        "fielddel", "delfield", "remfield"
    ])
    @with_role(*MODERATION_ROLES)
    async def embed_field_remove(self, ctx: Context, ID: int) -> None:
        """Remove field in embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        if self.embed_field_id[ctx.author] < ID or ID < 0:
            await ctx.send(f":x: {ctx.author.mention} Sorry, but there is no such field ID")
            return

        embed.remove_field(ID)

        self.embed[ctx.author] = embed
        self.embed_field_id[ctx.author] -= 1
        await ctx.send(f"Embed field with ID: **{ID}** removed (all other IDs were renumbered accordingly)")
    # endregion
    # endregion

    async def get_embed(self, ctx: Context) -> Embed:
        """Return the authors embed or send error message and return `False`"""
        try:
            embed = self.embed[ctx.author]
        except KeyError:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{prefix}help Embeds`)")
            return False
        return embed


def setup(bot: Bot) -> None:
    '''Load the Embeds cog.'''
    bot.add_cog(Embeds(bot))
