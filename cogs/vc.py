import discord
from discord.ext import commands, tasks
from discord import app_commands

from typing import Optional

import asyncio

class VCCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.full_stop = False
        bot.disable_auto_join = False
        try:
            try:
                bot.kyuu_channel = bot.get_guild(1246945254972723202).get_channel(1261473569355993209)
            except AttributeError:
                pass

            bot.test_channel = bot.get_guild(1069019652023398532).get_channel(1069019652539302013)
        except AttributeError:
            pass

        self.play_loop.start()
    
    def is_owner():
        def predicate(interaction: discord.Interaction):
            return interaction.user.id in (843230753734918154,
                                           601068265745416225,
                                           871505546593853461)
        return app_commands.check(predicate)

    toggle_group = app_commands.Group(name="toggle", description="Toggle commands")
    
    @app_commands.command()
    @is_owner()
    @app_commands.guild_only()
    async def join(self, interaction: discord.Interaction, *, channel: discord.VoiceChannel):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_connected():
            self.bot.disable_auto_join = True
            await interaction.guild.voice_client.disconnect()

        await channel.connect()
        await interaction.response.send_message(f"Joined {channel.mention}", ephemeral=True)
    
    @app_commands.command()
    @is_owner()
    @app_commands.guild_only()
    async def leave(self, interaction: discord.Interaction):
        self.bot.disable_auto_join = False

        channel = interaction.guild.voice_client.channel
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"Left {channel.mention}", ephemeral=True)
    
    @toggle_group.command(name="autojoin", description="Toggle auto join, which makes the bot auto rejoin <#1261473569355993209>")
    @is_owner()
    async def toggle_auto_join(self, interaction: discord.Interaction):
        self.bot.disable_auto_join = not self.bot.disable_auto_join
        await interaction.response.send_message(f"Auto join {'disabled' if self.bot.disable_auto_join else 'enabled'}", ephemeral=False)
    
    @toggle_group.command(name="stop", description="Stop the bot from playing")
    @is_owner()
    async def toggle_stop(self, interaction: discord.Interaction):
        self.bot.full_stop = not self.bot.full_stop
        await interaction.response.send_message(f"{'Stopped' if self.bot.full_stop else 'Resumed'}", ephemeral=False)
    
    @app_commands.command(name="upload", description="Upload a .mp3 file to add to the bot.")
    @is_owner()
    async def upload(self, interaction: discord.Interaction, *, sound: discord.Attachment, name: Optional[str] = False):
        if sound.content_type != "audio/mpeg":
            await interaction.response.send_message("File must be a .mp3 file", ephemeral=True)
            return
        
        if not name:
            name = sound.filename[:-4]
        
        file = await sound.to_file(f"{name}.mp3")

        with open(f"sounds/{name}.mp3", "wb") as f:
            f.write(file.fp)

        await interaction.response.send_message(f"Uploaded file {name}", ephemeral=True)
    
    @tasks.loop(seconds=1)
    async def play_loop(self):
        if self.bot.full_stop:
            return

        voice_clients = self.bot.voice_clients

        if 1246945254972723202 in [guild.id for guild in self.bot.guilds] and \
            not [c for c in voice_clients if c.channel.id == self.bot.kyuu_channel.id] and \
            not self.bot.disable_auto_join:
            await self.bot.kyuu_channel.connect()
        
        if 1069019652023398532 in [guild.id for guild in self.bot.guilds] and \
            not [c for c in voice_clients if c.channel.id == self.bot.test_channel.id]:
            await self.bot.test_channel.connect()

        for voice_client in voice_clients:
            if not voice_client.is_playing() and voice_client.is_connected():
                voice_client.play(discord.FFmpegPCMAudio("sounds/skibidiedgerizz.mp3"),
                                  after=lambda e: print(f'Error: {e}') if e else None)
    

async def setup(bot: commands.Bot):
    cog = VCCommands(bot)
    await bot.add_cog(cog)