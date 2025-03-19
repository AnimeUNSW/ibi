import asyncio
import logging
import os
from typing import Literal, Optional

from discord import HTTPException, Intents, Object
from discord.ext import commands
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from bot import Bot
from utils.tree import Tree

logging.basicConfig(level=logging.INFO, filename="ibi.log", filemode="w")
intents = Intents.all()  # evil laugh


async def run():
    load_dotenv()

    pool = AsyncConnectionPool(os.getenv("DATABASE_URL"), open=False)
    await pool.open()

    bot = Bot(
        prefix=os.getenv("PREFIX"),
        tree_cls=Tree,
        description=os.getenv("DESCRIPTION"),
        intents=intents,
        owner_ids=list(map(lambda id : int(id),os.getenv("OWNER_IDS").split(","))),
        db=pool,
    )

    @bot.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        ctx: commands.Context,
        guilds: commands.Greedy[Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
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

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    try:
        await bot.start(os.getenv("TOKEN"))
    except KeyboardInterrupt:
        pool.close()
        await bot.logout()


asyncio.run(run())
