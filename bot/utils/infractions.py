import datetime
import logging
from discord import Member
from bot.database import SQLite
from bot.constants import Time
from bot.utils import time
from dateutil.relativedelta import relativedelta

log = logging.getLogger(__name__)


class Infraction:
    def __init__(self,
                 user_id: int,
                 inf_type: str,
                 reason: str,
                 actor_id: int,
                 start: datetime.datetime,
                 duration: int,
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
                start, Time.time_format)

        self.duration = duration
        self.stop = self.start + datetime.timedelta(0, self.duration)
        self.id = rowid
        if write_to_db:
            self.add_to_database()

    @property
    def active(self) -> bool:
        '''Determine if infraction is currently active'''
        if datetime.datetime.now() > self.stop:
            return False
        else:
            return True

    @property
    def str_start(self) -> str:
        return datetime.datetime.strftime(self.start, Time.time_format)

    @property
    def str_duration(self) -> str:
        duration = time.humanize_delta(relativedelta(seconds=self.duration))
        if duration == 'less than a second':
            duration = 'instant'
        return duration

    @property
    def time_since_start(self) -> str:
        return time.time_since(self.start, max_units=2)

    def add_to_database(self) -> None:
        '''Add infraction to the database'''
        log.debug(
            f'Adding infraction {self.type} to {self.user_id}, reason: {self.reason} ; {self.str_start} [{self.duration}]')

        sql_command = f'''INSERT INTO infractions VALUES(
                        {self.user_id}, "{self.type}",
                        "{self.reason}", "{self.actor_id}", "{self.str_start}", {self.duration}
                        );
                        '''
        db = SQLite()
        db.execute(sql_command)
        db.close()


def get_infractions(user: Member) -> list:
    log.debug(f'Getting infractions of {user}')

    # Get all infractions from database
    db = SQLite()
    db.execute(f'SELECT *, rowid FROM infractions WHERE UID={user.id}')
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    return [Infraction(*infraction) for infraction in infractions]


def get_active_infractions(user: Member) -> list:
    infractions = get_infractions(user)
    return [infraction for infraction in infractions if infraction.active]


def get_inactive_infractions(user: Member) -> list:
    infractions = get_infractions(user)
    return [infraction for infraction in infractions if not infraction.active]
