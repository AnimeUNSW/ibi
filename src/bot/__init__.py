import os

import hikari
import lightbulb
import miru
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from bot import extensions

load_dotenv()

token = os.getenv("TOKEN")
if not token:
    raise ValueError("Set TOKEN in .env file")
bot = hikari.GatewayBot(token, logs="DEBUG")
client = lightbulb.client_from_app(bot)

miru_client = miru.Client(bot, ignore_unknown_interactions=True)
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(miru.Client, miru_client)

owner_id = os.getenv("OWNER_ID")
if not owner_id:
    raise ValueError("Set OWNER_ID in .env file")
type OwnerMention = str
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(OwnerMention, f"<@{owner_id}>")  # type: ignore[reportArgumentType]


@client.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    if isinstance(exc.__cause__, lightbulb.prefab.checks.MissingRequiredPermission):
        await exc.context.respond("You lack the permissions to do that.", ephemeral=True)
        return True
    else:
        return False


@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("Set DATABASE_URL in .env file")
    pool = AsyncConnectionPool(db_url)
    await pool.open()
    client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(AsyncConnectionPool, pool, teardown=pool.close)

    from server import run_server

    await run_server(client, pool)

    await client.load_extensions_from_package(extensions)
    await client.start()


# Enable lightbulb to do dependency cleanup
bot.subscribe(hikari.StoppingEvent, client.stop)
