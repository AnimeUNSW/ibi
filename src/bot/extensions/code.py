import os
from collections import defaultdict
from datetime import datetime, timedelta
import random
import string

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .event_code_utils.date_convert import convert_string_to_date, get_unix_timestamp

# constants
EXPIRY_SECONDS = 7200 # 2 hours


loader = lightbulb.Loader()
code = lightbulb.Group("code", "commands related to code")

def generate_code() -> str:
    length = 4
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return random_string


@code.register
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

        expiry_timestamp = unix_timestamp + EXPIRY_SECONDS

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO events (event_code, expiry_date)
                    VALUES (%s, %s)
                    """,
                    (code, expiry_timestamp),
                )

        ret_string = (
                    f"Code generated: {code} Event ends at {self.end_date} at "
                    f"{self.end_hour}:00 Unix timestamp is: "
                    f"{unix_timestamp} and the code will expire in {EXPIRY_SECONDS / 3600} hours, "
                    f"timestamp: {expiry_timestamp}"
            )

        await ctx.respond(ret_string)


@code.register
class Redeem(
    lightbulb.SlashCommand,
    name="redeem",
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
        await ctx.respond(f"Thank you {username} for coming to our code! We hope to see you soon!")


loader.command(code)
