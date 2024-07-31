import discord
from discord.ext import commands, tasks
from discord import app_commands

from typing import Optional, Literal

import os

import asyncio

from views import *

class VCCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.full_stop = False
        bot.disable_auto_join = False

        self.play_loop.start()
    
    def is_owner():
        def predicate(ctx):
            return ctx.author.id == 843230753734918154
        return commands.check(predicate)

    toggle_group = app_commands.Group(name="toggle", description="Toggle commands") 
    
    @app_commands.command()
    @app_commands.guild_only()
    @is_owner()
    async def join(self, interaction: discord.Interaction, *, channel: discord.VoiceChannel):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_connected():
            self.bot.disable_auto_join = True
            await interaction.guild.voice_client.disconnect()

        await channel.connect()
        await interaction.response.send_message(f"Joined {channel.mention}", ephemeral=True)
    
    @app_commands.command()
    @app_commands.guild_only()
    @is_owner()
    async def leave(self, interaction: discord.Interaction):
        self.bot.disable_auto_join = False

        channel = interaction.guild.voice_client.channel
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"Left {channel.mention}", ephemeral=True)
    
    @toggle_group.command(name="stop", description="Stop the bot from playing")
    @is_owner()
    async def toggle_stop(self, interaction: discord.Interaction):
        self.bot.full_stop = not self.bot.full_stop
        await interaction.response.send_message(f"{'Stopped' if self.bot.full_stop else 'Resumed'}", ephemeral=False)

    @tasks.loop(seconds=1)
    async def play_loop(self):
        if self.bot.full_stop:
            return

        voice_clients = self.bot.voice_clients

        for voice_client in voice_clients:
            if not voice_client.is_playing() and voice_client.is_connected():
                guild_settings = await self.bot.get_settings(voice_client.guild.id)
                if not guild_settings['base_sound_id']:
                    continue
                if self.bot.idling.get(voice_client.guild.id, True):
                    voice_client.play(discord.FFmpegPCMAudio(f"sounds/{guild_settings['base_sound_id']}.mp3"),
                                  after=lambda e: print(f'Error: {e}') if e else None)
                    
    

async def setup(bot: commands.Bot):
    cog = VCCommands(bot)
    await bot.add_cog(cog)