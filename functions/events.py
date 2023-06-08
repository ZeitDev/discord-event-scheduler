import time
import emoji
import asyncio
from datetime import datetime, timedelta
import nextcord

from general import config
from general import settings
from general import variables
from functions import stats

class Events():
    def __init__(self):
        self.channel = variables.bot.get_channel(config.channel_events)

    async def CreateEvent(self):
        event_date = datetime.now() + timedelta(days = settings.days_to_event)
        if not settings.event_time[event_date.weekday()]: return
        
        event_date = self.FixEventTime(event_date)
        event_title = event_date.strftime(f'{Tools().TranslateWeekday(event_date.strftime("%A"))} - %H:%M')
        
        thread = await self.channel.create_thread(name=event_title, content='\u200b')
        message = thread.last_message

        EventData = {
            'thread': thread,
            'message': message,
            'title': event_title,
            'date': event_date,
            'confirmed': False,
            'reminder_status': 0
        }

        self.InitEventLoop(EventData)

    def FixEventTime(self, event_date):
        hour, minute = settings.event_time[event_date.weekday()].split(':')
        event_date = event_date.replace(hour=int(hour), minute=int(minute), second=0)
        return event_date

    def InitEventLoop(self, EventData):
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(EventTracking().TrackThread(EventData))
        loop.run_until_complete

class EventTracking():
    def __init__(self):
        self.members = Tools().GetAllMembers()
        self.uncertain_emojinames = ['pinching_hand', 'peeposus', 'didsomeonesay', 'hmmge']
        self.spontaneous_emojinames = ['shrugging', 'shrug']
        self.canceled_emojinames = ['thumbs_down', 'bedge', 'peepoNo', 'leave']
        self.notconfirmed_emojinames = self.uncertain_emojinames + self.spontaneous_emojinames + self.canceled_emojinames

    async def TrackThread(self, EventData):
        while True:
            try:
                message = EventData['message']
                message = await message.channel.fetch_message(message.id)

                check = await Checks().CheckForDeletion(EventData)
                if check: break

                EventReactionData = await self.GetReactionData(message)
                await self.UpdateThread(EventData, EventReactionData)

                reminder_time_reached = Checks().CheckForReminderTime(EventData)
                if reminder_time_reached:
                    await self.SendReminder(EventData, EventReactionData)
                    await self.UpdatePenaltyStats(EventData, EventReactionData)
                    EventData['reminder_status'] += 1

                if not EventData['confirmed']: await Checks().CheckForEventConfirmation(EventData, EventReactionData)
                check = Checks().CheckForAllMembersVoted(EventReactionData, self.members)
                if check:
                    await self.FinishEvent(EventData, EventReactionData)
                    break

                check = Checks().CheckForEventTime(EventData)
                if check:
                    await self.UpdatePenaltyStats(EventData, EventReactionData)
                    await self.FinishEvent(EventData, EventReactionData)
                    break
                
                await asyncio.sleep(settings.update_interval)
            except Exception as e:
                print('LOOP ERROR:', e)
                await asyncio.sleep(settings.update_interval)

    async def GetReactionData(self, message):
        EventReactionData = {
            'members_reacted': [],
            'members_uncertain': [],
            'members_confirmed': [],
            'members_canceled': []
        }

        for reaction in message.reactions:
            EventReactionData['members_reacted'].extend(await reaction.users().flatten())

            if isinstance(reaction.emoji , str): emoji_name = emoji.demojize(reaction.emoji)
            else: emoji_name = reaction.emoji.name

            if not any(substring in emoji_name.lower() for substring in self.notconfirmed_emojinames):
                EventReactionData['members_confirmed'].extend(await reaction.users().flatten())

            if any(substring in emoji_name.lower() for substring in self.uncertain_emojinames):
                EventReactionData['members_uncertain'].extend(await reaction.users().flatten())

            if any(substring in emoji_name.lower() for substring in self.canceled_emojinames):
                EventReactionData['members_canceled'].extend(await reaction.users().flatten())

        EventReactionData['members_missing'] = [x for x in self.members if x not in EventReactionData['members_reacted']]

        return EventReactionData

    async def SendEventConfirmation(self, EventData, EventReactionData):
        guild = variables.bot.get_guild(config.server_id)

        title = 'FlexQ'
        event_entity = nextcord.ScheduledEventEntityType.external
        event_metadata = nextcord.EntityMetadata(location='Summoners Rift')
        event_start_time = EventData['date'] - timedelta(hours = 2)
        event_end_time = EventData['date'] 
        event_description = ''
        for member in EventReactionData['members_confirmed']:
            event_description += member.display_name + ', '

        await guild.create_scheduled_event(name=title, entity_type=event_entity ,start_time=event_start_time, metadata=event_metadata, end_time=event_end_time, description=event_description[:-2])
    
    async def SendReminder(self, EventData, EventReactionData):
        event_title = EventData['title']
        channel = EventData['message'].channel
        
        if EventData['reminder_status'] == 0:
            members = EventReactionData['members_missing']
            message_content = f'Missing vote on event: **{event_title}** in {channel.mention}'
        elif EventData['reminder_status'] == 1:
            members = EventReactionData['members_missing'] + EventReactionData['members_uncertain']
            message_content = f'Missing vote or remaining 🤏 on event: **{event_title}** in {channel.mention}'

        for member in members:
            if not member.bot: await member.send(message_content)
            await asyncio.sleep(1)

    async def UpdatePenaltyStats(self, EventData, EventReactionData):
        status = EventData['reminder_status']
        if status == 0: members = EventReactionData['members_missing']
        elif status in [1, 2]: members = EventReactionData['members_missing'] + EventReactionData['members_uncertain']

        stats.StatCommands().AddPenaltyToLeaderboard(members)

    async def UpdateThread(self, EventData, EventReactionData):
        message = EventData['message']
        emojis = [str(reaction.emoji) for reaction in message.reactions]
        num_members = len(self.members)
        num_members_missing = len(EventReactionData['members_missing'])

        reminder_status = EventData['reminder_status']
        reminder_date = (datetime.now() + Tools().TimeToNextReminder(EventData)).strftime('%d.%m. - %H:%M')
        if reminder_status == 0: reminder_string = f'next reminder: {reminder_date}'
        elif reminder_status == 1: reminder_string = f'next reminder: {reminder_date}'
        elif reminder_status == 2: reminder_string = 'no reminder left'

        content = f"{('  ').join(emojis)}\n| missing votes: {num_members_missing}/{num_members} | {reminder_string} | Event: {EventData['date'].strftime('%d.%m.')}"
        await message.edit(content=content)        

    async def FinishEvent(self, EventData, EventReactionData):
        members_confirmed = EventReactionData['members_confirmed']
        members_canceled = EventReactionData['members_canceled']
        members_missing = EventReactionData['members_missing']
        members_uncertain = EventReactionData['members_uncertain']

        state_emoji = '✅' if len(members_confirmed) >= 5 else '❌'
        await EventData['thread'].edit(name = f'{state_emoji} {EventData["title"]}')

        content = f'{state_emoji} | Zusagen: {len(members_confirmed)}, Unsicher: {len(members_uncertain)}, Absagen: {len(members_canceled)}, Keine Antwort: {len(members_missing)}'
        await EventData['message'].edit(content=content)

        stats.StatCommands().AddConfirmedToLeaderboard(members_confirmed)

class Checks():
    async def CheckForDeletion(self, EventData):
        message = EventData['message']
        thread = EventData['thread']
        for reaction in message.reactions:
            if reaction.emoji == '❌':
                await message.channel.send('Event canceled! Thread deleting itself in 15 seconds.')
                await thread.edit(name = 'DELETED EVENT')
                await asyncio.sleep(15)
                await thread.delete()
                return True

    async def CheckForEventConfirmation(self, EventData, EventReactionData):
        if len(EventReactionData['members_confirmed']) >= 5:
            ConfirmedEventData = {'event_date': EventData['date'], 'members_confirmed': EventReactionData['members_confirmed']}
            variables.confirmed_events.append(ConfirmedEventData)

            EventData['confirmed'] = True
            await EventTracking().SendEventConfirmation(EventData, EventReactionData)

    def CheckForReminderTime(self, EventData):
        reminder_delta = Tools().TimeToNextReminder(EventData)
        if EventData['reminder_status'] == 2: return False
        if reminder_delta.total_seconds() <= 0: return True

    def CheckForEventTime(self, EventData):
        delta_time = EventData['date'] - datetime.now()
        if delta_time.total_seconds() <= settings.event_finish: return True

    def CheckForAllMembersVoted(self, EventReactionData, members):
        all_voted = len(EventReactionData['members_reacted']) == len(members)
        no_uncertains = len(EventReactionData['members_uncertain']) == 0
        return all_voted and no_uncertains

class Tools():
    def GetAllMembers(self):
        guild = variables.bot.get_guild(config.server_id)
        for role in guild.roles:
            if role.id == config.role_reminder:
                return role.members
            
    def TranslateWeekday(self, weekday):
        switcher = {
            'Monday': 'Montag',
            'Tuesday': 'Dienstag',
            'Wednesday': 'Mittwoch',
            'Thursday': 'Donnerstag',
            'Friday': 'Freitag',
            'Saturday': 'Samstag',
            'Sunday': 'Sonntag',
        }
        return switcher.get(weekday, 'Invalid Weekday')

    def TimeToNextReminder(self, EventData):
        status = EventData['reminder_status']
        if status == 0: reminder_delta = timedelta(days=settings.days_first_reminder)
        elif status == 1: reminder_delta = timedelta(days=settings.days_second_reminder)

        hour, minute = settings.reminder_time.split(':')
        reminder_date = (EventData['date'] - reminder_delta).replace(hour=int(hour), minute=int(minute), second=0)
        delta_time = reminder_date - datetime.now()
        return delta_time