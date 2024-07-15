import discord
from discord.ext import commands
from discord import app_commands

class VCListeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.bot.user:
            if before.channel is not None and after.channel is None:
                print(type(member))
                await self.handle_disconnect(member.guild)
    
    async def handle_disconnect(self, guild):
        if guild.id in self.bot.settings_cache:
            g_settings = await self.bot.get_settings(guild.id)
            channel = guild.get_channel(g_settings["base_channel_id"])
            print(self.bot.get_settings(guild.id)["base_channel_id"])
            if channel is not None:
                await channel.connect()


async def setup(bot):
    await bot.add_cog(VCListeners(bot))