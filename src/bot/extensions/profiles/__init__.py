import os
from collections import defaultdict
from datetime import datetime, timedelta

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .db import get_profile

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
    new_profile = await profile.add_exp(pool, 25)
    await event.message.respond(f"{profile.exp} -> {new_profile.exp}")
