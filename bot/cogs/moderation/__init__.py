from .infractions import Infractions
from .modlog import ModLog
from .silence import Silence


def setup(bot) -> None:
    """Load the moderation cogs."""
    bot.add_cog(ModLog(bot))
    bot.add_cog(Infractions(bot))
    bot.add_cog(Silence(bot))
