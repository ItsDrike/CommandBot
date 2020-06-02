import asyncio
import logging
import textwrap
import typing as t
from abc import abstractmethod
from gettext import ngettext

import discord
from discord.ext.commands import Context

from bot import constants
from bot.bot import Bot
from bot.constants import STAFF_CHANNELS, Colours, Emojis
from bot.utils import time
from bot.utils.infractions import (Infraction, get_active_infractions,
                                   get_all_active_infractions, get_infractions,
                                   remove_infraction)
from bot.utils.scheduling import Scheduler

from . import utils
from .modlog import ModLog
from .utils import UserSnowflake

log = logging.getLogger(__name__)


class InfractionScheduler(Scheduler):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot
        self.bot.loop.create_task(self.reschedule_infractions())

    def mod_log(self) -> ModLog:
        """Get the currently loaded ModLog cog instance"""
        return self.bot.get_cog("ModLog")

    async def reschedule_infractions(self) -> None:
        """Schedule expiration for previous infractions."""
        await self.bot.wait_until_guild_available()

        log.debug("Rescheduling infractions")

        infractions = get_all_active_infractions()

        for infraction in infractions:
            # Do not schedule abort on permanent/instant infractions
            if not (infraction.duration == 1_000_000_000 or infraction.duration == 0):
                self.schedule_task(infraction.id, infraction)

    async def apply_infraction(
        self,
        ctx: Context,
        infraction: Infraction,
        user: UserSnowflake,
        action_coro: t.Optional[t.Awaitable] = None,
        hidden: bool = False
    ) -> None:
        """Apply an infraction to the user, log the infraction, and optionally notify the user."""

        inf_type = infraction.type
        icon = utils.INFRACTION_ICONS[inf_type][0]
        reason = infraction.reason
        duration = infraction.str_duration
        id_ = infraction.id

        confirm_msg = f":exclamation: User {user.mention} has been"

        dm_result = ""
        dm_log_text = ""
        log_title = "applied"
        log_content = None

        # Ignore duration in instant infractions
        if inf_type in ("kick", "warn"):
            expiry_msg = ""
            expiry_log = ""
        elif duration == "permanent":
            expiry_msg = "**permanently**"
            expiry_log = "Duration: permanent"
        else:
            expiry_msg = f"for {duration}"
            expiry_log = f"Duration: {duration}"

        # DM the user about infraction if it's not hidden infraction
        if not hidden:
            dm_result = ":no_bell:"
            dm_log_text = "\nDM: **Failed**"

            # Sometimes user is a discord.Object; make it a proper user
            try:
                if not isinstance(user, (discord.Member, discord.User)):
                    user = await self.bot.fetch_user(user.id)
            except discord.HTTPException as e:
                log.error(
                    f"Failed to DM {user.id}: could not fetch user (status: {e.status})")
            else:
                # Accordingly display wheather the user was successfully notified via DM
                if await utils.notify_infraction(user, inf_type, duration, reason, icon):
                    dm_result = ":bell:"
                    dm_log_text = "\nDM: Sent"

        # Include total infractions count in STAFF_CHANNELS
        if ctx.channel.id not in STAFF_CHANNELS:
            end_msg = ""
        else:
            total = len(get_infractions(user))
            end_msg = f"({total} infraction{ngettext('', 's', total)} total)"

        # Execute necessary actions to apply the infraction on Discord
        if action_coro:
            try:
                await action_coro
                # Do not schedule abort on permanent/instant infractions
                if not (infraction.duration == 1_000_000_000 or infraction.duration == 0):
                    self.schedule_task(infraction.id, infraction)
            except discord.HTTPException as e:
                confirm_msg = f"{Emojis.cross_mark} (Failed to apply) User {user.mention} haven't been"
                expiry_msg = ""
                log_content = ctx.author.mention
                log_title = "failed to apply"

                log_msg = f"Failed to apply {inf_type} infraction #{id_} to {user}"
                if isinstance(e, discord.Forbidden):
                    log.warning(f"{log_msg}: bot lacks permissions.")
                else:
                    log.exception(log_msg)

        await ctx.send(f"{dm_result} {confirm_msg} **{inf_type}ed** {expiry_msg} `{reason}` {end_msg}.")

        # Send the confirmation message
        await self.mod_log.send_log_message(
            icon_url=icon,
            colour=Colours.soft_red,
            title=f"Infractions {log_title}: {inf_type}",
            thumbnail=user.avatar_url_as(static_format="png"),
            text=textwrap.dedent(f"""
                Member: {user.mention} (`{user.id}`)
                Actor: {ctx.message.author}{dm_log_text}
                Reason: {reason}
                {expiry_log}
            """),
            content=log_content,
            footer=f"ID: {infraction.id}"
        )

        log.info(f"Applied {inf_type} infraction #{id_} to {user}")

    async def pardon_infraction(
        self,
        ctx: Context,
        infraction: Infraction,
        send_log: bool = True
    ) -> t.Union[t.Dict[str, str], bool]:
        """Prematurely end an infraction and log the action in modlog"""

        if not infraction.is_active:
            if send_log:
                await ctx.send(f"{Emojis.cross_mark} This infraction is not active")
            return False

        log_text = await self.deactivate_infraction(infraction, send_log=False)

        log_text["Pardoned"] = str(ctx.message.author)
        log_content = None
        id_ = infraction.id
        footer = f"ID: {id_}"
        user = await self.bot.fetch_user(infraction.user_id)

        # If multiple active infractions with shorter end_time were found, get their IDs
        infractions = get_active_infractions(user, inf_type=infraction.type)
        ids = []
        for inf in infractions:
            if inf.stop <= infraction.stop:
                if not (inf.duration == 1_000_000_000 or inf.duration == 0):
                    ids.append(inf.id)
        if len(ids) > 1:
            footer = f"Infraction IDs: {', '.join(ids)}"

        dm_emoji = ""
        if log_text.get("DM") == "Sent":
            dm_emoji = ":incoming_envelope:"
        elif "DM" in log_text:
            dm_emoji = f"{constants.Emojis.failmail}"

        if "Failure" in log_text:
            confirm_msg = f"{Emojis.cross_mark} failed to pardon"
            log_title = "pardon failed"
            log_content = ctx.author.mention

            log.warning(
                f"Failed to pardon {infraction.type} infraction #{id_} for {user}")
        else:
            confirm_msg = ":ok_hand: pardoned"
            log_title = "pardoned"

            log.info(
                f"Pardoned {infraction.type} infraction #{id_} for {user}")

        if isinstance(user, discord.Member):
            str_user = f"{user.mention}"
        else:
            str_user = str(user)

        if send_log:
            # Send a confirmation message to the invoking context.
            await ctx.send(
                f"{dm_emoji}{confirm_msg} infraction **{infraction.type}** for {str_user}. "
                f"{log_text.get('Failure', '')}"
            )

            # Send a log message to the mod log
            await self.mod_log.send_log_message(
                icon_url=utils.INFRACTION_ICONS[infraction.type][1],
                colour=Colours.soft_green,
                title=f"Infraction {log_title}: {infraction.type}",
                thumbnail=user.avatar_url_as(static_format="png"),
                text="\n".join(f"{k}: {v}" for k, v in log_text.items()),
                footer=footer,
                content=log_content
            )

    async def deactivate_infraction(
        self,
        infraction: Infraction,
        send_log: bool = True
    ) -> t.Dict[str, str]:
        """Deactivate an active infraction and return a dictionary of lines to send in a mod log"""

        guild = self.bot.get_guild(constants.Guild.id)
        staff_role = guild.get_role(constants.Roles.staff)
        user_id = infraction.user_id
        actor = infraction.actor_id
        type_ = infraction.type
        id_ = infraction.id

        # Stop function if the infraction is already deactivated
        if not infraction.is_active:
            log_text = f"Unable to deactivate infraction {id_}, it is not active"
            log.info(log_text)
            if send_log:
                await self.mod_log.send_log_message(
                    icon_url=constants.Icons.defcon_denied,
                    colour=Colours.soft_red,
                    title="Infraction deactivation fail",
                    text=log_text
                )
            return

        log.info(f"Marking infraction #{id_} as inactive (expired)")

        actor_usr = await self.bot.fetch_user(actor)
        actor = actor_usr if actor_usr is not None else actor
        log_content = None
        log_text = {
            "Member": f"<@{user_id}>",
            "Actor": str(actor),
            "Reason": infraction.reason,
            "Created": infraction.start
        }

        footer = f"ID: {id_}"

        user = await self.bot.fetch_user(user_id)

        infractions = get_active_infractions(user, inf_type=type_)

        # Abort pardon action if there is another infraction which is longer
        longest_infraction = max(infractions, key=lambda o: o.stop)
        if longest_infraction.duration <= infraction.duration:
            try:
                # Get the pardon coroutine for this specific infraction
                returned_log = await self._pardon_action(infraction)

                if returned_log is not None:
                    # Merge the dicts from pardon action and existing log text
                    log_text = {**log_text, **returned_log}
                else:
                    raise ValueError(
                        f"Attempted to deactivate an unsupported infraction #{id_} ({type_})"
                    )
            except discord.Forbidden:
                log.warning(
                    f"Failed to deactivate infraction #{id_} ({type_})")
                log_text["Failure"] = "The bot lacks permissions to do this (role hierarchy?)"
                log_content = staff_role.mention
            except discord.HTTPException as e:
                log.exception(
                    f"Failed to deactivate infraction #{id_} ({type_})")
                log_text["Failure"] = f"HTTPException with status {e.status} and code {e.code}"
                log_content = staff_role.mention
        else:
            log.debug(
                "Pardon action aborted, there are longer infractions of the same type")
            log_text["Note"] = "Infraction not pardoned: There are longer infractions"

        # If multiple active infractions with shorter end_time were found, mark them as inactive in the database
        # and cancel their expiration tasks.
        ids = []
        for inf in infractions:
            if inf.stop <= infraction.stop:
                # Check if duration can be deactivated (is not permanent)
                # In case it is permanent, check if current infraction is also permanent, if yes, continue anyway
                if not ((inf.duration == 1_000_000_000 and infraction.duration != 1_000_000_000) or inf.duration == 0):
                    inf.make_inactive()
                    self.cancel_task(inf.id)
                    ids.append(str(inf.id))

        if len(ids) > 1:
            footer = f"Infraction IDs: {', '.join(ids)}"
            log_note = f"Found multiple active {type_} infractions in the database."
            if "Note" in log_text:
                log_text["Note"] = f" {log_note}"
            else:
                log_text["Note"] = log_note

        if send_log:
            log_title = "expiration failed" if "Failure" in log_text else "expired"

            avatar = user.avatar_url_as(static_format="png") if user else None

            await self.mod_log.send_log_message(
                icon_url=utils.INFRACTION_ICONS[type_][1],
                colour=Colours.soft_green,
                title=f"Infraction {log_title}: {type_}",
                thumbnail=avatar,
                text="\n".join(f"{k}: {v}" for k, v in log_text.items()),
                footer=footer,
                content=log_content
            )

        return log_text

    async def remove_infraction(
        self,
        ctx: Context,
        infraction: Infraction
    ) -> None:
        """Remove given infraction from database"""

        if not infraction:
            await ctx.send(f"{Emojis.cross_mark} No such infraction")
            return
        # Try to pardon it first
        log_text = await self.pardon_infraction(ctx, infraction, send_log=False)

        remove_infraction(infraction)

        log_title = "Removed and Pardoned"

        if not log_text:
            log_title = "Removed"

            actor = infraction.actor_id
            actor_usr = await self.bot.fetch_user(actor)
            actor = actor_usr if actor_usr is not None else actor

            log_text = {
                "Member": f"<@{infraction.user_id}>",
                "Actor": str(actor),
                "Reason": infraction.reason,
                "Created": infraction.start,
                "Removed by": str(ctx.message.author)
            }
        else:
            del log_text["Pardoned"]
            log_text["Removed by"] = str(ctx.message.author)

        user = await self.bot.fetch_user(infraction.user_id)

        log.info(
            f"Removed {infraction.type} infraction #{infraction.id} for {user}")
        await ctx.send(f":exclamation: Infraction #{infraction.id} **{infraction.type}** has been **removed** for {user.mention}")

        await self.mod_log.send_log_message(
            icon_url=constants.Icons.token_removed,
            colour=Colours.soft_orange,
            title=f"Infraction {log_title}: {infraction.type}",
            thumbnail=user.avatar_url_as(static_format="png"),
            text="\n".join(f"{k}: {v}" for k, v in log_text.items()),
            footer=f"ID: {infraction.id}"
        )

    @abstractmethod
    async def _pardon_action(self, infraction: Infraction) -> t.Optional[t.Dict[str, str]]:
        """
        Execute deactivation steps specific to the infraction's type and return a log dict.

        If an infraction type is unsupported, return None instead.
        """
        raise NotImplementedError

    async def _scheduled_task(self, infraction: Infraction) -> None:
        """
        Marks an infraction expired after the delay from time of scheduling to time of expiration.

        At the time of expiration, the infraction is marked as inactive on the website and the
        expiration task is cancelled.
        """
        await time.wait_until(infraction.stop)

        # Because deactivate_infraction() explicitly cancels this scheduled task, it is shielded
        # to avoid prematurely cancelling itself.
        await asyncio.shield(self.deactivate_infraction(infraction))
