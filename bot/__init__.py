import asyncio
import logging
import os
import sys
from logging import handlers
from pathlib import Path

import coloredlogs

# Setup some parameters for logging
format_string = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
log_level = logging.DEBUG
log_format = logging.Formatter(format_string)

# Setup logging file
log_file = Path('logs', 'bot.log')
log_file.parent.mkdir(exist_ok=True)
file_handler = handlers.RotatingFileHandler(
    log_file, maxBytes=5242880, backupCount=7)
file_handler.setFormatter(log_format)

# Setup root_logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(file_handler)

# Some formatting for coloredlogs
coloredlogs.DEFAULT_LEVEL_STYLES = {
    **coloredlogs.DEFAULT_LEVEL_STYLES,
    "critical": {"background": "red"},
    "debug": coloredlogs.DEFAULT_LEVEL_STYLES["info"]
}

coloredlogs.DEFAULT_LOG_FORMAT = format_string
coloredlogs.DEFAULT_LOG_LEVEL = log_level

coloredlogs.install(logger=root_logger, stream=sys.stdout)

# Set other logging levels on imported modules
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('deepdiff').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.INFO)
logging.getLogger('bot.utils.checks').setLevel(logging.INFO)
logging.getLogger('bot.pagination').setLevel(logging.INFO)
logging.getLogger('bot.utils.infractions').setLevel(logging.INFO)
logging.getLogger('bot.utils.scheduling').setLevel(logging.INFO)
logging.getLogger('bot.decorators').setLevel(logging.INFO)

logging.getLogger(__name__)

# On Windows, the selector event loop is required for aiodns.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
