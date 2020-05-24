import datetime
import logging
import re
import typing as t

import dateutil.parser
import dateutil.tz
import discord
from dateutil.relativedelta import relativedelta
from discord.ext.commands import BadArgument, Context, Converter, UserConverter

log = logging.getLogger(__name__)


def proxy_user(user_id: str) -> discord.Object:
    """
    Create a proxy user object from the given id.

    Used when a Member or User object cannot be resolved.
    """
    log.debug(f"Attempting to create a proxy user for the user id {user_id}.")

    try:
        user_id = int(user_id)
    except ValueError:
        log.debug(
            f"Failed to create proxy user {user_id}: could not convert to int.")
        raise BadArgument(
            f"User ID `{user_id}` is invalid - could not convert to an integer.")

    user = discord.Object(user_id)
    user.mention = user.id
    user.display_name = f"<@{user.id}>"
    user.avatar_url_as = lambda static_format: None
    user.bot = False

    return user


class DiceThrow(Converter):
    """Convert dice throw strings into tuple[int, int]"""
    dice_parser = re.compile(
        r"^(?P<throws>(?:0*[1-9]\d*)??)[dD](?P<sides>0*[1-9]\d*?)$"
    )

    @classmethod
    async def convert(self, ctx: Context, dice_string: str) -> t.Tuple[int, int]:
        """
        Converts a `dice_string` to a Tuple[int, int] object

        The converter supports the following syntax:
        * XdY or XDY,
            - where X is a non-zero number (optional - can be left out) [dice throws]
            - where Y is a non-zero number (must be present) [dice sides]
        """
        match = self.dice_parser.fullmatch(dice_string)
        if not match:
            raise BadArgument(
                f"`{dice_string}` is not a valid dice throw string.")

        dice_dict = {
            param: (int(amount) if amount != '' else 1)
            for param, amount in match.groupdict(default=1).items()
        }

        return (dice_dict['throws'], dice_dict['sides'])


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects."""

    duration_parser = re.compile(
        r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
        r"((?P<months>\d+?) ?(months|month|mo) ?)?"
        r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
        r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
        r"((?P<hours>\d+?) ?(hours|hour|hrs|H|h) ?)?"
        r"((?P<minutes>\d+?) ?(minutes|minute|min|M|m) ?)?"
        r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
    )

    @classmethod
    async def convert(self, ctx: Context, duration: str) -> int:
        """
        Converts a `duration` string to a datetime object that's `duration` in the future.

        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `M`, `minute`, `minutes`
        - seconds: `S`, `s`, `second`, `seconds`

        The units need to be provided in descending order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) for unit,
                         amount in match.groupdict(default=0).items()}
        delta = relativedelta(**duration_dict)
        now = datetime.datetime.now()

        end_time = now + delta
        seconds = (end_time - now).total_seconds()

        return seconds


class ISODelta(Converter):
    """Converts an ISO-8601 datetime string into a datetime.datetime."""

    async def get_datetime(self, datetime_string: str) -> datetime:
        """
        First convert to datetime

        This is useful for testing purposes, as `datetime.datetime.now()` may be different
        at the time of testing compared to time of computing the delta
        """

        try:
            dt = dateutil.parser.isoparse(datetime_string)
        except ValueError:
            raise BadArgument(
                f"`{datetime_string}` is not a valid ISO-8601 datetime string")

        if dt.tzinfo:
            dt = dt.astimezone(dateutil.tz.UTC)
            dt = dt.replace(tzinfo=None)

        return dt

    async def convert(self, ctx: Context, datetime_string: str) -> int:
        """
        Converts a ISO-8601 `datetime_string` into a `datetime.datetime` object.

        The converter is flexible in the formats it accepts, as it uses the `isoparse` method of
        `dateutil.parser`. In general, it accepts datetime strings that start with a date,
        optionally followed by a time. Specifying a timezone offset in the datetime string is
        supported, but the `datetime` object will be converted to UTC and will be returned without
        `tzinfo` as a timezone-unaware `datetime` object.

        See: https://dateutil.readthedocs.io/en/stable/parser.html#dateutil.parser.isoparse

        Formats that are guaranteed to be valid by our tests are:

        - `YYYY-mm-ddTHH:MM:SSZ` | `YYYY-mm-dd HH:MM:SSZ`
        - `YYYY-mm-ddTHH:MM:SS±HH:MM` | `YYYY-mm-dd HH:MM:SS±HH:MM`
        - `YYYY-mm-ddTHH:MM:SS±HHMM` | `YYYY-mm-dd HH:MM:SS±HHMM`
        - `YYYY-mm-ddTHH:MM:SS±HH` | `YYYY-mm-dd HH:MM:SS±HH`
        - `YYYY-mm-ddTHH:MM:SS` | `YYYY-mm-dd HH:MM:SS`
        - `YYYY-mm-ddTHH:MM` | `YYYY-mm-dd HH:MM`
        - `YYYY-mm-dd`
        - `YYYY-mm`
        - `YYYY`

        Note: ISO-8601 specifies a `T` as the separator between the date and the time part of the
        datetime string. The converter accepts both a `T` and a single space character.
        """

        dt = await self.get_datetime(datetime_string)

        now = datetime.datetime.now()

        seconds = (dt - now).total_seconds()
        return seconds


class FetchedUser(UserConverter):
    """
    Converts to a 'discord.User' or, if it fails a 'discord.Object'

    If the fetch fails and the error doesn't imply the user doesn't exists, then a
    'discord.Object' is returned via the 'user_proxy' converter

    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup via API
    6. Create a proxy user with discord.Object
    """
    async def convert(self, ctx: Context, arg: str) -> t.Union[discord.User, discord.Object]:
        """Convert the `arg` to a `discord.User` or `discord.Object`."""
        try:
            return await super().convert(ctx, arg)
        except BadArgument:
            pass

        try:
            user_id = int(arg)
            log.debug(f"Fetching user {user_id}...")
            return await ctx.bot.fetch_user(user_id)
        except ValueError:
            log.debug(f"Failed to fetch user {arg}: could not convert to int.")
            raise BadArgument(
                f"The provided argument can't be turned into integer: `{arg}`")
        except discord.HTTPException as e:
            # If the Discord error isn't `Unknown user`, return a proxy instead
            if e.code != 10013:
                log.info(
                    f"Failed to fetch user, returning a proxy instead: status {e.status}")
                return proxy_user(arg)

            log.debug(f"Failed to fetch user {arg}: user does not exist.")
            raise BadArgument(f"User `{arg}` does not exist")


FetchedMember = t.Union[discord.Member, FetchedUser]
Expiry = t.Union[Duration, ISODelta]
