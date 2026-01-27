import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .profile_utils.db import get_all_time, reset_term, get_exp_rank

loader = lightbulb.Loader()

leaderboard = lightbulb.Group("leaderboard", "commands related to exp leaderboards")

async def gen_leaderboard(pool: AsyncConnectionPool, ctx: lightbulb.Context, term_leaderboard: bool):
    response = await get_all_time(pool, term_leaderboard)

    if term_leaderboard:
        title_string = "Term"
        desc_string = "term"
        embed_string = "term_exp"
    else:
        title_string = "All-Time"
        desc_string = "total"
        embed_string = "exp"

    rank = 1
    for row in response:
        row_id = row['user_id']
        row_user = await ctx.client.rest.fetch_user(row_id)
        row["username"] = row_user.username
        row["rank"] = rank
        row.pop("user_id")
        rank += 1

    embed = hikari.Embed(
        title=f"{title_string} Exp Leaderboard",
        description=f"🏆 Top 10 users by {desc_string} exp",
        color=0xA03DA9
    )

    rank_places = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for entry in response:
        if entry['rank'] == 1 or entry['rank'] == 2 or entry['rank'] == 3:
            place = rank_places[entry['rank']]
        else:
            place = entry['rank']

        embed.add_field(
            # the :2 makes single digit numbers print like double to preserver alignment between emojis, 10, and single digits
            name=f"{place:2}. {entry['username']}",
            value=f"{entry[f'{embed_string}']} exp",
            inline=False,
        )

    # need to add a field for the users own xp for that period (all time or term) and their rank
    user = ctx.member
    if user is None:
        await ctx.respond("Invalid user.")
        return
    
    user_id = user.id

    user_data = await get_exp_rank(pool, user_id, term_leaderboard)

    user_rank, user_exp = user_data[0]
    user_temp = await ctx.client.rest.fetch_user(user_id)
    user_name = user_temp.username

    embed.add_field(
        name="\n",
        value="-"*24,
        inline=False,
    )

    embed.add_field(
        name="\n**You:**",
        value=f"{user_rank}. {user_name}\n{user_exp} exp",
        inline=False,
    )

    return embed

# command 1:
# /leaderboard alltime
# general all time leaderboard - anyone can run the command - shows the top 10
# going to need a leaderboard group of commands similar to profile group with perms for anyone
@leaderboard.register
class AllTime(
    lightbulb.SlashCommand,
    name = "alltime",
    description = "view the 10 users with the most all-time exp"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        # defer response in case database query takes a while
        await ctx.defer()

        embed = await gen_leaderboard(pool, ctx, False)

        await ctx.respond(embed=embed)

# command 2:
# /leaderboard term
# term leaderboard - anyone can run the command - shows the top 10
@leaderboard.register
class Term(
    lightbulb.SlashCommand,
    name = "term",
    description = "view the 10 users with the most exp this term"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        # defer response in case database query takes a while
        await ctx.defer()

        embed = await gen_leaderboard(pool, ctx, True)

        await ctx.respond(embed=embed)

# command 3:
# /leaderboard reset term
# reset the term xp value for everyone to 0 - only admins can run it, maybe not able to put it into the leaderboard command group due to permissions, read hikari docs
@leaderboard.register
class Reset(
    lightbulb.SlashCommand,
    name = "reset",
    description = "reset the term-by-term exp",
    hooks=[lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)],
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, pool: AsyncConnectionPool) -> None:
        await ctx.defer()

        await reset_term(pool)

        embed = hikari.Embed(
            title="Reset exp Leaderboard",
            description="Term-by-term exp leaderboard successfully reset!",
        )

        await ctx.respond(embed=embed)

loader.command(leaderboard)