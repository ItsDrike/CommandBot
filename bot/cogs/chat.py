from collections import defaultdict

from discord import Embed, TextChannel
from discord.ext.commands import Cog, Context, command

from bot import constants
from bot.bot import Bot

prefix = constants.Bot.prefix


class Chat(Cog):
    """
    A cog which allows user to send messages using the bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.embed_mode = defaultdict(bool)
        self.embed = {}

    # region: embed mode

    @command(alias=["embed", "embedcreate"])
    async def embedbuild(self, ctx: Context) -> None:
        """Enter embed creation mode"""
        if not self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are now in embed creation mode, use `{prefix}embedhelp` for more info")
            self.embed_mode[ctx.author] = True
            self.embed[ctx.author] = Embed()
        else:
            await ctx.send(f":x: {ctx.author.mention} You are already in embed creation mode, use `{prefix}embedhelp` for more info")

    @command()
    async def embedquit(self, ctx: Context) -> None:
        """Leave embed creation mode"""
        if self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are no longer in embed creation mode, any unsent embeds were cleared")
            self.embed_mode[ctx.author] = False
            del self.embed[ctx.author]
        else:
            await ctx.send(f":x: {ctx.author.mention} You aren't in embed mode")

    @command()
    async def embedshow(self, ctx: Context) -> None:
        """Take a look at the embed"""
        try:
            await ctx.send(embed=self.embed[ctx.author])
        except KeyError:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{prefix}embedhelp`)")

    @command()
    async def embedsend(self, ctx: Context, channel: TextChannel) -> None:
        """Send the Embed to specified channel"""
        try:
            channel_perms = channel.permissions_for(ctx.author)
            if channel_perms.send_messages:
                await channel.send(embed=self.embed[ctx.author])
                await ctx.send(":white_check_mark: Embed sent")
            else:
                await ctx.send(f":x: Sorry, {ctx.author.mention} you don't have permission to send messages to this channel")
        except KeyError:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{prefix}embedhelp`)")

    # endregion
    # region: embed build
    # endregion


def setup(bot: Bot) -> None:
    '''Load the Chat cog.'''
    bot.add_cog(Chat(bot))
