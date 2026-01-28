import hikari
import lightbulb
from psycopg_pool import AsyncConnectionPool

from .profile_utils.db import get_all_time, reset_term, get_exp_rank, get_level_info

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

    # initialise as 2 because thats minimum len for discord username
    max_username_len = 2
    rank = 1
    for row in response:
        row_id = row['user_id']
        row_user = await ctx.client.rest.fetch_user(row_id)
        row["username"] = row_user.username

        if len(row["username"]) > max_username_len:
            max_username_len = len(row["username"])

        row["rank"] = rank
        row.pop("user_id")
        rank += 1

    embed_description = f"Top 10 users by **{desc_string}** XP & level."

    embed = hikari.Embed(
        title=f"🏆 {title_string} XP Leaderboard 🏆",
        description=embed_description,
        color=0xA03DA9
    )

    desc_string = desc_string.capitalize()

    # separating line length is either 3 + max username length (3 comes from the 3 chars of 10.) or if that would
    # be shorter than the embed description, use that length
    if (max_username_len + 3) > len(embed_description):
        sep_line_len = max_username_len + 3
    else:
        if term_leaderboard:
            # nicely fitting (lowkey arbitrary) length if no extra long usernames
            sep_line_len = 27
        else:
            # Fibonacci
            sep_line_len = 30

    rank_places = {
        # used 2 thin spaces to pad medals (U+2009)
        1: "🥇 ",
        2: "🥈 ",
        3: "🥉 "
    }

    embed.add_field(
        name="",
        # U+23AF dividing line
        value="⎯"*sep_line_len,
        inline=False,
    )

    for entry in response:
        if entry['rank'] == 1 or entry['rank'] == 2 or entry['rank'] == 3:
            place = rank_places[entry['rank']]
        else:
            # used a ZWSP
            place = f"​​{entry["rank"]}."

        level = get_level_info(entry[f'{embed_string}'])[0]

        if term_leaderboard:
            embed.add_field(
                name=f"{place} {entry['username']}",
                value=f"Level: {level}\nXP: {entry[f'{embed_string}']}",
                inline=False,
            )
        else:
            embed.add_field(
                name=f"{place} {entry['username']}",
                value=f"Level: {level}\nXP: {entry[f'{embed_string}']}",
                inline=False,
            )

    user = ctx.member
    if user is None:
        await ctx.respond("Invalid user.")
        return
    
    user_id = user.id
    user_data = await get_exp_rank(pool, user_id, term_leaderboard)
    user_rank, user_exp = user_data[0]
    user_temp = await ctx.client.rest.fetch_user(user_id)
    user_name = user_temp.username

    user_level = get_level_info(user_exp)[0]

    if user_rank == 1 or user_rank == 2 or user_rank == 3:
        user_place = rank_places[user_rank]
    else:
        user_place = f"{user_rank}."

    embed.add_field(
        name="\n",
        value="⎯"*sep_line_len,
        inline=False,
    )

    if term_leaderboard:
        embed.add_field(
            name="\n**You:**",
            value=f"{user_place} {user_name}\nLevel: {user_level}\n{desc_string} XP: {user_exp}",
            inline=False,
        )
    else:
        embed.add_field(
            name="\n**You:**",
            value=f"{user_place} {user_name}\nLevel: {user_level}\n{desc_string} XP: {user_exp}",
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