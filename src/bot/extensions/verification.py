import os
import re
from dataclasses import dataclass
from typing import Literal, Self
from urllib.request import urlopen

import email_validator
import hikari
import jwt
import lightbulb
import miru
from mailersend import emails
import phonenumbers
from psycopg_pool import AsyncConnectionPool

from bot import OwnerMention

type SupportedLanguage = Literal["en", "cn"]

type D[T] = dict[str, T | D[T]]


@dataclass
class UserInfo:
    lang: SupportedLanguage
    first_name: str
    last_name: str
    email: str | None = None
    zid: str | None = None
    phone: str | None = None
    id: int = 0

    def __post_init__(self):
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()

        if self.zid is not None:
            self.zid = self.zid.strip()
            if not self.zid.lower().startswith("z"):
                self.zid = f"z{self.zid}"

        if self.email is not None:
            self.email = self.email.strip()

        if self.phone is not None:
            self.phone = self.phone.strip()

    def validate(self) -> str | None:
        """
        Validates user info
        :return: None if valid else error message
        """
        t = translations[self.lang]
        if not self.first_name:
            return t["validation"]["first_name"]
        if not self.last_name:
            return t["validation"]["last_name"]
        if self.zid is not None and not re.match(r"z\d{7}$", self.zid):
            return t["validation"]["zid"]
        if self.email is not None:
            try:
                email_info = email_validator.validate_email(self.email, check_deliverability=False)
                self.email = email_info.normalized
            except Exception as e:
                print(self.email + str(e))
                return t["validation"]["email"]
        if self.phone is not None:
            try:
                x = phonenumbers.parse(self.phone, "AU")
                self.phone = phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.E164)
            except Exception as e:
                print(self.phone + str(e))
                return t["validation"]["phone"]

        return None

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "lang": self.lang,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "zid": self.zid,
            "email": self.email,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            lang=data["lang"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            zid=data["zid"],
            email=data["email"],
            phone=data["phone"],
            id=int(data["id"]),
        )


translations: dict[SupportedLanguage, D[str]] = {
    "en": {
        "choice": {
            "unsw": "Verify (UNSW)",
            "non-unsw": "Verify (Non-UNSW)",
        },
        "fields": {
            "first_name": "First Name",
            "last_name": "Last Name",
            "zid": "zID",
            "email": "Email",
            "phone": "Phone Number",
        },
        "field_hints": {
            "first_name": "",
            "last_name": "",
            "zid": "E.g. z1234567",
            "email": "E.g. ibi@animeunsw.net",
            "phone": "E.g. 0412345678 or +61412345678",
        },
        "validation": {
            "first_name": "First name is required.",
            "last_name": "Last name is required.",
            "zid": "Please enter a valid zID (e.g. z1234567)",
            "email": "Please enter a valid email. (e.g. ibi@animeunsw.net)",
            "phone": "Please enter a valid phone number (e.g. 0412345678 or +61412345678)",
        },
        "confirmed": "Thanks for verifying, {user_info.first_name}! "
        "Please check your email, {user_info.email}, for the next step.",
        "welcome_message": "Welcome {user}! "
        "Feel free to leave an introduction in {introduction_channel}",
        "endpoint": {
            "success": "Successfully verified!",
            "fail": "Verification was not successful, please contact {owner} on Discord for support.",
        },
        "message": {
            "initial": "Welcome to AUNSW! If you can see this then you're unverified, but don't worry; it's a simple process to get you verified.",
            "steps1": '1. Depending on whether you\'re a UNSW student or not, fill out the corresponding form by pressing on one of buttons below.\n2. If you filling out the UNSW form, you will receive a message in your student email, else if you filled out the Non-UNSW form, it will be sent to the email you provided.\n3. Click on the button in the email labeled "Verify," as shown below.',
            "steps2": "4. Profit!",
            "buttons": {
                "unsw": "Verify (UNSW)",
                "non-unsw": "Verify (Non-UNSW)",
            },
        },
    },
    "cn": {
        "choice": {
            "unsw": "验证 (UNSW)",
            "non-unsw": "验证 (非UNSW)",
        },
        "fields": {
            "first_name": "名",
            "last_name": "姓",
            "zid": "zID",
            "email": "电子邮件",
            "phone": "电话号码",
        },
        "field_hints": {
            "first_name": "",
            "last_name": "",
            "zid": "例如 z1234567",
            "email": "例如 lbi@animeunsw.net",
            "phone": "例如 0412345678 或 +61412345678",
        },
        "validation": {
            "first_name": "名是必填项。",
            "last_name": "姓是必填项。",
            "zid": "请输入有效的zID（例如 z1234567）",
            "email": "请输入有效的电子邮件（例如 lbi@animeunsw.net）",
            "phone": "请输入有效的电话号码（例如 0412345678 或 +61412345678）",
        },
        "confirmed": "感谢您的验证，{user_info.first_name}！"
        "请检查您的电子邮件，{user_info.email}，以获取下一步指示。",
        "welcome_message": "欢迎 {user}！欢迎在 {introduction_channel} 留下自我介绍",
        "endpoint": {
            "success": "验证成功！",
            "fail": "验证未成功，请在Discord上联系{owner}寻求帮助。",
        },
        "message": {
            "initial": "欢迎来到UNSW！如果您看到此消息，则表示您尚未通过验证，但请别担心；验证过程很简单。",
            "steps1": "1. 根据您是否是UNSW学生，通过点击以下按钮之一填写相应的表格。\n2. 如果您填写的是UNSW表格，您将在您的学生邮箱中收到一条消息；如果您填写的是非UNSW表格，则会发送到您提供的电子邮件地址。\n3. 点击电子邮件中标有“验证”的按钮，如下图所示。",
            "steps2": "4. 搞定！",
            "buttons": {
                "unsw": "验证 (UNSW)",
                "non-unsw": "验证 (非UNSW)",
            },
        },
    },
}


def verification_message_components(lang: SupportedLanguage):
    t = translations[lang]["message"]
    return [
        hikari.impl.TextDisplayComponentBuilder(content=t["initial"]),
        hikari.impl.ContainerComponentBuilder(
            components=[
                hikari.impl.TextDisplayComponentBuilder(content=t["steps1"]),
                hikari.impl.MediaGalleryComponentBuilder(
                    items=[
                        hikari.impl.MediaGalleryItemBuilder(
                            media=f"src/bot/images/verification_email_{lang}.png",
                        ),
                    ]
                ),
                hikari.impl.TextDisplayComponentBuilder(content=t["steps2"]),
            ]
        ),
        hikari.impl.MessageActionRowBuilder(
            components=[
                hikari.impl.InteractiveButtonBuilder(
                    style=hikari.components.ButtonStyle.PRIMARY,
                    label=t["buttons"]["unsw"],
                    custom_id=f"verify:button:{lang}:unsw",
                ),
                hikari.impl.InteractiveButtonBuilder(
                    style=hikari.components.ButtonStyle.SECONDARY,
                    label=t["buttons"]["non-unsw"],
                    custom_id=f"verify:button:{lang}:non-unsw",
                ),
            ]
        ),
    ]


public_ip = urlopen("https://ident.me").read().decode("utf8")


async def send_verification_email(user_info: UserInfo):
    url = f"http://{public_ip}:8000"
    link = (
        f"{url}/verify/{jwt.encode(user_info.to_dict(), os.getenv('JWT_TOKEN'), algorithm='HS256')}"
    )
    mailer = emails.NewEmail(os.getenv("MAILERSEND_API_KEY"))
    mail_body = {
        "from": {"name": "AnimeUNSW", "email": "socials@animeunsw.net"},
        "to": [{"name": user_info.first_name, "email": user_info.email}],
        "subject": "AnimeUNSW Discord Verification",
        "template_id": "z3m5jgr1wmz4dpyo" if user_info.lang == "en" else "3zxk54vv9o14jy6v",
        "personalization": [
            {
                "email": user_info.email,
                "data": {"link": link},
            }
        ],
    }
    return mailer.send(mail_body)


loader = lightbulb.Loader()

guild_id = int(os.getenv("GUILD_ID"))
role_ids = list(map(lambda id: int(id), os.getenv("VERIFICATION_ROLE_IDS").split(",")))
welcome_channel_id = int(os.getenv("WELCOME_CHANNEL"))
introduction_channel_id = int(os.getenv("INTRODUCTION_CHANNEL"))


async def verify_user(
    user_id: hikari.Snowflakeish, rest: hikari.api.RESTClient, lang: SupportedLanguage = "en"
):
    member = await rest.fetch_member(guild_id, user_id)
    for role_id in role_ids:
        await member.add_role(role_id, reason="verification")

    # If user does not already have the member role
    if role_ids[0] not in member.role_ids:
        await rest.create_message(
            welcome_channel_id,
            content=translations[lang]["welcome_message"].format(
                user="<@" + str(user_id) + ">",
                introduction_channel="<#" + str(introduction_channel_id) + ">",
            ),
        )


async def add_user_to_db(db: AsyncConnectionPool, user: UserInfo):
    if user.zid is not None:
        user.email = None
    async with db.connection() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, first_name, last_name, zid, email, phone_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                zid = EXCLUDED.zid,
                email = EXCLUDED.email,
                phone_number = EXCLUDED.phone_number
            """,
            (
                user.id,
                user.first_name,
                user.last_name,
                user.zid,
                user.email,
                user.phone,
            ),
        )
        await conn.commit()


verify = lightbulb.Group("verify", "commands related to verification")


@verify.register
class User(lightbulb.SlashCommand, name="user", description="verify a specific user"):
    user = lightbulb.user("user", "the user to verify")

    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context, client: lightbulb.Client, owner_mention: OwnerMention
    ) -> None:
        await ctx.defer(ephemeral=True)
        try:
            await verify_user(self.user.id, client.rest)
        except:
            await ctx.respond(
                f"There was an error in verifying {self.user.mention}. Please contact {owner_mention} for support!"
            )
        await ctx.respond(f"{self.user.mention} is verified!", ephemeral=True)


@verify.register
class Message(
    lightbulb.SlashCommand,
    name="message",
    description="send the verification view to the current chat",
):
    lang = lightbulb.string(
        "language",
        "the language of the view to be sent",
        choices=[lightbulb.Choice("English", "en"), lightbulb.Choice("Chinese", "cn")],
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, client: lightbulb.Client) -> None:
        await client.rest.create_message(
            ctx.channel_id, components=verification_message_components(self.lang)
        )
        await ctx.respond(
            "The verification message has been sent in the current channel!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )


# We do this manually as neither lightbulb nor miru support Components V2 just yet
@loader.listener(hikari.ComponentInteractionCreateEvent)
async def verify_button_listener(
    event: hikari.ComponentInteractionCreateEvent, miru_client: miru.Client
):
    match event.interaction.custom_id:
        case "verify:button:en:unsw":
            modal = VerifyModal("en", True)
            builder = modal.build_response(miru_client)
            await builder.create_modal_response(event.interaction)
            miru_client.start_modal(modal)
        case "verify:button:en:non-unsw":
            modal = VerifyModal("en", False)
            builder = modal.build_response(miru_client)
            await builder.create_modal_response(event.interaction)
            miru_client.start_modal(modal)
        case "verify:button:cn:unsw":
            modal = VerifyModal("cn", True)
            builder = modal.build_response(miru_client)
            await builder.create_modal_response(event.interaction)
            miru_client.start_modal(modal)
        case "verify:button:cn:non-unsw":
            modal = VerifyModal("cn", False)
            builder = modal.build_response(miru_client)
            await builder.create_modal_response(event.interaction)
            miru_client.start_modal(modal)


# This can return when either lightbulb modals support being sent without lightbulb.Context, or when lightbulb supports Components V2
# class VerificationModal(lightbulb.components.Modal):
#     def __init__(self, lang: SupportedLanguage, is_unsw: bool) -> None:
#         self.t = translations[lang]
#         self.is_unsw = is_unsw
#
#         self.first_name = self.add_short_text_input(self.t["fields"]["first_name"])
#         self.last_name = self.add_short_text_input(self.t["fields"]["last_name"])
#         if self.is_unsw:
#             self.zid = self.add_short_text_input(self.t["fields"]["zid"])
#         else:
#             self.email = self.add_short_text_input(self.t["fields"]["email"])
#             self.phone = self.add_short_text_input(self.t["fields"]["phone"])
#
#     async def on_submit(self, ctx: lightbulb.components.ModalContext) -> None:
#         await ctx.respond("owo")


class VerifyModal(miru.Modal):
    def __init__(self, lang: SupportedLanguage, is_unsw: bool) -> None:
        self.t = translations[lang]
        self.lang = lang
        self.is_unsw = is_unsw
        super().__init__(title=self.t["choice"]["unsw" if is_unsw else "non-unsw"])

        self.first_name = miru.TextInput(
            label=self.t["fields"]["first_name"],
            placeholder=self.t["field_hints"]["first_name"],
            required=True,
            min_length=1,
            max_length=64,
        )
        self.last_name = miru.TextInput(
            label=self.t["fields"]["last_name"],
            placeholder=self.t["field_hints"]["last_name"],
            required=True,
            min_length=1,
            max_length=64,
        )
        self.zid = miru.TextInput(
            label=self.t["fields"]["zid"],
            placeholder=self.t["field_hints"]["zid"],
            required=True,
            min_length=8,
            max_length=8,
        )
        self.email = miru.TextInput(
            label=self.t["fields"]["email"],
            placeholder=self.t["field_hints"]["email"],
            required=True,
            min_length=4,
            max_length=254,
        )
        self.phone = miru.TextInput(
            label=self.t["fields"]["phone"],
            placeholder=self.t["field_hints"]["phone"],
            required=True,
            min_length=8,
            max_length=15,
        )
        self.add_item(self.first_name)
        self.add_item(self.last_name)
        if is_unsw:
            self.add_item(self.zid)
        else:
            self.add_item(self.email)
            self.add_item(self.phone)

    async def callback(self, ctx: miru.ModalContext) -> None:
        await ctx.defer(flags=hikari.MessageFlag.EPHEMERAL)
        if self.is_unsw:
            user_info = UserInfo(
                self.lang, self.first_name.value, self.last_name.value, zid=self.zid.value
            )
        else:
            user_info = UserInfo(
                self.lang,
                self.first_name.value,
                self.last_name.value,
                email=self.email.value,
                phone=self.phone.value,
            )
        err = user_info.validate()
        if err is not None:
            await ctx.respond(err, flags=hikari.messages.MessageFlag.EPHEMERAL)
            return

        user_info.id = ctx.user.id
        if self.is_unsw:
            user_info.email = self.zid.value + "@unsw.edu.au"

        await send_verification_email(user_info)
        await ctx.respond(
            self.t["confirmed"].format(user_info=user_info),
            flags=hikari.messages.MessageFlag.EPHEMERAL,
        )


loader.command(verify)
