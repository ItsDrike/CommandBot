from .infractions import Infractions
from .modlog import ModLog


def setup(bot) -> None:
    '''Load the moderation cogs.'''
    bot.add_cog(ModLog(bot))
    bot.add_cog(Infractions(bot))
