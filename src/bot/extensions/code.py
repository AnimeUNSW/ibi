import random
import string
from datetime import datetime

import lightbulb
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from bot.extensions.profile_utils.db import get_profile

from .event_code_utils.date_convert import convert_string_to_date


loader = lightbulb.Loader()
code = lightbulb.Group("code", "commands related to code")


def generate_code() -> str:
    length = 4
    random_string = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return random_string


@code.register
class Create(
    lightbulb.SlashCommand,
    name="create",
    description="creates an event",
):
    end_date = lightbulb.string(
        "end_date",
        "the date when the event will end format it in DD/MM/YYYY e.g. 01/01/2000",
    )
    end_hour = lightbulb.string(
        "end_hour",
        "the hour when the event will end",
    )
    xp_amount = lightbulb.integer(
        "xp_amount",
        "how much xp the code gives",
        choices=[lightbulb.Choice(f"{amount} xp", amount) for amount in range(250, 1001, 250)],
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()

        try:
            event_end_date = convert_string_to_date(self.end_date, self.end_hour)
        except ValueError:
            await ctx.respond(f"Invalid end_date ({self.end_date}) or end_hour ({self.end_hour}).")
            return
        unix_timestamp = int(event_end_date.timestamp())

        # Try to generate a code
        for _ in range(3):
            code = generate_code()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT 1
                        FROM events
                        WHERE event_code = %s
                        """,
                        (code,),
                    )
                    if not await cur.fetchone():
                        break
        else:  # 3 tries to generate a unique code, if failed then error
            await ctx.respond("Could not generate a unique code. Please purge the database of old codes.")
            return

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO events (event_code, expiry_date, xp_amount)
                    VALUES (%s, %s, %s)
                    """,
                    (code, unix_timestamp, self.xp_amount),
                )

        await ctx.respond(f"Code generated: {code}\nEvent ends in <t:{unix_timestamp}:R>")


async def get_code_xp_amount(pool, event_code) -> int | None:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT xp_amount
                from events
                where event_code = %s
                """,
                (event_code,),
            )

            res = await cur.fetchone()

            return res[0] if res else None


async def code_not_expired(pool, code, date):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                from events
                where event_code = %s and expiry_date > %s
                """,
                (code, date),
            )

            res = await cur.fetchone()

            return bool(res)


async def try_redeem_code(pool, user_id, code):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    """
                    INSERT INTO event_participants (event_code, user_id)
                    VALUES (%s, %s)
                    """,
                    (code, user_id),
                )
                conn.commit()
                return True
            except UniqueViolation:
                return False


@code.register
class Redeem(lightbulb.SlashCommand, name="redeem", description="enter an event code to get extra EXP!"):
    code = lightbulb.string(
        "code",
        "code given to you at the event",
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        user = ctx.member
        if user is None:
            await ctx.respond("Invalid user", ephemeral=True)
            return
        command_sent_time = int(datetime.now().timestamp())

        # check that the code exists
        xp_amount = await get_code_xp_amount(pool, self.code)
        if xp_amount is None:
            await ctx.respond(f"Invalid code: {self.code}", ephemeral=True)
            return

        # check that the code has not expired
        if not await code_not_expired(pool, self.code, command_sent_time):
            await ctx.respond(f"Code: {self.code} expired", ephemeral=True)
            return

        # check that the player has not already submited the code
        if await try_redeem_code(pool, user_id=user.id, code=self.code):
            profile = await get_profile(pool, user)
            await profile.add_exp(pool, xp_amount)
            await ctx.respond(
                f"Thank you {user.mention} for coming to our event! We hope to see you soon!", ephemeral=True
            )
        else:
            await ctx.respond("You have already redeemed the code!", ephemeral=True)


loader.command(code)
