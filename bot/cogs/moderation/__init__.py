from .modlog import ModLog
from .infractions import Infractions
from bot.utils import infractions
from discord.ext.tasks import loop


def setup(bot) -> None:
    '''Load the moderation cogs.'''
    bot.add_cog(ModLog(bot))
    bot.add_cog(Infractions(bot))
    infraction_check.start(bot)


@loop(seconds=20)
async def infraction_check(bot):
    if bot.is_ready():
        await infractions.check_infractions_expiry(bot)
