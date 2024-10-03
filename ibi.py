import logging
logging.basicConfig(level=logging.INFO, filename='ibi.log', filemode='w')

import os
from dotenv import load_dotenv

from typing import Literal, Optional

from discord import Intents, Object, HTTPException
from discord.ext import commands

import asyncio

from bot import Bot
from utils.tree import Tree

intents = Intents.all() # evil laugh

async def run():
    load_dotenv()

    bot = Bot(
        prefix=os.getenv("PREFIX"),
        tree_cls=Tree,
        description=os.getenv("DESCRIPTION"),
        intents=intents,
        owner=os.getenv("OWNER_ID")
    )

    @bot.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(ctx: commands.Context, guilds: commands.Greedy[Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        await ctx.reply("Syncing...")
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
        await bot.start(os.getenv("TOKEN"))
    except KeyboardInterrupt:
        await bot.logout()

asyncio.run(run())
