import logging
import os
from io import BytesIO

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
        elif image.size > 10_000_000:
            return await interaction.response.send_message(
                "That image is too big!", ephemeral=True
            )

        await interaction.response.send_modal(LoveLetter(db=self.bot.db, image=image))

    # @group.command(name="test", description="ehe")
    # async def test(self, interaction: discord.Interaction):
    #     await interaction.response.defer(ephemeral=True, thinking=True)

    #     async with self.bot.db.connection() as conn:
    #         async with conn.cursor() as cur:
    #             await cur.execute("SELECT * FROM love_letters")
    #             rows = await cur.fetchall()
    #             for id, row in enumerate(rows, start=1):
    #                 f, e = self.embed(id, row[1], row[2], row[3])
    #                 await self.channel.send(file=f, embed=e)

    #     await interaction.followup.send("Done!", ephemeral=True)


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
    await bot.add_cog(Love(bot))
