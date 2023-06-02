import os
import time
import nextcord

from nextcord.ext import commands

from general import config
from general import settings
from general import variables

# Set timezone
os.environ['TZ'] = 'UTC-2' # Winter Time: UTC-1, Summer Time: UTC-2
if not settings.is_debug: time.tzset()

# Initialize bot
description = '''Bot for scheduling group events with reactions and reminders.'''
intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or(settings.prefix), description=description, intents=intents, case_insensitive=True)

# Load commands
print('> Loading Commands')
for filename in os.listdir('./commands'):
    if filename.endswith('.py'):
        bot.load_extension(f'commands.{os.path.splitext(filename)[0]}')
        print(f'{os.path.splitext(filename)[0]} loaded')
print()

# Start bot
@bot.event
async def on_ready():
    print(f'> Starting nextcord Bot = {bot.user}')
    print('-' * 45)
    await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=f'{settings.prefix}help'))
    if variables.first_startup:
        # TODO: _statistics.Stats().CheckForExisitingStatsFile()
        # TODO: _statistics.Stats().ResetUptime()
        # TODO: _backgroundTasks.BackgroundTasks().initialize()

        variables.first_startup = False

bot.run(config.bot_token)