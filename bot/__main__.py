import logging

import discord

from bot import constants
from bot.bot import Bot
from bot.database import SQLite

log = logging.getLogger('bot')

client = Bot(
    command_prefix=constants.Bot.prefix,
    activity=discord.Game(name='Use !help'),
    case_insensitivity=True
)

db = SQLite()
db.create_init_tables()
db.close()


@client.event
async def on_ready():
    log.info('Bot is ready')


client.load_extension('bot.cogs.error_handler')
client.load_extension('bot.cogs.security')
client.load_extension('bot.cogs.help')
client.load_extension('bot.cogs.moderation')

client.load_extension('bot.cogs.information')
client.load_extension('bot.cogs.clean')
client.load_extension('bot.cogs.announcements')
client.load_extension('bot.cogs.fun')

if constants.Bot.token:
    client.run(constants.Bot.token)
else:
    log.error('Bot token not found')
