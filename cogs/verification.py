import string
import random
import os
import logging
from zlib import adler32
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands
from mailersend import emails
import jwt


@dataclass
class UserInfo:
    name: str
    username: str
    email: str
    zid: str


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
                return await interaction.followup.send(
                    f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!",
                    ephemeral=True)
            await interaction.followup.send('You\'re verified!', ephemeral=True)
            await self.welcome_channel.send(
                f"Welcome {interaction.user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")
        else:
            await interaction.response.send_message(
                "That's not the right code silly! Did you put the right username on the form?", ephemeral=True)

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
            return await interaction.followup.send(
                f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!",
                ephemeral=True)
        await interaction.followup.send(f'{user.mention} is verified!', ephemeral=True)
        await self.welcome_channel.send(
            f"Welcome {user.mention}! Feel free to leave an introduction in {self.introduction_channel.mention}")

    @app_commands.command(name='test_email', description='Testing email verification thing')
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
    async def test_email(
            self,
            interaction: discord.Interaction,
            email: str,
            name: str = 'test_name',
            username: str = 'test_username',
            zid: str = '00000000'
    ):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            res = await self.send_verification_email(UserInfo(
                name=name,
                username=username,
                email=email,
                zid=zid,
            ))
            await interaction.followup.send(f'email sent: {res}', ephemeral=True)
        except Exception as e:
            logging.error(e)

    async def send_verification_email(self, user_info: UserInfo):
        url = 'http://127.0.0.1:8000'
        link = f'{url}/verify/{jwt.encode({
            'name': user_info.name,
            'username': user_info.username,
            'email': user_info.email,
            'zid': user_info.zid,
        }, os.getenv('JWT_TOKEN'), algorithm='HS256')}'
        mailer = emails.NewEmail(os.getenv('MAILERSEND_API_KEY'))
        mail_body = {}
        mail_from = {'name': 'AnimeUNSW', 'email': 'socials@animeunsw.net'}
        recipients = [{'name': user_info.username, 'email': user_info.email}]
        mailer.set_mail_from(mail_from, mail_body)
        mailer.set_mail_to(recipients, mail_body)
        mailer.set_subject('AnimeUNSW Discord Verification', mail_body)
        mailer.set_template('z3m5jgr1wmz4dpyo', mail_body)
        mailer.set_personalization([{
            'email': user_info.email,
            'data': {'link': link},
        }], mail_body)
        return mailer.send(mail_body)


async def setup(bot):
    await bot.add_cog(Verification(bot))
