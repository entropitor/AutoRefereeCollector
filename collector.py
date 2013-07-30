import urllib,urllib2
from sys import argv
import os, sys
import re

def main(argv):
    d = os.path.dirname("output/")
    if not os.path.exists(d):
        os.makedirs(d)
    
    for code in argv:
        Match.addmatch(code)

    Match.printstats()

class Match:
    objectives = set()
    records = {}
    matches = []

    def __init__(self,matchdetails,teamdetails):
        self.mapname = matchdetails["mapname"]
        self.date = matchdetails["date"]
        self.duration = matchdetails["duration"]
        self.winners = Team(teamdetails["team1"],teamdetails["team1full"],teamdetails["team1players"])
        self.losers = Team(teamdetails["team2"],teamdetails["team2full"],teamdetails["team2players"])
        if matchdetails["winners"] != self.winners.name:
            self.winners, self.losers = self.losers, self.winners

    def parselog(self,matchlog):
        for event in re.split('\n',matchlog):
            pattern = "<tr class='transcript-event (?P<class>.*?)' data-location='.*?'.*?><td class='message'>(?P<message>.*?)</td><td class='timestamp'>(?P<timestamp>.*?)</td></tr>"
            m = re.search(pattern, event)
            if m != None:
                eventdetails = m.groupdict()

                # An objective found event
                if eventdetails['class'].count('type-objective-found') != 0:
                    pattern = "<span class='player .*? team-(?P<team>.*?)'>(?P<retriever>.*?)</span>.*?<span class='block .*?'>(?P<objective>.*?)</span>"
                    m = re.search(pattern,eventdetails['message'])
                    team = (self.winners if self.winners.name == m.group('team') else self.losers)
                    team.retrieve_objective(m.group("objective"),eventdetails['timestamp'])
                    Match.objectives.add(m.group("objective").upper())
                # A team kill
                elif eventdetails['class'].find('type-player-death') != 0:
                    traitorteam = None
                    if(eventdetails['message'].count('team-'+self.winners.name) == 2):
                        #team kill in winners
                        traitorteam = self.winners
                    elif(eventdetails['message'].count('team-'+self.losers.name) == 2):
                        #team kill in losers
                        traitorteam = self.losers
                    if traitorteam != None:
                        pattern = "<span class='player.*?'>(?P<victim>.*?)</span>(.*?)<span class='player.*?'>(?P<traitor>.*?)</span>"
                        m = re.search(pattern,eventdetails['message'])
                        traitorteam.settraitor(m.group('traitor'))

    def parsestats(self,stats):
        for player in re.split('<tr>',stats):
            pattern = "<td>\d+?</td><td><span class='player player-(?P<name>.+?) team-(?P<team>.+?)'>(?P<fullname>.+?)</span></td><td>(?P<kills>\d+?)( (?P<assists>\d+?))?</td><td>(?P<deaths>\d+?)</td><td>(?P<accuracy>\d+?)% \((?P<hit>\d+?)/(?P<fired>\d+?)\)</td><td>(.+?)</td>"
            m = re.search(pattern, player)
            if m != None:
                playerdetails = m.groupdict()
                team = (self.winners if self.winners.name == m.group('team') else self.losers)
                team.setplayerdetails(playerdetails)

    @classmethod        
    def addmatch(cls,code):
        headers = { 'User-Agent' : "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.2 Safari/537.36", 'Referer' : "http://pastehtml.com/view/{0}.html".format(code) }
        req = urllib2.Request(url="http://pastehtml.com/raw/{0}.html".format(code),headers=headers)
        conn = urllib2.urlopen(req)

        html = conn.read()

        #Strip to only have relevant information left.
        pattern = "<body>\s*<div class='container'>\s*<div class='row'>((.|[\r\n])*?)</div>\s*<!-- Map Image Tooltip -->"
        m = re.search(pattern,html)
        html = m.group(1)

        #Get match details
        pattern = "<tr>\s*<th>Map Name:</th>\s*<td>(?P<mapname>.*?)</td>\s*</tr>\s*<tr>\s*<th>Date:</th>\s*<td>(?P<date>.*?)</td>\s*</tr>\s*<tr>\s*<th>Match Length:</th>\s*<td>(?P<duration>.*?)</td>\s*</tr>\s*<tr>\s*<th>Winners:</th>\s*<td><span class='team team-(?P<winners>.*?)'>(?P<winnersfull>.*?)</span></td>\s*</tr>"
        m = re.search(pattern, html)
        matchdetails = m.groupdict()

        #Get Team details
        pattern = "<h3>Teams</h3>\s*<div class='row'>\s*<div class='span3'><h4 class='team team-(?P<team1>.*?)'>(?P<team1full>.*?)</h4><ul class='teammembers unstyled'>(?P<team1players>(<li><input type='checkbox' class='player-toggle' data-player='.*?'><span class='player player-.*? team-(?P=team1)'>.*?</span></li>\s)*)</ul></div>\s<div class='span3'><h4 class='team team-(?P<team2>.*?)'>(?P<team2full>.*?)</h4><ul class='teammembers unstyled'>(?P<team2players>(<li><input type='checkbox' class='player-toggle' data-player='.*?'><span class='player player-.*? team-(?P=team2)'>.*?</span></li>\s)*)</ul></div>\s*</div>"
        m = re.search(pattern, html)
        teamdetails = m.groupdict()

        #create match
        match = Match(matchdetails,teamdetails)

        #parse the event log
        pattern = "<h3>Match Log</h3>((.|[\n\r])*?)<tbody>(?P<matchlog>(.|[\n\r])*?)</tbody>\s*</table>"
        m = re.search(pattern, html)
        matchlog = m.group("matchlog")
        match.parselog(matchlog)

        #parse the player stats
        pattern = "<h3>Player Stats</h3>((.|[\n\r])*?)<tbody>(?P<playerstats>(.|[\n\r])*?)</tbody>\s*</table>"
        m = re.search(pattern, html)
        playerstats = m.group("playerstats")
        match.parsestats(playerstats)

        #add match to list of matches
        cls.matches.append(match)

    @classmethod
    def check_record(cls,name,time):
        if cls.records.get(name,"99:99:99") > time:
            cls.records[name] = time

    @classmethod
    def printstats(cls):
        objlist = []

        # get order for objectives.
        while len(cls.objectives) > 1:
            objective = raw_input("First objective of remaining objectives ("+', '.join(cls.objectives)+"): \n").upper()
            if objective in cls.objectives:
                cls.objectives.remove(objective)
                objlist += [objective]
            else:
                print "Objective not found"
        objlist += [cls.objectives.pop()]

        nbobj = str(len(objlist))

        th_obj = ""
        for obj in objlist:
            th_obj += "<th>"+obj+"</th>"

        mapname = cls.matches[0].mapname

        output = "<html>"
        output += "<head><title>AutoReferee Report Collection for "+mapname+"</title><link rel='stylesheet' href='http://twitter.github.com/bootstrap/assets/css/bootstrap.css' /></head>"
        output +="<body><h1>"+mapname+"</h1><table class='table table-bordered'><thead>"
        output += "<tr><th rowspan=2>Winning Team</th><th rowspan=2>Losing Team</th><th rowspan=2>Match Time</th><th colspan="+nbobj+">Winner's Wool Touch Times</th><th colspan="+nbobj+">Loser's Wool Touch Times</th><th rowspan=2>Winner's KD</th><th rowspan=2>Loser's KD</th><th rowspan=2>Shots(Winning Team vs Losing Team)</th></tr>"
        output += "<tr>"+th_obj+th_obj+"</tr>"
        output += "</thead><tbody>"

        for match in cls.matches:
            output += "<tr><td>"+match.winners.fullname+"</td><td>"+match.losers.fullname+"</td><td>"+match.duration+"</td>"+match.winners.objoutput(objlist)+match.losers.objoutput(objlist)+"<td>"+match.winners.kd()+"</td><td>"+match.losers.kd()+"</td><td>"+str(match.winners.totalfired+match.losers.totalfired)+" ("+str(match.winners.totalfired)+"-"+str(match.losers.totalfired)+")</td></tr>"

        output += "</tbody></table>"

        output += "<table class='table table-bordered table-striped'><thead>"
        output += "<tr><th>Team</th><th>Survivors (no deaths)</th><th>Pacifists (no kills)</th><th>Traitors (team kill)</th></tr>"
        output += "</thead><tbody>"

        for match in cls.matches:
            output += match.winners.printplayerstats()
            output += match.losers.printplayerstats()

        output += "</tbody></table>*The darker rows are the winning teams"

        output += "</body></html>"

        f = open('output/output.html','w')
        f.write(output)
        print "\n###################\n###   RESULTS   ###\n###################\nFile exported to output/output.html"

        param = urllib.urlencode({'txt': output})
        req = urllib2.Request("http://pastehtml.com/upload/create?input_type=html&result=address&minecraft=1",param)
        conn = urllib2.urlopen(req)
        link = conn.read()
        print "File exported to "+link

class Team:
    def __init__(self,name,fullname,playerstext):
        self.name = name
        self.fullname = fullname
        self.parseplayers(playerstext)
        self.traitors = []
        self.pacifists = []
        self.survivors = []
        self.objectives = {}
        self.totalkills = 0
        self.totaldeaths = 0
        self.totalfired = 0
        self.totalhit = 0

    def parseplayers(self,playerstext):
        self.players = []
        for playertext in re.split('\n',playerstext):
            pattern = "<li><input type='checkbox' class='player-toggle' data-player='(?P<name>.*?)'><span class='player player-(?P=name) team-(.*?)'>(?P<fullname>.*?)</span></li>"
            m = re.search(pattern, playertext)
            if m != None:
                playerdetails = m.groupdict()
                self.players += [Player(playerdetails['name'],playerdetails['fullname'])]

    def settraitor(self,playername):
        self.traitors += [playername]

    def retrieve_objective(self,name,time):
        self.objectives[name] = time
        Match.check_record(name,time)

    def setplayerdetails(self,playerdetails):
        self.totalkills += int(playerdetails['kills'])
        self.totaldeaths += int(playerdetails['deaths'])
        self.totalfired += int(playerdetails['fired'])
        self.totalhit += int(playerdetails['hit'])

        if playerdetails['kills'] == 0:
            self.pacifists += [playerdetails['fullname']]
        if playerdetails['deaths'] == 0:
            self.survivors += [playerdetails['fullname']]

    def objoutput(self,objlist):
        output = ""
        for obj in objlist:
            time = self.objectives.get(obj, "-")
            if (time == Match.records[obj]):
                output += "<td><strong>"+time+"</strong></td>"
            else:
                output += "<td>"+time+"</td>"
        return output

    def kd(self):
        return str(self.totalkills)+"/"+str(self.totaldeaths)

    def printplayerstats(self):
        return  "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (self.fullname, ', '.join(self.survivors), ', '.join(self.pacifists), ', '.join(self.traitors))

class Player:
    "Currently not really used"
    def __init__(self,name,fullname):
        self.name = name
        self.fullname = fullname

if __name__ == '__main__':
    if len(argv) < 2:
        print '\nUsage: python collector.py code1 code2 ...\n'
        exit()
    main(argv[1:])