import discord
from discord import app_commands
from discord.ext import commands
import os

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
			os.getenv("MOD_ROLE")
		]
		self.bot.loop.create_task(self.get_everything())

	async def get_everything(self):
		self.guild = self.bot.fetch_guild(self.guild_id)

		self.roles = []
		for role_id in self.roles_ids:
			self.roles.append(await self.guild.get_role(role_id))

		self.mod_role = await self.guild.get_role(os.getenv("MOD_ROLE"))

		self.welcome_channel = await self.guild.get_channel(os.getenv("WELCOME_CHANNEL"))
		self.introduction_channel = await self.guild.get_channel(os.getenv("INTRODUCTION_CHANNEL"))

	@app_commands.command(name='verify', description='Verify yourself')
	@app_commands.guild_only()
	@app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
	async def verify(self, interaction: discord.Interaction, code: str):
		if True:
			await interaction.response.defer(ephemeral=True, thinking=True)
			try:
				await interaction.user.add_roles(*self.roles)
			except:
				return await interaction.followup.send(f"There was an error, sorry! Contact a {self.mod_role.mention} pls!!", ephemeral=True)
			await interaction.followup.send('You\'re verified!', ephemeral=True)
			await self.welcome_channel.send(f"Welcome {interaction.member.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")
		else:
			await interaction.response.send_message("That's not a valid code silly!", ephemeral=True)

	@app_commands.command(description='Verify yourself')
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_roles=True)
	@app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
	async def verify_user(self, interaction: discord.Interaction, user: discord.User):
		await interaction.response.defer(ephemeral=True, thinking=True)
		try:
			await interaction.user.add_roles(*self.roles)
		except:
			return await interaction.followup.send(f"There was an error, sorry! Contact a {self.mod_role.mention} pls!!", ephemeral=True)
		await interaction.followup.send(f'{user.mention} is verified!', ephemeral=True)
		await self.welcome_channel.send(f"Welcome {interaction.member.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")


async def setup(bot):
	await bot.add_cog(Verification(bot))
