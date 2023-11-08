import os
import time
import nextcord

from nextcord.ext import commands

from general import config
from general import settings
from general import variables
from functions import stats
from functions import events
from functions import background_tasks

# Set timezone
os.environ['TZ'] = settings.time_zone
if not settings.debug: time.tzset()

# Initialize bot
description = '''Bot for scheduling group events with reactions and reminders.'''
intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or(settings.prefix), description=description, intents=intents, case_insensitive=True)
variables.bot = bot

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
    await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=f'r1ct loosing'))
    if variables.first_startup:
        events.Events().CheckForSavedEvents()
        stats.Stats().CheckForExisitingStatsFile()
        stats.Stats().ResetUptime()
        background_tasks.BackgroundTasks().init()
        variables.first_startup = False

bot.run(config.bot_token)