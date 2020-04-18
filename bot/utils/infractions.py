import datetime
import logging
from discord import Guild
from bot.database import SQLite
from bot import constants
from bot.utils import time
from dateutil.relativedelta import relativedelta
from bot.utils.converters import FetchedMember
from bot.bot import Bot
from discord.errors import NotFound

log = logging.getLogger(__name__)


class Infraction:
    def __init__(self,
                 user_id: int,
                 inf_type: str,
                 reason: str,
                 actor_id: int,
                 start: datetime.datetime,
                 duration: int,
                 active: int = None,
                 rowid: int = None,
                 write_to_db: bool = False
                 ) -> None:

        self.user_id = user_id
        self.type = inf_type
        self.reason = reason
        self.actor_id = actor_id

        if type(start) == datetime.datetime:
            self.start = start
        # For easier convertion from database
        elif type(start) == str:
            self.start = datetime.datetime.strptime(
                start, constants.Time.time_format)

        self.duration = duration
        self.stop = self.start + datetime.timedelta(0, self.duration)
        if active is None:
            self.is_active = self.active
        else:
            self.is_active = bool(active)
        self.id = rowid
        if write_to_db:
            self.add_to_database()

    @property
    def active(self) -> bool:
        '''Determine if infraction is currently active'''
        if datetime.datetime.now() > self.stop and self.duration != 1_000_000_000:
            return False
        else:
            return True

    @property
    def str_start(self) -> str:
        return datetime.datetime.strftime(self.start, constants.Time.time_format)

    @property
    def str_duration(self) -> str:
        if self.duration == 1_000_000_000:
            return 'permanent'
        duration = time.humanize_delta(
            relativedelta(seconds=self.duration), max_units=2)
        if duration == 'less than a second':
            duration = 'instant'
        return duration

    @property
    def time_since_start(self) -> str:
        return time.time_since(self.start, max_units=2)

    def add_to_database(self) -> None:
        '''Add infraction to the database'''
        log.debug(
            f'Adding infraction {self.type} to {self.user_id} by {self.actor_id}, reason: {self.reason} ; {self.str_start} [{self.duration}]')

        sql_command = f'''INSERT INTO infractions VALUES(
                        {self.user_id}, "{self.type}", "{self.reason}", "{self.actor_id}",
                        "{self.str_start}", {self.duration}, {int(self.is_active)}
                        );
                        '''
        db = SQLite()
        db.execute(sql_command)
        db.close()

    def make_inactive(self) -> None:
        '''Set infraction Active state to 0 in database'''
        log.debug(
            f'Deactivating infraction #{self.id}: {self.type} to {self.user_id}, reason: {self.reason}; {self.str_start} [{self.duration}]')

        sql_command = f'''UPDATE infractions SET Active=0 WHERE rowid={self.id};'''

        db = SQLite()
        db.execute(sql_command)
        db.close()

    async def pardon(self, guild: Guild, bot: Bot, force: bool = False) -> None:
        # Ignore already pardoned infractions
        if not self.is_active:
            return

        user = await bot.fetch_user(self.user_id)

        if not force:
            if self.type == 'ban':
                try:
                    await guild.unban(user)
                    log.info(f'User {user} ({self.user_id}) has been unbanned')
                except NotFound:
                    log.info(
                        f"User {user} ({self.user_id}) isn't banned, but found an active ban infraction")

        self.make_inactive()


def get_infraction_by_row(row_id: int) -> Infraction:
    db = SQLite()
    db.execute(f'SELECT *, rowid FROM infractions WHERE rowid={row_id}')
    try:
        infraction = Infraction(*db.cur.fetchone())
        log.debug(f'Getting infraction #{row_id}')
    except TypeError:
        infraction = False
    db.close()

    return infraction


def get_all_active_infractions(inf_type: str = None) -> list:
    log.debug(f'Getting all active infractions')

    # Get all infractions from database
    db = SQLite()
    db.execute(f'SELECT *, rowid FROM infractions WHERE Active=1;')
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_infractions(user: FetchedMember, inf_type: str = None) -> list:
    log.debug(f'Getting infractions of {user}')

    # Get all infractions from database
    db = SQLite()
    db.execute(f'SELECT *, rowid FROM infractions WHERE UID={user.id}')
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_active_infractions(user: FetchedMember, inf_type: str = None) -> list:
    log.debug(f'Getting active infractions of {user}')

    # Get all infractions from database
    db = SQLite()
    db.execute(
        f'SELECT *, rowid FROM infractions WHERE UID={user.id} AND Active=1')
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_inactive_infractions(user: FetchedMember, inf_type: str = None) -> list:
    log.debug(f'Getting inactive infractions of {user}')

    # Get all infractions from database
    db = SQLite()
    db.execute(
        f'SELECT *, rowid FROM infractions WHERE UID={user.id} AND Active=0')
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


async def pardon_last_infraction(guild: Guild, user: FetchedMember, inf_type: str = None, force: bool = False) -> None:
    # Get all active infractions of given user
    infractions = get_active_infractions(user, inf_type)
    # Pardon last infraction
    await infractions[-1].pardon(guild, force=force)


async def check_infractions_expiry(bot: Bot, inf_type: str = None) -> None:
    guild = bot.get_guild(constants.Guild.id)
    active_infractions = get_all_active_infractions(inf_type=inf_type)

    for infraction in active_infractions:
        # Check if infraction is no longer active by duration
        if not infraction.active:
            # Infraction expired, de-activate it
            await infraction.pardon(guild, bot)


async def remove_infraction(guild: Guild, bot: Bot, row_id: int) -> Infraction:
    db = SQLite()
    db.execute(f'SELECT *, rowid FROM infractions WHERE rowid={row_id}')
    try:
        infraction = Infraction(*db.cur.fetchone())
        await infraction.pardon(guild, bot)
        db.execute(f'DELETE FROM infractions WHERE rowid={row_id}')
        log.info(f'Removed infraction #{row_id}')
    except TypeError:
        infraction = False
    db.close()

    return infraction
