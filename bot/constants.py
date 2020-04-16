import logging
import os
from typing import Dict, List
from enum import Enum

import yaml

# Paths
BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.yaml')

log = logging.getLogger(__name__)


def _env_var_constructor(loader, node):
    '''
    Implements a custom YAML tag for loading optional environment
    variables. If the environment variable is set, returns the
    value of it. Otherwise, returns `None`.

    Example usage in the YAML configuration:

        # Optional app configuration. Set `MY_APP_KEY` in the environment to use it.
        application:
            key: !ENV 'MY_APP_KEY'
    '''

    default = None

    # Check if the node is a plain string value
    if node.id == 'scalar':
        value = loader.construct_scalar(node)
        key = str(value)
    else:
        # The node value is a list
        value = loader.construct_sequence(node)

        if len(value) >= 2:
            # If we have at least two values, then we have both a key and a default value
            default = value[1]
            key = value[0]
        else:
            # Otherwise, we just have a key
            key = value[0]

    return os.getenv(key, default)


yaml.SafeLoader.add_constructor('!ENV', _env_var_constructor)

with open(CONFIG_FILE, encoding='UTF-8') as f:
    _CONFIG_YAML = yaml.safe_load(f)


class YAMLGetter(type):
    '''
    Implements a custom metaclass used for accessing
    configuration data by simply accessing class attributes.
    Supports getting configuration from up to two levels
    of nested configuration through `section` and `subsection`.

    `section` specifies the YAML configuration section (or 'key')
    in which the configuration lives, and must be set.

    `subsection` is an optional attribute specifying the section
    within the section from which configuration should be loaded.

    Example Usage:

        # config.yml
        bot:
            prefixes:
                direct_message: ''
                guild: '!'

        # config.py
        class Prefixes(metaclass=YAMLGetter):
            section = 'bot'
            subsection = 'prefixes'

        # Usage in Python code
        from config import Prefixes
        def get_prefix(bot, message):
            if isinstance(message.channel, PrivateChannel):
                return Prefixes.direct_message
            return Prefixes.guild
    '''

    subsection = None

    def __getattr__(cls, name):
        name = name.lower()

        try:
            if cls.subsection is not None:
                return _CONFIG_YAML[cls.section][cls.subsection][name]
            return _CONFIG_YAML[cls.section][name]
        except KeyError:
            dotted_path = '.'.join(
                (cls.section, cls.subsection, name)
                if cls.subsection is not None else (cls.section, name)
            )
            log.critical(
                f'Tried accessing configuration variable at `{dotted_path}`, but it could not be found.')
            raise

    def __getitem__(cls, name):
        return cls.__getattr__(name)

    def __iter__(cls):
        '''Return generator of key: value pairs of current constants class' config values.'''
        for name in cls.__annotations__:
            yield name, getattr(cls, name)


class Bot(metaclass=YAMLGetter):
    section = 'bot'

    prefix: str
    token: str


class Guild(metaclass=YAMLGetter):
    section = 'guild'

    id: int
    moderation_channels: List[int]
    staff_channels: List[int]

    moderation_roles: List[int]
    staff_roles: List[int]

    modlog_blacklist: List[int]


class Roles(metaclass=YAMLGetter):
    section = 'guild'
    subsection = 'roles'

    guests: int
    members: int
    owners: int
    admins: int
    mods: int
    trial_mods: int
    muted: int
    announcements: int


class Channels(metaclass=YAMLGetter):
    section = 'guild'
    subsection = 'channels'

    announcements: int

    off_topic: int
    ask_for_help: int
    commands: int

    admins: int
    mods: int

    support: int
    suggestions: int
    report: int

    attachment_log: int
    message_log: int
    voice_log: int
    user_log: int
    mod_log: int


class Database(metaclass=YAMLGetter):
    section = 'database'

    db_name: str


class AntiSpam(metaclass=YAMLGetter):
    section = 'anti_spam'

    punishment: Dict[str, Dict[str, int]]
    rules: Dict[str, Dict[str, int]]
    role_whitelist: List[int]


class Filter(metaclass=YAMLGetter):
    section = 'filter'

    domain_blacklist: List[int]
    word_watchlist: List[int]

    channel_whitelist: List[int]
    role_whitelist: List[int]


class AntiMalware(metaclass=YAMLGetter):
    section = 'anti_malware'

    whitelist: list


class CleanMessages(metaclass=YAMLGetter):
    section = 'clean_messages'

    message_limit: int


class RedirectOutput(metaclass=YAMLGetter):
    section = 'redirect_output'

    delete_invocation: bool
    delete_delay: int


class Time(metaclass=YAMLGetter):
    section = 'style'

    time_format: str


class Colours(metaclass=YAMLGetter):
    section = 'style'
    subsection = 'colours'

    soft_red: int
    soft_green: int
    soft_orange: int


class Emojis(metaclass=YAMLGetter):
    section = 'style'
    subsection = 'emojis'

    defcon_disabled: str
    defcon_enabled: str
    defcon_updated: str

    status_online: str
    status_idle: str
    status_dnd: str
    status_offline: str

    delete: str
    bullet: str
    pencil: str
    new: str
    cross_mark: str
    check_mark: str

    upvotes: str
    comments: str
    user: str


class Icons(metaclass=YAMLGetter):
    section = 'style'
    subsection = 'icons'

    crown_blurple: str
    crown_green: str
    crown_red: str

    message_bulk_delete: str
    message_delete: str
    message_edit: str

    sign_in: str
    sign_out: str

    filtering: str

    user_ban: str
    user_unban: str
    user_update: str
    user_mute: str
    user_unmute: str
    user_warn: str

    hash_blupre: str
    hash_green: str
    hash_red: str

    defcon_denied: str
    defcon_disabled: str
    defcon_enables: str
    defcon_updated: str

    voice_state_blue: str
    voice_state_green: str
    voice_state_red: str


class Event(Enum):
    """
    Event names. This does not include every event (for example, raw
    events aren't here), but only events used in ModLog for now.
    """

    guild_channel_create = "guild_channel_create"
    guild_channel_delete = "guild_channel_delete"
    guild_channel_update = "guild_channel_update"
    guild_role_create = "guild_role_create"
    guild_role_delete = "guild_role_delete"
    guild_role_update = "guild_role_update"
    guild_update = "guild_update"

    member_join = "member_join"
    member_remove = "member_remove"
    member_ban = "member_ban"
    member_unban = "member_unban"
    member_kick = "member_kick"
    member_update = "member_update"

    message_delete = "message_delete"
    message_edit = "message_edit"

    voice_state_update = "voice_state_update"


# Some vars
MODERATION_ROLES = Guild.moderation_roles
STAFF_ROLES = Guild.staff_roles

MODERATION_CHANNELS = Guild.moderation_channels
STAFF_CHANNELS = Guild.staff_channels


# Bot replies
NEGATIVE_REPLIES = [
    "Noooooo!!",
    "Nope.",
    "I don't think so.",
    "Not gonna happen.",
    "Huh? No.",
    "Nah.",
    "NEGATORY.",
    "Not in my house!",
    "Nuh-uh",
    "Not in a million years.",
    "Not likely."
]

POSITIVE_REPLIES = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Sure.",
    "Sure thing!",
    "Okay.",
    "Alright.",
    "You got it!",
    "ROGER THAT",
    "No problem.",
    "Of course!",
    "I got you.",
    "Yeah okay.",
]

ERROR_REPLIES = [
    "Please don't do that.",
    "You have to stop.",
    "That was a mistake.",
    "You blew it.",
    "You're bad at computers.",
    "Are you trying to kill me?",
    "Noooooo!!",
    "I can't believe you've done this",
]
