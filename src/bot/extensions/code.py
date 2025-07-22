import os
from collections import defaultdict
from datetime import datetime, timedelta
import random
import string
from psycopg.errors import UniqueViolation


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


async def code_exists(pool, event_code):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                from events
                where event_code = %s
                """,
                (event_code, )
            )

            res = await cur.fetchone()

            return bool(res)
        
async def code_not_expired(pool, code, date):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                from events
                where event_code = %s and expiry_date > %s
                """,
                (code, date)
            )

            res = await cur.fetchone()

            return bool(res)
        

async def code_not_expired(pool, code, date):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                from events
                where event_code = %s and expiry_date > %s
                """,
                (code, date)
            )

            res = await cur.fetchone()

            return bool(res)
        
async def try_redeem_code(pool, user_id, code):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into event_participants (event_code, user_id)
                values (%s, %s)
                """,
                (code, user_id)
            )




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

        command_sent_time = get_unix_timestamp(datetime.now())
        # check that the code exists

        if not await code_exists(pool, self.code):
            await ctx.respond(f"Invalid code: {self.code}")
            return
        # check that the code has not expired
        if not await code_not_expired(pool, self.code, command_sent_time):
            await ctx.respond(f"code: {self.code} expired")
            return
        # check that the player has not already submited the code

        user = ctx.member
        username = user.nickname or user.username
        await ctx.respond(f"Thank you {username} for coming to our code! We hope to see you soon!")


loader.command(code)
