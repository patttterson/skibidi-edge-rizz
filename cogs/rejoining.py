import discord
from discord.ext import commands, tasks
from discord import app_commands

import asyncio

class Rejoining(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.manual_rejoin.start()

        self.bot.yuh = self.manual_rejoin
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.bot.user:
            guild_settings = await self.bot.get_settings(member.guild.id)
            if before.channel is not None and after.channel is None:
                await asyncio.sleep(2.0)
                if self.bot.idling[member.guild.id]:
                    await self.handle_disconnect(member.guild)
            elif after.channel is not None and before.channel is not None and before.channel.id != after.channel.id:
                await asyncio.sleep(2.0)
                await self.handle_move(member.guild)
    
    async def handle_disconnect(self, guild):
        await asyncio.sleep(1)
        if guild.voice_client:
            return

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
        await self.bot.wait_until_ready()

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM settings")
            settings = await cursor.fetchall()
            settings = list(map(dict, settings))
            for s in settings:
                s["rejoin"] = True
                self.bot.settings_cache[s.pop('guild_id')] = s

        for g_id in self.bot.settings_cache:
            guild = self.bot.get_guild(g_id)
            channel = guild.get_channel(self.bot.settings_cache[g_id]['base_channel_id'])
            if guild.voice_client is None:
                await channel.connect()


async def setup(bot):
    await bot.add_cog(Rejoining(bot))