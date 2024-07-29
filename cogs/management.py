import discord
from discord.ext import commands, tasks
from discord import app_commands

from typing import Optional, Literal

import os

import logging

from views import *

class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        logging.info(f"Joined guild {guild.name} (ID: {guild.id}).")
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT INTO settings (guild_id, prefix, base_channel_id) VALUES (?, ?, ?)", (guild.id, "!", 0))
            self.settings_cache[guild.id] = {"prefix": "!", "base_channel_id": 0}
            await self.bot.db.commit()

    settings_group = app_commands.Group(name="settings", description="Manage the bot's settings.")

    @settings_group.command(name="prefix", description="Set the bot's prefix.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def prefix(self, interaction: discord.Interaction, prefix: str):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE settings SET prefix = ? WHERE guild_id = ?", (prefix, interaction.guild.id))
            self.settings_cache[interaction.guild.id]["prefix"] = prefix
            await self.bot.db.commit()
        await interaction.response.send_message(f"Prefix set to {prefix}.", ephemeral=True)
    
    @settings_group.command(name="base_channel", description="Set the base channel for the bot to live in while not being used.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def base_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE settings SET base_channel_id = ? WHERE guild_id = ?", (channel.id, interaction.guild.id))
            await self.bot.db.commit()
        
        self.bot.settings_cache.pop(interaction.guild.id, None)
        await interaction.response.send_message(f"Base channel set to {channel.mention}.", ephemeral=True)
    
    async def base_sound_callback(self, interaction: discord.Interaction, sound_id: str):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE settings SET base_sound_id = ? WHERE guild_id = ?", (sound_id, interaction.guild.id))
            await self.bot.db.commit()
        
        self.bot.settings_cache.pop(interaction.guild.id, None)
        await interaction.response.send_message(f"Base sound ID set to {sound_id}.", ephemeral=False)

    @settings_group.command(name="base_sound", description="Set the default sound that the bot will play while not in use.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def base_sound(self, interaction: discord.Interaction):
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.base_sound_callback, "Pick a sound...")
        await interaction.response.send_message("Pick a sound you've uploaded to set as the default.", ephemeral=False, view=file_selector)


async def setup(bot):
    await bot.add_cog(Management(bot))