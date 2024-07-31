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
    
    play_group = app_commands.Group(name="play", description="Play commands")  

    @app_commands.command(name="upload", description="Upload a .mp3 file to add to the bot.")
    async def upload(self, interaction: discord.Interaction, *, sound: discord.Attachment, name: Optional[str] = None):
        if sound.content_type != "audio/mpeg":
            await interaction.response.send_message("File must be a .mp3 file", ephemeral=True)
            return
        
        if name == None:
            name = sound.filename[:-4]
        
        sound_id = next(self.bot.snowflake_gen)
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT INTO sounds (id, author_id, name) VALUES (?, ?, ?)", (sound_id, interaction.user.id, name))
            await self.bot.db.commit()
        
        user_sounds = self.bot.user_cache.get(interaction.user.id, False)
        if user_sounds:
            self.bot.user_cache[interaction.user.id][sound_id] = 'name'

        file = await sound.to_file(filename=f"{sound_id}.mp3")

        with open(f"sounds/{sound_id}.mp3", "wb") as f:
            f.write(file.fp.read())

        embed = discord.Embed(title="Sound uploaded", description=f"Name: {name}\nID: {sound_id}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rename", description="Rename one of your sounds.")
    async def rename(self, interaction: discord.Interaction):
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        
        file_selector = SoundView(user_sounds, self.rename_callback, "Pick a sound...", skip=True)
        await interaction.response.send_message("Pick a sound you've uploaded to rename.", ephemeral=True, view=file_selector)

    async def rename_callback(self, interaction: discord.Interaction, sound_id: str, view: discord.ui.View):
        await interaction.response.send_modal(RenameInput(self.rename_modal_callback, sound_id))
        message = interaction.message
        await interaction.followup.edit_message(message.id, view=view)

    async def rename_modal_callback(self, interaction: discord.Interaction, name: str, sound_id: str):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE sounds SET name = ? WHERE id = ?", (name, int(sound_id),))
        
        sound = self.bot.sound_cache.get(int(sound_id), False)
        if sound:
            self.bot.sound_cache[int(sound_id)]["name"] = name
        
        embed = discord.Embed(title="Success!", description="Successfully renamed your sound.", color=discord.Colour.green())
        await interaction.followup.send(embed=embed)
    
    async def play_callback(self, interaction: discord.Interaction, sound_id: str, view: discord.ui.View):
        print("AHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
        await interaction.response.edit_message(view=view)

        if not os.path.isfile(f"sounds/{sound_id}.mp3"):
            await interaction.followup.send("File not found", ephemeral=True)
            return
        
        if interaction.guild.voice_client.channel.id != interaction.user.voice.channel.id and self.bot.idling[interaction.guild.id]:
            await interaction.guild.voice_client.disconnect()
            await interaction.user.voice.channel.connect()
        
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()

        self.bot.idling[interaction.guild.id] = False

        sound = await self.bot.get_sound(sound_id)
        await interaction.followup.send(f"Playing {sound['name']}", ephemeral=True)
        
        def after_playing(e):
            if e:
                print(f'Error: {e}')
            self.bot.idling[interaction.guild.id] = True
            asyncio.run_coroutine_threadsafe(interaction.guild.voice_client.disconnect(), self.bot.loop)

        interaction.guild.voice_client.play(discord.FFmpegPCMAudio(f"sounds/{sound_id}.mp3"),
                                            after=after_playing)

    async def delete_sound_callback(self, interaction: discord.Interaction, sound_id: str, view: discord.ui.View):
        await interaction.response.edit_message(view=view)

        if not os.path.isfile(f"sounds/{sound_id}.mp3"):
            await interaction.followup.send("File not found", ephemeral=True)
            return
        
        sound = await self.bot.get_sound(sound_id)

        embed = discord.Embed(title=f"Deleting {sound['name']}.", description=f"Are you sure you want to delete {sound['name']}? This action is irreversible.", color=discord.Colour.red())
        
        view = Confirm()
        await interaction.followup.send(embed=embed, ephemeral=True, view=view)
        await view.wait()
        if not view.value:
            await interaction.followup.send("Request timed out...", ephemeral=True)
        elif view.value:
            os.remove(f"sounds/{sound_id}.mp3")
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("DELETE FROM sounds WHERE id = ?", (sound_id,))
            
            embed = discord.Embed(title=f"Deleted {sound['name']}.", description="<:cold:1267581272969187390>")

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("Cancelled.", ephemeral=True)
        
        for b in view.children:
            b.disabled = True

    async def preview_callback(self, interaction: discord.Interaction, sound_id: str, view: discord.ui.View):
        sound = await self.bot.get_sound(sound_id)
        await interaction.response.edit_message(view=view)
        await interaction.followup.send(f"Previewing {sound['name']}",
                                                ephemeral=False,
                                                file=discord.File(open(f"sounds/{sound_id}.mp3", "rb"), filename=f"{sound['name']}.mp3"))

    @play_group.command(name="sound", description="Play a sound")
    @app_commands.guild_only()
    async def play_sound(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("Join a voice channel first!", ephemeral=True)
            return

        if self.bot.idling.get(interaction.guild.id, "empty") == "empty":
            self.bot.idling[interaction.guild.id] = True
        elif not self.bot.idling.get(interaction.guild.id):
            await interaction.response.send_message("I'm currently playing something, please try again later.", ephemeral=True)
            return

        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.play_callback, "Pick a sound...", skip=True)
        await interaction.response.send_message("Pick a sound you've uploaded to play!", ephemeral=True, view=file_selector)

    @app_commands.command(name="delete", description="Delete a sound")
    async def delete(self, interaction: discord.Interaction):
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.delete_sound_callback, "Pick a sound...", skip=True)
        await interaction.response.send_message("Pick a sound you've uploaded to delete.", ephemeral=True, view=file_selector)
    
    @app_commands.command(name="preview", description="Preview a sound")
    async def preview(self, interaction: discord.Interaction):
        user_sounds = await self.bot.get_sounds(interaction.user.id)
        if not user_sounds:
            await interaction.response.send_message("You haven't uploaded any sounds yet! Upload some with </upload:1262324370353815597>", ephemeral=True)
            return
        file_selector = SoundView(user_sounds, self.preview_callback, "Pick a sound...", skip=True)
        dropdown_msg = await interaction.response.send_message("Pick a sound you've uploaded to preview.", ephemeral=True, view=file_selector)
    
    @app_commands.command(name="list", description="List all sounds")
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