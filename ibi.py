import logging
logging.basicConfig(level=logging.INFO, filename='ibi.log', filemode='w')

from typing import Literal, Optional

from discord import Intents, Object, HTTPException
from discord.ext import commands

import asyncio

from utils import setup
config = setup.config()

from bot import Bot
from utils.tree import Tree

intents = Intents.all() # Temporary as I work things out

async def run():
    bot = Bot(
        prefix=config['prefix'],
        tree_cls=Tree,
        description=config['description'],
        intents=intents
    )

    @bot.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(ctx: commands.Context, guilds: commands.Greedy[Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    try:
        await bot.start(config['token'])
    except KeyboardInterrupt:
        await db.close()
        await bot.logout()

asyncio.run(run())
