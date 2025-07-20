import hikari
from attrs import field, frozen
from attrs.validators import instance_of, max_len
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool


@frozen
class Profile:
    user_id: int
    exp: int
    background_image: str
    quote: str = field(validator=[instance_of(str), max_len(100)])
    mal_profile: str | None
    anilist_profile: str | None
    rank: int

    @property
    def level(self) -> int:
        # Temporary
        return 1 + self.exp // 100

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

    async def set_mal_profile(self, pool: AsyncConnectionPool, mal_profile: str) -> None:
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
        (user_id, 0, "uwu.png", "Right here! Right now! Emerge!", None, None),
    )
    await conn.commit()
