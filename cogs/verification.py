import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import logging
from zlib import adler32


class VerifyModalUNSW(ui.Modal):
    """Modal for UNSW students."""

    def __init__(self, db):
        super().__init__(title="UNSW Verification")
        self.db = db

        # Required fields for UNSW
        self.first_name = ui.TextInput(label="First Name")
        self.last_name = ui.TextInput(label="Last Name")
        self.zid = ui.TextInput(label="zID (e.g. z1234567)")

        # Add to the modal
        self.add_item(self.first_name)
        self.add_item(self.last_name)
        self.add_item(self.zid)

    async def on_submit(self, interaction: discord.Interaction):
        # Insert into DB or do any other processing as needed
        async with self.db.connection() as conn:
            await conn.execute(
                "INSERT INTO love_letters (id, first_name, last_name, zid, email, phone_number) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    interaction.user.id,
                    self.first_name,
                    self.last_name,
                    self.zid,
                    None,
                    None,
                ),
            )
            await conn.commit()

        await interaction.response.send_message(
            f"Thanks for verifying, {self.first_name.value} {self.last_name.value}!\n",
            ephemeral=True,
        )


class VerifyModalNonUNSW(ui.Modal):
    """Modal for non-UNSW students."""

    def __init__(self, db):
        super().__init__(title="Non-UNSW Verification")
        self.db = db

        # Required fields for non-UNSW
        self.first_name = ui.TextInput(label="First Name")
        self.last_name = ui.TextInput(label="Last Name")
        self.phone = ui.TextInput(label="Phone Number")
        self.email = ui.TextInput(label="Email")

        # Add to the modal
        self.add_item(self.first_name)
        self.add_item(self.last_name)
        self.add_item(self.phone)
        self.add_item(self.email)

    async def on_submit(self, interaction: discord.Interaction):
        # Insert into DB or do any other processing as needed
        async with self.db.connection() as conn:
            await conn.execute(
                "INSERT INTO love_letters (id, first_name, last_name, zid, email, phone_number) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    interaction.user.id,
                    self.first_name,
                    self.last_name,
                    None,
                    self.email,
                    self.phone,
                ),
            )
            await conn.commit()

        await interaction.response.send_message(
            f"Thanks for verifying, {self.first_name.value} {self.last_name.value}!\n"
            f"Phone: {self.phone.value or 'N/A'}\n"
            f"Email: {self.email.value or 'N/A'}",
            ephemeral=True,
        )


class VerifyChoiceView(ui.View):
    """A view with two buttons: one for UNSW and one for non-UNSW."""

    def __init__(self):
        super().__init__()

    @ui.button(label="Verify (UNSW)", style=discord.ButtonStyle.primary)
    async def unsw_button(self, interaction: discord.Interaction, button: ui.Button):
        """Opens the UNSW modal."""
        await interaction.response.send_modal(VerifyModalUNSW())

    @ui.button(label="Verify (Non-UNSW)", style=discord.ButtonStyle.secondary)
    async def non_unsw_button(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        """Opens the Non-UNSW modal."""
        await interaction.response.send_modal(VerifyModalNonUNSW())


class VerifyModalUNSWCN(ui.Modal):
    """Modal for UNSW students."""

    def __init__(self):
        super().__init__(title="UNSW Verification")

        # Required fields for UNSW
        self.last_name = ui.TextInput(label="姓名")
        self.first_name = ui.TextInput(label="名字")
        self.zid = ui.TextInput(label="zID (e.g. z1234567)", required=True)

        # Add to the modal
        self.add_item(self.last_name)
        self.add_item(self.first_name)
        self.add_item(self.zid)

    async def on_submit(self, interaction: discord.Interaction):
        # Example of deriving email from zID if the user didn't provide one
        await interaction.response.send_message(
            f"Thanks for verifying, {self.first_name.value} {self.last_name.value}!\n"
            f"zID: {self.zid.value}\n",
            ephemeral=True,
        )


class VerifyModalNonUNSWCN(ui.Modal):
    """Modal for non-UNSW students."""

    def __init__(self):
        super().__init__(title="Non-UNSW Verification")

        # Required fields for non-UNSW
        self.last_name = ui.TextInput(label="姓名")
        self.first_name = ui.TextInput(label="名字")
        self.phone = ui.TextInput(label="电话")
        self.email = ui.TextInput(label="电子邮件")

        # Add to the modal
        self.add_item(self.last_name)
        self.add_item(self.first_name)
        self.add_item(self.phone)
        self.add_item(self.email)

    async def on_submit(self, interaction: discord.Interaction):
        # Insert into DB or do any other processing as needed
        await interaction.response.send_message(
            f"Thanks for verifying, {self.first_name.value} {self.last_name.value}!\n"
            f"Phone: {self.phone.value or 'N/A'}\n"
            f"Email: {self.email.value or 'N/A'}",
            ephemeral=True,
        )


class VerifyChoiceViewCN(ui.View):
    """A view with two buttons: one for UNSW and one for non-UNSW."""

    def __init__(self):
        super().__init__()

    @ui.button(label="验证 (UNSW)", style=discord.ButtonStyle.primary)
    async def unsw_button(self, interaction: discord.Interaction, button: ui.Button):
        """Opens the UNSW modal."""
        await interaction.response.send_modal(VerifyModalUNSWCN())

    @ui.button(label="验证 (非 UNSW)", style=discord.ButtonStyle.secondary)
    async def non_unsw_button(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        """Opens the Non-UNSW modal."""
        await interaction.response.send_modal(VerifyModalNonUNSWCN())


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = os.getenv("GUILD_ID")
        self.roles_ids = [
            os.getenv("MEMBER_ROLE"),
            os.getenv("COSMETIC_ROLE"),
            os.getenv("ABOUT_ROLE"),
            os.getenv("HOBBY_ROLE"),
            os.getenv("ANIME_ROLE"),
            os.getenv("SPECIAL_ROLE"),
            os.getenv("OPT_ROLE"),
        ]
        self.bot.loop.create_task(self.get_everything())

    async def get_everything(self):
        self.guild = await self.bot.fetch_guild(int(self.guild_id or 0))

        self.roles = []
        for role_id in self.roles_ids:
            self.roles.append(self.guild.get_role(int(role_id or 0)))

        self.mod_role = self.guild.get_role(int(os.getenv("MOD_ROLE") or 0))

        self.welcome_channel = await self.guild.fetch_channel(
            int(os.getenv("WELCOME_CHANNEL") or 0)
        )
        self.introduction_channel = await self.guild.fetch_channel(
            int(os.getenv("INTRODUCTION_CHANNEL") or 0)
        )

    @app_commands.command(name="verify", description="Verify yourself")
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
    async def verify(self, interaction: discord.Interaction, code: int):
        if adler32(interaction.user.name.encode("utf-8")) == int(code):
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                await interaction.user.add_roles(*self.roles)
            except Exception as e:
                logging.error(e)
                return await interaction.followup.send(
                    f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!",
                    ephemeral=True,
                )
            await interaction.followup.send("You're verified!", ephemeral=True)
            await self.welcome_channel.send(
                f"Welcome {interaction.user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}"
            )
        else:
            await interaction.response.send_message(
                "That's not the right code silly! Did you put the right username on the form?",
                ephemeral=True,
            )

    @app_commands.command(name="permit", description="Verify a member")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
    async def verify_user(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await user.add_roles(*self.roles)
        except Exception as e:
            logging.error(e)
            return await interaction.followup.send(
                f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!",
                ephemeral=True,
            )
        await interaction.followup.send(f"{user.mention} is verified!", ephemeral=True)
        await self.welcome_channel.send(
            f"Welcome {user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}"
        )

    @app_commands.command(name="verify-command", description="Verify a member")
    @app_commands.choices(
        language=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Chinese", value="cn"),
        ]
    )
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
    async def verify_command(
        self, interaction: discord.Interaction, language: app_commands.Choice[str]
    ):
        choice = language.value

        if choice == "en":
            view = VerifyChoiceView()
            await interaction.response.send_message(
                "Click below to verify uwu!", view=view
            )
        else:
            view = VerifyChoiceViewCN()
            await interaction.response.send_message(
                "Click below to verify uwu!", view=view
            )


async def setup(bot):
    guild_id = int(os.getenv("GUILD_ID"))
    guild = await bot.fetch_guild(guild_id)
    await bot.add_cog(Verification(bot), guild=guild)
    await bot.tree.sync(guild=discord.Object(id=guild_id))
