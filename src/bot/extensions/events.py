import os
from collections import defaultdict
from datetime import datetime, timedelta
import random
import string

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .event_utils.date_convert import convert_string_to_date, get_unix_timestamp

loader = lightbulb.Loader()

events = lightbulb.Group("event", "commands related to events")

def generate_code() -> str:
    length = 8
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return random_string


@events.register
class Create(
    lightbulb.SlashCommand,
    name="create",
    description="creates an event",
):
    end_date=lightbulb.string(
        "end_date",
        "the date when the event will end format it in DD/MM/YYYY e.g. 01/01/2000",
    )

    end_hour=lightbulb.string(
        "end_hour",
        "the hour when the event will end"
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        code = generate_code()

        event_end_date = convert_string_to_date(self.end_date, self.end_hour)
        unix_timestamp = get_unix_timestamp(event_end_date)

        await ctx.respond(f"Code generated: {code} Event ends at {self.end_date} at {self.end_hour}:00 Unix timestamp is: {unix_timestamp}")


@events.register
class Submit(
    lightbulb.SlashCommand,
    name="submit",
    description="enter an event code to get extra EXP!"
):
    code=lightbulb.string(
        "code",
        "code given to you at the event",
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = ctx.member
        username = user.nickname or user.username
        await ctx.respond(f"Thank you {username} for coming to our events! We hope to see you soon!")


loader.command(events)
