import discord
from discord.ext import commands, tasks
from discord import app_commands

import asyncio

class Rejoining(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.bot.user:
            guild_settings = await self.bot.get_settings(member.guild.id)
            if not guild_settings["rejoin"]:
                return
            if before.channel is not None and after.channel is None:
                await asyncio.sleep(1)
                await self.handle_disconnect(member.guild)
            elif after.channel is not None and before.channel is not None and before.channel.id != after.channel.id:
                await asyncio.sleep(1)
                await self.handle_move(member.guild)
    
    async def handle_disconnect(self, guild):
        if guild.id in self.bot.settings_cache:
            g_settings = await self.bot.get_settings(guild.id)
            channel = guild.get_channel(g_settings["base_channel_id"])
            if channel is not None:
                await channel.connect()
    
    async def handle_move(self, guild):
        await guild.voice_client.disconnect()
        await self.handle_disconnect(guild)
    
    @tasks.loop(minutes=1)
    async def manual_rejoin(self):
        for guild, _, channel_id in self.bot.settings_cache.values():
            guild = self.bot.get_guild(guild)
            channel = guild.get_channel(channel_id)
            if guild.voice_client is None:
                await channel.connect()


async def setup(bot):
    await bot.add_cog(Rejoining(bot))