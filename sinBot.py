#!/usr/bin/python
import sys
import socket
import string
import os #not necassary but later on I am going to use a few features from this
import pickle
import thread
import threading
import time
from Commands import *
from Actions import *

sys.path.append('lib')

############################################################
# sinBot: threaded IRC bot
# Author: Mike Boyd - mboyd@hp.com
# Ninja'd: marinna@gmail.com
# Date: May 25, 2007
#
# This bot has 4 classes (so far), the sinBot class, the 
# Message class, the Actions class and the Commands class.
#
# And there is also the startSinbot.py startup file, I
# usually run this in a screen session and check the output
# if something weird happens.
#
# The sinBot class is the super-simple class used to handle
# connecting to the IRC server, every message it receives is
# passed on to the Actions class via the actionMap or
# actionThreadMap.  These two maps essentially relate an IRC
# command directly to a function.
#
# The Message class encapsulates messages, and breaks piped
# messages apart.
#
# The Actions class handles all messages from the IRC
# server, including error codes and other commands, user
# messages are partially parsed, and if they're determined
# to be commands they are sent on to the Commands class via
# the commandMap or commandThreadMap.
#
# The Commands class defines all the actual channel commands
# sinBot supports. This will generally be the most modified
# class.  To add a new command:
#
# Sinbot commands are basically just functions that get added
# to a map, they are a part of the Command.py sinbot file.
# An example command, reverse:
#
#       def cReverse(self,args):
#                """reverse <word or phrase> - reverses the word or phrase"""
#                retval = ""
#                for x in " ".join(args[3:]):
#                        retval = x + retval
#
#                self.respond(retval,args)
#
# args is just an array of strings, args[0] is the user [1] 
# is the users name + IP address and [2] is the channel name,
# everything after that is the text (minus the command) passed
# into the function. "chan" and "user" and "nextCommand" are
# also properties of the args type. nextCommand is the next
# command in the pipe, chan is the originating channel, user
# is the originating user.
#
# For example, me sending the message: 
# "sinbot, reverse this is a test"
# in #boyd gets turned into the args:
# ['mboyd', 'mboyd@10.10.2.78', '#boyd', 'this', 'is', 'a', 'test']
#
# Prefix the command with a 'c' (like the one above) for
# non-threaded commands, usually commands that don't have to
# hit the internet. Use 't' for threaded commands. All other
# methods will be ignored as helper methods.
#
# To send the response, you can just use the respond method like
# above, and be sure to pass the args back in for piping (which
# is done behind the scenes in the args class)
#
# Also, Sinbot is currently running on Python 2.5.1
#
# And finally, after any changes to sinBot while the bot is
# running, give it the command "reload classes" to have it
# reload the classes and have the changes take effect.
#
# Good luck and have fun!
#
#
############################################################

class sinBot:

#	def execcommand(self,command):
#		print "Sending message: "+command
#		if command[-1] != '\n':
#			command = command + '\n'
#		self.s.send(command)

	def __init__(self,channel,name="mechaGnome",server="irc.freenode.net",password=None,parent=None):
		print "starting!!"
		self.password = password
		self.HOST=server #The server we want to connect to
		self.PORT=6667 #The connection port which is usually 6667
		self.TIMEOUT=200 #seconds.  Freenode pings at 3 minutes
		self.NICK=name #The bot's nickname
		self.currentNick=self.NICK
		self.VERSION=self.NICK+" v.08-threaded"
		self.IDENT=self.NICK+'-'+self.VERSION
		self.REALNAME=self.NICK+' Bot'
		self.OWNER='syrae' #The bot owner's nick
		self.CHANNELINIT=channel #The default channel for the bot
		self.readbuffer='' #Here we store all the messages from server 
		self.OPER = False;
		self.chanLimit = 0
		self.curChans = 0
		self.proxies = {}
		if parent != None:
			self.parent = parent
		self.reloadTime = None

		#just keeping track so we don't ask a million times in the same chan.
		self.requestedOpIn = {}
		self.requestedOpInLock = thread.allocate_lock()
		#mapping of chan name to user list
		try:
			self.userList = pickle.load(open('userlist.dat','r'))
		except:
			self.userList = {}
		self.userListLock = thread.allocate_lock()
		self.excessFlood = None

		self.s=socket.socket( ) #Create the socket
		self.s.settimeout(self.TIMEOUT)
		self.s.connect((self.HOST, self.PORT)) #Connect to server
		self.currentNick = self.NICK
		self.s.send('NICK '+self.NICK+'\n') #Send the nick to server
		self.s.send('USER '+self.IDENT+' '+self.HOST+' bla :'+self.REALNAME+'\n') #Identify to server
		self.actionThreadMap = {}
		self.actionMap = {}
		self.commandMap = {}
		self.commandThreadMap = {}
		self.commands = Commands(self)
		self.actions = Actions(self)
		# self.olgaTarget = ''
		# self.olgaTargetLock = thread.allocate_lock()
		self.startTime = time.localtime()
		self.RUN = True

		self.lockDict = {'userList':self.userListLock, 'requestedOpIn':self.requestedOpInLock}
		
	def run(self, info="", info2=""):
		joinBuffer = []
		while self.RUN:
			try:
				lines=self.s.recv(10000) #making this huge to handle giant server messages
			except socket.timeout, msg:
				print time.ctime()+": Idle connection detected. Restarting."
                                try:
					self.restart()
					continue
				except socket.gaierror, msg:
					print time.ctime()+": Restart failed. Trying again."	
					print msg
					retries = 100
					remaining = retries
					while remaining > 0:
						sleepTime = (retries-remaining+1)
						sleepTime = sleepTime*sleepTime*60
						time.sleep(sleepTime)
						remaining = remaining-1
						try:
							self.restart()
							break 
						except socket.gaierror, msg:
							print time.ctime()+": Restart failed. Trying again."						
							print msg
							continue
					continue
			if lines == "":
				print time.ctime()+": Idle connection detected.  Restarting."
				self.restart()
				continue
			else:
				lines = lines.split('\n')
				for line in lines:
					print line #server message is output
					if line == '':
#						print "Continuing"
						continue
	
					if line.find('MOTD')!=-1: #This is Crap(I wasn't sure about it but it works)
						time.sleep(3)
#						self.s.send('LIST\n')
						if self.password != None:
							this.actions.execcommand('OPER '+self.NICK+' '+self.password+'\n')
						time.sleep(1)
						if not hasattr(self, "parent"):
							joinBuffer = self.userList.keys()
							joinBuffer.append(self.CHANNELINIT)
						
					lineArr = line.strip().split()
					if len(lineArr) > 2:
						source = lineArr[0]
						action = lineArr[1]
						location = lineArr[2]
						if len(lineArr) > 3:
							data = " ".join(lineArr[3:])
					elif len(lineArr) > 1:
						action = lineArr[0]
						source = lineArr[1]
					import traceback
					if self.actionThreadMap.has_key(action):
						try:
							thread.start_new_thread(self.actionMap[action],(lineArr,))
						except Exception, e:
							print "There was an exception with action: %s % action"
							print lineArr
							print e
							traceback.print_exc(file=sys.stdout)
					elif self.actionMap.has_key(action):
						try:
							self.actionMap[action](lineArr)
						except Exception, e:
							print "There was an exception with action: %s" % action
							print lineArr
							print e
							traceback.print_exc(file=sys.stdout)
					elif action.isdigit():
						print "Unassigned action.  Value: " + action
						#print lineArr
					else:
						print "Action not defined: "+action
				if len(joinBuffer) > 0:
					self.joinChans(joinBuffer)
	
	def restart(self):
		self.s=socket.socket( ) #Create the socket
		self.s.settimeout(self.TIMEOUT)
		self.s.connect((self.HOST, self.PORT))	
		self.s.send('NICK '+self.NICK+'\n') #Send the nick to server
		self.s.send('USER '+self.IDENT+' '+self.HOST+' bla :'+self.REALNAME+'\n') #Identify to server


	def getRootSinBot(self):
		sb = self
		while hasattr(sb,"parent") and sb.parent != None:
			sb = sb.parent
		return sb

	def joinChans(self, joinBuffer):
		while(len(joinBuffer) > 0):
			chan = joinBuffer.pop()
			if chan[0] == "#":
				self.lockDict['userList'].acquire()
				try:
					self.userList[chan] = []
				except:
					pass
				self.lockDict['userList'].release()
				self.actions.execcommand('OJOIN @'+chan+'\n',[])
				print 'OJOIN @'+chan+'\n'
				self.actions.execcommand('JOIN '+chan+'\n',[])
				print 'JOIN '+chan+'\n'
				return
			else:
				self.lockDict['userList'].acquire()
				try:
					del self.userList[chan]
				except:
					pass
				self.lockDict['userList'].release()
	

	def reLoad(self):
#		import Commands.Commands
#		import Actions.Actions
		try:
			reload(sys.modules.get("Actions"))
			reload(sys.modules.get("Commands"))
			from Commands import *
			from Actions import *
	
			self.actions = Actions(self)
			self.commands = Commands(self)
			if hasattr(self, "child") and self.child != None:
				self.child.reLoad()
		except Exception,e:
			print "Caught an exception in reLoad(): ",e

	def spawnJoin(self, chan):
		if not hasattr(self, "child"):
			base = ""
			inst = ""
			for x in self.NICK:
				if x.isdigit():
					inst += x
				else:
					base += x
			try:
				inst = int(inst)
				inst += 1
			except:
				inst = 1
			print "no child, create a new one and start"
			self.child = sinBot(chan,base+str(inst),self.HOST,self.password, self)
			self.child.userList = self.userList
			self.child.lockDict['userList'] = self.lockDict['userList']
			print "RUNNING THREAD!"
			thread.start_new_thread(self.child.run,("test","test2"))
			print "THREAD STARTED!"
		else:
			print "already have child, tell him to join "+chan
			self.child.joinChans([chan])



##		numChans = 0
##		for chanName in self.userList.keys():
#			print "CHANNAME: "+chanName+" list: ",self.userList[chanName]
##			if self.NICK.lower() in self.userList[chanName] or "@"+self.NICK.lower() in self.userList[chanName]:
##				numChans = numChans + 1
##		if numChans > 8:
##			print "channels over 8: ",numChans
##			if not hasattr(self, "child"):
##				print "no child, create a new one and start"
##				self.child = sinBot(chan,self.NICK.lower()+"-",self.HOST,self.password)
##				self.child.parent = self
##				self.child.userList = self.userList
##				self.child.lockDict['userList'] = self.lockDict['userList']
##				thread.start_new_thread(self.child.run,("test",))
##			else:
##				print "already have child, tell him to join "+chan
##				self.child.spawnJoin(chan)
##		else:
##			print "channels under 8: ",numChans
##			print "attempt to join channel"
##			self.lockDict['userList'].acquire()
##			try:
##				self.userList[chan] = []
##				pickle.dump(self.userList, open('userlist.dat','w'))
##				self.actions.execcommand('JOIN '+chan+'\n',[])
##			except Exception,e:
##				print "Error in spawnJoin(): ",e
##			self.lockDict['userList'].release()

