import logging

import discord

from bot import constants
from bot.bot import Bot

log = logging.getLogger('bot')

client = Bot(
    command_prefix=constants.Bot.prefix,
    activity=discord.Game(name='Use !help'),
    case_insensitivity=True
)


@client.event
async def on_ready():
    log.info('Bot is ready')


client.load_extension('bot.cogs.error_handler')
client.load_extension('bot.cogs.help')
client.load_extension('bot.cogs.moderation')
client.load_extension('bot.cogs.clean')

client.run(constants.Bot.token)
