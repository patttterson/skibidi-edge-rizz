import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal, Optional

import time

import asqlite

import logging
import os
from dotenv import load_dotenv

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

        await bot.load_extension('jishaku')

        for filename in os.listdir('cogs'):
            if filename.endswith('.py') and not filename.startswith("_"):
                await bot.load_extension(f'cogs.{filename[:-3]}')
    
    async def get_settings(self, guild_id):
        if guild_id in self.settings_cache:
            return self.settings_cache[guild_id]
        await self.db.execute("SELECT prefix FROM settings WHERE guild_id = ?", (guild_id,))
        settings = self.db.fetchone()
        if not settings:
            return None
        self.settings_cache[guild_id] = settings
        return settings
    
    async def on_ready(self):
        logging.info("Connected to Discord.")

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
        embed = discord.Embed(title='An Error Occurred, and has been sent to the developers.',
                              description='', colour=discord.Colour.red())
        embed.add_field(name="Error", value=error)
        bug_message = await ctx.send(embed=embed)

        guild = bot.get_guild(1246945254972723202)
        dev = guild.get_member(843230753734918154)
        await dev.send(bug_message.jump_url)
        embed.title = f"An Error Occurred in {ctx.guild.name}."
        await dev.send(embed=embed)
        await dev.send(f"The command `{ctx.command.name}` failed to run properly.")

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