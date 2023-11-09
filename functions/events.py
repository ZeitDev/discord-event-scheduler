import os
import uuid
import pickle
import time
import emoji
import random
import asyncio
import traceback
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
        event_date = datetime.now() + timedelta(days = settings.days_to_event) #DEBUG: datetime.now() + timedelta(minutes=2)
        if not settings.event_time[event_date.weekday()]: return
        
        event_date = Tools().FixEventTime(event_date)
        event_title = event_date.strftime(f'{Tools().TranslateWeekday(event_date.strftime("%A"))} - %H:%M')
        
        thread = await self.channel.create_thread(name=event_title, content='\u200b')

        EventData = {
            'thread_ID': thread.id,
            'title': event_title,
            'date': event_date,
            'confirmed': False,
            'reminder_status': 0
        }

        uident = uuid.uuid4().hex
        Tools().PickleHandler('save', uident, EventData)

        self.InitEventLoop(uident)

    def InitEventLoop(self, uident):
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(EventTracking().TrackThread(uident))
        loop.run_until_complete

    def CheckForSavedEvents(self):
        if not os.path.exists(os.path.join('data', 'events.pickle')):
            with open(os.path.join('data', 'events.pickle'), 'wb') as f:
                pickle.dump({}, f)
                
        events = Tools().PickleHandler('load_all')

        for uident, EventData in events.items():
            thread = Events().channel.get_thread(EventData['thread_ID'])
            if not thread:
                Tools().PickleHandler('delete', uident)
                continue

            if EventData['date'] > datetime.now():
                print(f'INFO: loaded event "{EventData["title"]}"')
                self.InitEventLoop(uident)
            else: Tools().PickleHandler('delete', uident)
            
            time.sleep(1)

class EventTracking():
    def __init__(self):
        self.members = Tools().GetAllMembers()
        self.uncertain_emojinames = ['pinching_hand', 'peeposus', 'didsomeonesay', 'hmmge']
        self.spontaneous_emojinames = ['shrugging', 'shrug']
        self.canceled_emojinames = ['thumbs_down', 'bedge', 'peepoNo', 'leave']
        self.notconfirmed_emojinames = self.uncertain_emojinames + self.spontaneous_emojinames + self.canceled_emojinames

    async def TrackThread(self, uident):
        while True:
            try:
                if 'EventData' not in locals():
                    EventData = Tools().PickleHandler('load', uident)
                    thread = Events().channel.get_thread(EventData['thread_ID'])

                initial_EventData = EventData
                
                message = await thread.fetch_message(thread.last_message_id)

                check_deletion = await Checks().CheckForDeletion(thread, message)
                if check_deletion: break

                EventReactionData = await self.GetReactionData(message)
                await self.UpdateThread(EventData, EventReactionData, message)

                reminder_time_reached = Checks().CheckForReminderTime(EventData)
                if reminder_time_reached:
                    await self.SendReminder(EventData, EventReactionData)
                    await self.UpdatePenaltyStats(EventData, EventReactionData)
                    EventData['reminder_status'] += 1

                if not EventData['confirmed']: await Checks().CheckForEventConfirmation(EventData, EventReactionData)

                check_votes = Checks().CheckForMemberVotes(EventReactionData, self.members)
                check_time = Checks().CheckForEventTime(EventData)

                if check_votes or check_time:
                    if check_time: await self.UpdatePenaltyStats(EventData, EventReactionData)
                    await self.FinishEvent(EventData, EventReactionData, thread, message)
                    Tools().PickleHandler('delete', uident)
                    break
                
                if EventData != initial_EventData: Tools().PickleHandler('save', uident, EventData)
            
            except Exception as e:
                print('LOOP ERROR:', e)
                traceback.print_exc()

            await asyncio.sleep(settings.event_update_interval)

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
        event_start_time = EventData['date'] - timedelta(hours = int(settings.time_zone[-1]))
        event_end_time = EventData['date'] 
        event_description = ''
        for member in EventReactionData['members_confirmed']:
            event_description += member.display_name + ', '

        await guild.create_scheduled_event(name=title, entity_type=event_entity, start_time=event_start_time, metadata=event_metadata, end_time=event_end_time, description=event_description[:-2])
    
    async def SendReminder(self, EventData, EventReactionData):
        event_title = EventData['title']
        channel_notifications = variables.bot.get_channel(config.channel_notifications)
        
        if EventData['reminder_status'] == 0:
            members = EventReactionData['members_missing']
        elif EventData['reminder_status'] == 1:
            members = EventReactionData['members_missing'] + EventReactionData['members_uncertain']

        for member in members:
            message = Tools().GetReminderMessage(member, event_title)
            if not member.bot: await channel_notifications.send(message)
            await asyncio.sleep(10)

    async def UpdatePenaltyStats(self, EventData, EventReactionData):
        status = EventData['reminder_status']
        if status == 0: members = EventReactionData['members_missing']
        elif status in [1, 2]: members = EventReactionData['members_missing'] + EventReactionData['members_uncertain']

        stats.StatCommands().AddPenaltyToLeaderboard(members)

    async def UpdateThread(self, EventData, EventReactionData, message):
        num_members = len(self.members)
        num_members_confirmed = len(EventReactionData['members_confirmed'])
        num_members_missing = len(EventReactionData['members_missing'])

        reminder_status = EventData['reminder_status']
        reminder_date = (datetime.now() + Tools().TimeToNextReminder(EventData)).strftime('%d.%m. - %H:%M')
        if reminder_status == 0: reminder_string = f'next reminder (missings): {reminder_date}'
        elif reminder_status == 1: reminder_string = f'next reminder (missings + uncertains): {reminder_date}'
        elif reminder_status == 2: reminder_string = 'no reminder left'

        content = f"confirmed: {num_members_confirmed} | missing votes: {num_members_missing}/{num_members} | {reminder_string} | event date: {EventData['date'].strftime('%d.%m.')} |"
        await message.edit(content=content)

    async def FinishEvent(self, EventData, EventReactionData, thread, message):
        members_confirmed = EventReactionData['members_confirmed']
        members_canceled = EventReactionData['members_canceled']
        members_missing = EventReactionData['members_missing']
        members_uncertain = EventReactionData['members_uncertain']

        state_emoji = '✅' if len(members_confirmed) >= 5 else '❌'
        await thread.edit(name = f'{state_emoji} {EventData["title"]}')

        content = f'confirmed: {len(members_confirmed)}, uncertain: {len(members_uncertain)}, canceled: {len(members_canceled)}, no answer: {len(members_missing)}'
        await message.edit(content=content)

        stats.StatCommands().AddConfirmedToLeaderboard(members_confirmed)

class Checks():
    async def CheckForDeletion(self, thread, message):
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
        reminder_time_reached = reminder_delta.total_seconds() <= 0 and not EventData['reminder_status'] == 2
        return reminder_time_reached

    def CheckForEventTime(self, EventData):
        delta_time = EventData['date'] - datetime.now()
        if delta_time.total_seconds() <= settings.event_finish: return True

    def CheckForMemberVotes(self, EventReactionData, members):
        all_voted = len(EventReactionData['members_reacted']) == len(members)
        no_uncertains = len(EventReactionData['members_uncertain']) == 0

        confirm_not_possible = (len(members)-len(EventReactionData['members_canceled'])) < 5

        return (all_voted and no_uncertains) or confirm_not_possible

class Tools():
    def FixEventTime(self, event_date):
        hour, minute = settings.event_time[event_date.weekday()].split(':')
        event_date = event_date.replace(hour=int(hour), minute=int(minute), second=0)
        return event_date

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
        else: reminder_delta = timedelta(0)

        hour, minute = settings.reminder_time.split(':')
        reminder_date = (EventData['date'] - reminder_delta).replace(hour=int(hour), minute=int(minute), second=0)
        delta_time = reminder_date - datetime.now()
        return delta_time
    
    def PickleHandler(self, command, uident=None, event=None):
        events_path = os.path.join('data', 'events.pickle')

        if command == 'save':
            events = self.LoadPickle()
            with open(events_path, 'wb') as f:
                events[uident] = event
                pickle.dump(events, f)

        elif command == 'load':
            with open(events_path, 'rb') as f:
                events = pickle.load(f)
                return events[uident]
            
        elif command == 'load_all':
            with open(events_path, 'rb') as f:
                events = pickle.load(f)
                return events
            
        elif command == 'delete':
            events = self.LoadPickle()
            with open(events_path, 'wb') as f:
                del events[uident]
                if len(events) != 0:
                    pickle.dump(events, f)
                else:
                    pickle.dump({}, f)
                
    def LoadPickle(self):
        with open(os.path.join('data', 'events.pickle'), 'rb') as f:
            return pickle.load(f)

    def GetReminderMessage(self, member, event_title):
        messages = [
            f'Hey {member.mention}, verbringst du deine Zeit etwa mit Geheimagentenmissionen, anstatt auf den Termin "{event_title}" zu reagieren?',
            f'Na, {member.mention}, wir haben uns Sorgen gemacht, du steckst vielleicht in einem Zeittunnel fest und verpasst deshalb den Termin "{event_title}"!',
            f'Könnte es sein, dass du dich gerade auf einer Weltraumreise befindest, {member.mention}? Du hast ja offensichtlich vergessen, auf den Termin "{event_title}" zu reagieren!',
            f'{member.mention}, wenn du ein Superheld wärst, wäre "Vergesslicher Man" sicher dein Spitzname! Du hast den Termin "{event_title}" verpasst!',
            f'Hallo {member.mention}, wir haben uns gefragt, ob du vielleicht in einem Paralleluniversum steckst, wo du den Termin "{event_title}" bereits bestätigt hast?',
            f'Oh, {member.mention}, wir dachten, du hättest eine Mission, um die verlorenen Socken zu retten, deshalb konntest du nicht auf den Termin "{event_title}" antworten!',
            f'Hey {member.mention}, hast du vergessen, dass du kein Geheimagent bist? Du musst nicht so undercover sein, um auf den Termin "{event_title}" zu reagieren!',
            f'{member.mention}, vielleicht solltest du dein Hologramm schicken, um für dich auf den Termin "{event_title}" zu reagieren. Es wäre weniger vergesslich!',
            f'Glaub uns, {member.mention}, wir alle wünschten, wir könnten so coole Ausreden finden wie du, um nicht auf den Termin "{event_title}" zu reagieren!',
            f'Hey {member.mention}, haben die Aliens dich etwa entführt und dein Einverständnis zum Termin "{event_title}" gelöscht? Sollten wir sie anrufen?',
            f'Hey {member.mention}, versteckst du dich unter einem Stein oder was? Du hast vergessen auf den Termin "{event_title}" zu reagieren!',
            f'Komm schon, {member.mention}! Der Termin "{event_title}" wartet auf dich. Du bist nicht wirklich so beschäftigt, oder?',
            f'Hast du dich verlaufen, {member.mention}? Der Termin "{event_title}" ist hier und vermisst deine Aufmerksamkeit!',
            f'{member.mention}, du bist der Superstar! Aber, hey, vergiss nicht, den Termin "{event_title}" zu checken, sonst verpassen wir dich!',
            f'Ist es schon wieder Zeit für ein Nickerchen, {member.mention}? Du hast den Termin "{event_title}" verpennt!',
            f'Hallo? Jemand zuhause, {member.mention}? Der Termin "{event_title}" ruft nach dir, und wir alle warten gespannt!',
            f'Oh, {member.mention}, du bist unser Mysterium! Der Termin "{event_title}" will mit dir feiern, aber du bist unauffindbar!',
            f'Hätte ich einen Keks, wenn du endlich auf den Termin "{event_title}" reagierst, {member.mention}? Ich warte mit dem Keks in der Hand!',
            f'Glaub mir, {member.mention}, der Termin "{event_title}" ist wie eine Eintrittskarte zum Spaß. Du willst doch dabei sein, oder?',
            f'Hey, {member.mention}, bist du im Winterschlaf oder was? Verpasst du etwa den grandiosen Termin "{event_title}"?',
            f'Hallo Schlafmütze {member.mention}, du erinnerst mich an einen Bären, der den Termin "{event_title}" verpennt. Gähn!',
            f'Ey, {member.mention}, schon mal was von einem Wecker gehört? Der Termin "{event_title}" wartet auf deine Reaktion, du Langschläfer!',
            f'Hey, {member.mention}, unsere Geduld ist endlich. Der Termin "{event_title}" vermisst dich. Wo steckst du?',
            f'Ist dein Name Houdini, {member.mention}? Du verschwindest jedes Mal, wenn es um den Termin "{event_title}" geht!',
            f'{member.mention}, vielleicht sollten wir dir eine Eule schenken, damit du den Termin "{event_title}" nicht wieder verpasst. Eulen sind nachtaktiv, genau wie du!',
            f'Glaub mir, {member.mention}, wenn der Termin "{event_title}" ein Leckerli wäre, hättest du längst reagiert. Wo ist dein Appetit geblieben?',
            f'Du bist so geheimnisvoll, {member.mention}, dass selbst Sherlock Holmes den Termin "{event_title}" nicht finden kann, wenn du nicht reagierst!',
            f'Hey, {member.mention}, versteckt sich dein Rechner vor dir, dass du den Termin "{event_title}" nicht finden kannst?',
            f'{member.mention}, es gibt Gerüchte, dass dein Terminkalender ein Eigenleben führt und gegen dich arbeitet. Der Termin "{event_title}" wartet!',
            f'Anscheinend haben wir Sherlock Holmes persönlich in unserer Mitte - {member.mention}, du hast den Termin "{event_title}" fast schon enttarnt!',
            f'{member.mention}, der Termin "{event_title}" ist wie ein verlorenes Schaf und sucht nach dir. Kannst du ihm den Weg zeigen?',
            f'Hallo, {member.mention}! Dein Versteckspiel mit dem Termin "{event_title}" ist echt beeindruckend. Aber jetzt ist es Zeit zum Auftauchen!',
            f'{member.mention}, wenn der Termin "{event_title}" ein Geist wäre, würdest du wahrscheinlich mit ihm sprechen, oder? Lass uns sprechen!',
            f'Hey {member.mention}, wir haben eine Vermisstenanzeige für den Termin "{event_title}" aufgegeben. Bitte melde dich, wenn du ihn siehst!',
            f'{member.mention}, der Termin "{event_title}" weint in einer Ecke und fragt sich, warum du ihn ignoriert hast.',
            f'Hey, {member.mention}, versteckt sich dein Rechner vor dir, dass du den Termin "{event_title}" nicht finden kannst?',
            f'{member.mention}, es gibt Gerüchte, dass dein Terminkalender ein Eigenleben führt und gegen dich arbeitet. Der Termin "{event_title}" wartet!',
            f'Anscheinend haben wir Sherlock Holmes persönlich in unserer Mitte - {member.mention}, du hast den Termin "{event_title}" fast schon enttarnt!',
            f'{member.mention}, "{event_title}" ist wie ein verlorenes Schaf und sucht nach dir. Kannst du ihm den Weg zeigen?',
            f'Hallo, {member.mention}! Dein Versteckspiel mit dem Termin "{event_title}" ist echt beeindruckend. Aber jetzt ist es Zeit zum Auftauchen!',
            f'{member.mention}, wenn der Termin "{event_title}" ein Geist wäre, würdest du wahrscheinlich mit ihm sprechen, oder? Lass uns sprechen!',
            f'Hey {member.mention}, wir haben eine Vermisstenanzeige für den Termin "{event_title}" aufgegeben. Bitte melde dich, wenn du es siehst!',
            f'{member.mention}, der Termin "{event_title}" weint in einer Ecke und fragt sich, warum du ihn ignoriert hast. 😢',
            f'Hast du den Termin "{event_title}" in eine andere Dimension geschickt, {member.mention}? Es scheint verschwunden zu sein!',
            f'{member.mention}, selbst Bigfoot ist leichter zu finden als der Termin "{event_title}". Kannst du uns auf die richtige Spur bringen?',
            f'Wir dachten, der Termin "{event_title}" wäre auf einer geheimen Mission im Bermuda-Dreieck. Bist du sein Kommandant, {member.mention}?',
            f'{member.mention}, der Termin "{event_title}" ist wie der heilige Gral - schwer zu finden, aber legendär wichtig. 🏆',
            f'Entschuldige, {member.mention}, aber wir können den Termin "{event_title}" nicht einfach in den Papierkorb verschieben und vergessen!',
            f'{member.mention}, selbst Sherlock Holmes hätte Schwierigkeiten, den Termin "{event_title}" zu verpassen. Also, wo steckt er?',
            f'Hallo, {member.mention}! Wir veranstalten eine Schnitzeljagd, bei der du den Termin "{event_title}" finden musst. Los gehts!',
            f'{member.mention}, du und der Termin "{event_title}" - die beiden besten Versteckspieler. Kannst du es aufspüren?',
            f'Hey {member.mention}, erinnerst du dich an den Termin "{event_title}"? Es erinnert sich definitiv an dich und vermisst dich!',
            f'Vielleicht hat der Termin "{event_title}" sich in ein Chamäleon verwandelt und versucht, sich vor dir zu verstecken, {member.mention}?',
            f'Oh, {member.mention}, der Termin "{event_title}" hat eine Einladung zu deinem "Wie man Termine verpasst"-Workshop verpasst! 😉',
            f'Hallo {member.mention}, gibt es eine spezielle App, um den Termin "{event_title}" zu finden, oder müssen wir improvisieren?',
            f'{member.mention}, du und der Termin "{event_title}" - das unzertrennliche Duo! Schade, dass ihr den Termin verpasst hat.',
            f'{member.mention}, der Termin "{event_title}" sucht nach dir wie Nemo nach seinem Vater. 🐟',
            f'Wir sollten den Termin "{event_title}" zu einem Spiel des Versteckens einladen. {member.mention} ist sicher ein Meister darin!',
            f'Hallo, {member.mention}! Scheint, als hätte der Termin "{event_title}" dich in ein Rätsel verwickelt. Kannst du die Lösung finden?',
            f'Wenn der Termin "{event_title}" ein Detektiv wäre, hätte es dich längst gefunden, {member.mention}!',
            f'{member.mention}, hast du den Termin "{event_title}" ins Reich der vergessenen Dinge verbannt? Wir vermissen es!',
            f'Der Termin "{event_title}" hat sich sicher in deinem Spam-Ordner versteckt, {member.mention}. Zeit, nachzusehen!',
            f'Hey, {member.mention}, selbst die X-Files könnten den Termin "{event_title}" nicht aufspüren. Kannst du es schaffen?',
            f'{member.mention}, der Termin "{event_title}" verhält sich wie ein schüchternes Reh im Wald. Kannst du Bambis Mutter finden?',
            f'Gibt es eine Belohnung für das Finden von dem Termin "{event_title}", {member.mention}? Wir sind bereit, hohe Einsätze zu setzen!',
            f'{member.mention}, wir haben den Termin "{event_title}" vermisst, als wäre es der Hauptdarsteller in einem Hollywood-Film. 🎥',
            f'Der Termin "{event_title}" hat seine Anwesenheit verloren, aber wir wissen, dass du es finden kannst, {member.mention}!',
            f'{member.mention}, wenn der Termin "{event_title}" ein Buch wäre, wäre es wahrscheinlich in der Kategorie "Vermisst" gelistet!',
            f'Hallo, {member.mention}! Hast du den Termin "{event_title}" in ein Paralleluniversum katapultiert? Wir warten auf deine Rückkehr!',
            f'{member.mention}, hast du den Termin "{event_title}" in die Wüste geschickt, um eine spirituelle Erleuchtung zu finden? Zeit für die Rückkehr!',
            f'Hey {member.mention}, hast du den Termin "{event_title}" in einer Schatztruhe versteckt und den Schlüssel verloren? Wir brauchen Hilfe beim Finden!',
            f'{member.mention}, wenn du den Termin "{event_title}" findest, winkt vielleicht ein Ruhmreicher Rätsel-Löser-Preis!',
            f'Der Termin "{event_title}" ist wie ein verlorener Schatz, und du, {member.mention}, bist der mutige Abenteurer, der ihn bergen kann!',
            f'Hallo, {member.mention}! Wir haben Nachrichten von dem Termin "{event_title}" erhalten - es möchte wieder an unseren Meetings teilnehmen!',
            f'{member.mention}, der Termin "{event_title}" hat seinen Witz verloren, aber du kannst ihn sicherlich wiederfinden!',
            f'Vielleicht hat der Termin "{event_title}" nur einen Kurzurlaub genommen und ist jetzt bereit, wieder an Bord zu kommen, {member.mention}?',
            f'Wir haben überall nach dem Termin "{event_title}" gesucht, aber es scheint, als hättest du die exklusive Schatzkarte, {member.mention}!',
            f'{member.mention}, vielleicht hat der Termin "{event_title}" sich in einer Zeitschleife verfangen. Kannst du es befreien?'
        ]

        return random.choice(messages)