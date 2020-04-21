import logging
import textwrap
import typing as t

import discord

from bot.constants import Colours, Icons

log = logging.getLogger(__name__)

# apply icon, pardon icon
INFRACTION_ICONS = {
    "ban": (Icons.user_ban, Icons.user_unban),
    "kick": (Icons.sign_out, None),
    "mute": (Icons.user_mute, Icons.user_unmute),
    "note": (Icons.user_warn, None),
    "warn": (Icons.user_warn, None),
}

APPEALABLE_INFRACTIONS = ("ban", "mute")

# Type aliases
UserObject = t.Union[discord.Member, discord.User]
UserSnowflake = t.Union[UserObject, discord.Object]


async def notify_infraction(
    user: UserObject,
    infr_type: str,
    expires_at: t.Optional[str] = None,
    reason: t.Optional[str] = None,
    icon_url: str = Icons.token_removed
) -> bool:
    """DM a user about their new infraction and return True if the DM is successful."""
    log.debug(f"Sending {user} a DM about their {infr_type} infraction.")

    embed = discord.Embed(
        description=textwrap.dedent(f"""
            **Type:** {infr_type.capitalize()}
            **Expires:** {expires_at or "N/A"}
            **Reason:** {reason or "No reason provided."}
            """),
        colour=Colours.soft_red
    )

    embed.set_author(name="Infraction information", icon_url=icon_url)

    if infr_type in APPEALABLE_INFRACTIONS:
        embed.set_footer(
            text="If you think that this ban was unreasonable, deal with it, we have no appeal process quite yet"
        )

    return await send_private_embed(user, embed)


async def notify_pardon(
    user: UserObject,
    title: str,
    content: str,
    icon_url: str = Icons.user_verified
) -> bool:
    """DM a user about their pardoned infraction and return True if the DM is successful."""
    log.debug(f"Sending {user} a DM about their pardoned infraction.")

    embed = discord.Embed(
        description=content,
        colour=Colours.soft_green
    )

    embed.set_author(name=title, icon_url=icon_url)

    return await send_private_embed(user, embed)


async def send_private_embed(user: UserObject, embed: discord.Embed) -> bool:
    """
    A helper method for sending an embed to a user's DMs.

    Returns a boolean indicator of DM success.
    """
    try:
        await user.send(embed=embed)
        return True
    except (discord.HTTPException, discord.Forbidden, discord.NotFound):
        log.debug(
            f"Infraction-related information could not be sent to user {user} ({user.id}). "
            "The user either could not be retrieved or probably disabled their DMs."
        )
        return False
