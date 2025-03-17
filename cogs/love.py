import logging
import os
from io import BytesIO

import asyncio

import discord
from discord import app_commands
from discord.ext import commands


class Love(commands.Cog, name="love"):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = os.getenv("GUILD_ID")
        self.bot.loop.create_task(self.get_everything())

    async def get_everything(self):
        self.guild = await self.bot.fetch_guild(int(self.guild_id or 0))
        self.channel = await self.guild.fetch_channel(
            int(os.getenv("VALENTINES_CHANNEL") or 0)
        )

    def embed(self, id: int, author: int, content: str, image: bytes = None):
        e = discord.Embed(
            title=f"#{id}",
            description=content,
            color=discord.Colour.from_str("#F12A8A"),
        )
        f = None
        if image is not None:
            f = discord.File(BytesIO(image), filename="image.png")
            e.set_image(url="attachment://image.png")
        return (f, e)

    group = app_commands.Group(name="letter", description="Love letter commands")

    @group.command(name="submit", description="Submit a love letter!")
    async def verify_user(
        self, interaction: discord.Interaction, image: discord.Attachment = None
    ):
        if image is not None and not image.content_type.startswith("image"):
            return await interaction.response.send_message(
                "That's not an image!", ephemeral=True
            )
        elif image is not None and image.size > 10_000_000:
            return await interaction.response.send_message(
                "That image is too big!", ephemeral=True
            )

        await interaction.response.send_modal(LoveLetter(db=self.bot.db, image=image))

    @group.command(name="view", description="View a love letter given its id.")
    @commands.has_permissions(administrator=True)
    async def view(self, interaction: discord.Interaction, id: int):
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.bot.db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM love_letters WHERE id = %s", (id,))
                row = await cur.fetchone()
                if row is None:
                    return await interaction.followup.send(
                        "That's not a valid love letter id!", ephemeral=True
                    )
                f, e = self.embed(row[0], row[1], row[2], row[3])
                await interaction.followup.send(file=f, embed=e)

    @group.command(name="viewall", description="View all love letters.")
    @commands.has_permissions(administrator=True)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        async with self.bot.db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM love_letters ORDER BY id")
                rows = await cur.fetchall()
                for id, row in enumerate(rows, start=1):
                    f, e = self.embed(id, row[1], row[2], row[3])
                    await interaction.channel.send(file=f, embed=e)
                    await asyncio.sleep(60 * 20)

        await interaction.followup.send("Done!", ephemeral=True)

    @group.command(name="1984", description="Remove a love letter.")
    @commands.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, id: int):
        await interaction.response.defer(ephemeral=True, thinking=True)

        async with self.bot.db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM love_letters WHERE id = %s", (id,))
                print(cur.statusmessage)
                if cur.statusmessage == "DELETE 1":
                    await interaction.followup.send("Done!", ephemeral=True)
                else:
                    await interaction.followup.send("That's not a valid id!")

    async def post(self, id: int, num: int):
        async with self.bot.db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM love_letters WHERE id > %s ORDER BY id", (id,)
                )
                row = await cur.fetchone()
                if row["count"] == 0:
                    return id
                f, e = self.embed(num, row[1], row[2], row[3])
                await self.channel.send(file=f, embed=e)
                return row[0]


class LoveLetter(discord.ui.Modal, title="New Love Letter"):
    def __init__(self, db, image):
        super().__init__()
        self.db = db
        self.image = image

    letter = discord.ui.TextInput(
        label="What should be posted?",
        style=discord.TextStyle.paragraph,
        placeholder="Write your love letter here...",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        async with self.db.connection() as conn:
            await conn.execute(
                "INSERT INTO love_letters (author, content, image) VALUES (%s, %s, %s)",
                (
                    interaction.user.id,
                    self.letter.value,
                    await self.image.read() if self.image is not None else None,
                ),
            )
            await conn.commit()

        await interaction.response.send_message(
            "Love letter submitted!", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            "Oops! Something went wrong. Maybe try again later?", ephemeral=True
        )

        logging.error(error)


async def setup(bot):
    pass
    # await bot.add_cog(Love(bot))
