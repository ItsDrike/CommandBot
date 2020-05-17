from bot.bot import Bot
from discord.ext.commands import Cog


class Chat(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


def setup(bot: Bot) -> None:
    '''Load the Chat cog.'''
    bot.add_cog(Chat(bot))
