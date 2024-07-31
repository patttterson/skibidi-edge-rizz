import discord
from discord.ext import commands

import starlight

class MyMenuHelpCommand(starlight.MenuHelpCommand):
    async def format_bot_page(self, view, mapping):
        return discord.Embed(title="Help", description="Choose a category below to learn more or get started with </upload:1262324370353815597>! <:maholove:1268253820303966219>", color=self.accent_color)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = MyMenuHelpCommand(per_page=10, accent_color=0xffcccb, error_color=discord.Color.red())
        # bot.help_command = starlight.convert_help_hybrid(bot.help_command)
        bot.help_command.cog = self
        
    def cog_unload(self):
        self.bot.help_command = self._original_help_command

async def setup(bot):
    await bot.add_cog(Help(bot))