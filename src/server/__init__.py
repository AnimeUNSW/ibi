import asyncio
import os
import traceback

import jwt
import uvicorn
from fastapi import FastAPI
from lightbulb import Client
from psycopg_pool import AsyncConnectionPool
from starlette.responses import HTMLResponse

from bot.extensions.verification import UserInfo, add_user_to_db, translations, verify_user

app = FastAPI()
client: Client
db: AsyncConnectionPool

html_template = """
<html>
    <body>
        <pre>{}</pre>
    </body>
</html>
"""


@app.get("/verify/{token}", response_class=HTMLResponse)
async def verify(token: str):
    try:
        user_info = UserInfo.from_dict(
            jwt.decode(token, os.getenv("JWT_TOKEN"), algorithms=["HS256"])
        )
        if user_info.validate() is not None:
            return html_template.format(t["endpoint"]["malformed"])
        t = translations[user_info.lang]
        await add_user_to_db(db, user_info)
        await verify_user(user_info.id, client.rest, user_info.lang)
    except Exception as e:
        print(e)
        return html_template.format(t["endpoint"]["fail"])

    return html_template.format(t["endpoint"]["success"])


async def run_server(local_client: Client, global_db: AsyncConnectionPool):
    global client
    global db
    client = local_client
    db = global_db
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
