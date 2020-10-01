import re
from random import randint

from discord import Colour, Embed
from discord.ext.commands import Cog, Context, command

import aiohttp

from bot import constants
from bot.bot import Bot
from bot.converters import DiceThrow


class Fun(Cog):
    """
    A cog for built solely for fun
    """

    roll_pattern = re.compile(r"[1-9]*d[1-9]+")

    def __init__(self, bot) -> None:
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @command(name="roll", aliases=["dice", "throw", "dicethrow"])
    async def roll(self, ctx: Context, roll_string: DiceThrow) -> None:
        """
        Roll a random number on dice
        roll_patterns: XdY X: times, Y: dice sides [f.e.: 4d20 = roll 20-sided dice 4 times]
        """
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

    @command()
    async def joke(self, ctx: Context) -> None:
        """Send a random joke."""
        async with self.session.get("https://mrwinson.me/api/jokes/random") as resp:
            if resp.status == 200:
                data = await resp.json()
                joke = data["joke"]
                embed = Embed(
                    description=joke,
                    color=Color.gold()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Something went boom! :( [CODE: {resp.status}]")

    @command()
    async def koala(self, ctx: Context) -> None:
        """Get a random picture of a koala."""
        async with self.session.get("https://some-random-api.ml/img/koala") as resp:
            if resp.status == 200:
                data = await resp.json()
                embed = Embed(
                    title="Random Koala!",
                    color=Color.gold()
                )
                embed.set_image(url=data["link"])
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Something went boom! :( [CODE: {resp.status}]")

    @command()
    async def panda(self, ctx: Context) -> None:
        """Get a random picture of a panda."""
        async with self.session.get("https://some-random-api.ml/img/panda",) as resp:
            if resp.status == 200:
                data = await resp.json()
                embed = Embed(
                    title="Random Panda!",
                    color=Color.gold(),
                )
                embed.set_image(url=data["link"])
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Something went boom! :( [CODE: {resp.status}]")

    @command()
    async def catfact(self, ctx: Context) -> None:
        """Send a random cat fact."""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://cat-fact.herokuapp.com/facts") as response:
                self.all_facts = await response.json()

        fact = choice(self.all_facts["all"])
        await ctx.send(embed=Embed(
            title="Did you Know?",
            description=fact["text"],
            color=0x690E8
        ))

    @command()
    async def inspireme(self, ctx: Context) -> None:
        """Fetch a random "inspirational message" from the bot."""
        try:
            async with self.session.get("http://inspirobot.me/api?generate=true") as page:
                picture = await page.text(encoding="utf-8")
                embed = Embed()
                embed.set_image(url=picture)
                await ctx.send(embed=embed)

        except Exception:
            await ctx.send("Oops, there was a problem!")

    @command(aliases=["shouldi", "ask"])
    async def yesno(self, ctx: Context, *, question: str) -> None:
        """Let the bot answer a yes/no question for you."""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://yesno.wtf/api", headers=self.user_agent) as meme:
                if meme.status == 200:
                    mj = await meme.json()
                    ans = await self.get_answer(mj["answer"])
                    em = Embed(
                        title=ans,
                        description=f"And the answer to {question} is this:",
                        colour=0x690E8
                    )
                    em.set_image(url=mj["image"])
                    await ctx.send(embed=em)
                else:
                    await ctx.send(f"OMFG! [STATUS : {meme.status}]")


def setup(bot: Bot) -> None:
    """Load the Clean cog."""
    bot.add_cog(Fun(bot))
