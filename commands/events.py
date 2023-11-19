import datetime

from nextcord.ext import commands

from general import settings
from functions import events

class Events(commands.Cog):
    @commands.command(usage='', aliases=['init', 'initialize'])
    async def InitializeEventEmbeds(self, ctx):
        "Initialize event channel embeds"
        await ctx.message.delete()
        await events.Events().IniitializeEventEmbeds()

    @commands.command(usage='', aliases=['toggle'])
    async def ToggleReminder(self, ctx):
        "Toggle the automatic event creation"
        await ctx.message.delete()
        settings.reminders = not settings.reminders
        await ctx.channel.send(f'Reminders are now {"enabled" if settings.reminders else "disabled"}', delete_after=30)

    @commands.command(usage='weekday[int] time[string]', aliases=['event'])
    async def SetEventTime(self, ctx, *args):
        "Set the default time for event creation"
        await ctx.message.delete()
        try:
            weekday = int(args[0])
            if args[1] != 'False': settings.event_time[weekday] = args[1].replace('"', '').replace("'", '')
            else : settings.event_time[weekday] = False
            await ctx.channel.send(f'Default event time is now set to {settings.event_time}', delete_after=30)
        except:
            await ctx.channel.send(f'Invalid time format', delete_after=30)

    @commands.command(usage='', aliases=['reminder'])
    async def SetReminderTime(self, ctx, *args):
        "Set the time for receiving reminders"
        await ctx.message.delete()
        try:
            settings.reminder_time = args[0]
            await ctx.channel.send(f'Reminder time is now set to {settings.reminder_time}', delete_after=30)
        except:
            await ctx.channel.send(f'Invalid time format', delete_after=30)

    @commands.command(usage='', aliases=['test'])
    async def create(self, ctx):
        "For testing purposes only. Do not use in running environment."
        await ctx.message.delete()
        await events.Events().CreateEvent()

    @commands.command()
    async def check(self, ctx):
        "Check the server time"
        await ctx.message.delete()
        await ctx.channel.send(f'Server time zone check: {datetime.datetime.now().strftime("%d.%m. %H:%M")}', delete_after=30)

def setup(bot):
    bot.add_cog(Events(bot))