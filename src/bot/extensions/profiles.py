import os
from collections import defaultdict
from datetime import datetime, timedelta

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .profile_utils.db import get_profile

loader = lightbulb.Loader()


cooldowns: defaultdict[hikari.User, datetime] = defaultdict(lambda: datetime.min)
# Cooldown for xp
cooldown = timedelta(seconds=5)


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent, pool: AsyncConnectionPool) -> None:
    if event.message.channel_id != int(os.getenv("TESTING_CHANNEL") or 0):
        return

    user = event.author
    if user.is_bot:
        return

    current_time = datetime.now()
    time_since_last_xp = current_time - cooldowns[user]
    if time_since_last_xp < cooldown:
        time_until_next_xp = cooldown - time_since_last_xp
        await event.message.respond(f"already been fed pls wait {time_until_next_xp.total_seconds():.0f} more seconds")
        return
    cooldowns[user] = current_time

    profile = await get_profile(pool, user)
    await profile.add_exp(pool, 25)
    new_profile = await get_profile(pool, user)
    await event.message.respond(f"{profile.exp} -> {new_profile.exp}")


profile = lightbulb.Group("profile", "commands related to user profiles")


@profile.register
class View(
    lightbulb.SlashCommand,
    name="view",
    description="view user profile details",
):
    user = lightbulb.user("user", "the user, defaults to yourself", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = self.user or ctx.user
        profile = await get_profile(pool, user)
        await ctx.respond(
            f"Name: {user.display_name}\n"
            f"Quote: {profile.quote}\n"
            f"Exp: {profile.exp}\n"
            f"Level: {profile.level}\n"
            f"Rank: {profile.rank}\n"
        )


@profile.register
class Set(
    lightbulb.SlashCommand,
    name="set",
    description="set user profile details",
):
    quote = lightbulb.string("quote", "new quote to set", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = ctx.user
        profile = await get_profile(pool, user)
        if self.quote is not None:
            if len(self.quote) > 100:
                await ctx.respond(f"Max quote length is 100 characters, provided quote is {len(self.quote)} characters")
                return
            elif profile.quote == self.quote:
                await ctx.respond("Quote same as previous quote")
                return
            await profile.set_quote(pool, self.quote)
        await ctx.respond("Updated quote")


loader.command(profile)
