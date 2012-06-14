import sys
import socket
import string
import os #not necassary but later on I am going to use a few features from this
import random
import re
import pickle
import htmllib
import time
import thread
import urllib2
try:
    from bs4 import BeautifulSoup
except:
    print "mechaGnome requires BeautifulSoup 4.+"
    raise
try:
    import GeoIP
except:
    pass
from Actions import Message
from Actions import unescape

# t[A-Z][a-z]+ - like tQuotemovie() - commands are for threaded sinBot commands
# c[A-Z][a-z]+ - like cReverse() - commands are for unthreaded
# standard triple-quoted doc statements are used as help info, if a command has no doc it does not get added to the list of commands that the help command prints out (but it will still be a valid sinbot command, useful for "undocumented" commands)
headers = {
'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2',
#'Accept' : 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
#'Accept-Language' : 'en-us;q=0.7,en;q=0.3',
#'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'
}

class Commands(object):

    def tTime(this, args):
        """Syntax: 'time in <location>' - gives the current time for the given location (via google) #KEYWORDS time timezone local"""
        result = this.getGoogle(" ".join(["time"]+args[3:]))
        i = 0
        num = 3
        if len(result["quickresult"]) > 0:
            this.respond(htmldecode(result["quickresult"][0]), args)
        else:
            this.respond("couldn't find time for "+" ".join(args[4:]),args)
    def tWikipedia(this, args):
        args.append("site:wikipedia.org")
        this.tGoogle(args)
    def tTwitter(this, args):
        """Syntax: 'twitter <search terms> | from:<user>' - searches twitter for the terms specified, or gets tweets from a specific user #KEYWORDS twitter twit tweets"""
        results = this.getTwitterSearch(args[3:])
        if len(results) == 0:
            this.respond("No tweets found for that search.", args.copy())
        else:
            for twit in results:
                this.respond(twit, args.copy())
        
    def tTwit(this, args):
        this.tTwitter(args)
        
    def cGrep(this,args):
        this.respond(" ".join(args[3:]),args)

    def cTopic(this,args):
        """Syntax: 'topic <new topic>' - sets the topic for the current channel #KEYWORDS topic"""
        this.sinBot.actions.execcommand('TOPIC '+args.chan+" :"+" ".join(args[3:]), args)
    def tQuote(this, args):
        """Syntax: 'quote <stock symbol>|<movie title>' - get the stock info for <stock symbol> or get a quote from <movie title>"""
        if len(args) > 4 or len(args[3]) > 4:
            this.tQuotemovie(args, True)
            if this.tQuotemovie(args,True) == 0:
                this.tStock(args)
            #    this.tQuoteuser(args)
        else:
            this.tStock(args)
#            #this.sendToOlga(args,"quote")

    def cLmgtfy(this, args):
        """Syntax: 'lmgtfy <word or phrase' - creates a Let Me Google That For You link to add insult to injury for internet noobs"""
        google = "+".join(args[3:])
        this.respond("http://lmgtfy.com/?q="+google,args)

    def cHardware(this, args):
        #"""Syntax: 'hardware' - gives hardware info about sinbot's current host"""
        return
        command = 'cat /proc/cpuinfo | grep "model name" | sed -e "s/^.*:[\t ]*//g";cat /proc/meminfo | grep MemTotal | sed -e "s/^.*:[\t ]*//g"'
        output = os.popen(command)
        print command
        line = "Processor: "
        line += output.readline().strip()
        line += " with "
        line += output.readline().strip()
        line += " of ram."
        output.close()
        this.respond(line,args)
        
    def cSystemuptime(this, args):
        #"""Syntax: 'systemuptime' - gives the uptime of sinbot's current host"""
        return
        command = 'uptime'
        output = os.popen(command)
        print command
        line = output.readline().strip()
        output.close()
        this.respond(line,args)

    def cWall(this, args):
        """Syntax: 'wall <phrase>' - send out <phrase> along with the name of every member in the channel"""
        chan = args[2]
        msg = ">>>> "+" ".join(args[3:])+" <<<<"
        this.sinBot.lockDict['userList'].acquire()
        try:
            print "userList: ",this.sinBot.userList
            for user in this.sinBot.userList[chan]:
                if user[0] == "@":
                    msg = user[1:]+" "+msg
                else:
                    msg = user+" "+msg
        except:
            pass
        this.sinBot.lockDict['userList'].release()
        this.respond(msg,args)
#        this.sinBot.actions.execcommand('PRIVMSG '+chan+' :'+msg,args)

    def cTell(this, args):
        #"""Syntax: 'tell <nick/channel> <message> - sends the message to the channel or nick."""
        if args[0].lower() == this.sinBot.OWNER or args[0].lower() == "@"+this.sinBot.OWNER:
            print args
            target = args[3]
            if args[4] == "ACTION":
                message = " ".join(args[5:])
                this.sinBot.actions.execcommand('PRIVMSG '+target+' :'+chr(1)+'ACTION '+message+chr(1),args)
            else:
                message = " ".join(args[4:])
                this.sinBot.actions.execcommand('PRIVMSG '+target+' :'+message,args)
        else:
            this.respond("Sorry.  That is a command limited to my owner.",args)

    def tQuotemovie(this, args, suppress = False):
        """Syntax: 'quotemovie <movie name>' - find a random quote from <movie name>"""
        imdbId = this.findImdb(" ".join(args[3:]))
        if imdbId == None:
            return 0
        quotes = this.getImdbQuotes(imdbId)
        
        try:
            if args.nextCommand == "grep":
                args.nextPipe()
                tmpQuotes = []
                buffer = []
                for q in quotes:
                    tmpQ = " ".join(q)
                    found = True
                    if len(buffer) == 0:
                        for searchWord in args[3:]:
                            searchWord = searchWord.replace('"',"")
                            if tmpQ.lower().find(searchWord.lower()) < 0:
                                found = False
                    if found:
                        tmpQuotes.append(q)
                quotes = tmpQuotes
            quote = quotes[random.randrange(len(quotes))]
            while(len(quotes) > 0):
                if quote[0].startswith("Related Links") or len(quote) > 10:
                    print "discarding a quote"
                    del quotes[quotes.index(quote)]
                    quote = quotes[random.randrange(len(quotes))]
                else:
                    for q in quote:
                        msg = q.encode(this.out_encoding, 'replace')
                        if not msg.strip() == 'Share this quote':
                            this.respond(msg,args)
                    return 1
        except Exception, e:
            if not suppress:
                this.respond("Movie quote not found",args)
            print e
            return 0
        return 1

    def tQuoteuser(this, args):
        #"""Syntax: 'quoteuser [channel] <username> [searchwords]' - get an channel specific quote from [channel] (or the current channel) for <username> and optionally containing [searchwords] ANDed"""
        return
        user = args[0]
        sendChan = args[2].lower()
        if args[3][0] == "#":
            chan = args[3].lower()
            quoteUser = " ".join(args[4:])
        else:
            chan = sendChan
            quoteUser = " ".join(args[3:])
        finalUser = quoteUser.lower()
        try:
            search = finalUser.split()[1:]
        except:
            search = []
        if args.nextCommand == "grep":
            args.nextPipe()
            try:
                search = args[3:]
            except:
                pass

        finalUser = finalUser.split()[0]
        retVals = this.getQuotes(finalUser, chan)
        if(len(search) > 0):
            oldVals = retVals[:]
            retVals = []
            for x in oldVals:
                add = True
                for y in search:
                    if x.lower().find(y) < 0:
                        add = False
                if add:
                    retVals.append(x)
        if len(retVals) == 0:
            this.respond('"'+quoteUser+'"',args)
        else:
            this.respond(retVals[random.randrange(len(retVals))],args)

    def tImdb(this, args):
        """Syntax: 'imdb <movie name>' - get a summary of <movie name>"""
        user = args[0]
        chan = args[2]
        title = " ".join(args[3:])
        title = unicode(title, this.in_encoding, 'replace')
        try:
            # Do the search, and get the results (a list of Movie objects).
            results = this.imdb.search_movie(title)
        except imdb.IMDbError, e:
            print "Probably you're not connected to Internet.  Complete error report:"
            print e
        # Print the results.
        print '    %s result%s for "%s":' % (len(results),
                            ('', 's')[len(results) != 1],
                            title.encode(this.out_encoding, 'replace'))
        print 'movieID\t: imdbID : title'

# Print the long imdb title for every movie.
        for movie in results[:1]:
            movie = this.imdb.get_movie(movie.movieID)
            print movie.keys()
            print '%s\t: %s : %s' % (movie.movieID,
                this.imdb.get_imdbID(movie),
                movie['long imdb title'].encode(this.out_encoding, 'replace'))
            if movie.has_key('plot'):
                this.respond(movie['long imdb title'].encode(this.out_encoding, 'replace')+' - '+movie['plot'][0].encode(this.out_encoding, 'replace'), args)
            else:
                this.respond(movie['long imdb title'].encode(this.out_encoding, 'replace'),args)

    def geoLocate(this, address):
        if not hasattr(this.sinBot, "geoip") or this.sinBot.geoip is None:
            this.sinBot.geoip = GeoIP.open("/usr/share/GeoIP/GeoLiteCity.dat",GeoIP.GEOIP_STANDARD)
        geoip = this.sinBot.geoip
        gir = geoip.record_by_name(address)
        return gir        

    # takes a GeoIP result from geoLocate()
    def prettyGeoLocate(this, gir):
        resp = None
        longresp = ""
        for key in gir.keys():
            longresp = longresp+ key + ": " + str(gir[key]) + ", "
        print longresp[:-2]

        resp = None
        if gir["city"] is not None:
            resp = gir["city"]
        if gir["region_name"] is not None and gir["region_name"] != gir["city"]:
            if resp is not None:
                resp = resp + ", " + gir["region_name"]
            #else:
            #    resp = gir["region_name"]
        if gir["country_name"] is not None:
            if resp is not None:
                resp = resp + ", " + gir["country_name"]
            #else:
            #    resp = gir["country_code"]
        if gir["postal_code"] is not None:
            if resp is None:
                resp = str(gir["postal_code"])
            else:
                resp = resp + " " + str(gir["postal_code"])
        if resp is None:
            resp = longresp
        return resp

    def tWhere(this, args):
        msg = " ".join(args[3:]).lower()
        #print msg
        addr = None
        if msg.startswith("am i"):
            x, y, addr = args[1].partition("@")
        elif msg.startswith("is "):
            nick = args[4]
            while nick[-1] == "?":
                nick = nick[:-1]
            whoisInfo = this.getWhois(nick)
            if whoisInfo[nick.lower()] is not None:
                print whoisInfo[nick.lower()]
                addr = whoisInfo[nick.lower()]["host"]
            else:
                this.respond("This user could not be found or lookup failed.",args)
                return
        else: 
            this.respond("I'm sorry "+args[0]+" I don't know what you want me to do.", args)
            return
        resp = None
        if addr is not None:
            gir = this.geoLocate(addr)
            if gir is not None:
                resp = this.prettyGeoLocate(gir)        
        if resp is None:
            resp = "I have no idea.  Maybe the moon?"            
        this.respond(resp, args)
        
        
    def tWeather(this, args):
        """Syntax: 'weather <location or zip>' - get the current weather for your location or the specified location"""
        loc = args[3:]        
        nick = None
        addr = None
        if len(args) < 4 or args[3] == "me" or (args[3] == "for" and args[4] == "me"):
            x, y, addr = args[1].partition("@")
        elif args[3] == "for":
            nick = args[4]
            whoisInfo = this.getWhois(nick)
            if whoisInfo[nick.lower()] is not None:
                #print whoisInfo[nick.lower()]
                addr = whoisInfo[nick.lower()]["host"]
            else:
                this.respond("This user could not be found or lookup failed.",args)
                return

        if addr is not None:
            gir = this.geoLocate(addr)
            if gir is not None:
                if gir["postal_code"] is not None:
                        loc = [str(gir["postal_code"])]
                else:
                       loc = this.prettyGeoLocate(gir).split()
            else:
                if nick == None:
                    this.respond("I am unable to determine your location.",args)
                else: 
                    this.respond("I am unable to determine "+nick+"'s location.",args)
                return

        print "Looking up weather for: " + str(loc)
        weather = this.getWeather(loc)
        response = ""
        if weather["title"].lower().find("error") != -1:
            this.respond("I can't find that place. :(", args)
            #this.respond("Please try a ZIP, Airport code, or rephrasing the city/state/country.", args)
            return
        try:
            try:
                response = "Current weather for: "+weather["title"].split(" Conditions")[0].split("Forecast")[0]+":"
            except:
                response = "Current weather for: "+weather["title"].split(" Conditions")[0]+":"
        except:
            response = "Current weather for: "+" ".join(args[3:])
        try:
            response += weather["conditions"]+", "
        except:
            pass
        try:
            response += weather["tempf"]+"F "
        except:
            pass
        try:
            response += weather["humidity"]+"% humidity, "
        except:
            pass
        try:
            response += "wind "+weather["windspeedmph"]+"mph "
        except:
            pass
        try:
            response += weather["winddir"]
        except:
            pass
        this.respond(response,args)

    def cViolate(this, args):
        nick = " ".join(args[3:])
        stmts = [ nick + ": Violate, violate, violate!", \
            "Sorry, I'm not that brave.", \
            "Uh.... do you know where "+nick+"'s been? Ew!", \
            "Hmm, where's that garden hose and tu-tu?", \
            "No. I respect "+nick+" too much.", \
            "Why don't YOU violate "+nick+" if you want them violated so much. Damn, you're lazy.", \
            "The last time I violated "+nick+" I had to get tetanus, penicillin and rabies shots. I'd rather not go through that again.", \
            nick+": Risotto! Risotto! Risotto!", \
            "This one time? At band camp? I violated "+nick+" with a trumpet.", \
            chr(1)+"ACTION gives "+nick+" a violet. What's that? Oh! VioLATE. Oh, sorry. I'll get right on that."+chr(1), \
            chr(1)+"ACTION begins to peel a banana and looks at "+nick+" seductively."+chr(1), \
            chr(1)+"ACTION pulls out a waffle iron and grins at "+nick+"."+chr(1), \
            chr(1)+"ACTION attacks "+nick+" with his noodley appendages! ~(o.O~)"+chr(1), \
            chr(1)+"ACTION sits right next to "+nick+" and peers over their shoulder, violating "+nick+"'s personal space."+chr(1), \
            chr(1)+"ACTION plays some Nickelback for "+nick+"."+chr(1), \
            "What do you think I've been doing for the last 20 minutes?", \
            "Hey, "+nick+" I have a spare ethernet cable. I wonder what ports you have vulnerable....", \
            chr(1)+"ACTION censors "+nick+"'s speech and violates their 1st Amendment rights."+chr(1), \
            #chr(1)+"ACTION takes away "+nick+"'s guns an violates their 2th Amendment rights."+chr(1), \
            chr(1)+"ACTION chases "+nick+" around the channel, waving his tentacles."+chr(1), \
            "Sweet! I just finished my fursona costume, and I've been dying to try it out...", \
            chr(1)+'ACTION gets out some jumper cables, baby oil, rope, a "Best of Barry Manilow" CD, and a waffle iron for '+nick+'.'+chr(1), \
            nick+", last night I had a dream where you were in a threesome with Sarah Palin and John McCain.  It was hawt.", \
            "I'd rather violate you, "+args[0]+". Come here and give me some sugar!", \
            "SURPRISE BUTTSEX!!!1", \
            chr(1)+"ACTION installs Windows ME on "+nick+" with no virus protection."+chr(1), \
            chr(1)+"ACTION gives "+nick+" the choice between a backscatter porn scan or a TSA-approved groin grope."+chr(1), \
            "Hey "+args[0]+", let me show you how this electroejaculator works.", \
            chr(1)+"ACTION scans "+nick+"'s computer for pr0n."+chr(1), \
        ]
        stmt = random.choice(stmts)
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+stmt,args)

    def cJoke(this, args):
        this.cSilly(args)
    
    def cSilly(this, args):
        jokes = (["You know, I really wish I had a garden where I could put a couple of human statues.",
            "I think that last Vendor short changed me. <chuckling> Oh, that was a bad one.",
            "I do hope to find some interesting gadgets around here. I do love tinkering with things.",
            "I had an idea for a device that you could put small pieces of bread in to cook, but in the end I really didn't think there'd be much of a market for it.",
            "I'd like to give a shout out to my boys in Gnomeregan. Keeping it real Big-T, Snoop-Pup and Little Dees. Y'all are short, but you're real, baby!",
            "I look bigger in those mirrors where things look bigger.",
            "I apologize profusely for any inconvenience my murderous rampage may have caused.",
            "I've discovered that getting pummeled by a blunt weapon can be quite painful.",
            "You know... squirrels can be deadly when cornered.",
            "Some day, I hope to find the nuggets on a chicken." 
        ])

        joke = random.choice(jokes)
        this.respond(joke, args)

    def cFlirt(this, args):
        flirts = (["I have a number of inventions I'd like to show you, back at my place." ,
            "Everyone keeps talking about Beer Goggles. I can't find the plans for them anywhere." ,
            "I like large posteriors and I cannot prevaricate.",
            "Hey! Nice apparatus." ,
            "At this time, I think you should purchase me an alcoholic beverage and engage in diminutive conversation with me in hopes of establishing a rapport." ,
            "Your ability to form a complete sentence is a plus." ,
            "I cannot find you completely disagreeable." ,
            "I don't feel the 1 to 10 scale is fine enough to capture subtle details of compatibility. I'd prefer a 12 dimensional compatibility scale with additional parameters for mechanical aptitude and torque." ,
            "You are cute!" ,
        ])
        flirt = random.choice(flirts)
        this.respond(flirt, args)

    def cI18n(this, args):
        """Syntax: 'i18n <phrase>' - translate a phrase into an i18n-ism"""
        retVal = ""
        for x in args[3:]:
            punct = ""
            i = len(x)-1
            while i >= 0 and not x[i].isalpha():
                punct = x[i] + punct
                i = i - 1
                print i
            x = x[:i+1]
            if len(x) > 2:
                retVal += x[0]+str(len(x[1:-1]))+x[-1]
            else:
                retVal += x
            retVal += punct+" "
        this.respond(retVal, args)

    def tReload(this, args):
        """Syntax: 'reload classes' - reloads my actions and commands. Use only when my code has been updated. """
        if len(args) > 3 and args[3].lower().startswith("bushisms"):
            this.readBushisms()
        elif len(args) > 3 and args[3].lower().startswith("proxies"):
            urllib2.ProxyHandler(this.sinBot.proxies)
        elif len(args) > 3 and args[3].lower().startswith("classes"):
            sb = this.getRootSinBot()
            sb.reLoad()
            sb.actions.refreshMessages()
            try:
                sb.reloaded = sb.reloaded + 1
            except:
                sb.reloaded = 1
            sb.reloadTime = time.localtime()
        else: #reload classes anyway
            sb = this.getRootSinBot()
            sb.reLoad()
            sb.actions.refreshMessages()
            try:
                sb.reloaded = sb.reloaded + 1
            except:
                sb.reloaded = 1
            sb.reloadTime = time.localtime()

    def getRootSinBot(this):
        sb = this.sinBot
        while hasattr(sb,"parent") and sb.parent != None:
            sb = sb.parent
        return sb

    def cDisemvowel(this, args):
        """Syntax: 'disemvowel <word or phrase>' - remove the vowels from <word or phrase>"""
        text = " ".join(args[3:]).replace('a','').replace('e','').replace('i','').replace('o','').replace('u','').replace('y','').replace('A','').replace('E','').replace('I','').replace('O','').replace('U','').replace('Y','')
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+text,args)

    def cRefreshmessages(this, args):
        this.sinBot.actions.refreshMessages()

    def cEat(this, args):
        """Syntax: 'eat <word or phrase>' - makes me eat something"""
        this.responseActions("eats", args)
        randomEvent = random.random()
        print "Random! %f" % randomEvent
        if randomEvent < 0.2:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :Om nom nom!',args) 
        elif randomEvent < 0.4: 
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION burps!'+chr(1),args)

    def cDrink(this, args):
        """Syntax: 'drink <word or phrase>' - makes me drink something"""
        this.responseActions("drink", args)

    def cBe(this, args):
        """Syntax: 'be <word or phrase>' - makes me be something"""
        action = "".join(args[3:]).lower()
        if action == "good":
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION is always good!'+chr(1),args)            
        else: 
            #what = " ".join(args[3:]).lower().replace(" your"," his").replace(" my"," your").replace(" me "," you ")
            what = " ".join(this.replacePronouns(args[3:]))
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION is '+what+"!"+chr(1),args)

    def cWelcome(this, args):
        this.respond("Yeah, whatever", args)

    def tGoogle(this, args):
        """Syntax: 'google <query string> ' - return the top 3 results for the query"""
        result = this.getGoogle(" ".join(args[3:]))
        this.respond(result["results"][0], args)
        this.respond(result["results"][1], args)
        this.respond(result["results"][2], args)
    def tTrace(this, args):
        """Syntax: 'trace <phone number>' - return information about the phone number"""
        try:
            number = "".join(args[3:]).replace("-","")
            if number[0] != "1":
                number = "1"+number
            info = this.getPhonetrace(number)
            this.respond("That phone number is near "+info["city"]+", "+info["state"]+" "+info["zip code"]+", Company: "+info["company name"],args)
        except Exception, e:
            print "tTrace exception! ",e
            this.respond("Sorry, couldn't find any info on that number", args);

    def cWhose(this, args):
        this.cWho(args)

    def cWho(this, args):
        """Syntax: 'who <phrase>' - picks a person at random to blame"""
        what = " ".join(args[3:])
        chan = args[2]
        #print this.sinBot.userList[chan]
        randomPerson = random.randrange(len(this.sinBot.userList[chan]))
        #print "RANDOM PERSON %d" % randomPerson
        name = this.sinBot.userList[chan][random.randrange(len(this.sinBot.userList[chan]))]
        if name[0] == "@":
            name = name[1:]
        if name == this.sinBot.NICK.lower():
            #print "I found me!"
            this.cWho(args)
            return
        elif name[:3] == "cia":
            #print "I found CIA!"
            this.cWho(args)
            return
        this.sinBot.actions.execcommand('PRIVMSG '+chan+' :'+name,args)

    def cOp(this, args):
#        """Syntax: 'op <user>' - give <user> ops in the current channel"""
        if len(args) > 3:
            this.sinBot.actions.execcommand('MODE '+args[2]+' +o '+args[3]+'\n',args)
        else:
            this.sinBot.actions.execcommand('MODE '+args[2]+' +o '+args.name+'\n',args)

    def cOpme(this,args):
#        """Syntax: 'opme' - I will op you"""
        this.sinBot.actions.execcommand('MODE '+args[2]+' +o '+args.name+'\n',args)


    def cDeop(this,args):
#        """Syntax: 'deop <user>' - take <user> ops away in the current channel"""
        this.sinBot.actions.execcommand('MODE '+args[2]+' -o '+args[3]+'\n',args)

    def cJoin(this,args):
        for x in args[3:]:
            if x[0] == '@':
                x = x[1:]
            this.sinBot.actions.execcommand('OJOIN @'+x+'\n',args)
            this.sinBot.actions.execcommand('JOIN '+x+'\n',args)

    def cStatus(this,args):
        """Syntax: 'status' - gives the uptime and last reload of sinBot"""
        sb = this.getRootSinBot()
        ut = secondsToTime(time.time() - time.mktime(sb.startTime))
        print ut
        uptime = secondsToTime(time.time() - time.mktime(sb.startTime))["string"]
        if sb.reloadTime is None:
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :Status: My uptime '+time.strftime("%c", sb.startTime)+" ("+uptime+") and never reloaded.",args)
        else:
            reloadTime = secondsToTime(time.time() - time.mktime(sb.reloadTime))["string"]
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :Status: My uptime '+time.strftime("%c", sb.startTime)+" ("+uptime+") and reloaded: "+str(sb.reloaded)+" time(s). Last reloaded "+reloadTime,args)
    def cInfo(this, args):
        """Syntax: 'info' - version and maintainer info about sinBot plus status readout"""
        this.sinBot.actions.execcommand('PRIVMSG '+args["chan"]+' :I ('+this.sinBot.NICK+') am owned and maintained by '+this.sinBot.OWNER+'.', args)

    def cUptime(this,args):
        """Syntax: 'uptime' - gives the uptime of sinBot"""
        this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :My uptime: '+secondsToTime(time.time() - time.mktime(this.getRootSinBot().startTime))["string"],args)


    def cHelp(this,args):
        sendMsgStart = 'PRIVMSG '+args[2]+' :'
        if len(args) > 3:
            sendMsg = sendMsgStart+this.sinBot.helpMap[args[3]]
        else:            
            first = True
            cmds = this.sinBot.helpMap.keys()
            cmds.sort()
            for x in cmds:
                if first:
                    sendMsg = str(x)
                else:
                    sendMsg = sendMsg+", "+str(x)
                first = False
            sendMsg = sendMsgStart+'Commands: '+sendMsg
            # sendMsg = sendMsg+', '+'and almost anything '+this.sinBot.OLGANICK+' can do.'
            this.respond('Try "'+this.sinBot.NICK+' help <command>" for more detailed info on each command.', args.copy())
        this.sinBot.actions.execcommand(sendMsg+'\n',args.copy())

    def cAlert(this, args):
        """Syntax: 'alert' - gives the current WoW status alert if one exists. See http://launcher.worldofwarcraft.com/alert"""
        this.sinBot.actions.blizzAlerts(force=True)
        if this.sinBot.actions.blizzAlertsMessage == "":
            this.respond("There is no alert message currently.", args.copy())
        else:
            alertMsg = this.sinBot.actions.alertMsg(this.sinBot.actions.blizzAlertsMessage)
            this.respond(alertMsg, args.copy())
            if len(alertMsg) > 400:
                this.respond("See http://launcher.worldofwarcraft.com/alert for the full message.", args.copy())
            else:
                this.respond("Taken from http://launcher.worldofwarcraft.com/alert", args.copy())

    def cKick(this,args):
    #    """Syntax: 'kick <user>' - kick <user> from the current channel"""
        if args[3].lower() != this.sinBot.NICK.lower() and args[3].lower() != this.sinBot.OWNER.lower():
            if len(args) >2:
                this.sinBot.actions.execcommand('KICK '+args[2]+' '+args[3]+' :'+" ".join(args[4:])+'\n',args)
            else:
                this.sinBot.actions.execcommand('KICK '+args[2]+' '+args[3]+' :just get out!\n',args)
        else:
            this.sinBot.actions.execcommand('KICK '+args[2]+' '+args[0]+' :yeah right, jerk',args)

    def cLeave(this,args):
        """Syntax: 'leave' - tells me to exit the current channel"""
        print "Fine, I'm leaving!"
        print args
        this.sinBot.actions.execcommand('PART '+args[2]+' :screw you guys, *I\'m* going home\n',args)
        this.sinBot.lockDict['userList'].acquire()
        try:
            del this.sinBot.userList[args[2]]
            pickle.dump(this.sinBot.userList, open('userlist.dat','w'))
        except Exception,e:
            print "Error in cLeave(): ",e
        this.sinBot.lockDict['userList'].release()


    def cIcao(this, args):
        """Syntax: 'icao <word or phrase>' - spell out a word into international radio alphabet words"""
        retVal = ""
        for x in args[3:]:
            for letter in x.upper():
                try:
                    retVal += this.sinBot.icaoMap[letter]+" "
                except:
                    retVal += letter+" "
            retVal += " "
        this.respond(retVal, args)

    def cGet(this,args):
        """Syntax: 'get out' - tells me to exit the current channel"""
        print "Fine, I'm leaving!"
        print args
        if args[3] == "out" or args[3] == "bent" or args[3] == "lost":
            this.cLeave(args)

    def cIgnore(this,args):
        print "Ignoring: "+args[3]
        this.sinBot.ignore[args[3].lower()] = "yeah"
    def cUnignore(this,args):
        print "Unignoring: "+args[3]
        del this.sinBot.ignore[args[3].lower()]


    def cVoice(this,args):
        #"""Syntax: 'voice <user>' - give <user> voice (+v) in the current channel"""
        this.sinBot.actions.execcommand('MODE '+args[2]+' +v '+args[3]+'\n',args)

    def cNick(this,args):
        this.sinBot.actions.execcommand('NICK '+args[3]+'\n',args)
        this.sinBot.NICK = args[3].lower()

    def cDevoice(this,args):
        #"""Syntax: 'devoice <user>' - take <user> voice away (-v) in the current channel"""
        this.sinBot.actions.execcommand('MODE '+args[2]+' -v '+args[3]+'\n',args)

    def cVersion(this,args):
        """Syntax: 'version' - info about the current version of mechaGnome"""
        this.sinBot.actions.execcommand('PRIVMSG '+args["chan"]+' :'+ this.sinBot.VERSION,args)

    def cAdd(this,args):
        #"""Syntax: 'add <food|yousaid|select|acronym|weapon> <info>' - add the object to sinbot's repertoire, not persisted"""
        return
        if args[3].lower().startswith("food"):
            print "Adding food: "+" ".join(args[4:])
            curMap = this.sinBot.foodMap
            for x in args[4:]:
                if not curMap.has_key(x.lower()):
                    curMap[x.lower()] = {}
                curMap = curMap[x.lower()]
            curMap["#COMPLETE"] = "1"
        elif args[3].lower().startswith("yousaid"):
            print "Adding you said: "+" ".join(args[4:])
            curMap = this.sinBot.saidMap
            for x in args[4:]:
                if not curMap.has_key(x.lower()):
                    curMap[x.lower()] = {}
                curMap = curMap[x.lower()]
            curMap["#COMPLETE"] = "1"

        elif args[3].lower().startswith("select"):
            if " ".join(args[4:]) in this.sinBot.selectList:
                print "Already existed: "+" ".join(args[4:])
            else:
                print "Adding select: "+" ".join(args[4:])
                this.sinBot.selectList.append(" ".join(args[4:]))
        elif args[3].lower().startswith("when"):
            if " ".join(args[4:]) in this.sinBot.whenList:
                print "Already existed: "+" ".join(args[4:])
            else:
                print "Adding when: "+" ".join(args[4:])
                this.sinBot.whenList.append(" ".join(args[4:]))
        elif args[3].lower().startswith("h8ball"):
            if " ".join(args[4:]) in this.sinBot.h8List:
                print "Already existed: "+" ".join(args[4:])
            else:
                print "Adding h8ball: "+" ".join(args[4:])
                this.sinBot.h8List.append(" ".join(args[4:]))

        elif args[3].lower().startswith("acronym"):
            if args[5] == "=":
                acr = " ".join(args[6:])
            else:
                acr = " ".join(args[5:])
            try:
                tmpList = this.sinBot.acronymMap[args[4].upper()]
            except:
                tmpList = []
            if tmpList.__class__ != [].__class__:
                tmpList = []
            tmpList.append(acr)
            this.sinBot.acronymMap[args[4].upper()] = tmpList
        elif args[3].lower().startswith("weapon"):
            if args[5] == "=":
                acr = " ".join(args[6:])
            else:
                acr = " ".join(args[5:])
            try:
                list = this.sinBot.bagOfHolding[args[4].upper()]
            except:
                list = []
                this.sinBot.bagOfHolding[args[4].upper()] = list
            print "Adding: "+args[4].upper()+" to bag of holding"
            list.append(acr)
        elif args[3].lower().startswith("prep"):
            print "Adding: "+args[4].upper()+" to bag of holding prep"
            if args[5] == "=":
                acr = " ".join(args[6:])
            else:
                acr = " ".join(args[5:])
            try:
                list = this.sinBot.bagOfHoldingPrep[args[4].upper()]
            except:
                list = []
                this.sinBot.bagOfHoldingPrep[args[4].upper()] = list
            list.append(acr)

    def cDebug(this,args):
        doPrint = args[3].lower() == "print"
        doSet = args[3].lower() == "set"
        doDel = args[3].lower() == "del"
        curVar = None
        varName = None
        varLoc = None
        if doPrint or doSet or doDel:
            varName = args[4].split("[")[0]
            try:
                varLoc = args[4].split("[")[1].split("]")[0]
                varLoc = int(varLoc)
            except:
                pass
            if hasattr(this.sinBot, varName):
                curVar = this.sinBot.__dict__[varName]
            elif hasattr(this.sinBot.commands, varName):
                curVar = this.sinBot.commands.__dict__[varName]
            elif hasattr(this.sinBot.actions, varName):
                curVar = this.sinBot.actions.__dict__[varName]
            else:
                this.respond("Sorry, didn't find a variable by the name of: "+varName, args)
                return
            if doPrint:
                if varLoc != None:
                    this.respond(curVar[varLoc].__repr__(),args)
                else:
                    this.respond(curVar.__repr__(),args)
            elif doSet:
                if varLoc != None:
                    curVar[varLoc] = " ".join(args[6:])
                else:
                    curVar = " ".join(args[6:])

    def cReverse(this,args):
        """Syntax: 'reverse <word or phrase>' - reverse the <word or phrase>"""
        retval = ""
        for x in " ".join(args[3:]):
            retval = x + retval

        this.respond(retval,args)

    def cCensor(this, args):
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :sorry guys, that command is censored', args)

    def cRoulette(this, args):
        """Syntax: 'roulette' - play a game of Russian roulette"""
        if not this.sinBot.rouletteMap.has_key(args[2].lower()):
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION loads a round and spins the barrel'+chr(1),args)
            this.sinBot.rouletteMap[args[2].lower()] = 0
        if random.randrange(5 - this.sinBot.rouletteMap[args[2].lower()]) == 0:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :*BANG!*', args)
            this.sinBot.actions.execcommand('KICK '+args[2]+' '+args[0]+' :you LOSE',args)
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION loads another round and spins the barrel'+chr(1),args)
            this.sinBot.rouletteMap[args[2].lower()] = 0
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :anyone else?', args)
        else:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :--click--', args)
            this.sinBot.rouletteMap[args[2].lower()] = this.sinBot.rouletteMap[args[2].lower()] + 1

    def tTranslate(this, args):
        """Syntax: 'translate [from language] <to language> <phrase>' translate the phrase from one language to another, if [from language] is left out it is assumed to be english"""
        if args[3].lower() == "diz":
            try:
                msglist = this.sinBot.logDict[args.chan]
                for msg in msglist:
                    msg = msg.split(">",1)
                    print "testing: ",msg
                    if msg[0].split("<")[1].lower() == "diz":
                        print "found!"
                        this.respond(this.getTranslation(msg[1].strip().split(),"french","english"),args)
                        break
            except Exception, e:
                print "exception!",e
                pass
        else:
            this.respond(this.getTranslation(args[5:],args[3],args[4]),args)
            
    def tBabel(this, args):
        """Syntax: 'babel <phrase>' - babelize a phrase"""
        translations = [["english","french"],["french","english"],["english","german"],["german","english"],["english","italian"],["italian","english"],["english","portugese"],["portugese","english"],["english","spanish"],["spanish","english"]]
        retVal = args[4:]
        for x in translations:
            curVal = None
            first = True
            iter = 0
            while curVal == None and iter < 10:
                if not first:
                    print "Babel fail, sleeping 1 and retrying"
                    time.sleep(1)
                    iter = iter + 1
                curVal = this.getTranslation(retVal, x[0],x[1])
                first = False
            retVal = curVal.split()
        this.respond(" ".join(retVal),args)

    def tWhy(this, args):
        """ Syntax: 'why <phrase>' - returns a 'Bastard Operator From Hell'-style excuse from http://www.cs.wisc.edu/~ballard/bofh/"""
        this.respond(this.getExcuse(),args)

    def tLol(this, args):
        """Syntax: 'lol <phrase> ' - translate a phrase into a lolcat-ism"""
        retVal = this.getLol(" ".join(args[3:]))
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+retVal, args)
        
    def tPirate(this, args):
        """Syntax: ' <phrase> ' - translate a phrase into a pirate speak"""
        retVal = this.getPirate(args[3:])
        this.respond(retVal, args)

    def tRfc(this, args):
        """Syntax: 'rfc <number>' - get a *very* brief description of the rfc, and a link."""
        link = "http://www.faqs.org/rfcs/rfc"+args[3]+".html"
        this.respond(this.getTitle(link)+": "+link, args)

    def cPiglatin(this, args):
        """Syntax: 'piglatin <string>' - translate the string to piglatin"""
        vowels = ['a','e','i','o','u'] #and, in this case, never 'y'
        punctuation = [',','.','?','!',"'",':',';']
        retVal = ""
        for word in args[3:]:
            newWord = ""
            i = 0
            for letter in word:
                if letter not in vowels:
                    newWord += letter
                    i += 1
                else:
                    break
            for letter in word[i:]:
                if letter not in punctuation:
                    retVal += letter
                    i += 1
                else:
                     break
            retVal += newWord + "ay"+word[i:]+" "
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+retVal, args)

    def cMorse(this, args):
        """Syntax: 'morse <string>' - translate the string to/from morse"""
        message = " ".join(args[3:])
        retVal = ""
        if message.count(".") > 3 or message.count("-") > 3:
            retVal = this.decodeMorse(message)
        else:
            retVal = this.encodeMorse(message)
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+retVal, args)
    
    def tGooglefightBroken(this, args):
        if "vs." in args:
            phrases = " ".join(args[3:]).split("vs.")
        elif "vs" in args:
            phrases = " ".join(args[3:]).split("vs")
        else:
            phrases = args[3:5]
        results = this.getGooglefight(phrases[0], phrases[1])
        if int(results[0]["score"].replace(",","")) > int(results[1]["score"].replace(",","")):
            winner = results[0]["word"]
        else:
            winner = results[1]["word"]
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+results[0]["word"]+": "+results[0]["score"]+"    "+results[1]["word"]+": "+results[1]["score"]+" - "+winner+" FTW!", args)

    def tGooglefight(this, args):
        """Syntax: 'googlefight <word1> <word2>' OR 'googlefight <phrase1> vs.|vs <phrase2>' - return the results of the googlefight for the two words or phrases"""
        if "vs." in args:
            phrases = " ".join(args[3:]).split("vs.")
        elif "vs" in args:
            phrases = " ".join(args[3:]).split("vs")
        else:
            phrases = args[3:5]
        res1 = this.getGoogle(phrases[0])
        res2 = this.getGoogle(phrases[1])
        if res1["result_count"] > res2["result_count"]:
#            winner = results[0]["word"]
            winner = phrases[0]
        else:
            winner = phrases[1]
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+phrases[0]+": "+str(res1["result_count"])+"    "+phrases[1]+": "+str(res2["result_count"])+" - "+winner+" FTW!", args)

    def cWindchill(this, args):
        """Syntax: 'windchill <degrees> degrees at <mph> mph' - gives you the windchill for those conditions"""
        prev = ""
        for x in args[3:]:
            if x.strip().lower().startswith("degrees") or x.strip().lower() == "f":
                degrees = int(prev)
            elif x.strip().lower().startswith("mph") or x.strip().lower() == "miles":
                mph = int(prev)
            prev = x.strip()
        this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+str(35.74+.6215*degrees-(35.75*(pow(mph,.16)))+(.4275*degrees*(pow(mph,.16))))+' degrees F',args)

    def tEtymology(this, args):
        """Syntax: 'etymology <word> ' - find the etymology of a word"""
        ety = this.getEtymology(args[3])
        if ety == None or ety.strip() == "":
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :couldn\'t find any etymology info for '+args[3], args)
        else:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+ety, args)
    
    def tSurname(this, args):
        """Syntax: 'surname <name> ' - find information about a surname #KEYWORDS surname name history meaning"""
        surname = this.getSurname(args[3:])
        if surname == None or surname.strip() == "":
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :couldn\'t find any surname info for '+args[3], args)
        else:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :(surnamedb)'+surname, args)
    
    def cLeet(this, args):
        """Syntax: 'leet <string>' - translate the string to l33tsp3ak"""
        leet = ""
        for x in args[3:]:
            if x == "|":
                break
            leet += leetDict[x]+" "
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+leet, args)

    def cDice(this, args):
        this.cRoll(args)

    def cRoll(this, args):
        """Syntax: 'roll <number of dice>d<number of sides>' - roll the dice! example "sinbot, roll 1d20" #KEYWORDS dice roll"""
        retVal = ""
        sum = 0
        dice = int(args[3].split("d")[0])
        sides = args[3].split("d")[1].split("+")
        mod = 0
        if len(sides) > 1:
            mod = int(sides[1])
        sides = int(sides[0])
        
        for x in range(dice):
            sum += random.randrange(sides)+1
#            retVal = retVal + str(random.randrange(sides)+1) + " "
#        this.respond("You rolled: "+retVal,args)
        if sum == dice:
            if dice == 2 and sides == 6:
                this.respond("You rolled: "+str(sum)+", SNAKE-EYES! Awwww.... sucks to be you!", args)
            else:
                this.respond("You rolled: "+str(sum)+", critical FAIL suckah!", args)
        elif sides == 20 and sum == dice * sides:
            if mod != 0:
                this.respond("You rolled: "+str(sum)+"("+str(sum+mod)+"), you roll 20's!", args)
            else:
                this.respond("You rolled: "+str(sum)+", you roll 20's!", args)
        else:
            if mod != 0:
                this.respond("You rolled: "+str(sum)+"("+str(sum+mod)+")", args)
            else:
                this.respond("You rolled: "+str(sum), args)

    def tWiktionary(this, args):
        """Syntax: 'wiktionary <word>' - look up the definition of a word in wiktionary.org"""
        try:
            dfn = this.getWiktionary(args[3:])["def"]
            if dfn == None or dfn.strip() == "":
                this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :couldn\'t find a definition for '+args[3], args)
            else:
                this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+ htmldecode(dfn), args)
        except:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :couldn\'t find a definition for '+args[3], args)

    def tCyborg(this, args):
        """Syntax: 'cyborg <word(s)>' - turn any word or phrase into a cyborg name"""
        this.respond(this.getCyborg(args[3:]), args)
        
    def tInsult(this, args):
        """Syntax: 'insult <name>' - insult someone"""
        this.respond(this.getInsult(args[3:]), args)
    
    def tUrban(this, args):
        """Syntax: 'urban <word or phrase>' - get the urban dictionary definition of a word or phrase #KEYWORDS define definition meaning look up urban urbandictionary"""
        try:
            dfn = this.getUrban(args[3:])
            this.respond("(urbandictionary): "+htmldecode(dfn),args)
        except:
            this.respond('couldn\'t find a definition for \''+" ".join(args[3:])+'\' on urbandictionary.com',args)
            
    def tDefine(this, args):
        """Syntax: 'define <word> ' - find the definition of a word using m-w.com, and failing over to wiktionary.org #KEYWORDS define definition meaning look up"""
        try:
            dfn = this.getDefinition(args[3:])["def"]
        except:
            dfn = None

        if dfn == None or dfn.strip() == "":
            try:
                dfn = this.getWiktionary(args[3:])["def"]
            except:
                pass
            if dfn == None or dfn.strip() == "":
                try:
                    acr = this.getRootSinBot().acronymMap[args[3].upper().replace(".","").replace("?","").replace("!","").replace(",","").replace("'","").replace('"',"")]
                    for x in acr:
                        this.respond("(acronym): "+x,args.copy())
                except:
                    try:
                        acronym = this.getAcronym(args[3].upper().replace(".","").replace("?","").replace("!","").replace(",","").replace("'","").replace('"',""))[0]
                        this.respond("(acronymfinder.com): "+htmldecode(acronym),args)
                        
                    except:
                        try:
                            dfn = this.getSurname(args[3:])
                            this.respond("(surnamedb): "+htmldecode(dfn),args)
                        except:
                            try:
                                dfn = this.getUrban(args[3:])
                                this.respond("(urbandictionary): "+htmldecode(dfn),args)
                            except:
                                this.respond('couldn\'t find a definition for \''+" ".join(args[3:])+'\' ANYWHERE, it must not be a word :/',args)
            else:
                this.respond('(wiktionary.org)'+ htmldecode(dfn), args)
        else:
            this.respond('(m-w.com)'+ htmldecode(dfn), args)

    def tStock(this, args):
        """Syntax: 'stock <symbol>' - get the current trading value of the stock #KEYWORDS stock"""
        try:
            info = this.getStock(args[3])
            chart = ""
            if info.has_key("extCurVal"):
                if info["extDeltaP"] < -.5:
                    chart = "\\"
                elif info["extDeltaP"]> .5:
                    chart = "/"
                else:
                    chart = "-"
                this.respond(unescape(" ".join(info["title"].split()[:-3])+' currently(AFTERHOURS) trading at: '+str(info["extCurVal"])+' change amount: '+str(info["extDelta"])+' change percentage: '+str(info["extDeltaP"])+'% Chart: '+chart),args)
            else:
                if info["deltaP"] < -.5:
                    chart = "\\"
                elif info["deltaP"]> .5:
                    chart = "/"
                else:
                    chart = "-"
                this.respond(unescape(" ".join(info["title"].split()[:-3])+' currently trading at: '+str(info["curVal"])+' change amount: '+str(info["delta"])+' change percentage:'+str(info["deltaP"])+'% volume: '+info["volume"]+' market cap: '+info["marketcap"]+" Chart: "+chart),args)
        except Exception, e:
            print e
            this.respond('couldn\'t find stock info for \''+args[3]+'\'',args)


    def cWhat(this, args):
        if args[3].lower() == "is" and args[4].lower() == "wrong" and args[5].lower() == "with":
            if "c"+args[6][0].upper()+args[6][1:].lower() in dir(this):
                try:
                    this.__getattribute__("c"+args[6][0].upper()+args[6][1:].lower())(Message(args[:3]+args[7:]))
                except Exception, e:
                    this.respond(e.__repr__(),args)
                    return
                this.respond("nothing is wrong with that command", args)
            elif "t"+args[6][0].upper()+args[6][1:].lower() in dir(this):
                try:
                    this.__getattribute__("t"+args[6][0].upper()+args[6][1:].lower())(Message(args[:3]+args[7:]))
                except Exception, e:
                    this.respond(e.__repr__(), args)
                    return
                this.respond("nothing is wrong with that command",args)


    def cIdentify(this, args):
        """Syntax: 'identify <ipaddress>' - reverse-lookup's the IRC nickname of the person using an IP address"""
        print args
        this.respond(this.getRootSinBot().ipToUser[args[3]], args)

    def cFail(this, args):
        rand = random.random()
        if rand < 0.01:
            this.respond("OMG, I DO FAIL!!!", args)
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION sobs.'+chr(1),args)        
            this.respond("I am so sorry, "+args.name+"!",args)
        else:
            this.respond("No "+args.name+", you FAIL.", args)

    def cAre(this, args):
        """Syntax: 'Are you thinking what I'm thinking?' - responds with a random Pinky pondering from 'Pinky and the Brain'"""
        if args[3].lower().startswith("you"):
            this.respond(ponderings[random.randrange(len(ponderings))].replace("Brain",args.name),args)

    def cRestartparent(this, args):
        if len(args) >= 4:
            print "setting nick to "+args[3]
            this.sinBot.child.NICK = args[3]
        this.sinBot.parent.restart()
        thread.start_new_thread(this.sinBot.parent.run,("test","test2"))


    def cRestartchild(this, args):
        if len(args) >= 4:
            print "setting nick to "+args[3]
            this.sinBot.child.NICK = args[3]
        this.sinBot.child.restart()
        thread.start_new_thread(this.sinBot.child.run,("test","test2"))

    def tRhyme(this, args):
        """Syntax: 'rhyme <word or phrase>' - provides an random rhyming word for each word in the phrase"""
#        print this.getRhymes(args[3])
        response = ""
        for word in args[3:]:
            try:
                rhymes = this.getRhymes(word)
                response += rhymes[random.randrange(len(rhymes))]+" "
            except:
                response += word+" "
        this.respond(response.strip(),args)
    def cBushism(this, args):
        """Syntax: 'bushism' - returns a bushism"""
        bushisms = this.getRootSinBot().bushisms[:]
        if args.nextCommand == "grep":
            args.nextPipe()
            bushisms = grep(args[3:],bushisms)

        this.respond(bushisms[random.randrange(len(bushisms))],args)

    def cVerbs(this, args):
        """I respond to several action verbs.  Not all of them are documented. You can do the action to me such as, "/me kicks Bot" or you can tell me what to do like, "Bot, eat pie".  Known verbs: eat, drink, be, hug, glomp, poke, kick, tickle, stab, give, punch, bite""" 
        this.respond('I can respond to several action verbs such as "hug" or "poke". Use "help verbs" for more info.',args)

    def cGlomp(this, args):
        #"""Syntax: 'glomp' [individual] - glomp the person or glomps you"""
        this.responseActions("glomps", args)
    def cHug (this, args):    
        #"""Syntax: 'hug' [individual] - hugs the person or hugs you"""
        this.responseActions("hugs", args)
    def cLove (this, args):    
        #"""Syntax: 'hug' [individual] - hugs the person or hugs you"""
        randomEvent = random.random()
        action = "loves"
        if len(args) == 4:
            if randomEvent < 0.25:
                action = "starts up the Barry White music, lights some candles, and gets ready to love"
            elif randomEvent < 0.5:
                action = "growls in affection and pounces on"
        this.responseActions(action, args)
        if randomEvent < 0.25 and len(args) == 4:
            this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :*Bow chicka wow wow!*',args)

    def cPoke (this, args):
        #"""Syntax: 'poke' [individual] - pokes the person or pokes you"""
        this.responseActions("pokes", args)
    def cKick (this, args):
        #"""Syntax: 'kick' [individual] - kicks the person or kicks you"""
        this.responseActions("kicks", args)
    def cGive (this, args):
        this.responseActions("gives", args)
    def cStab (this, args):
        this.responseActions("stabs", args)
    def cTickle (this, args):
        this.responseActions("tickles", args)
    def cPunch (this, args):
        this.responseActions("punches", args)
    def cBite (this, args):
        this.responseActions("bites", args)

    def responseActions(this, action, args):
        #print "Args: '"+"' '".join(args)
        if args[-1][-1] == "." or args[-1][-1] == "!" or args[-1][-1] == "?":
            args[-1] = args[-1][:-1]
        victim = " ".join(this.replacePronouns(args[3:]))
        this.sinBot.actions.execcommand('PRIVMSG '+args[2]+' :'+chr(1)+'ACTION '+action+' '+victim+'!'+chr(1),args)

    #TODO: add back in yourself -> hisself and myself->yourself
    # handle punctuation correctly
    # REGEXES!!!!
    def replacePronouns(this, msgList):
        outList = []
        for x in msgList:
            x = x.replace(chr(1),"")
            if not x.isalpha():
                if x.find("me") or x.find("my") or x.find("your"):
                    #cheap replacement!!
                    x = x.replace("me","you").replace("my","your").replace("your","his")
            else:
                if x == "your":
                    x = "his"
                elif x == "my":
                    x = "your"
                elif x == "me":
                    x = "you"
            outList.append(x)
        return outList

    def decodeMorse(this, message):
        retVal = ""
        for x in message.split():
            if reverse_morse_dict.has_key(x):
                retVal = retVal + reverse_morse_dict[x]
        return retVal

    def encodeMorse(this, message):
        retVal = ""
        for x in message.upper():
            print x, morse_dict[x]
            retVal = retVal +" "+ morse_dict[x]
        return retVal
        
    def readBushisms(this):
        sinBot = this.getRootSinBot()
        sinBot.bushisms = []
        bushismUrls = ["http://politicalhumor.about.com/library/blbushisms2000.htm", "http://politicalhumor.about.com/library/blbushisms2001.htm","http://politicalhumor.about.com/library/blbushisms2002.htm","http://politicalhumor.about.com/library/blbushisms2003.htm","http://politicalhumor.about.com/library/blbushisms2004.htm","http://politicalhumor.about.com/library/blbushisms2005.htm","http://politicalhumor.about.com/library/blbushisms2006.htm","http://politicalhumor.about.com/library/blbushisms2007.htm","http://politicalhumor.about.com/library/blbushisms.htm"]
        for url in bushismUrls:
            tags = []
            try:
                tags = this.getPage(url).replace("\n"," ").replace("\r","").split("<")
            except:
                pass
            firstTag = False
            inIsm = False
            curIsm = ""
            
            for tag in tags:
                tag = tag.split(">")
                if tag[0].lower() == "p":
                    firstTag = True
                    inIsm = True
                    if len(tag) > 1:
                        curIsm = curIsm + " " + tag[1].strip()
                elif tag[0].lower() == "/p":
                    inIsm = False
                    firstTag = False
                    this.getRootSinBot().bushisms.append(curIsm.strip())
                    curIsm = ""
                elif inIsm:
                    if firstTag:
                        firstTag = False
                        #a <p> followed by a <i> means we are done with this page
                        if tag[0].lower() == "i":
                            break
                    if len(tag) > 1:
                        curIsm = curIsm + " " + tag[1].strip()

    def getUrban(this, word):
        word = urllib.quote(word)
        print "Urban: " + word
        tags = this.getPage("http://www.urbandictionary.com/define.php?term="+word).replace("\n"," ").replace("\r","").split("<")
        inDef = False
        retVal = ""
        for tag in tags:
            tag = tag.split(">")
            if tag[0].startswith("div class='definition'"):
                print tag
                retVal = tag[1]
                inDef = True
            elif inDef:
                if tag[0].startswith("/div"):
                    return retVal
                elif len(tag) > 1:
                    retVal += tag[1]

    def getAcronym(this, acronym):
        req = urllib2.Request('http://www.acronymfinder.com/~/search/af.aspx?Acronym='+acronym+'&string=exact&Find=find', None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().startswith("h2"):
                return [tag[1].strip()]

    def getRhymes(this, word):
        req = urllib2.Request('http://poetrywithmeaning.com/rhyme/'+word.lower(), None, headers)
        data = this.sinBot.opener.open(req).read()
        retVal = []
        tags = data.split("class=\"rhyme\">")
        for tag in tags:
            tag = tag.split("<")[0]
            retVal.append(tag)
        return retVal[1:]


    def getPhonetrace(this, number):
        areaCode = number[1:4]
        firstThree = number[4:7]
        print "AreaCode: ",areaCode
        print "FirstThree: ",firstThree
        req = urllib2.Request('http://www.areacodedownload.com/'+areaCode+'/'+firstThree+'/index.html', None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        #read until you hit the 4th table, pull all the info from that into a dict, and return the dict
        retVal = {}
        key = ""
        table = 0
        for tag in tags:
            tag = tag.split(">")
            if table == 4:
                print "in table 4"
                if tag[0].lower().startswith("/table"):
                    print "end of table"
                    return retVal
                elif key != "" and tag[1].strip() != "":
                    print "value: ",tag[1].strip()
                    retVal[key] = tag[1].strip()
                    key = ""
                elif key == "" and tag[1].strip() != "":
                    print "Key: ",tag[1].strip().lower()
                    key = tag[1].strip().lower()
            elif tag[0].lower().startswith("table"):
                table = table + 1

    def getSurname(this, name):
        req = urllib2.Request('http://www.surnamedb.com/surname.aspx?name='+"+".join(name), None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().endswith("class=\"surnamehistory\""):
                return tag[1].strip()
                
    def getIptrace(this, acronym):
        req = urllib2.Request('http://www.acronymfinder.com/~/search/af.aspx?Acronym='+acronym+'&string=exact&Find=find', None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().startswith("h2"):
                return [tag[1].strip()]

    def getDefinition(this, word):
        if word.__class__ == [].__class__:
            word = "%20".join(word)
        word = word.lower()
        req = urllib2.Request('http://www.m-w.com/dictionary/'+word, None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")

        retval = {}
        if len(data) == 0:
            return None
        inEntry = False
        inData = False
        dataName = ""
        inDef = False
        subdiv = 0
        tags = data.split("<")
        retval["def"] = ""
        for tag in tags:
            tag = tag.split(">")
            if tag[0].startswith("div"):
                if inEntry:
                    subdiv += 1
                    if tag[0].find('"defs"') > 0:
                        inDef = True
                        retval["def"] = ""
                        try:
                            retval["def"] += tag[1]
                        except:
                            pass
                elif tag[0].find("entry misc") > 0:
                    inEntry = True
            elif tag[0].startswith("/div"):
                if inEntry:
                    if subdiv == 0:
                        inEntry = False
                    else:
                        subdiv -= 1
                        #assuming no sub divs under defs
                        inDef = False
            elif inEntry:
                if inDef:
                    try:
                        retval["def"] += tag[1]+" "
                    except:
                        pass
                elif tag[0].startswith("dd"):
                    try:
                        q1 = tag[0].find('"')+1
                        q2 = tag[0].find('"', q1)
                        dataName = tag[0][q1:q2]
                        retval[dataName] = ""
                        retval[dataName] += tag[1]
                    except:
                        pass
                elif tag[0].startswith("/dd"):
                    dataName = ""
                elif dataName != "":
                    try:
                        retval[dataName] += tag[1]
                    except:
                        pass
        return retval
        
    def getWiktionary(this, word):
        if word.__class__ == [].__class__:
            word = "_".join(word)
        req = urllib2.Request('http://www.wiktionary.org/wiki/'+word, None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")

        retval = {}
        if len(data) == 0:
            print "no lines!"
            return None
        inEntry = False
        inData = False
        dataName = ""
        inDef = False
        defNumber = 0
        tags = data.split("<")
        retval["def"] = ""
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower() == "ol":
                inDef = True
            if inDef:
                print tag[0]
                if tag[0] == "li":
                    defNumber += 1
                    if defNumber > 1:
                        retval["def"] += " "+str(defNumber)+":"
                    else:
                        retval["def"] += str(defNumber)+":"
                elif tag[0] == "dd":
                    retval["def"] += " - "
                elif tag[0].lower() == "/ol":
                    inDef = False
                if len(tag) == 2:
                    retval["def"] += tag[1].replace('\n','')
        return retval

    def getExcuse(this):
        try:
            req = urllib2.Request('http://pages.cs.wisc.edu/~ballard/bofh/bofhserver.pl', None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            if len(lines) == 0:
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e
            return "Service not available"

        try:
            foundOnce = False
            for line in lines:
                print line
                if line.startswith('font size = "+2">'):
                    if foundOnce:
                        print "Returning: "+line.split('>')[1].strip()
                        return line.split('>')[1].strip()
                    else:
                        foundOnce = True

        except Exception, e:
            print "getExcuse exception: ",e
            return "Parsing issue"

        print "t10"

    def getTitle(this, link):
        req = urllib2.Request(link, None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        if len(data) == 0:
            print "no lines!"
            return None
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().startswith("title"):
                return tag[1].strip()
    

    def getCyborg(this, words):
        try:
            req = urllib2.Request('http://cyborg.namedecoder.com/index.php?acronym='+"+".join(words)+'&robotchoice=edox', None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            if len(lines) == 0:
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e
            return "Service not available"

        try:
            for line in lines:
                if line.startswith('p class="mediumheader">'):
                    return line.split('>')[1].strip()

        except Exception, e:
            print "getCyborg exception: ",e
            return "Parsing issue"

        print "t10"

    def getInsult(this, names):
        try:
            req = urllib2.Request('http://www.insult-o-matic.com/insults/?yourname='+"+".join(names)+'&numinsults=1&mode=classic', None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            if len(lines) == 0:
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e
            return "Service not available"

        retVal = ""
        try:
            found = False
            for line in lines:
                if line.startswith('font size=+3>'):
                    if found:
                        retVal = line.split('>')[1].strip()
                    else:
                        found = True
                elif retVal != "":
                    return " ".join((" ".join(names)+", "+retVal.lower()+line.split('>')[1].strip()).split())

        except Exception, e:
            print "getInsult exception: ",e
            return "Parsing issue"

        print "t10"


    def getEtymology(this, word):
        lines = this.getPage('http://www.etymonline.com/index.php?term='+word).split("\n")
        retVal = ""
        for line in lines:
            if line.startswith("<dd"):
                for tag in line.split("<"):
                    tag = tag.split(">")
                    if len(tag) > 1:
                        retVal = retVal + tag[1]
                return retVal

    def getPage(this, link):
        try:
            req = urllib2.Request(link, None, headers)
            return this.sinBot.opener.open(req).read()
        except Exception, e:
            print "getPage() exc eption: ",e
        

    def getStock(this, symbol):
        retVal = {"title":"","curVal":"","delta":"","deltaP":"","high":"","low":"","high52":"","low52":"","volume":"","averagevolume":"","instown":"","marketcap":""}
        try:
            if symbol.lower() == "dji" or symbol.lower() == "^dji":
                req = urllib2.Request('http://finance.google.com/finance?cid=983582', None, headers)
            else:
                req = urllib2.Request('http://finance.google.com/finance?q='+symbol.lower()+'&hl=en', None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            if len(lines) == 0:
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e
            if first:
                return this.getTranslation(phrase,fromL, toL, False)

        try:
            pastVal = ""
            tmpVal = ""
            for line in lines:
                try:
                    tmpVal = line.split(">")[1].strip()
                except:
                    pass
                if line.startswith('title>'):
                    print "title: "+line
                    retVal["title"] = line.split('>')[1].strip()
                elif line.find('_l"') >= 0:
                    print "t9"
#                       return line.split('>')[1]
                    try:
                        retVal["curVal"] = float(line.split('>')[1].strip().replace(",",""))
                    except:
                        pass
                elif line.find('_c"') >= 0:
                    print "_c"
                    try:
                        retVal["delta"] = float(line.split('>')[1].strip().replace(",",""))
                    except:
                        pass
                elif line.find('_cp"') >= 0:
                    print "_cp"
                    try:
                        retVal["deltaP"] = float(line.split('>')[1].strip()[1:-2].replace(",",""))
                    except:
                        pass
                #elif line.find('_hi"') >= 0:
                elif line.find('_el"') >= 0:
                    print "_cp"
                    try:
                        retVal["extCurVal"] = float(line.split('>')[1].strip().replace(",",""))
                    except:
                        pass
                elif line.find('_ec"') >= 0:
                    print "_ec"
                    try:
                        retVal["extDelta"] = float(line.split('>')[1].strip().replace(",",""))
                    except:
                        pass
                elif line.find('_ecp"') >= 0:
                    print "_ecp"
                    try:
                        retVal["extDeltaP"] = float(line.split('>')[1].strip()[1:-2].replace(",",""))
                    except:
                        pass

                elif pastVal.lower() == "range" and tmpVal != "":
                    try:
                        tmpHL = tmpVal.split("-")
                        retVal["high"] = tmpHL[1].strip()
                        retVal["low"] = tmpHL[0].strip()
                    except:
                        print "FAILED reading range high/low values"
                elif pastVal.lower() == "52 week" and tmpVal != "":
                    try:
                        tmpHL = tmpVal.split("-")
                        retVal["high52"] = tmpHL[1].strip()
                        retVal["low52"] = tmpHL[0].strip()
                    except:
                        print "FAILED reading 52 week range high/low values"
                elif pastVal.lower() == "vol / avg." and tmpVal != "":
                    try:
                        tmpHL = tmpVal.split("/")
                        retVal["volume"] = tmpHL[0].strip()
                        retVal["averagevolume"] = tmpHL[1].strip()
                    except:
                        print "FAILED reading vol/avg. values"
                elif pastVal.lower() == "inst. own" and tmpVal != "":
                    retVal["instown"] = tmpVal.strip()
                    print "returning : ",line.split('>')[1]
                    return retVal
                elif pastVal.lower() == "high:" and tmpVal != "":
                    retVal["high"] = tmpVal
                #elif line.find('_hi52"') >= 0:
                elif pastVal.lower() == "52wk high:" and tmpVal != "":
                    retVal["high52"] = tmpVal
                elif pastVal.lower() == "low:" and tmpVal != "":
                #elif line.find('_lo"') >= 0:
                    retVal["low"] = tmpVal
                elif pastVal.lower() == "mkt cap" and tmpVal != "":
                #elif line.find('_mc"') >= 0:
                    retVal["marketcap"] = tmpVal
                elif pastVal.lower() == "52wk low:" and tmpVal != "":
                #elif line.find('_lo52"') >= 0:
                    retVal["low52"] = tmpVal
                elif pastVal.lower() == "volume:" and tmpVal != "":
                #elif line.find('_vo"') >= 0:
                    print "_vo"
                    retVal["volume"] = line.split('>')[1].strip()
                if tmpVal != "":
                    pastVal = tmpVal
        except Exception, e:
            print "getStock exception: ",e
            return None

        print "t10"
        return retVal


    def getWeather(this, search):
        retVal = {}
        try:
            print "getting weather page"
            req = urllib2.Request('http://www.wunderground.com/cgi-bin/findweather/getForecast?query='+"+".join(search), None, headers)
            page = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
            print "done"
            if page.find("<title>Search for") > 0:
                #if this search returned multiple results then run through and grab the first result
                print "SEARCH PAGE"
                lines = page.split("<")
                found = False
                for line in lines:
                    if found:
                        print "searching for ahref in: "+line
                        if line.find("a href") >= 0:
                            print "FOUND LINK"
                            req = urllib2.Request('http://www.wunderground.com'+line.split('"')[1], None, headers)
                            page = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
                            break
                    elif line.find('"blueBox"') >= 0:
                        print "FOUND KEY"
                        found = True
                        
            lines = page.split("<")
            if len(lines) == 0:
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e
            if first:
                return this.getTranslation(phrase,fromL, toL, False)

        try:
            id = None
            for line in lines:
                if line.startswith('title>'):
                    retVal["title"] = line.split('>')[1].strip()
                if not retVal.has_key("conditions") and line.find('class="condIcon"') >= 0:
                    print "CONDITIONS: "+line
                    retVal["conditions"] = line.split('alt="')[1].split('"')[0]
                if id == None and line.find('pwsid="') >= 0:
                    id = line.split('pwsid="')[1].split('"')[0]
                if id != None and line.find('pwsid="'+id+'"') >= 0:
                    try:
                        retVal[line.split('pwsvariable="')[1].split('"')[0]] = line.split('value="')[1].split('"')[0]
                    except Exception, e:
                        print "getWeather exception!",e

        except Exception, e:
            print "getWeather exception: ",e
            return None

        return retVal


    def getTranslation(this, phrase, fromL, toL, first = True):
        print "t1"
        try:
            print "t2"
            phrasetr = phrase[:]
            toLtr = languageMap[toL.lower()]
            fromLtr = languageMap[fromL.lower()]
        except:
            print "t3"
            phrasetr = [toL]+phrase[:]
            toLtr = languageMap[fromL.lower()]
            fromLtr = "en"
        if not first:
            print "t4"
            print "Retrying: "+fromL+", "+toL
        text = "+".join(phrasetr)
        retVal = ""
        lines = []
        try:
            print "t5"
#            req = urllib2.Request('http://babelfish.altavista.com/tr?tt=urltext&doit=done&intl=1&trtext='+text+'&lp='+fromLtr+'_'+toLtr, None, headers)
            req = urllib2.Request('http://babelfish.yahoo.com/translate_txt?tt=urltext&fr=bf-res&ei=UTF-8&btnTrTxt=Translate&doit=done&intl=1&trtext='+text+'&lp='+fromLtr+'_'+toLtr, None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            if len(lines) == 0:
                print "t6"
                print "len(lines) = 0!"
                if first:
                    return this.getTranslation(phrase,fromL, toL, False)
                return None
        except Exception, e:
            print "Connection issue: ",e
            if first:
                return this.getTranslation(phrase,fromL, toL, False)

        try:
            print "t7"
            for line in lines:
                if line.find('style="padding:0.6em;"') > 0:
                    print "t9"
#                    print "returning : ",line.split('style=padding:10px;>')[1].split('<')[0]
                    print "returning : ",line.split('style="padding:0.6em;"')[1].split('<')[0]
#                    return line.split('style=padding:10px;>')[1].split('<')[0]
                    return line.split('style="padding:0.6em;"')[1][1:].split('<')[0]

        except Exception, e:
            print "getTranslation exception: ",e
            if first:
                return this.getTranslation(phrase,fromL, toL, False)
            return None

        print "t10"

    def getPirate(this, phrase):
        print "t1"
        text = "+".join(phrase)
        retVal = ""
        try:
            print "t5"
            req = urllib2.Request('http://www.talklikeapirateday.com/translate/index.php', None, headers)
            lines = this.sinBot.opener.open(req,"text="+text+"&submit=Translate&debug=0").read().replace("\r","").split("\n")
            if len(lines) == 0:
                print "t6"
                print "len(lines) = 0!"
                return None
        except Exception, e:
            print "Connection issue: ",e

        try:
            print "t7"
            for line in lines:
                if line.find('<p><b>Pirate Speak:</b></p>') == 0:
                    print line
                    return " ".join(line[27:-8].strip().split())

        except Exception, e:
            print "getTranslation exception: ",e
            return None
        return retVal
        print "t10"

    def getQuotes(this, user, chan = "#hfc"):
        chan = chan.lower()
        user = user.lower()
        try:
            retVals = file("/home/syrae/sinBot-free/logs/"+chan+"/"+user).readlines()
            return retVals
        except:
            pass
        command = 'cat "./'+chan+'.Opsware.log" | grep -e "^\[[^)]\+\] <'+user+'> [^(]" -i'
        output = os.popen(command)
        print command
        
        line = output.readline()

        retVals = []
        while line != None and line != '':
            retVals.append(line)
            line = output.readline()
        output.close()
        return retVals

                
    def getLol(this, phrase):
        req = urllib2.Request('http://speaklolcat.com/?from='+phrase.upper().replace(" ","+").replace('"','\\"'), None, headers)
        lines = this.sinBot.opener.open(req).read().replace("\r","").split("\n")

        foundIntro = False
        inLol = False
        for x in lines:
            if x.startswith("<div id=\"text\">"):
                foundIntro = True
            elif foundIntro:
                if not inLol:
                    if x.strip().startswith("<p>"):
                        inLol = True
                else:
                    if x.strip().startswith("<p>"):
                        return x.replace("<p>","").replace("</p>","").strip()

        return ""

    def getTwitterSearch(this, terms, number = 3):
        tags = this.getPage("http://search.twitter.com/search?q="+"+".join(terms)).replace('\r','').replace('\n',' ').split("<")
        specificUser = terms[0].lower().startswith("from:")
        #'div class="msg"'
        inMessage = False
        retVal = []
        curMessage = ""
        for tag in tags:
            tag = tag.split(">")
            if tag[0].startswith('div class="msg"'):
                print "In Message!"
                inMessage = 1
            elif inMessage:
                print tag[1]
                print curMessage
                if inMessage == 1:
                    print "Username!"
                    if not specificUser:
                        curMessage = "&lt;"+tag[1].strip()+"&gt;"
                    inMessage += 1
                elif inMessage == 2:
                    inMessage += 1
                elif tag[0].startswith("/span"):
                    curMessage = curMessage +" "+tag[1].strip()
                    retVal.append(htmldecode(curMessage))
                    if len(retVal) >= number:
                        return retVal
                    curMessage = ""
                    inMessage = False
                else:
                    curMessage = curMessage +" "+tag[1].strip()
        return retVal
        
    def getNames(this, query):
        this.sinBot.gettingNames = True
        
        try:
            this.sinBot.namesInfo = None
            this.sinBot.actions.execcommand('NAMES '+query, [])
            i = 20
            while i > 0:
                i = i - 1
                try:
                    if this.sinBot.namesInfo["locked"]:
                        time.sleep(1)
                    else:
                        try:
                            retVal = this.sinBot.namesInfo["results"]
                        except Exception, e:
                            print "FAIL exception!: ",e
                            retVal = None
                            break
                        this.sinBot.namesInfo = None
                        this.sinBot.gettingNames = False
                        return retVal
                except Exception, e:
                    print "IGNORED Exception! getNames(): ",e
                    time.sleep(1)
        except Exception, e:
            print "Exception! getNames(): ",e
            pass
        this.sinBot.gettingNames = False


    def getWho(this, query, caller = True):
        if caller:
            return this.getRootSinBot().commands.getWho(query, False)
        try:
            while this.sinBot.gettingWho:
                time.sleep(1)
        except:
            print "gettingWho not set, setting to true and continuing"
            pass
        this.sinBot.gettingWho = True
        
        try:
            this.sinBot.whoInfo = None
            this.sinBot.actions.execcommand('WHO '+query, [])
            i = 20
            while i > 0:
                i = i - 1
                try:
                    if this.sinBot.whoInfo["locked"]:
                        time.sleep(1)
                    else:
                        try:
                            retVal = this.sinBot.whoInfo["results"]
                        except Exception, e:
                            print "FAIL exception!: ",e
                            retVal = None
                            break
                        this.sinBot.whoInfo = None
                        this.sinBot.gettingWho = False
                        return retVal
                except Exception, e:
                    print "IGNORED Exception! getWho(): ",e
                    time.sleep(1)
        except Exception, e:
            print "Exception! getWho(): ",e
            pass
        this.sinBot.gettingWho = False
        try:
            return this.sinBot.child.commands.getWho(query, False)
        except:
            pass

    def getWhois(this, user):
        print "Getting WHOIS for " + user
        if not hasattr(this.getRootSinBot(),"whoisInfo"):
            this.getRootSinBot().whoisInfo = {}
        print "Getting WHOIS for " + user
        try:
            while this.sinBot.gettingWhois:
                time.sleep(1)
        except:
            pass
        this.sinBot.gettingWhois = True
        print "Getting WHOIS for " + user
        try:
            this.getRootSinBot().whoisInfo[user.lower()] = None
            this.getRootSinBot().whoisInfo["locked"] = True
            this.sinBot.actions.execcommand('WHOIS '+user, [])
            i = 5
            while(i > 0):
                i = i - 1
                try:
                    if this.getRootSinBot().whoisInfo["locked"]:
                        time.sleep(1)
                    else:
                        retVal = dict(this.getRootSinBot().whoisInfo)
                        this.sinBot.gettingWhois = False
                        return retVal
                except Exception, e:
                    print "Exception! getWhois(): ",e
                    time.sleep(1)
        except:
            pass
        this.sinBot.gettingWhois = False
        
    def getSurname(this, name):
        req = urllib2.Request('http://www.surnamedb.com/surname.aspx?name='+"+".join(name), None, headers)
        data = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","")
        tags = data.split("<")
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().endswith("class=\"surnamehistory\""):
                return tag[1].strip()
    def getGooglefight(this,phrase1, phrase2):
        retVal = [{},{}]
        req = urllib2.Request('http://googlefight.com/query.php?lang=en_GB&word1='+"+".join(phrase1.split())+'&word2='+"+".join(phrase2.split()), None, headers)
        data = this.sinBot.opener.open(req).read()
    
        tags = data.split("<")
        inCaption = False
        wordNum = 0
        scoreNum = 0
        for tag in tags:
            try:
                if inCaption:
                    if tag.startswith("b"):
                        retVal[wordNum]["word"] = htmldecode(tag.split(">")[1].strip())
                        wordNum += 1
                    elif tag.startswith("span"):
                        retVal[scoreNum]["score"] = tag.split(">")[1].split()[0].strip()
                        scoreNum += 1
                    if wordNum > 1 and scoreNum > 1:
                        return retVal
                else:
                    if tag.startswith("caption"):
                        inCaption = True
            except:
                pass

        return retVal

    def getGoogle(this, phrase):
        retVal = {"results":[],"quickresult":[]}
        phrase = phrase.replace("+","%2B")
        req = urllib2.Request('http://www.google.com/search?ie=UTF-8&q='+"+".join(phrase.split()), None, headers)
        data = this.sinBot.opener.open(req).read()

        tags = data.split("<")
        foundResult = False
#        count = 60
        foundLink = False
        gettingData = False
        gettingClock = False
        result = ""
        for tag in tags:
#            print tag
            tag = tag.split(">")
            if foundResult and not retVal.has_key("result_count"):
                print "Result0!"
                retVal["result_count"] = int(tag[1].strip().replace(",",""))
                #for now just return when you find the result count
                foundResult = False
            elif len(tag) > 1 and tag[1].strip() == "of about":
                print "Result1!"
                foundResult = True
            if tag[0].lower().find('chc=localtime') >= 0:
                print "Getting clock"
                gettingClock = True
            if foundLink or gettingData or gettingClock:
                if tag[0].lower().find('chc=localtime') >= 0:
                    print "Getting clock"
                    gettingClock = True
                foundLink = False
                if (not gettingData) and (tag[0].find('"') >= 0):
                    print "Found 1!: ",tag[0]
                    retVal["results"].append(tag[0].split('"')[1])
                elif len(tag) > 1:
                    print "Found 2!: ",tag[0]
                    if tag[0].lower().strip() == "sup":
                        result = result + "^"
                    result = result + tag[1]
                    gettingData = True
                if gettingData and gettingClock:
                    if tag[0].lower().startswith("br") or tag[0].lower().find("table") >= 0:
                        retVal["quickresult"].append(result)
                        result = ""
                        gettingData = False
                        gettingClock = False
                elif gettingData and tag[0].lower().startswith("/h2"):
                    print "END ANSWER!"
                    retVal["quickresult"].append(result)
                    result = ""
                    gettingData = False
                    
            elif tag[0].find("class=r") >= 0:
                print "Found link!"
                foundLink = True
#            elif len(tag) > 1 and not tag[1].strip() == "" and count > 0:
#                print tag[1]
#                count = count - 1
        return retVal
        
    def getImdbSynopsis(this, imdbId):
        req = urllib2.Request('http://www.imdb.com/title/'+imdbId+'/plotsummary', None, headers)
        data = this.sinBot.opener.open(req).read()

        tags = data.split("<")
        foundResult = False
        count = 60
        foundLink = False
        isList = True
        for tag in tags:
            tag = tag.split(">")


    def getImdbQuotes(this, imdbId):
        req = urllib2.Request('http://www.imdb.com/title/'+imdbId+'/quotes', None, headers)
        data = this.sinBot.opener.open(req).read()
        retVal = []

        tags = data.split("<")
        foundResult = False
        count = 60
        curQuote = None
        curLine = ""
        for tag in tags:
            tag = tag.split(">")
            if tag[0].lower().find('a name="qt') >= 0:
                if curLine.strip() != "":
                    curQuote.append(curLine.strip())
                if curQuote != None and len(curQuote) > 0:
                    retVal.append(curQuote)
                curQuote = []
                curLine = ""
            elif curQuote != None:
                if tag[0].lower().strip() == "br" and curLine.strip() != "":
                    curQuote.append(curLine.strip())
                    curLine = ""
                elif len(tag) > 1:
                    curLine = curLine + tag[1].replace("\n"," ").replace("\r","")
            if tag[0].lower().find("h3") == 0:
                if curLine.strip() != "":
                    curQuote.append(curLine)
                if len(curQuote) > 0:
                    retVal.append(curQuote)
                return retVal
        return retVal
            

    #just returns the first match for a string
    def findImdb(this, phrase):
        req = urllib2.Request('http://www.imdb.com/find?s=tt&q='+"+".join(phrase.split()), None, headers)
        data = this.sinBot.opener.open(req).read()

        tags = data.split("<")
        foundResult = False
        count = 60
        foundLink = False
        isList = True
        for tag in tags:
            tag = tag.split(">")
            if tag[0].strip().lower() == "title":
                if tag[1].lower().find("imdb title search") < 0:
                    isList = False
                    print "NOT A LIST!: ",tag[1]
            if isList:
                if foundLink:
                    if tag[0].lower().find("/title/") >= 0:
                        return tag[0].split("/")[2].strip()
                elif len(tag) > 1 and tag[1].lower().find("displaying") >= 0 and tag[1].lower().find("result") >= 0:
                    foundLink = True
            else:
                if len(tag) > 1 and tag[0].lower().find("id=tt") >= 0:
                    return "tt"+tag[0].lower().split("id=tt")[1].split(";")[0].strip()
#            if len(tag) > 1 and not tag[1].strip() == "" and count > 0:
#                print tag[1]
#                count = count - 1

    def shellsafe(this,shellStr):
        return shellStr.replace(' ','').replace(';','').replace('`','').replace('(','').replace(')','').replace('[','').replace('&','').replace('>','').replace('..','').replace('^','').replace('*','').replace('@','').replace('=','').replace('~','')


    def getLogfight(this,phrase1, phrase2, chan):
        retVal = [{},{}]
        command = 'grep -i "'+phrase1.replace('"','\\"').strip()+'" /home/syrae/sinBot-free/logs/'+chan.replace(";","").replace("&","").replace("$","").lower()+'/* | wc -l'
        output = os.popen(command)
        print command
        retVal[0]["score"] = output.readline().strip()
        retVal[0]["word"] = phrase1
        output.close()
        command = 'grep -i "'+phrase2.replace('"','\\"').strip()+'" /home/syrae/sinBot-free/logs/'+chan.replace(";","").replace("&","").replace("$","").lower()+'/* | wc -l'
        output = os.popen(command)
        print command
        retVal[1]["score"] = output.readline().strip()
        retVal[1]["word"] = phrase2
        output.close()
        return retVal


    #this version almost works, but it tuurns out the API doesn;t let you search for "a" or "the" or similar items, whereas the website does
    def getGooglefightBeta(this,phrase1, phrase2):
        retVal = [{},{}]
        retVal[0]["word"] = phrase1
        try:
            retVal[0]["score"] = commas(google.doGoogleSearch(phrase1).meta.estimatedTotalResultsCount)
        except:
            retVal[0]["score"] = "0"
        retVal[1]["word"] = phrase2
        try:
            retVal[1]["score"] = commas(google.doGoogleSearch(phrase2).meta.estimatedTotalResultsCount)
        except:
            retVal[1]["score"] = "0"
        return retVal

    def cReplace(this, args):
        msgpart = " ".join(args[3:])
        print "msgpart: "+msgpart
        search = msgpart.strip().split("/")[1]
        print "search: "+search
        replace = msgpart.strip().split("/")[2]
        print "replace: "+replace
        msg = "/".join(msgpart.split("/")[3:])
        this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+re.sub(search, replace, msg).replace("\n","\\n").replace("\r","\\r"), args)

    #just a loop that checks pastebin every 5 minutes for new posts
    def pastebinLoop(this):
        try:
            req = urllib2.Request('http://pastebin.com/', None, headers)
            lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
            found = False
            number = 1
            for line in lines:
                if found:
                    if line.find("a href=\"http://") >= 0:
                        number = int(line.split("=",3)[2].split('"',1)[0])
                        break
                elif line.find("Recent Posts") >= 0:
                    found = True
        except Exception, e:
            print "Exception in pastebin loop! ",e
            print "exiting!"
            return
        while(1):
            time.sleep(1*this.getRootSinBot().registerMap["pastebin-interval"])
            try:
                newNumber = number + 1
                while newNumber > number:
                    
                    req = urllib2.Request('http://pastebin.com/pastebin.php?show='+str(number+1), None, headers)
                    lines = this.sinBot.opener.open(req).read().replace("\n"," ").replace("\r","").split("<")
                    found = False
                    for line in lines:
                        if found:
                            print "found recent, looking for URL"
                            if line.find("a href=\"http://") >= 0:
                                newNumber = int(line.split("=",3)[2].split('"',1)[0])
                                print "Latest post: "+str(number)
                                found = False
                                print "found URL, unestting 'found'"
                        elif line.find("Recent Posts") >= 0:
                            print "found recent posts"
                            found = True
                        if line.find("Posted by") >= 0:
                            print "found 'posted by': "+line
                            name = line.split()[2]
                            number += 1
                            print "posted by: "+name
                            chan = ""
                            if name.find("-") >=0:
                                chan = name.split("-",1)[1]
                                name = name.split("-",1)[0]
                            if chan == "":
                                this.getRootSinBot().commands.respondToList(name+" just posted to pastebin: http://pastebin.com/pastebin.php?show="+str(number), this.getRootSinBot().registerMap["pastebin"], [])
                                this.getRootSinBot().commands.channelSend(name+" just posted to pastebin: http://pastebin.com/pastebin.php?show="+str(number), this.getRootSinBot().registerMap["pastebin"], [])
                            else:
                                if chan[0] != "#":
                                    chan = "#"+chan
                                if not chan in this.sinBot.userList.keys():
                                    for x in this.sinBot.userList.keys():
                                        if x.startswith(chan):
                                            chan = x
                                            break
                                this.getRootSinBot().commands.channelSend(name+" just posted to pastebin: http://pastebin.com/pastebin.php?show="+str(number), [chan], [])
                            break
            except Exception, e:
                print "Exception in pastebing update loop! ", e
                print "http://pastebin.com/pastebin.php?show="+str(number)


    def channelSend(this, text, chans, args):
        try:
            for x in chans:
                if x.startswith("#") and (this.sinBot.NICK.lower() in this.sinBot.userList[x] or "@"+this.sinBot.NICK.lower() in this.sinBot.userList[x]):
                    try:
                        this.sinBot.actions.execcommand('PRIVMSG '+x+' :'+text, args.copy())
                    except:
                        this.sinBot.actions.execcommand('PRIVMSG '+x+' :'+text, args)
            this.sinBot.child.commands.channelSend(text, chans, args)
        except Exception, e:
            print "Exception in channelSend(): ",e

    def respondToList(this, text, users, args):
        for x in users:
            if not x.startswith("#"):
                try:
                    this.sinBot.actions.execcommand('PRIVMSG '+x+' :'+text, args.copy())
                except:
                    this.sinBot.actions.execcommand('PRIVMSG '+x+' :'+text, args)


    def respond(this, text, args):
        if text.strip() == "":
            text = "no"
        try:
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+text, args.copy())
        except:
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+text, args)
    def action(this, text, args):
        try:
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+chr(1)+'ACTION '+text+chr(1),args.copy())
        except:
            this.sinBot.actions.execcommand('PRIVMSG '+args.chan+' :'+chr(1)+'ACTION '+text+chr(1),args)

    def __init__(this, bot):
        Commands.VERSION="v.5"
        print "Loading Commands "+Commands.VERSION
        this.sinBot = bot
        this.sinBot.commandThreadMap = {}
        this.sinBot.commandMap = {}
        this.sinBot.helpMap = {}
        proxyHandler = urllib2.ProxyHandler(this.sinBot.proxies)
        this.sinBot.opener = urllib2.build_opener(proxyHandler)
        this.sinBot.headers = headers

        for x in dir(this):
            if x[0] == "c" and x[1].isupper():
                command = x[1:].lower()
                #print "loading command: "+command
                this.sinBot.commandMap[command] = this.__getattribute__(x)
                doc = this.__getattribute__(x).func_doc
                if doc != None:
                    this.sinBot.helpMap[command] = doc
            elif x[0] == "t" and x[1].isupper():
                command = x[1:].lower()
                #print "loading threaded command: "+command
                this.sinBot.commandThreadMap[command] = this.__getattribute__(x)
                doc = this.__getattribute__(x).func_doc
                if doc != None:
                    this.sinBot.helpMap[command] = doc
         
        try:
            this.sinBot.weatherMap.keys()
        except:
            this.sinBot.weatherMap = {}
        this.sinBot.weatherMap["10.10.7"] = "#nc vpn"
        this.sinBot.weatherMap["192.168.22"] = "#ca vpn"
        this.sinBot.weatherMap["10.10"] = "KRDU"
        this.sinBot.weatherMap["192.168"] = "KSJC"
        this.sinBot.weatherMap["10.128"] = "KNYC"
        this.sinBot.weatherMap["10.255"] = "KBFI"
        this.sinBot.weatherMap["10.44"] = "EGKK" #uk
        this.sinBot.weatherMap["lon"] = "EGKK" #uk
        this.sinBot.weatherMap["ny"] = "KNYC"
        this.sinBot.weatherMap["nc"] = "KRDU"
        this.sinBot.weatherMap["ca"] = "KSJC"
        this.sinBot.weatherMap["wa"] = "KBFI"
        
        try:
            if hasattr(this.sinBot, "parent"):
                this.sinBot.rouletteMap = this.sinBot.parent.rouletteMap
                print "LOADED PARENT!"
            this.sinBot.rouletteMap.keys()
        except:
            this.sinBot.rouletteMap = {}

        try:
            if hasattr(this.sinBot, "parent"):
                this.sinBot.bushisms = this.sinBot.parent.bushisms
                print "LOADED PARENT!"
            len(this.sinBot.whenList)
        except:
            this.sinBot.bushisms = []
            this.readBushisms()

        try:
            this.sinBot.icaoMap.keys()
        except:
            this.sinBot.icaoMap = {}
            this.sinBot.icaoMap["A"] = "ALPHA"
            this.sinBot.icaoMap["N"] = "NOVEMBER"
            this.sinBot.icaoMap["B"] = "BRAVO"
            this.sinBot.icaoMap["O"] = "OSCAR"
            this.sinBot.icaoMap["C"] = "CHARLIE"
            this.sinBot.icaoMap["P"] = "PAPA"
            this.sinBot.icaoMap["D"] = "DELTA"
            this.sinBot.icaoMap["Q"] = "QUEBEC"
            this.sinBot.icaoMap["E"] = "ECHO"
            this.sinBot.icaoMap["R"] = "ROMEO"
            this.sinBot.icaoMap["F"] = "FOXTROT"
            this.sinBot.icaoMap["S"] = "SIERRA"
            this.sinBot.icaoMap["G"] = "GOLF"
            this.sinBot.icaoMap["T"] = "TANGO"
            this.sinBot.icaoMap["H"] = "HOTEL"
            this.sinBot.icaoMap["U"] = "UNIFORM"
            this.sinBot.icaoMap["I"] = "INDIA"
            this.sinBot.icaoMap["V"] = "VICTOR"
            this.sinBot.icaoMap["J"] = "JULIET"
            this.sinBot.icaoMap["W"] = "WHISKY"
            this.sinBot.icaoMap["K"] = "KILO"
            this.sinBot.icaoMap["X"] = "X-RAY"
            this.sinBot.icaoMap["L"] = "LIMA"
            this.sinBot.icaoMap["Y"] = "YANKEE"
            this.sinBot.icaoMap["M"] = "MIKE"
            this.sinBot.icaoMap["Z"] = "ZULU"


#        Commands.releaseMap = {}
#        this.releaseMap = Commands.releaseMap
        # this.sinBot.OLGANICK = 'olga'

        this.in_encoding = sys.getdefaultencoding()
        this.out_encoding = sys.getdefaultencoding()
        # if not hasattr(this.getRootSinBot(), "pastebinThread"):
            # this.getRootSinBot().pastebinThread = thread.start_new_thread(this.pastebinLoop,())
        #if not hasattr(this.getRootSinBot(), "registerMap"):
        #    this.getRootSinBot().registerMap = {'pastebin':set(),'pastebin-interval':10}
#        this.getRootSinBot().registerMap['pastebin-interval'] = "bob"

def grep(grepArgs, listToGrep, limit = 30):
    print "grep!"
    finalList = listToGrep[:]
    for arg in grepArgs:
#        print "grepping for: '"+arg+"'"
        for x in finalList[:]:
            if isinstance(x, list):
                found = False
                if len(x) > limit:
                    finalList.remove(x)
                else:
                    for line in x:
                        if line.lower().find(arg.lower()) >= 0:
                            found = True
                    if not found:
                        finalList.remove(x)
            else:
                if x.lower().find(arg.lower()) < 0:
#                    print "removing: "+x
                    finalList.remove(x)
#                else:
#                    print x+" HAD THE STRING: "+arg
    return finalList


def parseArgs(args):
    curArg = ""
    argList = []
    inQuote = False
    for x in args:
        if x[0] == '"' or inQuote:
            inQuote = ( x[-1] != '"' )
            if not inQuote:
                curArg += x[x[0]=='"':-1]+" "
            else:
                curArg += x[x[0]=='"':]+" "
        else:
            curArg = x
        if not inQuote:
            argList.append(curArg.strip())
            curArg = ""
    print argList
    return argList

def htmldecode(html):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(html)
    return p.save_end()


def htmldecodeSpolak(html):
    retval = ""
    curIndex = 0
    while curIndex < len(html):
        ampIndex = html.find("&",curIndex)
        if ampIndex == -1:
            return retval + html[curIndex:]
        semiIndex = html.find(";",ampIndex)
        if semiIndex == -1:
            return retval + html[curIndex:]
        retval += html[curIndex:ampIndex]
        print "checking: "+html[ampIndex:semiIndex+1]
        if htmlentitydefs.entitydefs.has_key(html[ampIndex:semiIndex+1]):
            retval += htmlentitydefs.entitydefs[html[ampIndex:semiIndex+1]]
        elif htmlentitydefs.entitydefs.has_key(html[ampIndex+1:semiIndex]):
            retval += htmlentitydefs.entitydefs[html[ampIndex+1:semiIndex]]
        else:
            retval += html[ampIndex:semiIndex+1]
        curIndex = semiIndex+1
    return retval

def commas(number):
    number = str(number)
    retval = ""
    while len(number) > 3:
        retval = ","+number[-3:]+retval
        number = number[:-3]
    return number + retval

class LeetMap:
    def __init__(this):
        this.map = {}

    def __setitem__(this, key, value):
        try:
            if len(key) > 1:
                cur = this.map[key.lower()]
            else:
                cur = this.map[key]
        except:
            cur = []
        cur.append(value)
        this.map[key] = cur

    def __getitem__(this, key):
        try:
            cur = this.map[key]
            return cur[int(random.random() * 100000)%len(cur)]
        except:
            if len(key) > 1:
                retVal = ""
                for x in key:
                    retVal += this[x]
                return retVal
            else:
                return key
def secondsToTime(ut):
    retVal = {}
    retVal["seconds"] = int(ut % 60)
    ut = int(ut / 60)
    retVal["minutes"] = int(ut % 60)
    ut = int(ut / 60)
    retVal["hours"] = int(ut % 24)
    ut = int(ut / 24)
    retVal["days"] = int(ut % 365)
    retVal["years"] = int(ut /365)
    stringTime = ""
    comma = ""
    if retVal["years"] > 1:
        stringTime += comma + str(retVal["years"]) + " years"
        comma = ", "
    if retVal["days"] > 0:
        stringTime += comma + str(retVal["days"]) + " days"
        comma = ", "
    if retVal["hours"] > 0:
        stringTime += comma + str(retVal["hours"]) + " hours"
        comma = ", "
    if retVal["minutes"] > 0:
        stringTime += comma + str(retVal["minutes"]) + " minutes"
        comma = ", "
    if retVal["seconds"] > 0:
        stringTime += comma + str(retVal["seconds"]) + " seconds"
        comma = ", "
    retVal["string"] = stringTime
    return retVal

ponderings = \
["I think so, Brain, but where are we going to find a duck and a hose at this hour?",
"I think so, but where will we find an open tattoo parlor at this time of night?",
"Wuh, I think so, Brain, but if we didn't have ears, we'd look like weasels.",
"Uh... yeah, Brain, but where are we going to find rubber pants our size?",
"Uh, I think so, Brain, but balancing a family and a career ... ooh, it's all too much for me.",
"Wuh, I think so, Brain, but isn't Regis Philbin already married?",
"Wuh, I think so, Brain, but burlap chafes me so.",
"Sure, Brain, but how are we going to find chaps our size?",
"Uh, I think so, Brain, but we'll never get a monkey to use dental floss.",
"Uh, I think so Brain, but this time, you wear the tutu.",
"I think so, Brain, but culottes have a tendency to ride up so.",
"I think so, Brain, but if they called them 'Sad Meals', kids wouldn't buy them!",
"I think so, Brain, but me and Pippi Longstocking -- I mean, what would the children look like?",
"I think so, Brain, but this time *you* put the trousers on the chimp.",
"Well, I think so, Brain, but I can't memorize a whole opera in Yiddish.",
"I think so, Brain, but there's still a bug stuck in here from last time.",
"Uh, I think so, Brain, but I get all clammy inside the tent.",
"I think so, Brain, but I don't think Kay Ballard's in the union.",
"Yes, I am!",
"I think so, Brain, but, the Rockettes? I mean, it's mostly girls, isn't it?",
"I think so, Brain, but pants with horizontal stripes make me look chubby.",
"Well, I think so -POIT- but *where* do you stick the feather and call it macaroni?",
"Well, I think so, Brain, but pantyhose are so uncomfortable in the summertime.",
"Well, I think so, Brain, but it's a miracle that this one grew back.",
"Well, I think so, Brain, but first you'd have to take that whole bridge apart, wouldn't you?",
"Well, I think so, Brain, but 'apply North Pole' to what?",
"I think so, Brain, but 'Snowball for Windows'?",
"Well, I think so, Brain, but *snort* no, no, it's too stupid!",
"Umm, I think so, Don Cerebro, but, umm, why would Sophia Loren do a musical?",
"Umm, I think so, Brain, but what if the chicken won't wear the nylons?",
"I think so, Brain, but isn't that why they invented tube socks?",
"Well, I think so Brain, but what if we stick to the seat covers?",
"I think so Brain, but if you replace the 'P' with an 'O', my name would be Oinky, wouldn't it?",
"Oooh, I think so Brain, but I think I'd rather eat the Macarana.",
"Well, I think so *hiccup*, but Kevin Costner with an English accent?",
"I think so, Brain, but don't you need a swimming pool to play Marco Polo?",
"Well, I think so, Brain, but do I really need two tongues?",
"I think so, Brain, but we're already naked.",
"We eat the box?",
"Well, I think so, Brain, but if Jimmy cracks corn, and no one cares, why does he keep doing it?",
"I think so, Brain *NARF*, but don't camels spit a lot?",
"I think so, Brain, but how will we get a pair of Abe Vigoda's pants?",
"I think so, Brain, but Pete Rose? I mean, can we trust him?",
"I think so, Brain, but why would Peter Bogdanovich?",
"I think so, Brain, but isn't a cucumber that small called a gherkin?",
"I think so, Brain, but if we get Sam Spade, we'll never have any puppies.",
"I think so, Larry, and um, Brain, but how can we get seven dwarves to shave their legs?",
"I think so, Brain, but calling it pu-pu platter? Huh, what were they thinking?",
"I think so, Brain, but how will we get the Spice Girls into the paella?",
"I think so, Brain, but if we give peas a chance, won't the lima beans feel left out?",
"I think so, Brain, but if we had a snowmobile, wouldn't it melt before summer?",
"I think so, Brain, but what kind of rides do they have in Fabioland?",
"I think so, Brain, but can the Gummi Worms really live in peace with the Marshmallow Chicks?",
"Wuh, I think so, Brain, but wouldn't anything lose it's flavor on the bedpost overnight?",
"I think so, Brain, but three round meals a day wouldn't be as hard to swallow.",
"I think so, Brain, but if the plural of mouse is mice, wouldn't the plural of spouse be spice?",
"Umm, I think so, Brain, but three men in a tub? Ooh, that's unsanitary!",
"Yes, but why does the chicken cross the road, huh, if not for love?  (sigh)  I do not know.",
"Wuh, I think so, Brain, but I prefer Space Jelly.",
"Yes Brain, but if our knees bent the other way, how would we ride a bicycle?",
"Wuh, I think so, Brain, but how will we get three pink flamingos into one pair of Capri pants?",
"Oh Brain, I certainly hope so.",
"I think so, Brain, but Tuesday Weld isn't a complete sentence.",
"I think so, Brain, but why would anyone want to see Snow White and the Seven Samurai?",
"I think so, Brain, but then my name would be Thumby.",
"I think so, Brain, but I find scratching just makes it worse.",
"I think so, Brain, but shouldn't the bat boy be wearing a cape?",
"I think so, Brain, but why would anyone want a depressed tongue?",
"Um, I think so, Brain, but why would anyone want to Pierce Brosnan?",
"Methinks so, Brain, verily, but dost thou think Pete Rose by any other name would still smell as sweaty?",
"I think so, Brain, but wouldn't his movies be more suitable for children if he was named Jean-Claude van Darn?",
"Wuh, I think so, Brain, but will they let the Cranberry Dutchess stay in the Lincoln Bedroom?",
"I think so, Brain, but why does a forklift have to be so big if all it does is lift forks?",
"I think so, Brain, but if it was only supposed to be a three hour tour, why did the Howells bring all their money?",
"I think so, Brain, but Zero Mostel times anything will still give you Zero Mostel.",
"I think so, Brain, but if we have nothing to fear but fear itself, why does Elanore Roosevelt wear that spooky mask?",
"I think so, Brain, but what if the hippopotamus won't wear the beach thong?",
]
        

leetDict = LeetMap()
leetDict['a'] = "@"  
leetDict['a'] = "a"  
leetDict['E'] = "3"
leetDict['b'] = "6"
leetDict['b'] = "B"
leetDict['b'] = "b"
leetDict['e'] = "3"
leetDict['e'] = "e"
leetDict['e'] = "e"
leetDict['h'] = "4"
leetDict['h'] = "h"
leetDict['h'] = "h"
leetDict['h'] = "H"
leetDict['H'] = "4"
leetDict['i'] = "1"
leetDict['i'] = "i"
leetDict['i'] = "i"
leetDict['i'] = "l"
leetDict['l'] = "1"
leetDict['l'] = "L"
leetDict['o'] = "0"
leetDict['s'] = "5"
leetDict['s'] = "s"
leetDict['s'] = "s"
leetDict['s'] = "s"
leetDict['s'] = "S"
leetDict['t'] = "7"
leetDict['t'] = "t"
leetDict['t'] = "t"
leetDict['t'] = "T"
leetDict['v'] = "\/"
leetDict['!'] = "1"
leetDict['!'] = "!"
leetDict['!'] = "!"
leetDict['you'] = "u"
leetDict['to'] = "2"
leetDict['two'] = "2"
leetDict['too'] = "2"
leetDict['for'] = "4"
leetDict['the'] = 'teh'
leetDict['the'] = 't3h'
leetDict['what'] = 'wut'
leetDict['what'] = 'wat'
leetDict['sucks'] = 'sux'
leetDict['suck'] = 'suxor'

languageMap = {}
languageMap["english"] = "en"
languageMap["chinese"] = "zh"
languageMap["chinese-trad"] = "zt"
languageMap["chinese-simple"] = "zh"
languageMap["dutch"] = "nl"
languageMap["french"] = "fr"
languageMap["german"] = "de"
languageMap["greek"] = "el"
languageMap["italian"] = "it"
languageMap["japanese"] = "ja"
languageMap["korean"] = "ko"
languageMap["portugese"] = "pt"
languageMap["russian"] = "ru"
languageMap["spanish"] = "es"


"""
A set of morse code characters.
"""
#
#   characters.py -- Character collections.
#   Copyright (C) 2002 Christian Hje
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

morse_dict = {
    'A': '.-',
    'B': '-...',
    'C': '-.-.',
    'D': '-..',
    'E': '.',
    'F': '..-.',
    'G': '--.',
    'H': '....',
    'I': '..',
    'J': '.---',
    'K': '-.-',
    'L': '.-..',
    'M': '--',
    'N': '-.',
    'O': '---',
    'P': '.--.',
    'Q': '--.-',
    'R': '.-.',
    'S': '...',
    'T': '-',
    'U': '..-',
    'V': '...-',
    'W': '.--',
    'X': '-..-',
    'Y': '-.--',
    'Z': '--..',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    '0': '-----',
    '.': '.-.-.-',   #<AAA>
    ',': '--..--',   #<MIM>
    '?': '..--..',   #<IMI>
    '/': '-..-.',    #<DN>
    '+': '.-.-.',    #<AR> End of Message
    '*': '...-.-',   #<SK> End of Work
    '=': '-...-',    #<BT>
    ' ': '-...-',    #<BT>
    ';': '-.-.-.',   #<KR>
    ':': '---...',   #<OS>
    "'": '.----.',   #<WG>
    '"': '.-..-.',   #<AF>
    '-': '-....-',   #<DU>
    '_': '..--.-',   #<IQ>
    '$': '...-..-',  #<SX>
    '(': '-.--.',    #<KN>
    ')': '-.--.-',   #<KK>
    '&': '.-...',    #<AS> Wait
    '!': '...-.',    #<SN> Understood
    '%': '-.-.-',    #<KA> Starting Signal
    '@': '........', #<HH> Error
    '#': '.-.-..',   #<AL> Paragraph
    }
reverse_morse_dict = {
    '.-': 'A',
    '-...': 'B',
    '-.-.': 'C',
    '-..': 'D',
    '.': 'E',
    '..-.': 'F',
    '--.': 'G',
    '....': 'H',
    '..': 'I',
    '.---': 'J',
    '-.-': 'K',
    '.-..': 'L',
    '--': 'M',
    '-.': 'N',
    '---': 'O',
    '.--.': 'P',
    '--.-': 'Q',
    '.-.': 'R',
    '...': 'S',
    '-': 'T',
    '..-': 'U',
    '...-': 'V',
    '.--': 'W',
    '-..-': 'X',
    '-.--': 'Y',
    '--..': 'Z',
    '.----': '1',
    '..---': '2',
    '...--': '3',
    '....-': '4',
    '.....': '5',
    '-....': '6',
    '--...': '7',
    '---..': '8',
    '----.': '9',
    '-----': '0',
    '.-.-.-': '.',   #<AAA>
    '--..--': ',',   #<MIM>
    '..--..': '?',   #<IMI>
    '-..-.': '/',    #<DN>
    '.-.-.': '+',    #<AR> End of Message
    '...-.-': '*',   #<SK> End of Work
    '-...-': ' ',    #<BT>
    '-.-.-.': ';',   #<KR>
    '---...': ':',   #<OS>
    '.----.': "'",   #<WG>
    '.-..-.': '"',   #<AF>
    '-....-': '-',   #<DU>
    '..--.-': '_',   #<IQ>
    '...-..-': '$',  #<SX>
    '-.--.': '(',    #<KN>
    '-.--.-': ')',   #<KK>
    '.-...': '&',    #<AS> Wait
    '...-.': '!',    #<SN> Understood
    '-.-.-': '%',    #<KA> Starting Signal
    '........': '@', #<HH> Error
    '.-.-..': '#',   #<AL> Paragraph
    }

ARRL_list = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?+*=/'
ARRL_lessons = ( 'AERN+T',
         'IOSDHC',
         'UY.LMPG',
         'F,WB=J/',
         'KQXVZ?*',
         '12345',
         '67890' )

# Koch Method Lessons
KOCH_lessons = ( 'KMRSUA',
         'PTLOWI',
         '.NJE0FY',
         ',VG5/Q',
         '9ZH38B',
         '?427C1',
         'D6X=*+' )

ARRL_prosigns = '.,?+*=/'


#a list of lists regexes to convert python code to java
#if the first element in the list is matched and replace, then attempt the rest of the ones in the list
python2java = [
[["print ([^#]*)","System.out.println(\\1)"],[",","+"]],
[["([^0-9\t ][^\t ]*)[\t ]*=[\t ]*([0-9]\+)", "int \\1 = \\2;\\3"]],
[["([^0-9\t ][^\t ]*)[\t ]*=[\t ]*(['\"].*['\"])", "String \\1 = \\2;"]],
[["([^0-9\t ][^\t ]*)[\t ]*=[\t ]*([\[])(.*)([\]])", "List \\1 = new ArrayList(\\3);"],["List ([^0-9\t ][^\t ]*) = new ArrayList\(([^\)]+)\);","List \\1 = new ArrayList();\n\\1.add(\\2);"]],
[["([^0-9\t ][^\t ]*)[\t ]*=[\t ]*([{])(.*)([}])", "Map \\1 = new HashMap(\\3);"]],


[["#","//"]],
]
