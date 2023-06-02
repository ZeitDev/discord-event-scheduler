import time
import asyncio
from datetime import datetime

from general import config
from general import settings
from general import variables
from functions import events
from functions import stats

class BackgroundTasks():
    def __init__(self):
        self.triggered_for_day = -1

    def init(self):
        try:
            loop = asyncio.get_event_loop()
            asyncio.ensure_future(BackgroundTasks().AutomaticEventCreation())
            asyncio.ensure_future(BackgroundTasks().StartingEventNotification())

            asyncio.ensure_future(BackgroundTasks().UpdateServerCost())
            asyncio.ensure_future(BackgroundTasks().UpdateServerUptime())
            loop.run_forever()
            loop.close()
        except:
            pass

    async def AutomaticEventCreation(self):
        while True:
            if settings.event_creation:
                hour, _ = settings.event_creation_time.split(':')
                if datetime.now().hour == int(hour) and self.triggered_for_day != datetime.today().weekday():
                    self.triggered_today = datetime.today().weekday()
                    await events.Events().InitEventCreation()

            await asyncio.sleep(settings.update_interval)

    async def StartingEventNotification(self):
        while True:
            for i in range(len(variables.confirmed_events)):
                event_time = time.mktime(variables.confirmed_events[i]['event_date'].timetuple())
                
                if int(event_time - time.time()) < settings.event_finish:
                    alert_channel = variables.bot.get_channel(config.channel_notifications)

                    members_confirmed_string = ''
                    for member in variables.confirmed_events[i]['members_confirmed']:
                        members_confirmed_string += member.display_name + '\n'
                    await alert_channel.send(f"```\nUpcoming Event in 15min:\n\n{members_confirmed_string}\n```")

                    del variables.confirmed_events[i]

            await asyncio.sleep(60)

    async def UpdateServerCost(self):
        while True:
            price = 60
            cost = (price/2628000) * 3600 # 60*60*24*30.42 (durchschnittliche Tage im Monat übers Jahr)
            await stats.StatCommands().AddServerStats('server_cost', cost)

            await asyncio.sleep(3600)

    async def UpdateServerUptime(self):
        while True:
            await stats.StatCommands().AddServerStats('uptime', 900)
            await asyncio.sleep(900)