import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from bot.extensions.profile_utils.db import get_profile

loader = lightbulb.Loader()

mod = lightbulb.Group("mod", "commands for moderators")


@mod.register
class Reset(
    lightbulb.SlashCommand,
    name="reset",
    description="reset fields in a user's profile",
    hooks=[lightbulb.prefab.has_permissions(hikari.Permissions.MODERATE_MEMBERS)],
):
    user = lightbulb.user("user", "the user")
    field = lightbulb.string(
        "field",
        "which field to reset",
        default="all",
        choices=[
            lightbulb.Choice("Quote", "quote"),
            lightbulb.Choice("MAL", "mal profile"),
            lightbulb.Choice("AniList", "anilist profile"),
            lightbulb.Choice("All", "all"),
        ],
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer(ephemeral=True)
        profile = await get_profile(pool, self.user)
        if self.field in ("quote", "all"):
            await profile.set_quote(pool, "Hello!")
        if self.field in ("mal_profile", "all"):
            await profile.set_mal_profile(pool, None)
        if self.field in ("anilist_profile", "all"):
            await profile.set_anilist_profile(pool, None)

        if self.field == "all":
            await ctx.respond(f"{self.user.mention}'s profile has been reset!")
        else:
            await ctx.respond(f"{self.user.mention}'s {self.field} field has been reset!")


loader.command(mod)
