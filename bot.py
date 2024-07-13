import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal, Optional

import time

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

bot = commands.Bot(command_prefix='!',
                   intents=discord.Intents.all(),
                   activity=discord.Activity(type=discord.ActivityType.listening, name="brainrot"),
                   owner_id=843230753734918154)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    await bot.load_extension('jishaku')

    for filename in os.listdir('cogs'):
        if filename.endswith('.py') and not filename.startswith("_"):
            await bot.load_extension(f'cogs.{filename[:-3]}')

def is_owner():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == 843230753734918154
    return app_commands.check(predicate)

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