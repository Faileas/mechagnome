mechaGnome
==========

Python IRC bot based on sinbot (http://sourceforge.net/projects/sinbot/)

Requirements
============

 - Python 2.6 or better
 
 Libraries:
  - pygeoip (included by default)
  - Beautiful Soup 4 (included by default as bs4)
  - python-six (for pygeoip, included by default)
   
Setup
============

 - Edit startBot.py to change the default bot name, network, and initial join channel.
 - Run the bot. You'll probably want to do this in a screen session as it doesn't auto-background itself.
 `python startBot.py`
