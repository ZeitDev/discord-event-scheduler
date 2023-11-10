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
        self.last_triggered_day = -1
        self.last_triggered_day_report = -1
        self.channel_notifications = variables.bot.get_channel(config.channel_notifications)

    def init(self):
        try:
            loop = asyncio.get_event_loop()
            asyncio.ensure_future(BackgroundTasks().AutomaticEventCreation())
            asyncio.ensure_future(BackgroundTasks().AutomaticReport())
            asyncio.ensure_future(BackgroundTasks().StartingEventNotification())

            asyncio.ensure_future(BackgroundTasks().UpdateServerCost())
            asyncio.ensure_future(BackgroundTasks().UpdateServerUptime())

            asyncio.ensure_future(BackgroundTasks().PrintInfoMessages())
            
            loop.run_forever()
            loop.close()
        except:
            pass

    async def AutomaticEventCreation(self):
        while True:
            if settings.event_creation:
                hour, _ = settings.event_creation_time.split(':')
                current_weekday = datetime.today().weekday()
                if datetime.now().hour == int(hour) and self.last_triggered_day != current_weekday:
                    self.last_triggered_day = current_weekday
                    await asyncio.sleep(current_weekday*30)
                    await events.Events().CreateEvent()

            await asyncio.sleep(settings.update_interval)

    async def AutomaticReport(self):
        while True:
            if datetime.today().weekday() == 5 and datetime.now().hour == 13 and self.last_triggered_day_report != datetime.today().weekday():
                self.last_triggered_day_report = datetime.today().weekday()
                embed = stats.Stats().CreateEmbed()
                await self.channel_notifications.send('Weekly Stat Report')
                await self.channel_notifications.send(embed=embed)

            await asyncio.sleep(settings.update_interval)

    async def StartingEventNotification(self):
        while True:
            for i in range(len(variables.confirmed_events)):
                event_time = time.mktime(variables.confirmed_events[i]['event_date'].timetuple())
                
                if int(event_time - time.time()) < settings.event_finish:
                    members_confirmed_string = ''
                    for member in variables.confirmed_events[i]['members_confirmed']:
                        members_confirmed_string += member.display_name + '\n'
                    await self.channel_notifications.send(f"```\nUpcoming Event in 15min:\n\n{members_confirmed_string}\n```")

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
            await stats.StatCommands().AddServerStats('uptime', 3600)
            await asyncio.sleep(3600)

    async def PrintInfoMessages(self):
        while True:
            print(f'Active Events: {variables.active_events}')
            await asyncio.sleep(86400)