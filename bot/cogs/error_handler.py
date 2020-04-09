import logging
import typing as t

from discord.ext.commands import Cog, Command, Context, errors
from sentry_sdk import push_scope

from bot.bot import Bot
from bot.decorators import InChannelCheckFailure

log = logging.getLogger(__name__)


class ErrorHandler(Cog):
    """Handles errors emitted from commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, e: errors.CommandError) -> None:
        """
        Provide generic command error handling.

        Error handling is deferred to any local error handler, if present. This is done by
        checking for the presence of a `handled` attribute on the error.

        Error handling emits a single error message in the invoking context `ctx` and a log message,
        prioritized as follows:

        1. If the name fails to match a command:
            * If CommandNotFound is raised when invoking the tag (determined by the presence of the
              `invoked_from_error_handler` attribute), this error is treated as being unexpected
              and therefore sends an error message
        2. UserInputError: see `handle_user_input_error`
        3. CheckFailure: see `handle_check_failure`
        4. CommandOnCooldown: send an error message in the invoking context
        5. Otherwise, if not a DisabledCommand, handling is deferred to `handle_unexpected_error`
        """
        command = ctx.command

        if hasattr(e, "handled"):
            log.trace(
                f"Command {command} had its error already handled locally; ignoring.")
            return

        if isinstance(e, errors.CommandNotFound) and not hasattr(ctx, "invoked_from_error_handler"):
            await self.command_not_found(ctx)
            return  # Exit early to avoid logging.
        elif isinstance(e, errors.UserInputError):
            await self.handle_user_input_error(ctx, e)
        elif isinstance(e, errors.CheckFailure):
            await self.handle_check_failure(ctx, e)
        elif isinstance(e, errors.CommandOnCooldown):
            await ctx.send(e)
        elif isinstance(e, errors.CommandInvokeError):
            await self.handle_unexpected_error(ctx, e.original)
            return  # Exit early to avoid logging.
        elif not isinstance(e, errors.DisabledCommand):
            # ConversionError, MaxConcurrencyReached, ExtensionError
            await self.handle_unexpected_error(ctx, e)
            return  # Exit early to avoid logging.

        log.debug(
            f"Command {command} invoked by {ctx.message.author} with error "
            f"{e.__class__.__name__}: {e}"
        )

    @staticmethod
    async def command_not_found(ctx: Context) -> None:
        '''
        Send an error message in 'ctx' for CommandNotFound error
        '''
        log.debug(
            f"{ctx.author} tried to use an invalid command"
        )
        await ctx.send(f'Command not found, use !help for help')

    async def get_help_command(self, command: t.Optional[Command]) -> t.Tuple:
        """Return the help command invocation args to display help for `command`."""
        parent = None
        if command is not None:
            parent = command.parent

        # Retrieve the help command for the invoked command.
        if parent and command:
            return self.bot.get_command("help"), parent.name, command.name
        elif command:
            return self.bot.get_command("help"), command.name
        else:
            return self.bot.get_command("help")

    async def handle_user_input_error(self, ctx: Context, e: errors.UserInputError) -> None:
        """
        Send an error message in `ctx` for UserInputError, sometimes invoking the help command too.

        * MissingRequiredArgument: send an error message with arg name and the help command
        * TooManyArguments: send an error message and the help command
        * BadArgument: send an error message and the help command
        * BadUnionArgument: send an error message including the error produced by the last converter
        * ArgumentParsingError: send an error message
        * Other: send an error message and the help command
        """
        # TODO: use ctx.send_help() once PR #519 is merged.
        help_command = await self.get_help_command(ctx.command)

        if isinstance(e, errors.MissingRequiredArgument):
            await ctx.send(f"Missing required argument `{e.param.name}`.")
            await ctx.invoke(*help_command)
        elif isinstance(e, errors.TooManyArguments):
            await ctx.send(f"Too many arguments provided.")
            await ctx.invoke(*help_command)
        elif isinstance(e, errors.BadArgument):
            await ctx.send(f"Bad argument: {e}\n")
            await ctx.invoke(*help_command)
        elif isinstance(e, errors.BadUnionArgument):
            await ctx.send(f"Bad argument: {e}\n```{e.errors[-1]}```")
        elif isinstance(e, errors.ArgumentParsingError):
            await ctx.send(f"Argument parsing error: {e}")
        else:
            await ctx.send("Something about your input seems off. Check the arguments:")
            await ctx.invoke(*help_command)

    @staticmethod
    async def handle_check_failure(ctx: Context, e: errors.CheckFailure) -> None:
        """
        Send an error message in `ctx` for certain types of CheckFailure.

        The following types are handled:

        * BotMissingPermissions
        * BotMissingRole
        * BotMissingAnyRole
        * NoPrivateMessage
        * InChannelCheckFailure
        """
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole
        )

        if isinstance(e, bot_missing_errors):
            await ctx.send(
                f"Sorry, it looks like I don't have the permissions or roles I need to do that."
            )
        elif isinstance(e, (InChannelCheckFailure, errors.NoPrivateMessage)):
            await ctx.send(e)

    @staticmethod
    async def handle_unexpected_error(ctx: Context, e: errors.CommandError) -> None:
        """Send a generic error message in `ctx` and log the exception as an error with exc_info."""
        await ctx.send(
            f"Sorry, an unexpected error occurred. Please let us know!\n\n"
            f"```{e.__class__.__name__}: {e}```"
        )

        with push_scope() as scope:
            scope.user = {
                "id": ctx.author.id,
                "username": str(ctx.author)
            }

            scope.set_tag("command", ctx.command.qualified_name)
            scope.set_tag("message_id", ctx.message.id)
            scope.set_tag("channel_id", ctx.channel.id)

            scope.set_extra("full_message", ctx.message.content)

            if ctx.guild is not None:
                scope.set_extra(
                    "jump_to",
                    f"https://discordapp.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
                )

            log.error(
                f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}", exc_info=e)


def setup(bot: Bot) -> None:
    """Load the ErrorHandler cog."""
    bot.add_cog(ErrorHandler(bot))
