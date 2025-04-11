from psycopg_pool import AsyncConnectionPool

from cogs.verification import UserInfo


async def add_user_to_db(db: AsyncConnectionPool, user: UserInfo):
    async with db.connection() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, first_name, last_name, zid, email, phone_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                user.id,
                user.first_name,
                user.last_name,
                user.zid,
                user.email,
                user.phone_number,
            ),
        )
        await conn.commit()
