import uvicorn
from fastapi import FastAPI
import jwt
import os
import asyncio

import bot

app = FastAPI()
discord_bot: bot.Bot = None


@app.get("/verify/{token}")
async def verify(token: str):
    guild = await discord_bot.fetch_guild(int(os.getenv("GUILD_ID")))
    channel = await guild.fetch_channel(1334667128850087987)
    await channel.send(f'email verified: {repr(jwt.decode(token, os.getenv("JWT_TOKEN"), algorithms=["HS256"]))}')
    return {"message": "Successfully verified!"}


async def run_server(local_bot: bot.Bot):
    global discord_bot
    discord_bot = local_bot
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
