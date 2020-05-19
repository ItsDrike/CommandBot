import textwrap
from collections import defaultdict

from discord import Colour, Embed, TextChannel
from discord.ext.commands import Cog, Context, command, group

from bot import constants
from bot.bot import Bot
from bot.cogs.moderation.modlog import ModLog
from bot.decorators import with_role

prefix = constants.Bot.prefix


class Embeds(Cog):
    """
    A cog which allows user to send messages using the bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.embed_mode = defaultdict(bool)
        self.embed = {}

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

    # region: embed mode

    @command(alias=["embed", "embedcreate"])
    async def embedbuild(self, ctx: Context) -> None:
        """Enter embed creation mode"""
        if not self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are now in embed creation mode, use `{prefix}help Embed` for more info")
            self.embed_mode[ctx.author] = True
            self.embed[ctx.author] = Embed()
        else:
            await ctx.send(f":x: {ctx.author.mention} You are already in embed creation mode, use `{prefix}help Embed` for more info")

    @command()
    async def embedquit(self, ctx: Context) -> None:
        """Leave embed creation mode"""
        if self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are no longer in embed creation mode, your embed was cleared")
            self.embed_mode[ctx.author] = False
            del self.embed[ctx.author]
        else:
            await ctx.send(f":x: {ctx.author.mention} You aren't in embed mode")

    @command()
    async def embedshow(self, ctx: Context) -> None:
        """Take a look at the embed"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        await ctx.send(embed=embed)

    @command()
    async def embedsend(self, ctx: Context, channel: TextChannel) -> None:
        """Send the Embed to specified channel"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        channel_perms = channel.permissions_for(ctx.author)
        if channel_perms.send_messages:
            embed_msg = await channel.send(embed=embed)

            await self.mod_log.send_log_message(
                icon_url=constants.Icons.message_edit,
                colour=Colour.blurple(),
                title="Embed message sent",
                thumbnail=ctx.author.avatar_url_as(static_format="png"),
                text=textwrap.dedent(f"""
                    Actor: {ctx.author.mention} (`{ctx.author.id}`)
                    Channel: {channel.mention}
                    Message jump link: {embed_msg.jump_url}
                """),
            )
            await ctx.send(":white_check_mark: Embed sent")

    # endregion
    # region: embed build
    @group(invoke_without_command=True, name='embed', aliases=["embedset"])
    @with_role(*constants.MODERATION_ROLES)
    async def embed_group(self, ctx: Context) -> None:
        '''Commands for configuring the Embed message'''
        await ctx.invoke(self.bot.get_command('help'), 'embed')

    @embed_group.command(name="title")
    @with_role(*constants.MODERATION_ROLES)
    async def embed_title(self, ctx: Context, *, title: str) -> None:
        """Set embeds title"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.title = title
        self.embed[ctx.author] = embed
        await ctx.send("Embeds title updated")

    @embed_group.command(name="footer")
    @with_role(*constants.MODERATION_ROLES)
    async def embed_footer(self, ctx: Context, *, footer: str) -> None:
        """Set embeds footer"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_footer(text=footer)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds footer updated")

    @embed_group.command(name="image", aliases=["img"])
    @with_role(*constants.MODERATION_ROLES)
    async def embed_image(self, ctx: Context, *, url: str) -> None:
        """Set embeds image (not passing URL will remove the image)"""
        embed = await self.get_embed(ctx)

        if embed is False:
            return

        embed.set_image(url=url)
        self.embed[ctx.author] = embed
        await ctx.send("Embeds Image URL updated")

    # endregion

    async def get_embed(self, ctx):
        try:
            embed = self.embed[ctx.author]
        except KeyError:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{prefix}help Embeds`)")
            return False
        return embed


def setup(bot: Bot) -> None:
    '''Load the Embeds cog.'''
    bot.add_cog(Embeds(bot))
