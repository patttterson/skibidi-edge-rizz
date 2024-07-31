import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal, Optional

import time

import asqlite

import logging
import os
from dotenv import load_dotenv

import datetime

import subprocess

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

async def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or("!")(bot, message)
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT prefix FROM settings WHERE guild_id = ?", (message.guild.id,))
        prefix = await cursor.fetchone()
        return commands.when_mentioned_or(prefix[0] if prefix else "!")(bot, message)

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def setup_hook(self):
        logging.info(f'Logged in as {bot.user.name}.')

        self.db = await asqlite.connect("skibidi.db")
        self.settings_cache = {}
        self.sound_cache = {} # key is sound's id
        self.user_cache = {} # same as sound cache but key is user_id

        self.idling = {} # guild_id: true or false

        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM settings")
            settings = await cursor.fetchall()
            settings = list(map(dict, settings))
            for s in settings:
                self.settings_cache[s.pop('guild_id')] = s
        
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM sounds")
            sounds = await cursor.fetchall()
            sounds = list(map(dict, sounds))
            for s in sounds:
                self.sound_cache[s.pop('id')] = s

        await bot.load_extension('jishaku')

        for filename in os.listdir('cogs'):
            if filename.endswith('.py') and not filename.startswith("_"):
                await bot.load_extension(f'cogs.{filename[:-3]}')
    
    async def get_settings(self, guild_id):
        if not self.settings_cache.get(guild_id, False):
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM settings WHERE guild_id = ?", (guild_id,))
                settings = dict(await cursor.fetchone())
                if not settings:
                    return None
                settings["rejoin"] = True
                self.settings_cache[settings.pop('guild_id')] = settings

        return self.settings_cache[guild_id]
    
    async def get_sounds(self, user_id):
        if not self.user_cache.get(user_id, False):
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM sounds WHERE author_id = ?", (user_id,))
                sounds = await cursor.fetchall()
                if not sounds:
                    return None
                try:
                    self.user_cache[user_id]
                except KeyError:
                    self.user_cache[user_id] = {}
                for s in sounds:
                    so = list(s)
                    self.user_cache[user_id][so[0]] = so[2]

        return self.user_cache[user_id]

    async def get_sound(self, sound_id: int):
        if not self.sound_cache.get(sound_id, False):
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM sounds WHERE id = ?", (sound_id,))
                sound = dict(await cursor.fetchone())
                if not sound:
                    return None
                self.sound_cache[sound.pop('id')] = sound

        print(self.sound_cache)
        return self.sound_cache[int(sound_id)]
    
    async def on_ready(self):
        logging.info("Connected to Discord.")

        if os.path.exists("./restart_message_id.txt"):
            with open("./restart_message_id.txt", "r") as file:
                message_id, channel_id, restart_time = list(map(int, file.read().strip().split(" ")))
        
            restart_time = datetime.datetime.timestamp(datetime.datetime.now()) - restart_time
        
            restart_channel = await self.fetch_channel(channel_id)
            restart_message = await restart_channel.fetch_message(message_id)

            embed = discord.Embed(title="Finished restarting.", description=f"Restarting took {restart_time} seconds.", color=discord.Colour.green())
            await restart_message.edit(embed=embed)

            os.remove("./restart_message_id.txt")

bot = Bot(command_prefix=get_prefix,
                   intents=discord.Intents.all(),
                   activity=discord.Activity(type=discord.ActivityType.listening, name="brainrot"),
                   owner_id=843230753734918154)

def is_owner():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == 843230753734918154
    return app_commands.check(predicate)

@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
        return
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid Command Used.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"You are missing permissions to run this command.\n"
                       f"If you think this is a mistake, please contact {bot.application_info().owner}.")
    elif isinstance(error, commands.ExtensionNotLoaded):
        await ctx.send("The extension(s) you are trying to unload are currently not loaded.")
    elif isinstance(error, commands.ExtensionAlreadyLoaded):
        await ctx.send("The extension(s) you are trying to load are currently already loaded.")
    elif isinstance(error, commands.ExtensionNotFound):
        await ctx.send("The extension you are trying to load does not exist.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("The command you are trying to call can only be called in a server, not a DM.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("nope lmao")
    else:
        embed = discord.Embed(title='An Error Occurred.',
                              description='', colour=discord.Colour.red())
        embed.add_field(name="Error", value=error)
        bug_message = await ctx.send(embed=embed)

        dev = bot.get_user(843230753734918154)
        await dev.send(bug_message.jump_url)
        embed.title = f"An Error Occurred in {ctx.guild.name}."
        await dev.send(embed=embed)
        await dev.send(f"The command `{ctx.command.name}` failed to run properly.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(error)
    print("skibidi.")
    if hasattr(interaction.command, 'on_error'):
        return
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("Invalid Command Used.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.followup.send(f"You are missing permissions to run this command.\n"
                       f"If you think this is a mistake, please contact {bot.application_info().owner}.", ephemeral=True)
    elif isinstance(error, app_commands.ExtensionNotLoaded):
        await interaction.response.send_message("The extension(s) you are trying to unload are currently not loaded.", ephemeral=True)
    elif isinstance(error, app_commands.ExtensionAlreadyLoaded):
        await interaction.response.send_message("The extension(s) you are trying to load are currently already loaded.", ephemeral=True)
    elif isinstance(error, app_commands.ExtensionNotFound):
        await interaction.response.send_message("The extension you are trying to load does not exist.", ephemeral=True)
    elif isinstance(error, app_commands.NoPrivateMessage):
        await interaction.response.send_message("The command you are trying to call can only be called in a server, not a DM.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("nope lmao", ephemeral=True)
    else:
        embed = discord.Embed(title='An Error Occurred.',
                              description='', colour=discord.Colour.red())
        embed.add_field(name="Error", value=error)
        bug_message = await interaction.response.send_message(embed=embed)

        dev = bot.get_user(843230753734918154)
        await dev.send(bug_message.jump_url)
        embed.title = f"An Error Occurred in {interaction.guild.name}."
        await dev.send(embed=embed)
        await dev.send(f"The command `{interaction.command.name}` failed to run properly.")

@bot.command(hidden=True)
@commands.is_owner()
async def restart(ctx: commands.Context):
    embed = discord.Embed(title="Restarting...", description="(i really hope this wasnt a typo) [i was too lazy to code a confirmation prompt]", color=discord.Colour.red())
    
    shutdown_message = await ctx.send(embed=embed)

    with open("./restart_message_id.txt", "w") as file:
        file.write(f"{shutdown_message.id} {ctx.channel.id} {int(datetime.datetime.timestamp(datetime.datetime.now()))}")

    subprocess.Popen(['./restart_bot.sh'])

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, extension):
    loaded_cogs = ''
    if extension != '~':
        await bot.load_extension(extension)
        loaded_cogs += f'\U000023eb {extension}'
    else:
        for filename in os.listdir('cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                loaded_cogs += f'\U000023eb cogs.{filename[:-3]}\n\n'
        loaded_cogs = loaded_cogs[:-2]
    await ctx.send(loaded_cogs)


@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, extension):
    unloaded_cogs = ''
    if extension != '~':
        await bot.unload_extension(extension)
        unloaded_cogs += f'\U000023ec {extension}'
    else:
        for filename in os.listdir('cogs'):
            if filename.endswith('.py'):
                await bot.unload_extension(f'cogs.{filename[:-3]}')
                unloaded_cogs += f'\U000023ec cogs.{filename[:-3]}\n\n'
        unloaded_cogs = unloaded_cogs[:-2]
    await ctx.send(unloaded_cogs)


@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, extension="~"):
    reload_start = time.time()
    reloaded_cogs = ''
    if extension != '~':
        await bot.unload_extension(extension)
        await bot.load_extension(extension)
        reloaded_cogs += f'\U0001f502 {extension}'
    else:
        for filename in os.listdir('cogs'):
            if filename.endswith('.py') and not filename.startswith("_"):
                try:
                    await bot.unload_extension(f'cogs.{filename[:-3]}')
                except commands.ExtensionNotLoaded:
                    pass
                await bot.load_extension(f'cogs.{filename[:-3]}')
                reloaded_cogs += f'\U0001f501 cogs.{filename[:-3]}\n\n'
        reloaded_cogs = reloaded_cogs[:-2]
    reload_end = time.time()
    await ctx.send(f'{reloaded_cogs}\nTook {reload_end - reload_start} to reload all')

os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))