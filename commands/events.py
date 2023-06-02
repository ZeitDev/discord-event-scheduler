import datetime

from nextcord.ext import commands

from general import settings
from functions import events

class Events(commands.Cog):
    @commands.command(usage='', aliases=['toggle'])
    async def ToggleEventCreation(self, ctx):
        "Toggle the automatic event creation"
        await ctx.message.delete()
        settings.event_creation = not settings.event_creation
        await ctx.channel.send(f'Automatic event creation is now {"enabled" if settings.event_creation else "disabled"}', delete_after=30)
        events.test = 0

    @commands.command(usage='')
    async def SetEventTime(self, ctx, *args):
        "Set the default time for event creation"
        await ctx.message.delete()
        try:
            settings.event_time = args[0]
            await ctx.channel.send(f'Default event time is now set to {settings.event_time}', delete_after=30)
        except:
            await ctx.channel.send(f'Invalid time format', delete_after=30)

    @commands.command(usage='')
    async def SetReminderTime(self, ctx, *args):
        "Set the time for receiving reminders"
        await ctx.message.delete()
        try:
            settings.reminder_time = args[0]
            await ctx.channel.send(f'Reminder time is now set to {settings.reminder_time}', delete_after=30)
        except:
            await ctx.channel.send(f'Invalid time format', delete_after=30)

    @commands.command()
    async def test(self, ctx):
        "For testing purposes only. Do not use in running environment."
        await ctx.message.delete()
        await events.Events().InitEventCreation()

    @commands.command()
    async def check(self, ctx):
        "Check the server time"
        await ctx.message.delete()
        await ctx.channel.send(f'Server time check: {datetime.datetime.now().strftime("%d.%m. %H:%M")}', delete_after=30)

def setup(bot):
    bot.add_cog(Events(bot))