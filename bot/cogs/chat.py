from bot.bot import Bot
from discord import Embed, TextChannel
from discord.ext.commands import Cog, Context, command
from collections import defaultdict
from bot import constants


prefix = constants.Bot.prefix


class Chat(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.embed_mode = defaultdict(bool)
        self.embed = {}

    @command(alias=["embedbuild "])
    async def embed(self, ctx: Context) -> None:
        """Enter embed creation mode"""
        if not self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are now in embed creation mode, use `{prefix}embedhelp` for more info")
            self.embed_mode[ctx.author] = True
            self.embed[ctx.author] = Embed()
        else:
            await ctx.send(f":x: {ctx.author.mention} You are already in embed creation mode, use `{prefix}embedhelp` for more info")

    @command(hidden=True)
    async def embedquit(self, ctx: Context) -> None:
        if self.embed_mode[ctx.author]:
            await ctx.send(f"{ctx.author.mention} You are no longer in embed creation mode, any unsent embeds were cleared")
            self.embed_mode[ctx.author] = False
            del self.embed[ctx.author]
        else:
            await ctx.send(f":x: {ctx.author.mention} You aren't in embed mode")

    @command(hidden=True)
    async def embedshow(self, ctx: Context) -> None:
        try:
            await ctx.send(embed=self.embed[ctx.author])
        except KeyError:
            await ctx.send(f":x: {ctx.author.mention} No active embed found, are you in embed building mode? (`{prefix}embedhelp`)")

    @command(hidden=True)
    async def embedsend(self, ctx: Context, channel: TextChannel) -> None:
        """Send the Embed"""
        pass

    @command(hidden=True)
    async def embedhelp(self, ctx: Context) -> None:
        """Show help page for embed creation"""
        pass


def setup(bot: Bot) -> None:
    '''Load the Chat cog.'''
    bot.add_cog(Chat(bot))
