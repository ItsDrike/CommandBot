import datetime
import logging

from dateutil.relativedelta import relativedelta

from bot import constants
from bot.cogs.moderation.utils import UserSnowflake
from bot.database import SQLite
from bot.utils import time

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
        """Determine if infraction is currently active"""
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
            return "permanent"
        duration = time.humanize_delta(
            relativedelta(seconds=self.duration), max_units=2)
        if duration == "less than a second":
            duration = "instant"
        return duration

    @property
    def time_since_start(self) -> str:
        return time.time_since(self.start, max_units=2)

    def add_to_database(self) -> None:
        """Add infraction to the database"""
        log.debug(
            f"Adding infraction {self.type} to {self.user_id} by {self.actor_id}, reason: {self.reason} ; {self.str_start} [{self.duration}]")

        # In order to prevent SQL Injections use `?` as placeholder and let SQLite handle the input
        sql_write_command = """INSERT INTO infractions VALUES(?, ?, ?, ?, ?, ?, ?);"""
        sql_write_args = (self.user_id, self.type, self.reason, self.actor_id,
                          self.str_start, self.duration, int(self.is_active))

        sql_find_command = """SELECT rowid FROM infractions WHERE(
                        UID=? and Type=? and Reason=? and ActorID=? and Start=? and Duration=? and Active=?
        );"""
        sql_find_args = (self.user_id, self.type, self.reason, self.actor_id,
                         self.str_start, self.duration, int(self.is_active))

        db = SQLite()
        db.execute(sql_write_command, sql_write_args)
        db.execute(sql_find_command, sql_find_args)
        self.id = db.cur.fetchone()[0]
        db.close()

    def make_inactive(self) -> None:
        """Set infraction Active state to 0 in database"""
        log.debug(
            f"Deactivating infraction #{self.id}: {self.type} to {self.user_id}, reason: {self.reason}; {self.str_start} [{self.duration}]")

        sql_command = """UPDATE infractions SET Active=0 WHERE rowid=?;"""
        sql_args = (self.id, )

        db = SQLite()
        db.execute(sql_command, sql_args)
        db.close()


def get_infraction_by_row(row_id: int) -> Infraction:
    db = SQLite()
    db.execute("SELECT *, rowid FROM infractions WHERE rowid=?", (row_id, ))
    try:
        infraction = Infraction(*db.cur.fetchone())
        log.debug(f"Getting infraction #{row_id}")
    except TypeError:
        infraction = False
    db.close()

    return infraction


def get_all_active_infractions(inf_type: str = None) -> list:
    log.debug("Getting all active infractions")

    # Get all infractions from database
    db = SQLite()
    db.execute("SELECT *, rowid FROM infractions WHERE Active=1;")
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_infractions(user: UserSnowflake, inf_type: str = None) -> list:
    log.debug(f"Getting infractions of {user}")

    # Get all infractions from database
    db = SQLite()
    db.execute("SELECT *, rowid FROM infractions WHERE UID=?", (user.id, ))
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_active_infractions(user: UserSnowflake, inf_type: str = None) -> list:
    log.debug(f"Getting active infractions of {user}")

    # Get all infractions from database
    db = SQLite()
    db.execute(
        "SELECT *, rowid FROM infractions WHERE UID=? AND Active=1", (user.id, ))
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def get_inactive_infractions(user: UserSnowflake, inf_type: str = None) -> list:
    log.debug(f"Getting inactive infractions of {user}")

    # Get all infractions from database
    db = SQLite()
    db.execute(
        "SELECT *, rowid FROM infractions WHERE UID=? AND Active=0", (user.id, ))
    infractions = [infraction for infraction in db.cur.fetchall()]
    db.close()

    # Convert infractions to Infraction class
    all_infractions = [Infraction(*infraction) for infraction in infractions]

    if inf_type:
        return [infraction for infraction in all_infractions if infraction.type == inf_type]
    else:
        return all_infractions


def remove_infraction(infraction: Infraction) -> None:
    row_id = infraction.id
    db = SQLite()
    db.execute("DELETE FROM infractions WHERE rowid=?", (row_id, ))
    db.close()
