import logging

import discord
from discord.ext import commands

from bot import constants

log = logging.getLogger('bot')

client = commands.Bot(
    command_prefix=constants.Bot.prefix,
    activity=discord.Game(name='Use !help'),
    case_insensitivity=True
)


@client.event
async def on_ready():
    log.info('Bot is ready.')


client.run(constants.Bot.token)
