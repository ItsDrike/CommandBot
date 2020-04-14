from .modlog import ModLog
from .infractions import Infractions


def setup(bot) -> None:
    '''Load the moderation cogs.'''
    bot.add_cog(ModLog(bot))
    bot.add_cog(Infractions(bot))
