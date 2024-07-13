import discord
from discord.ext import commands, tasks
from discord import app_commands

import asyncio

from typing import Literal, Optional

async def start(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if not voice_client.is_connected():
        await voice_client.connect()
    
    await voice_client.play(discord.FFmpegPCMAudio("skibidiedgerizz.mp3"))

    while voice_client.is_playing():
        await asyncio.sleep(1)

class VCCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.full_stop = False
        bot.kyuu_channel = bot.get_guild(1246945254972723202).get_channel(1261473569355993209)
        bot.test_channel = bot.get_guild(1069019652023398532).get_channel(1069019652539302013)

        self.play_loop.start()
    
    def is_owner():
        def predicate(interaction: discord.Interaction):
            return interaction.user.id == 843230753734918154
        return app_commands.check(predicate)
    
    @app_commands.command()
    @is_owner()
    @app_commands.guild_only()
    async def join(self, interaction: discord.Interaction, *, channel: discord.VoiceChannel):
        await channel.connect()
        await interaction.response.send_message(f"Joined {channel.mention}", ephemeral=True)
    
    @app_commands.command()
    @is_owner()
    @app_commands.guild_only()
    async def leave(self, interaction: discord.Interaction):
        channel = interaction.guild.voice_client.channel
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"Left {channel.mention}", ephemeral=True)
    
    @app_commands.command()
    @is_owner()
    async def full_stop(self, interaction: discord.Interaction):
        self.bot.full_stop = True
        for c in self.bot.voice_clients:
            c.stop()
        await interaction.response.send_message("Stopped all", ephemeral=True)
    
    @tasks.loop(seconds=1)
    async def play_loop(self):
        if self.bot.full_stop:
            return

        if 1246945254972723202 in [guild.id for guild in self.bot.guilds] and not self.bot.kyuu_channel.is_connected():
            await self.bot.kyuu_channel.join()
        
        if 1069019652023398532 in [guild.id for guild in self.bot.guilds] and not self.bot.test_channel.is_connected():
            await self.bot.test_channel.join()

        voice_clients = self.bot.voice_clients
        for voice_client in voice_clients:
            if not voice_client.is_playing() and voice_client.is_connected():
                voice_client.play(discord.FFmpegPCMAudio("skibidiedgerizz.mp3"),
                                  after=lambda e: print(f'Error: {e}') if e else None)
    

async def setup(bot: commands.Bot):
    cog = VCCommands(bot)
    await bot.add_cog(cog)