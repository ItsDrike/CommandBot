import datetime
import logging
from discord import Member
from bot.database import SQLite
from bot.constants import Time

log = logging.getLogger(__name__)


str(datetime.datetime)


class Infraction:
    def __init__(self,
                 user_id: int,
                 inf_type: str,
                 reason: str,
                 start: datetime.datetime,
                 duration: int,
                 rowid: int = None,
                 write_to_db: bool = False
                 ) -> None:

        self.user_id = user_id
        self.type = inf_type
        self.reason = reason

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

    def get_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'type': self.type,
            'reason': self.reason,
            'start': str(self.start),
            'duration': self.duration
        }

    def __iter__(self):
        for key, value in self.get_dict().items():
            yield key, value

    def add_to_database(self) -> None:
        '''Add infraction to the database'''
        log.debug(
            f'Adding infraction {self.type} to {self.user_id}, reason: {self.reason} ; {self.str_start} [{self.duration}]')

        sql_command = f'''INSERT INTO infractions VALUES(
                        {self.user_id}, "{self.type}",
                        "{self.reason}", "{self.str_start}", {self.duration}
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
