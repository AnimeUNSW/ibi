import logging
import os
import re
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Self

import discord
import jwt
from discord import app_commands, ui
from discord.ext import commands
from mailersend import emails

type SupportedLanguage = Literal['en', 'cn']
supported_languages: list[SupportedLanguage] = ['en', 'cn']

type D[T] = dict[str, T | D[T]]

translations: dict[SupportedLanguage, D[str]] = {
    'en': {
        'choice': {
            'unsw': 'Verify (UNSW)',
            'non-unsw': 'Verify (NOT UNSW)',
        },
        'fields': {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'zid': 'zID (e.g. z1234567)',
            'phone': 'Phone Number',
            'email': 'Email',
        },
        'validation': {
            'first_name': 'First name is required.',
            'last_name': 'Last name is required.',
            'zid': 'Invalid zID, type a 7 digit number.',
        },
        'processing': 'Processing...',
        'confirmed': 'Thanks for verifying, {user_info.first_name}! '
                     'Please check your email, {user_info.email}, for the next step.',
        'button_text': 'Click below to verify uwu!',
        'welcome_message': 'Welcome {user.mention}! '
                           'Feel free to leave an introduction in {introduction_channel.mention}',
        'endpoint': {
            'success': 'Successfully verified!',
            'fail': 'Verification was not successful: {}',
        },
    },
    'cn': {
        'choice': {
            'unsw': '验证 (UNSW)',
            'non-unsw': 'Verify (NOT UNSW)',
        },
        'fields': {
            'first_name': '姓名',
            'last_name': '名字',
            'zid': 'zID (e.g. z1234567)',
            'phone': '电话',
            'email': '电子邮件',
        },
        'validation': {
            'first_name': '名字是必填项。',
            'last_name': '姓氏是必填项。',
            'zid': '无效的zID，请输入一个7位数字。',
        },
        'processing': '处理中...',
        'confirmed': '感谢您的验证，{user_info.first_name}！'
                     '请查看您的邮箱 {user_info.email}，以进行下一步操作。',
        'button_text': '请点击下面验证哦～uwu',
        'welcome_message': '欢迎 {user.mention}！'
                           '欢迎在 {introduction_channel.mention} 频道留下你的自我介绍～',
        'endpoint': {
            'success': '验证成功！',
            'fail': '验证失败：\n{}',
        },
    },
}


@dataclass
class UserInfo:
    first_name: str
    last_name: str
    lang: SupportedLanguage
    email: str = None
    zid: str | None = None
    phone_number: str | None = None
    id: int = 0

    def __post_init__(self):
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()

        if self.zid is not None:
            self.zid = self.zid.strip()
            if not self.zid.lower().startswith('z'):
                self.zid = f'z{self.zid}'

        if self.email is None:
            self.email = f'{self.zid}@unsw.edu.au'
        else:
            self.email = self.email.strip()

        if self.phone_number is not None:
            self.normalize_phone_number()

    def normalize_phone_number(self):
        num = self.phone_number.strip()
        if self.phone_number.startswith("04"):
            num = f"+61{num[1:]}"
        if not self.phone_number.startswith("+"):
            num = f"+{num}"
        self.phone_number = num

    def validate(self) -> str | None:
        """
        Validates user info
        :return: None if valid else error message
        """
        t = translations[self.lang]
        if not self.first_name:
            return t['validation']['first_name']
        if not self.last_name:
            return t['validation']['last_name']
        if self.zid is not None and not re.match(r'z\d{7}$', self.zid):
            return t['validation']['zid']
        return None

    def to_dict(self) -> dict:
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'lang': self.lang,
            'email': self.email,
            'zid': self.zid,
            'phone_number': self.phone_number,
            'id': self.id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            first_name=data['first_name'],
            last_name=data['last_name'],
            lang=data['lang'],
            email=data['email'],
            zid=data['zid'],
            phone_number=data['phone_number'],
            id=data['id'],
        )


def verify_modal_factory(lang: Literal['en', 'cn']):
    t = translations[lang]

    class ReturnModal(ui.View):
        """A view with two buttons: one for UNSW and one for non-UNSW."""

        @ui.button(label=t['choice']['unsw'], style=discord.ButtonStyle.primary)
        async def unsw_button(self, interaction: discord.Interaction, button: ui.Button):
            """Opens the UNSW modal."""
            await interaction.response.send_modal(VerifyModalUNSW())

        @ui.button(label=t['choice']['non-unsw'], style=discord.ButtonStyle.secondary)
        async def non_unsw_button(self, interaction: discord.Interaction, button: ui.Button):
            """Opens the Non-UNSW modal."""
            await interaction.response.send_modal(VerifyModalNonUNSW())

    class VerifyModalABC(ABC, ui.Modal):
        """Abstract class for data input modals."""

        def __init__(self) -> None:
            super().__init__(timeout=None)

        @property
        @abstractmethod
        def user_info(self) -> UserInfo: ...

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_info = self.user_info
                err = user_info.validate()
                if err is not None:
                    await interaction.response.send_message(err, ephemeral=True)
                    return
                user_info.id = interaction.user.id
                await interaction.response.defer(ephemeral=True, thinking=True)
                await send_verification_email(user_info)
                await interaction.followup.send(t['confirmed'].format(user_info=user_info), ephemeral=True)
            except Exception as e:
                traceback.print_exception(e)

    class VerifyModalUNSW(VerifyModalABC, title='UNSW Verification'):
        """Modal for UNSW students."""
        first_name = ui.TextInput(label=t['fields']['first_name'], required=True)
        last_name = ui.TextInput(label=t['fields']['last_name'], required=True)
        zid = ui.TextInput(label=t['fields']['zid'], required=True)

        @property
        def user_info(self) -> UserInfo:
            return UserInfo(
                first_name=self.first_name.value,
                last_name=self.last_name.value,
                lang=lang,
                zid=self.zid.value,
            )

    class VerifyModalNonUNSW(VerifyModalABC, title='Non-UNSW Verification'):
        """Modal for UNSW students."""
        first_name = ui.TextInput(label=t['fields']['first_name'], required=True)
        last_name = ui.TextInput(label=t['fields']['last_name'], required=True)
        phone = ui.TextInput(label=t['fields']['phone'])
        email = ui.TextInput(label=t['fields']['email'], required=True)

        @property
        def user_info(self) -> UserInfo:
            return UserInfo(
                first_name=self.first_name.value,
                last_name=self.last_name.value,
                lang=lang,
                phone_number=self.phone.value,
                email=self.email.value,
            )

    return ReturnModal


VerifyChoiceView = {
    lang: verify_modal_factory(lang)
    for lang in supported_languages
}


class Verification(commands.Cog):
    guild: discord.Guild
    roles: list[discord.Role]
    mod_role: discord.Role
    welcome_channel: discord.TextChannel
    introduction_channel: discord.TextChannel

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

    async def verify_user(self, user: discord.User, lang: SupportedLanguage = 'en'):
        # member = await self.guild.fetch_member(user.id)
        # await member.add_roles(*self.roles)
        await self.welcome_channel.send(
            translations[lang]['welcome_message'].format(
                user=user, introduction_channel=self.introduction_channel
            )
        )

    @app_commands.command(name="permit", description="Verify a member")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.guilds(discord.Object(id=os.getenv("GUILD_ID")))
    async def permit(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.verify_user(user)
        except Exception as e:
            logging.error(e)
            return await interaction.followup.send(
                f"There was an error, sorry! Contact {(await self.bot.application_info()).owner.mention} pls!!",
                ephemeral=True,
            )
        await interaction.followup.send(f"{user.mention} is verified!", ephemeral=True)

    @app_commands.command(name="verify", description="Verify a member")
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
        lang: SupportedLanguage = language.value
        view = VerifyChoiceView[lang]()
        await interaction.response.send_message(
            translations[lang]['button_text'],
            view=view,
        )


async def send_verification_email(user_info: UserInfo):
    url = 'http://127.0.0.1:8000'
    link = f'{url}/verify/{jwt.encode(user_info.to_dict(), os.getenv('JWT_TOKEN'), algorithm='HS256')}'
    mailer = emails.NewEmail(os.getenv('MAILERSEND_API_KEY'))
    mail_body = {
        'from': {'name': 'AnimeUNSW', 'email': 'socials@animeunsw.net'},
        'to': [{'name': user_info.first_name, 'email': user_info.email}],
        'subject': 'AnimeUNSW Discord Verification',
        'template_id': 'z3m5jgr1wmz4dpyo',
        'personalization': [{
            'email': user_info.email,
            'data': {'link': link},
        }]
    }
    return mailer.send(mail_body)


async def setup(bot):
    guild_id = int(os.getenv("GUILD_ID"))
    guild = await bot.fetch_guild(guild_id)
    await bot.add_cog(Verification(bot), guild=guild)
    await bot.tree.sync(guild=discord.Object(id=guild_id))
