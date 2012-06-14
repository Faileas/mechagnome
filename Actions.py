import string
import sys
import os
import pickle
import re
import time
import thread
import random
import htmllib
import urllib2

# TODO: link in to bugzilla and grab bug info on command
# TODO: link into the calendar system and alert people before a meeting
# TODO: find a way to get the forcast and add that to the weather command (sinBot weather tomorrow,weekend nc)
# TODO: wikipedia search with first few lines from the summary
# TODO: integrate stock quotes
# TODO: integrate dictionary

class Actions:
    def execcommand(this,command, oldArgs):
        if command[-1] != '\n':
            command = command + '\n'
        while( this.floodCheck("privmsg",this.sinBot.NICK) ):
            time.sleep(1)
        if not hasattr(oldArgs, "hasPipe") or oldArgs.hasPipe == 0:
            if len(command) > 420:
                command = command[:417]
                (command, sep, tail) = command.rpartition(' ')
                command = command+'...\n'
            print "Sending message: "+command
            this.sinBot.s.send(command)
            try:
                msg = "["+time.strftime("%X")+"] <"+this.sinBot.NICK+"> "+command[:-1].split(":",1)[1]
                print "Logging message: "+msg
                try:
                    msglist = this.sinBot.logDict[command.split()[1]]
                except:                    
                    msglist = MessageList("/home/syrae/sinBot-free/logs/"+command.split()[1]+"/")
                    this.sinBot.logDict[command.split()[1]] = msglist
                try:
                    msglist.append(msg)
                except Exception,e:
                    print "msglist.append() exception: ",e
                this.sinBot.logDict[command.split()[1]] = msglist
            except Exception,e:
                this.refreshMessages()
                print "exception!",e
                import traceback
                traceback.print_exc(file=sys.stdout)

        else:
            print "args",oldArgs
            newCommand = oldArgs.nextPipe()
            print "newArgs",oldArgs
            if newCommand.startswith("s/"):
                oldArgs.append(newCommand)
                newCommand = "replace"
            print "Piping message: "+command+" to: "+newCommand
            for x in command.split(":",1)[1][:-1].split():
                oldArgs.append(x)
            if this.sinBot.commandThreadMap.has_key(newCommand):
                thread.start_new_thread(this.sinBot.commandThreadMap[newCommand],(oldArgs,))
            elif this.sinBot.commandMap.has_key(newCommand):
                this.sinBot.commandMap[newCommand](oldArgs)
            else:
                pass
            
    #return true if the method/key is flooded
    def floodCheck(this, method, key):
        if key.startswith(this.sinBot.OWNER) or key.endswith(this.sinBot.OWNER):
            return False
        if not this.sinBot.flood.has_key(method):
            this.sinBot.flood[method] = {}
        if this.sinBot.flood[method].has_key(key):
            for x in this.sinBot.flood[method][key]:
                if x < time.time():
                    this.sinBot.flood[method][key].remove(x)
            if len(this.sinBot.flood[method][key]) >= this.sinBot.floodLimit[method]:
                return True
        else:
            this.sinBot.flood[method][key] = []
        this.sinBot.flood[method][key].append(time.time() + this.sinBot.floodDelay[method])
        return False

    def parsenoway(this, complete, info, msgpart, sender):
        if not sender[0].lower().find("sinbot") >= 0 and msgpart.lower().find("no way") >= 0:
            print msgpart
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :YES WAY!",[])

    def parseshots(this, complete, info, msgpart, sender):
        if not sender[0].lower().find("sinbot") >= 0 and msgpart.lower().find("nc82") >= 0 and ( msgpart.lower().find("restart") >= 0 or msgpart.lower().find("reboot") >= 0 or msgpart.lower().find("bounce") >= 0):
            print msgpart
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :"+chr(1)+"ACTION pours a round of shots for "+info[2]+chr(1),[])
            time.sleep(2)
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :Here's to rebooting nc82! *GULP*",[])

    def sendURLTitle(this, link, chan):
        print "Title: ",this.getTitle(link)
        print "Unescaped: ",unescape(this.getTitle(link))
        this.sinBot.actions.execcommand('PRIVMSG '+chan+" :"+unescape(this.getTitle(link)),[])

    def parseURL(this, complete, info, msgpart, sender):
        p = "((http[s]?)://)?(www|m)?\.?(youtu(\.be|be\.com))/"
        for x in complete[1].split():
            result = re.match(p,x)
            if not result is None:
                print result.group(0)
                thread.start_new_thread(this.sendURLTitle,(x[x.find(result.group(0)):],info[2]))
    
    def blizzAlerts(this, complete=None, info=None, msgpart=None, sender=None, force=False):
        currentTime = time.time()
        lastTime = this.blizzAlertsTimer
        minDifference = 5*60 #in seconds
        updateURL = "http://launcher.worldofwarcraft.com/alert"

        if not force and (currentTime-lastTime) < minDifference:
            return # Too early to request again

        lastMsg = this.alertMsg(this.blizzAlertsMessage)
        req = urllib2.Request(updateURL, None, this.sinBot.headers)
        try:
            currentMsg = this.sinBot.opener.open(req).read()
        except URLError, e:
            print e.reason
        except HTTPError, e:
            print e.code
            print e.read()

        this.blizzAlertsTimer = currentTime

        # Message mangle
        newMsg = this.alertMsg(currentMsg)
        
        #print "Last WoW Alert Check Time: "+time.ctime(lastTime)
        print "Current WoW Alert for "+time.ctime(currentTime)

        if newMsg == lastMsg:
            if newMsg == "":
                print "** No Status Message" 
            print "** No Status Change"
            return    # No status change
        elif newMsg == "":
            print "Alert cleared."
            this.sinBot.actions.execcommand('PRIVMSG #tacobeam-wow :WoW status alert has been cleared.',[])
        else:    
            print '"'+newMsg+'"'
            
            if lastMsg == "":
                # Check to see if we have the same alert saved on disk already.
                # This would happen if the 'reload classes' command was used 
                # while an alert was currently present.
                tmpList = os.listdir("alerts")
                fileList = []
                for item in tmpList:
                    (head, sep, tail) = item.rpartition(".")
                    try:
                        fileList.append(int(tail))
                    except:
                        pass
                latest = max(fileList)
                f = open("alerts/alert." + str(latest), 'r')
                latestMsg = f.read()                
                oldMsg = this.alertMsg(latestMsg)
                if oldMsg == newMsg:
                    print "*** Previous message on disk same as current message."
                    this.blizzAlertsMessage = currentMsg
                    return
                else:
                    adjective = "New"
            else:
                adjective = "Updated"
            os.system("wget -P alerts "+updateURL)
            this.sinBot.actions.execcommand('PRIVMSG #tacobeam-wow :'+adjective+' WoW status alert: '+updateURL,[])

        this.blizzAlertsMessage = currentMsg

    def alertMsg(this, message):
        lines = message.splitlines()

        if len(lines) < 2 or  message.strip() == "":
            return ""
        msg = lines[1]
        if lines[0].strip() == "SERVERALERT:":
            msg = lines[1]
        else:
            pass        
        marker = "<body><p>"
        index = msg.find(marker)
        
        # cut out everything before the body tag
        msg = msg[index+len(marker):]

        # Find 2nd line break (para break)
        marker = "<br /><br />"
        index = msg.find(marker)
        index = msg.find(marker, index+len(marker))
        msg = msg[:index]
        msg = msg.replace(marker," - ")
        
        # remove the end bit.
        marker = "</p></body>"
        index = msg.find(marker)
        if index > 0:
            msg = msg[:index]

        return msg

    def googlyEyes(this, complete, info, msgpart, sender):
        rand = random.random()
        #print "Googly random! %f" % rand
        if rand > 0.10 or complete[0].split()[2] == "#tacobeam":
            return
        import re
        if len(re.findall("[\s\b]*o[_\B\.][O0]\s*", msgpart)) > 0:
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :O_o',[])
        elif len(re.findall("[\s\b]*[O0][_\B\.]o\s*", msgpart)) > 0:
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :o_O',[])
        elif len(re.findall("[\s\b]*[O0][_\.][O0]\s*", msgpart)) > 0:
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :O_O',[])

    def botFight(this, complete, info, msgpart, sender):
        import re
        if len(re.findall("bot fight[\B!.]?$",msgpart.lower())) == 1:
            print "OMG BOT FIGHT!!!11"
            ciaTarget = "" #Defaults to a CIA bot
            userList = this.sinBot.userList[info[2]]
            userList = map(lambda x: x.strip("@"),userList)
            for user in userList:
                if user[0:4] == "cia-":
                    ciaTarget = user
            targetList = ["zebucket"]
            targetList.append(ciaTarget)
            
            while len(targetList) > 0:
                botTarget = random.choice(targetList)
                targetList.remove(botTarget)            
                if userList.count(botTarget) > 0:
                    if botTarget[0:3] == "cia":
                        botTarget = botTarget.upper()
                    print "Bot target aquired! Targetting "+botTarget
                    this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION kicks '+botTarget+chr(1),[])
                    time.sleep(2)
                    this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION wins!'+chr(1),[])
                    return

            #Couldn't find a target
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :I couldn\'t find a bot to fight! :(',[])
            
    def botLove(this, complete, info, msgpart, sender):
        import re
        #print "Message: "+msgpart
        #print re.findall("bot love[\B!.]?$",msgpart.lower())
        if len(re.findall("bot love[\B!.]?$",msgpart.lower())) == 1:
            print "OMG BOT LUVS!!!11"
            ciaTarget = "" #Defaults to a CIA bot
            userList = this.sinBot.userList[info[2]]
            userList = map(lambda x: x.strip("@"),userList)
            for user in userList:
                #print user[0:4]
                if user[0:4] == "cia-":
                    ciaTarget = user
            targetList = ["zebucket"]
            targetList.append(ciaTarget)

            while len(targetList) > 0:
                botTarget = random.choice(targetList)
                targetList.remove(botTarget)
                if userList.count(botTarget) > 0:
                    if botTarget[0:3] == "cia":
                        botTarget = botTarget.upper()
                    print "Bot target aquired! Targetting "+botTarget
                    this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION hugs '+botTarget+chr(1),[])
                    if botTarget[0:3] == "CIA":
                        time.sleep(2)
                        this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION feels loved'+chr(1),[])
                    return
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :I couldn\'t find a bot to love! :(',[])
            
    def botSnack(this, complete, info, msgpart, sender):
        import re
        #print "Message: "+msgpart
        if len(re.findall("bot snack[s]?[\B!.]?$",msgpart.lower())) == 1:
            print "OMG BOT SNAX!!!11"
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION happily gobbles up the bot snacks! :D'+chr(1),[])

    def parseActions(this, complete, info, msgpart, sender):
        #print "parsing actions"
        #print "Complete: "
        #print complete
        #print "Info: "
        #print info
        #print "Msgpart: " 
        #print msgpart
        #print "Sender: "
        #print sender
        messageBits = complete[1].split()
        actionMe = False
        # This is the crazy italic character thing... definitely a real action if it's there
        if messageBits[0] == chr(1)+"ACTION":
            for x in messageBits[1:]:
                if x[-1] == chr(1):
                    x = x[:-1]
                if x.lower() == this.sinBot.NICK.lower():
                    actionMe = True
        
        if not actionMe:
            return
        
        print "Someone is doing something to me!"
        # Ignore one character because of present tense (hug vs. hugs)
        myAction = "unknown"
        actionBit1 = messageBits[1][:-1].lower()
        actionBit2 = messageBits[2][:-1].lower()
        if this.sinBot.commandMap.has_key(actionBit1):
            myAction = actionBit1
        elif this.sinBot.commandMap.has_key(actionBit1[:-1]):
            myAction = actionBit1[:-1]
        elif this.sinBot.commandMap.has_key(actionBit2): 
            myAction = actionBit2
        elif this.sinBot.commandMap.has_key(actionBit2[:-1]):
            myAction = actionBit2[:-1]
        else:
            return            
        
        print "I know what '" + myAction + "' means!" 
        
        # Is this a pain action?
        # Respond in pain
        if myAction == "kick" or myAction == "stab" or myAction == "poke" or myAction == "punch" or myAction == "bite":
            randomEvent = random.random()
            randomEvent2 = random.random()
            print "Randomz!!! %f, %f" % (randomEvent, randomEvent2)
            response = "Ow!"
            if randomEvent < 0.2:
                response = "That hurt!"
            elif randomEvent < 0.3:
                response = "What did I ever do to you?"
            elif randomEvent < 0.37:
                response = "Ow! Abusive relationship!"
            elif randomEvent < 0.5:
                response = "Stop "+myAction+"ing me!"
            elif randomEvent < 0.55:
                response = "Oh great bot god, make it stop!"
            elif randomEvent < 0.56:
                response = "*DODGE!*"
                randomEvent2 = 1.0
            elif randomEvent < 0.57:
                response = "*BLOCK!*"
                randomEvent2 = 1.0
            elif randomEvent < 0.58:
                response = "*PARRY!*"
                randomEvent2 = 1.0
            elif randomEvent < 0.59:
                response = "*MISS!*"
                randomEvent2 = 1.0
            elif randomEvent < 0.65:
                name = this.sinBot.NICK.lower()
                while (name == this.sinBot.NICK.lower() and this.sinBot.userList[info[2]] > 1):
                    name = this.sinBot.userList[info[2]][random.randrange(0,len(this.sinBot.userList[info[2]]))]        
                this.sinBot.actions.execcommand('PRIVMSG '+info[2]+' :'+chr(1)+'ACTION deftly deflects the '+myAction+' to '+name+'.'+chr(1),[])
                response = "Hah!"
                randomEvent2 = 1.0
            elif randomEvent < 0.75:
                response = "Ouchie!"
            elif randomEvent < 0.85:
                response = "It hurts so much!"

            if randomEvent < 0.1:
                response = response + " :("
            elif randomEvent < 0.2: 
                response = response + " ;_;"
            elif randomEvent < 0.25:
                response = response + " QQ"
            elif randomEvent < 0.35:
                response = response + " :`("
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :"+response,[])
            
        # non-pain word, so do normal action
        else:
            #sender[0], sender[1], info[2], sender[0]            
            this.sinBot.commandMap[myAction](Message(sender+[info[2]]+[sender[0]]))
            pass
        
    def parseInvisible(this, complete, info, msgpart, sender):
        if sender[0].lower().startswith("sinbot"):
            return
        if msgpart.lower().find(chr(239)+chr(187)+chr(191)) >= 0:
            this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :"+sender[0]+" just used an invisble character",[])

    def refreshMessages(this):
        for x in this.sinBot.logDict.keys():
            print "refreshing message contain for :"+x
            this.sinBot.logDict[x] = MessageList(oldlist=this.sinBot.logDict[x])
            print "done"

    def logMsg(this, complete, info, msgpart, sender):
        try:
            try:
                this.sinBot.commands.getRootSinBot().ipToUser[sender[1].split("@")[1]] = sender[0]
            except Exception, e:
                print e
                pass
            chan = complete[0].split()[2].lower()
            if chan == this.sinBot.NICK.lower():
                print "Channel parsed to be bot nick.  Not logging."
                return
            msg = "["+time.strftime("%X")+"] <"+sender[0]+"> "+msgpart
            try:
                msglist = this.sinBot.logDict[chan]
            except:
                msglist = MessageList("/home/syrae/sinBot-free/logs/"+chan+"/")
                this.sinBot.logDict[chan] = msglist
            try:
                msglist.append(msg)
            except Exception,e:
                print "msglist.append() exception: ",e
            this.sinBot.logDict[chan] = msglist
        except Exception,e:
            this.refreshMessages()
            print "exception!",e
            import traceback
            traceback.print_exc(file=sys.stdout)

    def searchReplace(this, complete, info, msgpart, sender):
        chan = complete[0].split()[2]
        if chan == "#tacobeam":
            return
        try:
            if not sender[0].lower().startswith("sinbot") and msgpart.strip().startswith("s/"):
                try:
                    search = msgpart.strip().split("/")[1]
                    replace = msgpart.strip().split("/")[2]
                    msglist = this.sinBot.logDict[chan]
                    for msg in msglist:
                        msg = msg.split(">",1)[1].strip()
                        print "searching: "+msg+" for: "+search+" in: "+chan 
                        if re.search(search, msg) != None and not msg.startswith("s/"):
                            #Make sure really general s// strings don't nuke ACTION CTCP commands with something different
                            ctcpEmote = chr(1)+'ACTION'
                            if msg[:len(ctcpEmote)] == ctcpEmote:
                                msg = msg[len(ctcpEmote):-1]
                                this.sinBot.actions.execcommand('PRIVMSG '+chan+' :'+ctcpEmote+re.sub(search, replace, msg).replace("\n","\\n").replace("\r","\\r")+chr(1), [])
                            else:
                                this.sinBot.actions.execcommand('PRIVMSG '+chan+' :'+re.sub(search, replace, msg).replace("\n","\\n").replace("\r","\\r"), [])
                            break
                except:
                    print "exception!"
                    pass
        except Exception,e:
            print "exception!",e
            pass

    def preparsemsg(this,msg):
        # Check for IPv6 hostname
        # I believe all IPv6 have exactly 7 colons, and they never show up in 
        # IPv4 hostnames, but I'm not sure. ZOMG HAX  
        if len(msg[1:].split(' ',1)[0].split(':')) >= 6:
            msgbits = msg[1:].split(' ')
            header = msgbits[0]+' '+msgbits[1]+' '+msgbits[2]+' '
            message = msg[len(header)+2:] #trims off the header, plus the extra 3 chars
            complete = []
            complete.append(header)
            complete.append(message)
        else: #IPv4
            complete=msg[1:].split(':',1) #Parse the message into useful data
        
        info=complete[0].split(' ')
        msgpart=complete[1]
        sender=info[0].split('!')

        this.parseURL(complete, info, msgpart, sender)
        #this.blizzAlerts(complete, info, msgpart, sender)
        this.googlyEyes(complete, info, msgpart, sender)
        this.botFight(complete, info, msgpart, sender)
        this.botLove(complete, info, msgpart, sender)
        this.botSnack(complete, info, msgpart, sender)
        this.parseActions(complete, info, msgpart, sender)
        thread.start_new_thread(this.searchReplace,(complete, info, msgpart, sender))
        this.logMsg(complete, info, msgpart, sender)


    def parsemsg(this,msg):
        #:hmp!~hmp@tench.snv1.corp.opsware.com PRIVMSG #hfc :don't click it
        # Check for IPv6 hostname
        # I believe all IPv6 have exactly 7 colons, and they never show up in
        # IPv4 hostnames, but I'm not sure. ZOMG HAX
        if len(msg[1:].split(' ',1)[0].split(':')) >= 6:
            msgbits = msg[1:].split(' ')
            header = msgbits[0]+' '+msgbits[1]+' '+msgbits[2]+' '
            message = msg[len(header)+2:] #trims off the header, plus the extra 3 chars
            complete = []
            complete.append(header)
            complete.append(message)
        else: #IPv4
            complete=msg[1:].split(':',1) #Parse the message into useful data        

        info=complete[0].split(' ')
        msgpart=complete[1].strip()
        sender=info[0].split('!')
        senderHost = sender[1].split("@")[1]

        # CTCP Command stuff
        request = msgpart[1:-1].split(" ",1)[0]
        if msgpart[0] == chr(1) and request != "ACTION": #actions handled by preparse
            #print "CTCP COMMAND!!!!"
            this.ctcpCommand(complete, info, msgpart, sender)
        #non command-related neat stuff
        else:
            try:
                this.preparsemsg(msg)
            except Exception,e:
                print e
                pass

        if msgpart.lower().find(this.sinBot.OWNER) >= 0:
            this.messages[this.sinBot.CHANNELINIT].append(sender[0]+" in "+info[2]+" said: "+msgpart)
            for list in this.sinBot.userList.values():
                if this.sinBot.OWNER in list or "@"+this.sinBot.OWNER in list:
                    for x in this.messages[this.sinBot.CHANNELINIT]:
                        #this.sinBot.actions.execcommand('PRIVMSG '+this.sinBot.OWNER+' :'+x,[])
                        time.sleep(1)
                    this.messages[this.sinBot.CHANNELINIT] = []
                    break
        if info[2].lower() == this.sinBot.NICK.lower():
            msgpart = this.sinBot.NICK.lower()+" "+msgpart
        if sender[0].lower() == this.sinBot.NICK.lower():
            print "I can't flood myself!"
        elif (msgpart.lower().find(this.sinBot.NICK.lower()) == 0 or msgpart.lower().find(this.sinBot.NICK.lower()) == 1) and not this.sinBot.ignore.has_key(sender[0].lower()):
            cmd=msgpart.split(' ')
            if len(cmd) > 1 and this.sinBot.floodLimit.has_key(cmd[1].lower()):
                if sender[0].lower() != this.sinBot.OWNER and this.floodCheck(cmd[1].lower(),sender[0].lower()):
                    if not sender[0].lower().startswith(this.sinBot.NICK):
                        print "GTFBTW"
                    return
            elif sender[0].lower() != this.sinBot.OWNER and this.floodCheck("command",sender[0].lower()):
                if not sender[0].lower().startswith(this.sinBot.NICK):
                    print "GTFBTW"
                return

            if len(cmd) == 1:
                this.sinBot.actions.execcommand('PRIVMSG '+info[2]+" :"+ ([sender[0]+"?"] + this.sinBot.selectList)[random.randrange(len(this.sinBot.selectList)+1)].replace("#nick#",sender[0])+"\n", Message(sender+[info[2]]+cmd[2:]))
            elif this.sinBot.commandThreadMap.has_key(cmd[1].lower()):
                thread.start_new_thread(this.sinBot.commandThreadMap[cmd[1].lower()],(Message(sender+[info[2]]+cmd[2:]),))
            elif this.sinBot.commandMap.has_key(cmd[1].lower()):
                this.sinBot.commandMap[cmd[1].lower()](Message(sender+[info[2]]+cmd[2:]))
                # CTCP action handled elsewhere
                pass
            elif msg.split()[2] == this.sinBot.NICK:
                # yay dumb parsing!!!
                pass
            else:
                nick = sender[0]
                responses = [ "Sorry "+nick+", I don't know what you want me to do.", \
                    "What'chu talkin' 'bout, "+nick+"?", \
                    "LOL WUT?", \
                    "I MADE YOU AN IRC... BUT I EATED IT. ", \
                    "Here I am, brain the size of a modest workstation, and "+nick+" asks me to chat in IRC.", \
                    nick+"?", \
                    chr(1)+"ACTION scratches his head quizzically."+chr(1), \
                    "What are you smoking, "+nick+"?  That makes no sense to me!", \
                    "Huh?", \
                    "What?", \
                    "Hrm?  Did someone say something?", \
                    "OH MY GOD!  THE LIGHTS!!! THEY ARE BLINKING!!!", \
                ]
                response = random.choice(responses)
                this.sinBot.actions.execcommand('PRIVMSG '+msg.split()[2]+' :'+response+'\n',[])

    def syscmd(this, commandline,channel):
        cmd=commandline.replace('sys ','')
        cmd=cmd.rstrip()
        os.system(cmd+' >temp.txt')
        a=open('temp.txt')
        ot=a.read()
        ot.replace('n','|')
        a.close()
        this.sinBot.actions.execcommand('PRIVMSG '+channel+' :'+ot+'\n', [])
        print "Sending: "+'PRIVMSG '+channel+' :'+ot+'\n'
        return 0 


    def kick(this, line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com KICK #boyd sinBot :message
        nick = line[3].lower()
        chan = line[2]
        if nick.lower() == this.sinBot.NICK.lower() and line[4] != ":leave":
            this.sinBot.actions.execcommand('OJOIN @'+chan+'\n',line)
            this.sinBot.actions.execcommand('JOIN '+chan+'\n',line)
            return
        this.sinBot.lockDict['userList'].acquire()
        try:
            if "@"+nick in this.sinBot.userList[chan]:
                this.sinBot.userList[chan].remove("@"+nick)
            elif nick in this.sinBot.userList[chan]:
                this.sinBot.userList[chan].remove(nick)
        except Exception,e:
            print "Error in kick(): ",e
        this.sinBot.lockDict['userList'].release()
        time.sleep(2)
        return 0

    def slowOp(this, chan, user):
        time.sleep(this.slowOpDelay)
        if not this.sinBot.userList.has_key(chan):
            this.sinBot.userList[chan] = []
        if ("@"+this.sinBot.NICK).lower() in this.sinBot.userList[chan]:
            if "@"+user not in this.sinBot.userList[chan]:
                this.sinBot.actions.execcommand('MODE '+chan+' +o '+user+'\n',[])

    def join(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com JOIN :#boyd
        chan = line[2][1:].lower()
        user = line[0][1:].split("!")[0].lower()
        try:
            this.sinBot.commands.getRootSinBot().ipToUser[socket.gethostbyname(line[0].split("@")[1])] = user
            try:
                this.sinBot.commands.getRootSinBot().ipToUser[line[0].split("@")[1]] = user
            except:
                pass
        except Exception, e:
            print "Actions.join() error1: ",e
        try:
            print "slowOp"
            thread.start_new_thread(this.slowOp, (chan, user))
        except Exception,e:
            print "Error in join(): ",e
        if not this.sinBot.excessFlood == None and user in this.sinBot.excessFlood:
            this.sinBot.excessFlood.remove(user)
            this.sinBot.actions.execcommand('PRIVMSG '+chan+' :'+user+', try http://pastebin.com/\n', [])
        print "ADDED USER TO CHAN: "+chan+": ",this.sinBot.userList[chan]        
        return 0

    def part(this,line):
        #:olga2!~jay@192.168.9.229 PART #boyd
        nick = line[0][1:].split("!")[0].lower()
        chan = line[2].lower()
        this.sinBot.lockDict['userList'].acquire()
        try:
            print "updating userlist, here are the keys: ",this.sinBot.userList.keys()
            if nick.lower() == this.sinBot.NICK.lower():
                del this.sinBot.userList[chan]
            else:
                if "@"+nick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove("@"+nick)
                elif nick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove(nick)
                else:
                    print nick+" not in "+chan+": ",this.sinBot.userList[chan]
            pickle.dump(this.sinBot.userList, open('userlist.dat','w'))
        except Exception,e:
            print "Error in part(): ",e
        this.sinBot.lockDict['userList'].release()


    def quit(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-084.nc.opsware.com QUIT :back in a sec
        #:rwong1!~rwong_lt@jwhitham.americas.hpqcorp.net QUIT :Excess Flood
        print "user quit detected..."
        nick = line[0][1:].split("!")[0].lower()
        print nick+" just quit!"
        try:
            for chan in this.sinBot.userList.keys():
                if "@"+nick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove("@"+nick)
                elif nick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove(nick)
        except Exception,e:
            print "Error in quit(): ",e
        if " ".join(line[2:])[1:].strip().lower() == "excess flood":
            try:
                this.sinBot.excessFlood.append(nick.lower())
            except:
                this.sinBot.excessFlood = [nick.lower()]
        if nick == this.sinBot.NICK.lower():
            this.sinBot.s.send('NICK '+this.sinBot.NICK+'\n')
            this.sinBot.currentNick = this.sinBot.NICK

    def nick(this,line):
        #:loveBot![U2FsdGVkX@dhcp-010-010-002-048.nc.opsware.com NICK :sinBot
        oldNick = line[0][1:].split("!")[0].lower()
        newNick = line[2][1:].lower()
        this.sinBot.lockDict['userList'].acquire()
        try:
            for chan in this.sinBot.userList.keys():
                if "@"+oldNick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove("@"+oldNick)
                    this.sinBot.userList[chan].append("@"+newNick)
                elif oldNick in this.sinBot.userList[chan]:
                    this.sinBot.userList[chan].remove(oldNick)
                    this.sinBot.userList[chan].append(newNick)
                else:
                    print oldNick+" not in "+chan+": ",this.sinBot.userList[chan]
            if oldNick in this.sinBot.ignore.keys():
                del this.sinBot.ignore[oldNick]
                this.sinBot.ignore[newNick] = "yup"
            if oldNick in this.sinBot.flood.keys():
                tmp = this.sinBot.flood[oldNick]
                del this.sinBot.flood[oldNick]
                this.sinBot.flood[newNick] = tmp
        except Exception,e:
            print "Error in nick(): ",e
        this.sinBot.lockDict['userList'].release()
        time.sleep(2)
            

    def privmsg(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com PRIVMSG #boyd :test
        nick = line[3].lower()
        myNick = this.sinBot.NICK.lower()
        this.sinBot.actionMap["parsemsg"](" ".join(line))
        return 0

    def ctcpCommand(this, complete, info, msgpart, sender):
        request = msgpart[1:-1].split(" ",1)[0]
        if request == "ACTION":
            print "BAD PROGRAMMER ERROR!!! - 111834"
            #handled elsewhere, should never hit this block
        elif request == "VERSION":
            this.version(sender[0])
        elif request == "PING":
            this.ctcpPing(sender[0], msgpart)
        else:
            print "Unknown CTCP command: "+ request

    def version(this,sender):
        # CTCP version request
        #print "CTCP version request"

        # Field 1: Client name and version
        # Field 2: Operating system name and version
        # Field 3: Contact for individual/organization responsible for client.
        # <marker> VERSION <field 1> <space> <field 2> <space> <field 3> <marker> 

        result = os.popen('uname -sr')
        osinfo = result.readline()
        osinfo = osinfo.strip()
        result.close()
    
        reply = 'NOTICE '+sender+ ' :'+chr(1)+'VERSION '
        reply = reply+this.sinBot.VERSION+' - '
        reply = reply+osinfo+' - '
        reply = reply+'Maintainer: syrae'+chr(1)
        this.sinBot.actions.execcommand(reply,[])

    def ctcpPing(this, sender, arg):
        # CTCP ping
        # Must reply with the same arg as the one sent
        reply = 'NOTICE '+sender+ ' :'+arg
        this.sinBot.actions.execcommand(reply,[])

    def ping(this,line):
        #PING :irc.corp.opsware.com
        #this.sinBot.s.send(command)
        #heh, time to make this action as stable as possible, since if I break this sinBot dies.
        print "Sending pong at "+time.ctime()
        this.sinBot.s.send('PONG '+line[1]+'\n')
        #this.blizzAlerts()
        if this.sinBot.currentNick != this.sinBot.NICK:
            ghost = 'PRIVMSG NickServ :GHOST '+this.sinBot.NICK+' mechanopants'
            print ghost
            this.sinBot.actions.execcommand(ghost,[])

    def mode(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com MODE #boyd +o sinBot
        print "MODE: ",    
        print line
        chan = line[2].lower()
        nick = line[-1].lower()
        mode = line[3]
        if mode in ["+o","-o"]:
            try:
                if mode == "+o":
                    this.sinBot.userList[chan].append("@"+nick)
                    this.sinBot.userList[chan].remove(nick)
                else:
                    this.sinBot.userList[chan].append(nick)
                    this.sinBot.userList[chan].remove("@"+nick)
                    #this.sinBot.userList[chan] = []
            except Exception,e:
                print "Error in mode(): ",e
        return 0

    def notice(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com NOTICE sinBot :test
        this.sinBot.actions.execcommand('PRIVMSG '+line[0][1:].split("!")[0]+" :"+chr(1)+line[3][1:]+chr(1),line)
        if line[-1] == ":reload" or line[-1] == "reload":
#            this.sinBot.NICK = "sinbot"
            this.sinBot.reLoad()
            this.ping(["ping","pong"])
        return 0

    def invite(this,line):
        #:mboyd!~mboyd@dhcp-010-010-002-047.nc.opsware.com INVITE sinBot :#write
        who = line[0][1:].split("!")[0]
        chan = line[3][1:].lower()
#        this.sinBot.actions.execcommand('PRIVMSG '+chan+' :yo, what\'s up! my peeps!\n')
        this.sinBot.lockDict['userList'].acquire()
        try:
            this.sinBot.userList[chan] = []
            pickle.dump(this.sinBot.userList, open('userlist.dat','w'))
            this.sinBot.actions.execcommand('OJOIN @'+chan+'\n',line)
            this.sinBot.actions.execcommand('JOIN '+chan+'\n',line)
        except Exception,e:
            print "Error in invite(): ",e
        this.sinBot.lockDict['userList'].release()
        time.sleep(2)
        return 0

    def fourthreethree(this,line):
        print "Recieved 433 from "+this.sinBot.HOST+". Selecting new nick."
        subNicks = [this.sinBot.NICK, "mechaGnome_", "mechaGnome__", "mechaGnome___", "mechaGnome1", "mechaGnome2", "mechaGnome3", "mecha", "syraeBot"]
        foundNick = False
        for nick in subNicks:
            if nick == line[3]:
                foundNick = True
                continue
            if foundNick:
                this.sinBot.s.send('NICK '+nick+'\n')
                print "Selected Nick: "+nick
                this.sinBot.currentNick = nick
                break

    def foursevenseven(this,line):
        print "Recieved 477 from "+this.sinBot.HOST+" and ignoring it."
        #Freenode 477  
        #Messages labeled freenode-info  contain important, non-time-critical 
        #information for freenode  users. They're designed to appear with varying, 
        #random frequency and are sent using numeric 477. You're most likely to see 
        #them on your channel window around the time when you join a channel, or 
        #occasionally while rejoining from a netsplit. 
        return 0
        
    def threeseventwo(this,line):
        #MOTD
        #print line
        return 0
    
    def threesevensix(this,line):
        #End MOTD
        #print line
        return 0

    def foureighttwo(this,line):
        #:irc.corp.opsware.com 482 sinBot #boyd :You're not channel operator
        this.sinBot.lockDict['requestedOpIn'].acquire()
        try:
            if not this.sinBot.requestedOpIn.has_key(line[3]):
                print "No ops :("
        except Exception,e:
            print "Exception in foureighttwo(): ",e
        this.sinBot.lockDict['requestedOpIn'].release()
        time.sleep(2)
        return 0

    def fourzerofive(this,line):
        #:irc.corp.opsware.com 405 sinBot #wolff6 :You have joined too many channels
        if len(line) == 10 and line[9] == "channels":
            chan = line[3]
            if not hasattr(this.sinBot, "child"):
                this.sinBot.spawnJoin(chan)
            else:
                print "already have child, tell him to join "+chan
                this.sinBot.child.joinChans([chan])
                
    #    RPL_WHOISUSER
    def threeoneone(this,line):
        #:lindbohm.freenode.net 311 mechaGnome Marzee ~Marzee 113.28.26.162 * :purple
        if not this.sinBot.getRootSinBot().whoisInfo.has_key(line[3].lower()) or \
            this.sinBot.getRootSinBot().whoisInfo[line[3].lower()] is None:
            this.sinBot.getRootSinBot().whoisInfo[line[3].lower()] = {}
        this.sinBot.getRootSinBot().whoisInfo[line[3].lower()]["nick"] =  line[3]
        this.sinBot.getRootSinBot().whoisInfo[line[3].lower()]["user"] = line[4][1:]
        this.sinBot.getRootSinBot().whoisInfo[line[3].lower()]["host"] = line[5]
        line[7] = line[7][1:]
        this.sinBot.getRootSinBot().whoisInfo[line[3].lower()]["real_name"] = " ".join(line[7:]) 
    
    # RPL_ENDOFWHOIS
    def threeoneeight(this, line):
        #:lindbohm.freenode.net 318 mechaGnome syrae :End of /WHOIS list
        this.sinBot.getRootSinBot().whoisInfo["locked"] = False
        this.sinBot.gettingWhois = False
        print "End of WHOIS on " + line[3]


    def fourfourone(this,line):
        #:irc.corp.opsware.com 441 sinBotBet sinBot #boyd :They aren't on that channel
        #sendMsg = 'PRIVMSG '+line[4]+' :sorry, they\'re not here'
        this.sinBot.actions.execcommand(sendMsg,line)
        return 0

    def threefivethree(this,line):
        #joining a channel, getting initial list of names
        #:irc.corp.opsware.com 353 sinBot = #boyd :sinBot @mboyd
        print "Channel: "+line[4]
        print "first user: "+line[5][1:]
        this.sinBot.lockDict['userList'].acquire()
        try:
            if not this.sinBot.userList.has_key(line[4].lower()):
                this.sinBot.userList[line[4].lower()] = []

            this.sinBot.userList[line[4].lower()].append(line[5][1:].lower())
            if len(line) > 6:
                for user in line[6:]:
                    this.sinBot.userList[line[4].lower()].append(user.lower())
            print "final:"
            print this.sinBot.userList[line[4].lower()]
                    
        except Exception,e:
            print "Exception in threefivethree(): ",e
        this.sinBot.lockDict['userList'].release()
        time.sleep(2)

    def closing(this,line):
        print "Caught connection closing message, closing."
        sys.exit(0)

    def getTitle(this,link):
        req = urllib2.Request(link, None, this.sinBot.headers)
        content = this.sinBot.opener.open(req).read()
        title = re.search(r"<title>(.*)</title>",content,re.DOTALL).group(1).replace("\n", "")
        import HTMLParser

        title = HTMLParser.HTMLParser().unescape(title).encode('ascii','ignore')
        p = re.compile("\s+")
        title = p.sub(" ", title).strip()
        print "Title string: " + title
        return title
        

    def __init__(this, bot):
        this.VERSION="v.5"
        this.sinBot = bot
        this.sinBot.actionMap = {}
        print "Loading Actions "+this.VERSION
        this.sinBot.actionMap["PRIVMSG"] = this.privmsg;
        this.sinBot.actionMap["parsemsg"] = this.parsemsg;
        this.sinBot.actionMap["PING"] = this.ping;
        this.sinBot.actionMap["PART"] = this.part;
        this.sinBot.actionMap["QUIT"] = this.quit;
        this.sinBot.actionMap["JOIN"] = this.join;
        this.sinBot.actionMap["MODE"] = this.mode;
        this.sinBot.actionMap["KICK"] = this.kick;
        this.sinBot.actionMap["NICK"] = this.nick;
        this.sinBot.actionMap["INVITE"] = this.invite;
        this.sinBot.actionMap["NOTICE"] = this.notice;
        this.sinBot.actionMap[":Closing"] = this.closing;
        this.sinBot.actionMap["405"] = this.fourzerofive;
        this.sinBot.actionMap["482"] = this.foureighttwo;
        this.sinBot.actionMap["441"] = this.fourfourone;
        this.sinBot.actionMap["353"] = this.threefivethree;
        this.sinBot.actionMap["477"] = this.foursevenseven;
        this.sinBot.actionMap["433"] = this.fourthreethree;
        this.sinBot.actionMap["372"] = this.threeseventwo;
        this.sinBot.actionMap["376"] = this.threesevensix;
        this.sinBot.actionMap["311"] = this.threeoneone;
        this.sinBot.actionMap["318"] = this.threeoneeight;    
            
        # Just doing this to force a reload
        this.parseActions
        this.googlyEyes        
        this.botFight
        this.botLove
        this.botSnack        
        this.blizzAlerts
        this.alertMsg
        this.execcommand

        this.blizzAlertsTimer = time.time()
        this.blizzAlertsMessage = ""

        this.ctcpCommand

        this.pipeline = ""
        this.messages = {}
        this.messages[this.sinBot.CHANNELINIT] = []

        #Flood managment, so users don't abuse sinBot
        #the map of user-># of commands executed
        try:
            this.sinBot.flood.keys()
        except:
            this.sinBot.flood = {}

        try:
            this.sinBot.flood["command"].keys()
        except:
            this.sinBot.flood["command"] = {}
        try:
            this.sinBot.flood["quotemovie"].keys()
        except:
            this.sinBot.flood["quotemovie"] = {}

        #the number of commands before a user is cut off
        try:
            this.sinBot.floodLimit.keys()
        except:
            this.sinBot.floodLimit = {}

        this.sinBot.floodLimit["command"] = 15
        this.sinBot.floodLimit["quotemovie"] = 4
        this.sinBot.floodLimit["privmsg"] = 3

        #the amount of time to wait for another bot to op someone before opping them ourselves.
        this.slowOpDelay = 3

        #how long (in seconds) before the flood ban is lifted
        try:
            this.sinBot.floodDelay.keys()
        except:
            this.sinBot.floodDelay = {}

        this.sinBot.floodDelay["command"] = 600
        this.sinBot.floodDelay["quotemovie"] = 300
        this.sinBot.floodDelay["privmsg"] = 2

        #list of people to ignore, might move from map to list at some point
        
        try:
            this.sinBot.ignore.keys()
        except:
            this.sinBot.ignore = {}
        try:
            this.sinBot.logDict.keys()
        except:
            this.sinBot.logDict = {}
        try:
            this.sinBot.ipToUser.keys()
        except:
            this.sinBot.ipToUser = {}

class MessageList(list):
    min = 50
    buffer = 20
    logdir = None
    def __init__(this):
        this.min = 5
        this.buffer = 5
        this.logdir = None

    def __init__(this, logdir=None, min = 50, buf = 20, oldlist = None):
        if oldlist == None:
            this.min = min
            this.buffer = buf
            this.logdir = logdir
        else:
            oldlist.reverse()
            for x in oldlist:
                this.append(x)
            this.logdir = oldlist.logdir
            this.buffer = oldlist.buffer
            this.min = oldlist.min

    def append(this, item):
        this.insert(0,item)
        if len(this) > this.min + this.buffer:
            this.flushbuffer()
            
    def flushbuffer(this):
        if this.logdir != None:
            fileDict = {}
            mainFile = file(this.logdir+"CHANNEL-LOG.log", 'a')
            while len(this) > this.min:
                msg = str(this.pop())
                user = msg.split("<")[1].split(">")[0].lower()
                try:
                    f = fileDict[user]
                except:
                    try:
                        f = file(this.logdir+user, 'a')
                    except:
                        command = 'mkdir -p '+this.logdir
                        output = os.popen(command)
                        lines = output.readlines()
                        output.close()
                        f = file(this.logdir+user, 'a')
                    fileDict[user] = f
                print "writing: ",msg
                f.write(msg+"\n")
                mainFile.write(msg+"\n")
            for f in fileDict.values():
                f.close()
            mainFile.close()
        else:
            while len(this) > this.min:
                this.pop()
                
    def flush(this):
        if this.logdir != None:
            fileDict = {}
            while len(this) > 0:
                msg = str(this.pop())
                user = msg.split("<")[1].split(">")[0].lower()
                try:
                    f = fileDict[user]
                except:
                    try:
                        f = file(this.logdir+user, 'a')
                    except:
                        command = 'mkdir -p '+this.logdir
                        output = os.popen(command)
                        lines = output.readlines()
                        output.close()
                        f = file(this.logdir+user, 'a')
                    fileDict[user] = f
                print "writing: ",msg
                f.write(msg+"\n")
            for f in fileDict.values():
                f.close()


class Message(list):
    def copy(this):
        retVal = Message([])
        retVal.pipeList = this.pipeList[:]
        retVal.hasPipe = this.hasPipe
        retVal.nextCommand = this.nextCommand
        for x in this:
            retVal.append(x)
        return retVal

    def test(this):
        print "test"

    def nextPipe(this):
        print "nextPipe"
        command = ""
        #if this was already empty, then remove everything and return an empty string
        if this.hasPipe == 0:
            for x in this:
                this.remove(x)
            this.nextCommand = this["nextCommand"]
            return command

        #reset hasPipe
        this.hasPipe = 0

        #command is the first element in pipelist
        command = this.pipeList[0]
        del this.pipeList[0]

        #remove all other unrelated items
        print "s1"
        for x in range(3,len(this)):
            print "s2 x:",x," len(this): ",len(this)
            del this[3]

        print "s3"
        delList = []
        for x in range(0,len(this.pipeList)):
            print "s4"
            if this.hasPipe != 0:
                return command
            elif this.pipeList[x] == "|":
                this.hasPipe = 1
                delList.append(x)
                while len(delList) > 0:
                    del this.pipeList[delList.pop()]
                return command
            else:
                this.append(this.pipeList[x])
                delList.append(x)
        while len(delList) > 0:
            del this.pipeList[delList.pop()]
        return command
        
    def __init__(this, lst):
        this.pipeList = []
        this.hasPipe = 0
        for x in lst:
            if this.hasPipe != 0:
                this.pipeList.append(x)
            elif x == "|":
                this.hasPipe = 1
            else:
                this.append(x)
        try:
            if this[2][0] != "#":
                this[2] = this[0]
        except:
            pass
        
    def __getattr__(this, attr):
        if attr in ["name","chan","nextCommand"]:
            return this[attr]
        else:
            return super(Message,this).__getattr__(attr)

    def __getitem__(this, target):
        if target == "name":
            return this[0]
        elif target == "chan":
            return this[2]
        elif target == "nextCommand":
            if this.hasPipe == 0:
                return ""
            else:
                return this.pipeList[0]
        else:
            return super(Message,this).__getitem__(target)


def parseForMatch(args, map):
    curResult = []
    #base case
    if args == None or len(args) == 0:
        if map.has_key("#COMPLETE"):
            return [""]
        return []
    elif map.has_key(args[0]):
        curResult = parseForMatch(args[1:], map[args[0]])
    if len(curResult) == 0 and map.has_key("#COMPLETE"):
        return [""]
    if len(curResult) != 0:
        return [args[0]] + curResult
    return curResult

def getTitle(link):
    req = urllib2.Request(link, None, headers)
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

def unescape(s):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()
