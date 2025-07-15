import csv
from io import StringIO

import hikari
import lightbulb
from psycopg.sql import SQL, Identifier
from psycopg_pool import AsyncConnectionPool

loader = lightbulb.Loader()


@loader.command
class UserCsvs(
    lightbulb.SlashCommand,
    name="user_csvs",
    description="get user csvs",
    hooks=[lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)],
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        old_users = await get_csv(pool, "old_users")
        new_users = await get_csv(pool, "users")
        await ctx.respond(
            attachments=[
                hikari.Bytes(old_users, "old_users.csv"),
                hikari.Bytes(new_users, "new_users.csv"),
            ]
        )


async def get_csv(pool: AsyncConnectionPool, table_name: str) -> StringIO:
    buffer = StringIO()
    writer = csv.writer(buffer)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            query = SQL("SELECT * FROM {}").format(Identifier(table_name))
            await cur.execute(query)
            if cur.description is None:
                raise ValueError(f"{table_name} table does not exist")
            col_names = [desc.name for desc in cur.description]
            writer.writerow(col_names)
            async for row in cur:
                writer.writerow(row)
    buffer.seek(0)
    return buffer
