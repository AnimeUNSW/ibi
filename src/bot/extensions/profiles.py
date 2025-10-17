import os
from datetime import datetime
from io import BytesIO

import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from bot.extensions.profile_utils.color import get_colors, make_progress_bar

from .profile_utils.db import cooldown, cooldowns, get_exp, get_profile

loader = lightbulb.Loader()


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent, pool: AsyncConnectionPool) -> None:
    user = event.author
    if user.is_bot:
        return

    current_time = datetime.now()
    time_since_last_xp = current_time - cooldowns[user]
    if time_since_last_xp < cooldown:
        return
    cooldowns[user] = current_time

    profile = await get_profile(pool, user)
    await profile.add_exp(pool, get_exp())
    new_profile = await get_profile(pool, user)
    if profile.level != new_profile.level and profile.level > 0:
        channel_id = int(os.getenv("XP_CHANNEL") or 0)
        await event.app.rest.create_message(
            channel_id, f"🎉 {user.mention} leveled up to **Level {new_profile.level}**!"
        )


profile = lightbulb.Group("profile", "commands related to user profiles")

translations = {
    "en": {
        "fields": {
            "title": "'s Profile",
            "level": "Level",
            "rank": "Rank",
            "mal_profile": "MAL",
            "anilist_profile": "AniList",
        },
    },
    "cn": {
        "fields": {
            "title": "的轮廓",
            "level": "等级",
            "rank": "秩",
            "mal_profile": "MAL轮廓",
            "anilist_profile": "AniList轮廓",
        },
    },
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

        level, xp_remainder, xp_total = profile.get_level_info()
        fg_color, bg_color = get_colors(user.display_avatar_url)

        xp_img = make_progress_bar(xp_remainder, xp_total, fg_color, bg_color)
        buffer = BytesIO()
        xp_img.save(buffer, format="PNG")
        buffer.seek(0)
        xp_bytes = hikari.Bytes(buffer, "xp.png")

        embed = hikari.Embed(
            title=f"{user.display_name}{fields['title']}",
            description=str(profile.quote),
            color=fg_color,
        ).set_thumbnail(user.display_avatar_url)

        if profile.mal_profile is not None:
            embed.add_field(
                name=str(fields["mal_profile"]),
                value=f"[{profile.mal_profile}]({profile.mal_url})",
            )

        if profile.anilist_profile is not None:
            embed.add_field(
                name=str(fields["anilist_profile"]),
                value=f"[{profile.anilist_profile}]({profile.anilist_url})",
            )

        embed.add_field(name=str(fields["rank"]), value="#" + str(profile.rank))
        embed.add_field(name=str(fields["level"]), value=f"{level} | {xp_remainder}/{xp_total}")
        embed.set_image(xp_bytes)

        await ctx.respond(embed=embed)


@profile.register
class Set(
    lightbulb.SlashCommand,
    name="set",
    description="set user profile details",
):
    quote = lightbulb.string("quote", "quote to be displayed (max 100 characters)", default=None)

    mal_profile = lightbulb.string("mal", "username (not link) for your MAL profile", default=None)
    anilist_profile = lightbulb.string("anilist", "username (not link) for your AniList profile", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        user = ctx.user
        profile = await get_profile(pool, user)
        if self.quote is not None:
            if len(self.quote) > 100:
                await ctx.respond(
                    f"Max quote length is 100 characters, provided quote is {len(self.quote)} characters.",
                    ephemeral=True,
                )
                return
            elif profile.quote == self.quote:
                await ctx.respond("Quote same as previous quote.", ephemeral=True)
                return
            await profile.set_quote(pool, self.quote)

        if self.mal_profile is not None:
            if profile.mal_profile != self.mal_profile:
                await profile.set_mal_profile(pool, self.mal_profile)

        if self.anilist_profile is not None:
            if profile.anilist_profile != self.anilist_profile:
                await profile.set_anilist_profile(pool, self.anilist_profile)

        await ctx.respond("Profile updated!", ephemeral=True)


@profile.register
class Remove(lightbulb.SlashCommand, name="remove", description="remove certain fields of your profile"):
    profile_field = lightbulb.string(
        "field",
        "field of profile you want to remove",
        choices=[
            lightbulb.Choice("MAL", "mal_profile"),
            lightbulb.Choice("AniList", "anilist_profile"),
        ],
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        user = ctx.user
        profile = await get_profile(pool, user)

        if self.profile_field is not None:
            await profile.remove_attribute(pool, self.profile_field)

        await ctx.respond("Profile updated!", ephemeral=True)


loader.command(profile)
