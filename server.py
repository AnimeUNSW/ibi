import asyncio
import os
import traceback

import jwt
import uvicorn
from fastapi import FastAPI

from bot import Bot
from cogs.verification import Verification, translations
from database import UserInfo, add_user_to_db

app = FastAPI()
bot: Bot


@app.get("/verify/{token}")
async def verify(token: str):
    try:
        user_info = UserInfo.from_dict(jwt.decode(token, os.getenv("JWT_TOKEN"), algorithms=["HS256"]))
        t = translations[user_info.lang]
        # Only works if user is cached
        user = bot.get_user(user_info.id)
        if user is None:
            user = await bot.fetch_user(user_info.id)
        verif_cog = bot.get_cog('Verification')

        await add_user_to_db(bot.db, user_info)
        await verif_cog.verify_user(user, user_info.lang)
    except Exception as e:
        return {'message': t['endpoint']['fail'].format(traceback.format_exception(e))}

    return {"message": t['endpoint']['success']}


async def run_server(local_bot: Bot):
    global bot
    bot = local_bot
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
