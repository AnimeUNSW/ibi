import math
import random
from collections import defaultdict
from datetime import datetime, timedelta

import hikari
from attrs import field, frozen
from attrs.validators import instance_of, max_len
from psycopg import AsyncConnection, sql
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

LEVEL_ONE_XP_REQ = 100
FIRST_XP_INC = 55
XP_INC_DELTA = 10

cooldowns: defaultdict[hikari.User, datetime] = defaultdict(lambda: datetime.min)
# Cooldown for xp
cooldown = timedelta(minutes=1)


def exp_for_level(level: int) -> int:
    """
    Formula for xp is (non-cumulative)
    0 -> 1: LEVEL_ONE_XP_REQ
    1 -> 2: LEVEL_ONE_XP_REQ + FIRST_XP_INC
    2 -> 3: LEVEL_ONE_XP_REQ + 2 * FIRST_XP_INC + XP_INC_DELTA
    """
    return (
        LEVEL_ONE_XP_REQ * level
        + FIRST_XP_INC * math.comb(level, 2)  #
        + XP_INC_DELTA * math.comb(level, 3)
    )


def get_exp() -> int:
    return random.randint(15, 25)


@frozen
class Profile:
    user_id: int
    exp: int
    background_image: str
    quote: str = field(validator=[instance_of(str), max_len(100)])
    mal_profile: str | None
    anilist_profile: str | None
    rank: int

    def get_level_info(self) -> tuple[int, int, int]:
        """
        Calculates level info from xp

        Returns:
            (current level, remaining xp until next level, xp required for next level)
        """
        if self.exp <= 0:
            return 0, self.exp, LEVEL_ONE_XP_REQ

        # Binary search for current level
        lower, upper = 0, 1
        while self.exp >= exp_for_level(upper):
            upper *= 2
        while lower < upper:
            m = (lower + upper) // 2
            if exp_for_level(m) <= self.exp:
                lower = m + 1
            else:
                upper = m

        curr_level = lower - 1
        remaining_xp_til_next_level = self.exp - exp_for_level(curr_level)
        # Calculate xp required from level
        xp_required_for_next_level = (
            LEVEL_ONE_XP_REQ
            + FIRST_XP_INC * curr_level  #
            + XP_INC_DELTA * math.comb(curr_level, 2)
        )
        return curr_level, remaining_xp_til_next_level, xp_required_for_next_level

    @property
    def level(self) -> int:
        return self.get_level_info()[0]

    @property
    def mal_url(self) -> str:
        return f"https://myanimelist.net/profile/{self.mal_profile}"

    @property
    def anilist_url(self) -> str:
        return f"https://anilist.co/user/{self.anilist_profile}"

    @classmethod
    def from_row(cls, row: DictRow):
        return cls(
            user_id=row["user_id"],
            exp=row["exp"],
            background_image=row["background_image"],
            quote=row["quote"],
            mal_profile=row["mal_profile"],
            anilist_profile=row["anilist_profile"],
            rank=row["rank"],
        )

    async def add_exp(self, pool: AsyncConnectionPool, amount: int) -> None:
        """Add exp to the profile

        Args:
            pool: DB pool
            exp: Amount to add
        """
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE profiles
                    SET exp = exp + %s
                    WHERE user_id = %s
                    """,
                    (amount, self.user_id),
                )

    async def set_quote(self, pool: AsyncConnectionPool, new_quote: str) -> None:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE profiles
                    SET quote = %s
                    WHERE user_id = %s
                    """,
                    (new_quote, self.user_id),
                )

    async def set_mal_profile(self, pool: AsyncConnectionPool, mal_profile: str | None) -> None:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE profiles
                    SET mal_profile = %s
                    WHERE user_id = %s
                    """,
                    (mal_profile, self.user_id),
                )

    async def set_anilist_profile(self, pool: AsyncConnectionPool, anilist_profile: str | None) -> None:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE profiles
                    SET anilist_profile = %s
                    WHERE user_id = %s
                    """,
                    (anilist_profile, self.user_id),
                )

    async def remove_attribute(self, pool: AsyncConnectionPool, attribute: str) -> None:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = sql.SQL("""
                    UPDATE profiles
                    SET {column} = NULL
                    WHERE user_id = %s
                """).format(column=sql.Identifier(attribute))
                await cur.execute(
                    query,
                    (self.user_id,),
                )


async def get_profile(pool: AsyncConnectionPool, user: hikari.User) -> Profile:
    """Gets the profile of a user from the db, creates a default one of it doesn't exist

    Args:
        pool: PSQL connection pool
        user: Discord user object

    Returns:
        Profile
    """
    user_id = int(user.id)
    async with pool.connection() as conn:
        row = await fetch_profile_from_id(conn, user_id)
        if row is not None:
            return Profile.from_row(row)

        # If no profile found, make one
        await insert_default_profile(conn, user_id)

        # Refetch row from profile to avoid update anomalies
        row = await fetch_profile_from_id(conn, user_id)
        if row is None:
            raise ValueError("Default profile creation failed")
        return Profile.from_row(row)


async def fetch_profile_from_id(conn: AsyncConnection, user_id: int) -> DictRow | None:
    """Given the user id, get the row in the profiles table

    Args:
        conn: DB connection
        user_id: User id

    Returns:
        The row or None
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT *
            FROM (
                SELECT *, RANK() OVER (ORDER BY exp DESC) AS rank
                FROM profiles
            ) ranked_profiles
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return await cur.fetchone()


async def insert_default_profile(conn: AsyncConnection, user_id: int) -> None:
    """Insert a default profile for the user

    Args:
        conn: DB connection
        user_id: User id
    """
    await conn.execute(
        """
        INSERT INTO profiles (user_id, exp, background_image, quote, mal_profile, anilist_profile)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, 0, "", "Hello!", None, None),
    )
