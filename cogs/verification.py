import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

import os
import logging
from zlib import adler32


class VerifyModal(discord.ui.Modal):
	name = discord.ui.TextInput(label="Full Name.", placeholder="Enter your full name")
	username = discord.ui.TextInput(label="Discord username.", placeholder="Enter your discord username")
	email = discord.ui.TextInput(label="email:", placeholder="Enter your email")
	id = discord.ui.TextInput(label="zID:", placeholder="Enter your ZID")
	
	async def on_submit(self, interaction: discord.interaction):
		async with self.bot.db.connection() as conn:
			async with conn.cursor() as cur:
				await conn.execute(
					"INSERT INTO verification_data (user_id, name, username, email, zid) VALUES (%s, %s, %s, %s, %s)",
					(
						interaction.user.id,
						self.name.value,
						self.username.value,
						self.email.value,
						self.id.value,
					),
				)
            	await conn.commit()

        await interaction.response.send_message(
            "Love letter submitted!", ephemeral=True
        )


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
			os.getenv("OPT_ROLE")
		]
		self.bot.loop.create_task(self.get_everything())

	async def get_everything(self):
		self.guild = await self.bot.fetch_guild(int(self.guild_id or 0))

		self.roles = []
		for role_id in self.roles_ids:
			self.roles.append(self.guild.get_role(int(role_id or 0)))

		self.mod_role = self.guild.get_role(int(os.getenv("MOD_ROLE") or 0))

		self.welcome_channel = await self.guild.fetch_channel(int(os.getenv("WELCOME_CHANNEL") or 0))
		self.introduction_channel = await self.guild.fetch_channel(int(os.getenv("INTRODUCTION_CHANNEL") or 0))

	@app_commands.command(name='verify', description='Verify yourself')
	@app_commands.guild_only()
	@app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
	async def verify(self, interaction: discord.Interaction, code: int):
		if adler32(interaction.user.name.encode('utf-8')) == int(code):
			await interaction.response.defer(ephemeral=True, thinking=True)
			try:
				await interaction.user.add_roles(*self.roles)
			except Exception as e:
				logging.error(e)
				return await interaction.followup.send(f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!", ephemeral=True)
			await interaction.followup.send('You\'re verified!', ephemeral=True)
			await self.welcome_channel.send(f"Welcome {interaction.user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")
		else:
			await interaction.response.send_message("That's not the right code silly! Did you put the right username on the form?", ephemeral=True)

	@app_commands.command(name='permit', description='Verify a member')
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_roles=True)
	@app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
	async def verify_user(self, interaction: discord.Interaction, user: discord.User):
		await interaction.response.defer(ephemeral=True, thinking=True)
		try:
			await user.add_roles(*self.roles)
		except Exception as e:
			logging.error(e)
			return await interaction.followup.send(f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!", ephemeral=True)
		await interaction.followup.send(f'{user.mention} is verified!', ephemeral=True)
		await self.welcome_channel.send(f"Welcome {user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")


	

	@app_commands.command(name='verifiy-command', description='Verify a member')
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_roles=True)
	@app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
	async def verify_user(self, interaction: discord.Interaction, user: discord.User):
		await interaction.response.defer(ephemeral=True, thinking=True)
		button = Button(label="verify uwu", style=discord.Buttonstyle.green)

		async def button_callback(interaction):
			await interaction.response.send_modal(VerifyModal())

		button.callback = button_callback
		view = View()
		view.add_item(button)
		await self.welcome_channel.send(f"Welcome {user.mention}! Please verify by clicking the button below!")


async def setup(bot):
	await bot.add_cog(Verification(bot))
