import discord
from discord.ext import commands, tasks
from discord import app_commands

from typing import Optional, Literal

import os

import asyncio

class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Confirming', ephemeral=True)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Cancelling', ephemeral=True)
        self.value = False
        self.stop()

class Dropdown(discord.ui.Select):
    def __init__(self, vcs: list[discord.VoiceChannel], custom_callback):
        self.custom_callback = custom_callback

        options = [discord.SelectOption(label=c.name, value=c.id) for c in vcs]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Pick a voice channel...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction, self.values[0])

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
    play_group = app_commands.Group(name="play", description="Play commands")   
    
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
    async def upload(self, interaction: discord.Interaction, *, sound: discord.Attachment, name: Optional[str] = None):
        if sound.content_type != "audio/mpeg":
            await interaction.response.send_message("File must be a .mp3 file", ephemeral=True)
            return
        
        if name == None:
            name = sound.filename[:-4]
        
        file = await sound.to_file(filename=f"{name}.mp3")

        with open(f"sounds/{name}.mp3", "wb") as f:
            f.write(file.fp.read())

        await interaction.response.send_message(f"Uploaded file {name}", ephemeral=True)
    
    async def custom_callback(self, interaction: discord.Interaction, voice_channel_id: str):
        voice_channel = interaction.guild.get_channel(int(voice_channel_id))
        await voice_channel.connect()
        await interaction.response.send_message(f"Joined {voice_channel.mention}", ephemeral=True)

    @play_group.command(name="sound", description="Play a sound")
    @app_commands.guild_only()
    async def play_sound(self, interaction: discord.Interaction, file: str):
        if not interaction.guild.voice_client:
            view = Dropdown(interaction.guild.voice_channels, self.custom_callback)
            await interaction.response.send_message(f"I'm not connected to a voice channel, pick one you want me to join.", ephemeral=True, view=view)
            return
        
        if interaction.guild.voice_client.channel.id != interaction.author.voice.channel.id:
            self.bot.disable_auto_join = True
            await interaction.guild.voice_client.disconnect()
            await interaction.author.voice.channel.connect()

        if not os.path.isfile(f"sounds/{file}"):
            await interaction.response.send_message("File not found", ephemeral=True)
            return

        def after_playing(e):
            if e:
                print(f'Error: {e}')
            self.bot.disable_auto_join = False
            asyncio.run_coroutine_threadsafe(interaction.guild.voice_client.disconnect(), self.bot.loop)

        interaction.guild.voice_client.play(discord.FFmpegPCMAudio(f"sounds/{file}"),
                                            after=after_playing)
        
        await interaction.response.send_message(f"Playing {file}", ephemeral=True)
        self.done_playing.start()
    
    @play_sound.autocomplete("file")
    async def file_autocomplete(self, interaction: discord.Interaction, current: str):
        path = "sounds"
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        return [
            app_commands.Choice(name=file, value=file)
            for file in files if current.lower() in file.lower()
        ]


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