
import logging
import sqlite3 as lite

from bot.constants import Database

log = logging.getLogger(__name__)


class SQLite():
    def __init__(self):
        self.conn = lite.connect(Database.db_name)
        self.cur = self.conn.cursor()

    def close(self):
        self.conn.close()

    def execute(self, *args):
        self.cur.execute(*args)
        self.conn.commit()

    def create_init_tables(self):
        try:
            self.execute('''CREATE TABLE infractions(
                            UID INTEGER,
                            Type TEXT,
                            Reason TEXT,
                            ActorID INTEGER,
                            Start TEXT,
                            Duration INTEGER,
                            Active INTEGER
                            );''')
            self.execute('''CREATE TABLE users(
                            UID INTEGER,
                            Muted INTEGER,
                            Banned INTEGER
                            );''')
            log.info('Database tables created')
        except lite.OperationalError:
            log.debug('Tables exists')
