import os
import random
import string
from datetime import datetime
from zoneinfo import ZoneInfo

import hikari
import lightbulb
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from bot.extensions.profile_utils.db import get_profile

loader = lightbulb.Loader()
code = lightbulb.Group("code", "commands related to event codes")


def generate_code() -> str:
    length = 4
    random_string = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return random_string


@code.register
class Create(
    lightbulb.SlashCommand,
    name="create",
    description="creates a code for an event",
):
    end_time = lightbulb.string(
        "end_time",
        "format as DD/MM/YYYY HH:MM, e.g. 01/01/2000 17:30",
    )
    xp_amount = lightbulb.integer(
        "xp_amount",
        "how much XP the code gives",
        choices=[lightbulb.Choice(f"{amount} XP", amount) for amount in range(250, 1001, 250)],
    )

    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context, pool: AsyncConnectionPool, client: hikari.api.RESTClient
    ) -> None:
        await ctx.defer(ephemeral=True)

        tz = ZoneInfo("Australia/Sydney")
        try:
            event_end_date = datetime.strptime(
                self.end_time,
                "%d/%m/%Y %H:%M",
            ).replace(tzinfo=tz)
        except ValueError:
            await ctx.respond(
                f"Invalid `end_time` ({self.end_time}).\nGive time in DD/MM/YYYY HH:MM format."
            )
            return
        if event_end_date < datetime.now(tz):
            await ctx.respond(f"Provided `end_time` of ({event_end_date}) is in the past.")
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
            await ctx.respond(
                "Could not generate a unique code. Please purge the database of old codes."
            )
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

        embed = hikari.Embed(description=f"Code: `{code}`\nExpires <t:{unix_timestamp}:R>")
        channel_id = int(os.getenv("EVENT_CODES_CHANNEL") or 0)
        await client.create_message(channel_id, embed=embed)


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
class Redeem(lightbulb.SlashCommand, name="redeem", description="enter an event code to get XP!"):
    code = lightbulb.string(
        "code",
        "the code given to you at the event",
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        user = ctx.member
        if user is None:
            await ctx.respond("Invalid user.")
            return
        command_sent_time = int(datetime.now().timestamp())

        # check that the code exists
        xp_amount = await get_code_xp_amount(pool, self.code)
        if xp_amount is None:
            await ctx.respond(f"Invalid code: `{self.code}`.")
            return

        # check that the code has not expired
        if not await code_not_expired(pool, self.code, command_sent_time):
            await ctx.respond(f"Code: `{self.code}` has expired.")
            return

        # check that the player has not already submited the code
        if await try_redeem_code(pool, user_id=user.id, code=self.code):
            profile = await get_profile(pool, user)
            await profile.add_exp(pool, xp_amount)
            await ctx.respond(
                f"Thank you {user.mention} for coming to our event! We hope to see you again soon!",
            )
        else:
            await ctx.respond("You have already redeemed this code!")


loader.command(code)


@loader.task(lightbulb.uniformtrigger(hours=24))
async def purge_expired_events(pool: AsyncConnectionPool):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # DELETE ON CASCADE is on for event_participants so it handles that automatically
            await cur.execute(
                """
                DELETE FROM events
                WHERE expiry_date < %s
                """,
                (int(datetime.now().timestamp()),),
            )
