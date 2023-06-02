import os
import json
import nextcord

from nextcord import Color

from general import config
from general import settings
from general import variables

class Stats():
    def __init__(self):
        self.stats_path = os.path.join('data', 'stats.json')

    def CheckForExisitingStatsFile(self):
        try:
            print('Loading stats.json')
            json.load(open(self.stats_path))
        except:
            print('No stats found. Creating new one.')
            self.CreateStatsFile()

    def ResetUptime(self):
        stats = json.load(open(self.stats_path))
        stats['server_stats']['uptime'] = 0
        json.dump(stats, open(self.stats_path, 'w'))

    def CreateStatsFile(self):
        leaderboard_reminder, leaderboard_wasted_time, leaderboard_confirmed = self.CreateLeaderboards()
        server_stats = {'starting_date': '02.06.2023', 'uptime': 0, 'server_cost': 0}
        
        stats = {
            'leaderboard_reminder': leaderboard_reminder,
            'leaderboard_wasted_time': leaderboard_wasted_time,
            'leaderboard_confirmed': leaderboard_confirmed,
            'server_stats': server_stats}

        json.dump(stats, open(self.stats_path, 'w'))

    def CreateLeaderboards(self):
        members = Tools().GetAllMembers()

        leaderboard_reminder = {}
        leaderboard_wasted_time = {}
        leaderboard_confirmed = {}
        for member in members:
            leaderboard_reminder[f'{member}'] = 0
            leaderboard_wasted_time[f'{member}'] = 0
            leaderboard_confirmed[f'{member}'] = 0

        return leaderboard_reminder, leaderboard_wasted_time, leaderboard_confirmed
    
    def CreateEmbed(self):
        StatsDict = self.FormatStats()

        embed = nextcord.Embed(title='Statistics', color=Color.dark_orange())

        embed.add_field(name='Time of others wasted', value=StatsDict['wasted_time_members'], inline=True)
        embed.add_field(name='\u200b', value=StatsDict['wasted_time_scores'], inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=False)

        embed.add_field(name='Reminders received + Events missed', value=StatsDict['reminder_members'], inline=True)
        embed.add_field(name='\u200b', value=StatsDict['reminder_scores'], inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=False)

        embed.add_field(name='Events confirmed', value=StatsDict['confirmed_members'], inline=True)
        embed.add_field(name='\u200b', value=StatsDict['confirmed_scores'], inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=False)

        embed.add_field(name='Server Stats', value=StatsDict['server_stats_titles'], inline=True)
        embed.add_field(name='\u200b', value=StatsDict['server_stats_values'], inline=True)

        return embed
    
    def FormatStats(self):
        stats = json.load(self.stats_path)

        leaderboard_wasted_time = dict(sorted(stats['leaderboard_wasted_time'].items(), key=lambda item: item[1], reverse=True))
        leaderboard_reminder = dict(sorted(stats['leaderboard_reminder'].items(), key=lambda item: item[1], reverse=True))
        leaderboard_confirmed = dict(sorted(stats['leaderboard_confirmed'].items(), key=lambda item: item[1], reverse=True))
        server_stats = stats['server_stats']
        member_displaynames = Tools().GetMemberDisplaynames()

        StatsDict = {
            'reminder_members': '',
            'reminder_scores': '',
            'wasted_time_members': '',
            'wasted_time_scores': '',
            'confirmed_members': '',
            'confirmed_scores': '',

            'server_stats_titles': '',
            'server_stats_values': '',
        }

        for key, value in leaderboard_wasted_time.items():
            StatsDict['wasted_time_members'] += (member_displaynames[key] + '\n')
            StatsDict['wasted_time_scores'] += (Tools().ConvertSecondsToReadable(value, skips=1) + '\n')

        for key, value in leaderboard_reminder.items():
            StatsDict['reminder_members'] += (member_displaynames[key] + '\n')
            StatsDict['reminder_scores'] += (str(value) + '\n')

        for key, value in leaderboard_confirmed.items():
            StatsDict['confirmed_members'] += (member_displaynames[key] + '\n')
            StatsDict['confirmed_scores'] += (str(value) + '\n')

        StatsDict['server_stats_titles'] = 'Starting Date' + '\n' 'Continuous uptime' + '\n' + 'Server Costs'
        StatsDict['server_stats_values'] = server_stats['starting_date'] + '\n' + str(Tools().ConvertSecondsToReadable(int(server_stats['uptime']))) + '\n' + Tools().ConvertCentsToReadable(server_stats['server_cost'])

        return StatsDict

class StatCommands():
    def __init__(self):
        self.stats_path = os.path.join('data', 'stats.json')

    async def ShowStats(self, ctx):
        embed = self.CreateEmbed()
        await ctx.send(embed=embed)

    def AddPenaltyToLeaderboard(self, members):
        stats = json.load(open(self.stats_path))

        for member in members:
            stats['leaderboard_reminder'][f'{member}'] += 1
            stats['leaderboard_wasted_time'][f'{member}'] += settings.reminder_penalty

        json.dump(stats, open(self.stats_path, 'w'))

    async def AddTimeToWastedTimeLeaderboard(self, ctx, args):
        stats = json.load(open(self.stats_path))

        try:
            minutes = int(args[0])
            member = ctx.message.mentions[0]
        except:
            await ctx.channel.send(f'Error: arguments not valid. See .help wasted!')
            return

        stats['leaderboard_wasted_time'][f'{member}'] += minutes * 60
        await ctx.channel.send(f'Adding {minutes} minutes to {member.display_name}')

        json.dump(stats, open(self.stats_path, 'w'))

    def AddConfirmedToLeaderboard(self, members):
        stats = json.load(open(self.stats_path))

        for member in members:
            stats['leaderboard_confirmed'][f'{member}'] += 1

        json.dump(stats, open(self.stats_path, 'w'))

    def AddServerStats(self, key, value):
        stats = json.load(open(self.stats_path))
        stats['server_stats'][key] += value
        json.dump(stats, open(self.stats_path, 'w'))

class Tools():
    def GetAllMembers(self):
        guild = variables.bot.get_guild(config.server_id)
        for role in guild.roles:
            if role.id == config.role_reminder:
                return role.members
            
    def GetAllMemberDisplaynames(self):
        members = self.GetAllMembers()
        member_displaynames = {}
        for member in members:
            member_displaynames[f'{member}'] = member.display_name

        return member_displaynames
    
    def ConvertSecondsToReadable(self, seconds, skips=0):
        intervals = (
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),    # 60 * 60 * 24
            ('hours', 3600),    # 60 * 60
            ('minutes', 60),
            #('seconds', 1),
        )

        result = []
        if seconds == 0: return 'none'
        else:
            for name, count in intervals[skips:]:
                value = seconds // count
                if value:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip('s')
                    result.append("{} {}".format(value, name))
            return ', '.join(result)
        
    def ConvertCentsToReadable(self, cents):
        return '{:,.2f} €'.format(cents/100)