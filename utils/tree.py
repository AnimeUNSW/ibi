import traceback

from discord.app_commands import CommandTree
from discord import Interaction


class Tree(CommandTree):
    async def interaction_check(self, interaction: Interaction) -> bool:
        return True

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        traceback.print_exception(error)
