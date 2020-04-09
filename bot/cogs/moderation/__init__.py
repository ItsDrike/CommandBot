from .modlog import ModLog


def setup(bot) -> None:
    '''Load the moderation cogs.'''
    bot.add_cog(ModLog(bot))
