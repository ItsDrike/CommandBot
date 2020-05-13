import re
from random import randint

from discord import Colour, Embed
from discord.ext.commands import Cog, Context, command

from bot import constants
from bot.bot import Bot
from bot.utils.converters import DiceThrow


class Fun(Cog):
    '''
    A cog for built solely for fun
    '''

    roll_pattern = re.compile(r"[1-9]*d[1-9]+")

    def __init__(self, bot) -> None:
        self.bot = bot

    @command(name="roll", aliases=["dice", "throw", "dicethrow"])
    async def roll(self, ctx: Context, roll_string: DiceThrow) -> None:
        '''
        Roll a random number on dice
        roll_patterns: XdY X: times, Y: dice sides [f.e.: 4d20 = roll 20-sided dice 4 times]
        '''
        throws = roll_string[0]
        sides = roll_string[1]

        rolls = [randint(1, sides) for _ in range(throws)]
        total = sum(rolls)

        # Change color and extra in case there is a natural roll
        # If natural 1 red 20 green, otherwise use blurple
        color = Colour.blurple()
        extra = " "
        if all(throw == rolls[0] for throw in rolls):  # All rolls are same
            if rolls[0] == 1:
                extra = "natural "
                color = constants.Colours.soft_red
            elif rolls[0] == sides:
                extra = "natural "
                color = constants.Colours.soft_green

        embed = Embed(
            title="Dice Roll",
            description=f"{ctx.author.mention} You have rolled {extra}{total}",
            color=color
        )
        embed.set_footer(text=", ".join(str(roll) for roll in rolls))

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    '''Load the Clean cog.'''
    bot.add_cog(Fun(bot))
