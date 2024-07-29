import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional

import os
import asyncio

from views import *

from snowflake import SnowflakeGenerator

class CustomSounds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.snowflake_gen = SnowflakeGenerator(42)

    def is_owner():
        def predicate(ctx):
            return ctx.author.id == 843230753734918154
        return commands.check(predicate)

    def can_use():
        def predicate(interaction: discord.Interaction):
            return interaction.user.id in (843230753734918154,
                                           601068265745416225,
                                           871505546593853461)
        return app_commands.check(predicate)
    
    play_group = app_commands.Group(name="play", description="Play commands")  

    @app_commands.command(name="upload", description="Upload a .mp3 file to add to the bot.")
    @can_use()
    async def upload(self, interaction: discord.Interaction, *, sound: discord.Attachment, name: Optional[str] = None):
        if sound.content_type != "audio/mpeg":
            await interaction.response.send_message("File must be a .mp3 file", ephemeral=True)
            return
        
        if name == None:
            name = sound.filename[:-4]
        
        sound_id = next(self.bot.snowflake_gen)
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT INTO sounds (id, author_id, name) VALUES (?, ?, ?)", (sound_id, interaction.user.id, name))
            await self.bot. db.commit()

        file = await sound.to_file(filename=f"{sound_id}.mp3")

        with open(f"sounds/{sound_id}.mp3", "wb") as f:
            f.write(file.fp.read())

        embed = discord.Embed(title="Sound uploaded", description=f"Name: {name}\nID: {sound_id}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def jvc_callback(self, interaction: discord.Interaction, voice_channel_id: str):
        voice_channel = interaction.guild.get_channel(int(voice_channel_id))
        await voice_channel.connect()
        await interaction.response.send_message(f"Joined {voice_channel.mention}", ephemeral=True)
    
    async def play_callback(self, interaction: discord.Interaction, sound_id: str):
        if not os.path.isfile(f"sounds/{sound_id}.mp3"):
            await interaction.response.send_message("File not found", ephemeral=True)
            return

        def after_playing(e):
            if e:
                print(f'Error: {e}')
            self.bot.disable_auto_join = False
            asyncio.run_coroutine_threadsafe(interaction.guild.voice_client.disconnect(), self.bot.loop)

        interaction.guild.voice_client.play(discord.FFmpegPCMAudio(f"sounds/{sound_id}.mp3"),
                                            after=after_playing)
        
        sound = await self.bot.get_sound(sound_id)
        await interaction.response.send_message(f"Playing {sound['name']}", ephemeral=True)
        self.done_playing.start()

    async def delete_sound_callback(self, interaction: discord.Interaction, sound_id: str):
        if not os.path.isfile(f"sounds/{sound_id}.mp3"):
            await interaction.response.send_message("File not found", ephemeral=True)
            return
        
        view = Confirm()
        await interaction.response.send_message(f"Are you sure you want to delete {self.bot.get_sound(sound_id)['name']}?", ephemeral=True, view=view)
        await view.wait()
        if not view.value:
            await interaction.followup.send("Request timed out...", ephemeral=True)
        elif view.value:
            os.remove(f"sounds/{sound_id}.mp3")
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("DELETE FROM sounds WHERE id = ?", (sound_id,))
            await interaction.followup.send(f"Deleted {self.bot.get_sound(sound_id)['name']}.", ephemeral=True)
        else:
            await interaction.followup.send("Cancelled.", ephemeral=True)
        
        for b in view.children:
            b.disabled = True

    async def preview_callback(self, interaction: discord.Interaction, sound_id: str):
        await interaction.response.send_message(f"Previewing {self.bot.get_sound(sound_id)['name']}",
                                                ephemeral=False,
                                                file=discord.File(open(f"sounds/{sound_id}.mp3", "rb"), filename=f"{sound_id}.mp3"))

    @play_group.command(name="sound", description="Play a sound")
    @app_commands.guild_only()
    async def play_sound(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            view = VCView(interaction.guild.voice_channels, self.jvc_callback, "Pick a voice channel...")
            await interaction.response.send_message(f"I'm not connected to a voice channel, pick one you want me to join.", ephemeral=True, view=view)
            return
        
        if interaction.guild.voice_client.channel.id != interaction.user.voice.channel.id:
            self.bot.disable_auto_join = True
            await interaction.guild.voice_client.disconnect()
            await interaction.user.voice.channel.connect()
        
        if interaction.guild.voice_client.is_playing():
            await interaction.response.send_message("I'm already playing something!", ephemeral=True)
            return
        
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.play_callback, "Pick a sound...")
        await interaction.response.send_message("Pick a sound you've uploaded to play!", ephemeral=False, view=file_selector)

    @app_commands.command(name="delete", description="Delete a sound")
    async def delete(self, interaction: discord.Interaction):
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.delete_sound_callback, "Pick a sound...")
        await interaction.response.send_message("Pick a sound you've uploaded to delete.", ephemeral=False, view=file_selector)
    
    @app_commands.command(name="preview", description="Preview a sound")
    @can_use()
    async def preview(self, interaction: discord.Interaction):
        user_sounds = self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.preview_callback, "Pick a sound...")
        await interaction.response.send_message("Pick a sound you've uploaded to preview.", ephemeral=True, view=file_selector)
    
    @app_commands.command(name="list", description="List all sounds")
    @can_use()
    async def list_sounds(self, interaction: discord.Interaction):
        """
        path = "sounds"
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        files = "\n".join(files)
        """
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT name, id FROM sounds")
            sounds = await cursor.fetchall()
            sounds = list(map(dict, sounds))
        
        files = "\n".join([f"{s['name']} - {s['id']}" for s in sounds])
        await interaction.response.send_message(f"```\n{files}\n```", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CustomSounds(bot))