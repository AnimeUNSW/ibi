import os
from collections import defaultdict
from datetime import datetime, timedelta

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .profile_utils.db import get_profile

loader = lightbulb.Loader()


cooldowns: defaultdict[hikari.User, datetime] = defaultdict(lambda: datetime.min)
# Cooldown for xp
cooldown = timedelta(seconds=5)


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message(
    event: hikari.GuildMessageCreateEvent, pool: AsyncConnectionPool
) -> None:
    if event.message.channel_id != int(os.getenv("TESTING_CHANNEL") or 0):
        return

    user = event.author
    if user.is_bot:
        return

    current_time = datetime.now()
    time_since_last_xp = current_time - cooldowns[user]
    if time_since_last_xp < cooldown:
        time_until_next_xp = cooldown - time_since_last_xp
        await event.message.respond(
            f"already been fed pls wait {time_until_next_xp.total_seconds():.0f} more seconds"
        )
        return
    cooldowns[user] = current_time

    profile = await get_profile(pool, user)
    await profile.add_exp(pool, 25)
    new_profile = await get_profile(pool, user)
    await event.message.respond(f"{profile.exp} -> {new_profile.exp}")


profile = lightbulb.Group("profile", "commands related to user profiles")

translations = {
    "en": {
        "fields": {
            "title": "'s profile",
            "quote": "quote",
            "exp": "exp",
            "level": "level",
            "rank": "rank",
            "mal_profile": "mal profile",
            "anilist_profile": "anilist profile",
            "hyperlink": "click me!",
        },
    },
    "cn": {
        "fields": {
            "title": "的轮廓",
            "quote": "引用",
            "exp": "XP",
            "level": "等级",
            "rank": "秩",
            "mal_profile": "MAL轮廓",
            "anilist_profile": "AniList轮廓",
            "hyperlink": "点我！",
        },
    },
}

prefixes = {
    "anilist_profile": "https://anilist.co/user/",
    "mal_profile": "https://myanimelist.net/profile/"
}


@profile.register
class View(
    lightbulb.SlashCommand,
    name="view",
    description="view user profile details",
):
    lang = lightbulb.string(
        "language",
        "the language of the view to be sent",
        choices=[lightbulb.Choice("English", "en"), lightbulb.Choice("Chinese", "cn")],
        default="en",
    )

    user = lightbulb.user("user", "the user, defaults to yourself", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = self.user or ctx.user
        profile = await get_profile(pool, user)
        fields = translations[self.lang]["fields"]

        embed = (
            hikari.Embed(title=f"{user.display_name}{fields["title"]}")
            .set_thumbnail(user.display_avatar_url)
            .add_field(name=str(fields["quote"]), value=str(profile.quote))
            .add_field(name=str(fields["exp"]), value=str(profile.exp))
            .add_field(name=str(fields["level"]), value=str(profile.level))
            .add_field(name=str(fields["rank"]), value=str(profile.rank))
        )

        if profile.mal_profile is not None:
            embed.add_field(
                name=str(fields["mal_profile"]),
                value=f"[{fields["hyperlink"]}]({profile.mal_profile})",
            )

        if profile.anilist_profile is not None:
            embed.add_field(
                name=str(fields["anilist_profile"]),
                value=f"[{fields["hyperlink"]}]({profile.anilist_profile})",
            )

        await ctx.respond(embed=embed)


@profile.register
class Set(
    lightbulb.SlashCommand,
    name="set",
    description="set user profile details",
):
    quote = lightbulb.string("quote", "new quote to set", default=None)

    mal_profile = lightbulb.string("mal", "Enter your username for your MAL profile", default=None)
    anilist_profile = lightbulb.string("anilist", "Enter your username for your AniList profile", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = ctx.user
        profile = await get_profile(pool, user)
        if self.quote is not None:
            if len(self.quote) > 100:
                await ctx.respond(
                    f"Max quote length is 100 characters, provided quote is {len(self.quote)} characters"
                )
                return
            elif profile.quote == self.quote:
                await ctx.respond("Quote same as previous quote")
                return
            await profile.set_quote(pool, self.quote)

        if self.mal_profile is not None:
            if profile.mal_profile != self.mal_profile:
                self.mal_profile = prefixes["mal_profile"] + self.mal_profile
                await profile.set_mal_profile(pool, self.mal_profile)

        if self.anilist_profile is not None:
            if profile.anilist_profile != self.anilist_profile:
                self.anilist_profile = prefixes["anilist_profile"] + self.anilist_profile
                await profile.set_anilist_profile(pool, self.anilist_profile)

        await ctx.respond("Updated profile")


@profile.register
class Remove(
    lightbulb.SlashCommand,
    name="remove",
    description="remove user profile details"
):
    profile_field = lightbulb.string(
        "field",
        "field of profile you want to delete",
        choices=[lightbulb.Choice("MAL", "mal_profile"), lightbulb.Choice("AniList", "anilist_profile")],
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()
        user = ctx.user
        profile = await get_profile(pool, user)

        if self.profile_field is not None:
            await profile.remove_attribute(pool, self.profile_field)

        await ctx.respond("Updated profile")


loader.command(profile)
