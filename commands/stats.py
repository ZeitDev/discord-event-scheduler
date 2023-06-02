from nextcord.ext import commands

from general import settings

class Stats(commands.Cog):
    @commands.command(usage='', aliases=['stats'])
    async def ShowStats(self, ctx, *args):
        "Displays the statistics board"

    @commands.command(usage='', aliases=['wasted'])
    async def TimeWasted(self, ctx, *args):
        "Adds time to the wasted time account of a user"

    @commands.command(usage='')
    async def SetReminderPenalty(self, ctx, *args):
        "Change the penalty for missing a reminder"
        await ctx.message.delete()
        try:
            settings.penalty = int(args[0])
            await ctx.channel.send(f'Reminder penalty is now set to {settings.penalty} seconds', delete_after=30)
        except:
            await ctx.channel.send(f'Invalid time format', delete_after=30)


def setup(bot):
    bot.add_cog(Stats(bot))