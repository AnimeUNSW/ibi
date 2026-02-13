import os
import hikari
import lightbulb

loader = lightbulb.Loader()

letter = lightbulb.Group("letter", "commands related to love letters")

command_counter = 1

# command 1:
# /letter submit
# text contents of command will be put into the love letters discord channel
# anonymously, but internal logs will keep track of who said what for moderation
# purposes - will just put their username, user_id, and message contents in a txt temporarily
@letter.register
class Submit(
    lightbulb.SlashCommand,
    name = "submit",
    description = "submit an anonymous love letter"
):

    message = lightbulb.string("message", "message contents of your 2026 love letter")
    image = lightbulb.attachment("image", "optional image attachment for your love letter", default=None)

    @lightbulb.invoke
    async def invoke (self, ctx: lightbulb.Context) -> None:
        global command_counter

        if self.message is None:
            await ctx.respond("Please put something in your love letter", ephemeral=True)
            return

        with open("love_letter_logs.txt", "a") as f:
            f.write(f"Love letter #{command_counter}, user: {ctx.user}, message: {self.message}\n")


        embed = hikari.Embed(
            title=f"#{command_counter}",
            color=0xFFC0CB
        )
        
        command_counter += 1

        embed.add_field(
            value=self.message,
            inline=False
        )

        if self.image is not None:
            embed.set_image(self.image.url)

        await ctx.client.rest.create_message(
            int(os.getenv("LOVE_LETTERS_CHANNEL")),
            embed
        )

        await ctx.respond("Anonymous love letter sent successfully", ephemeral=True)

loader.command(letter)

        

