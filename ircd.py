#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       ircd.py
#       
#       Copyright 2010 Curtis (Programble) <programble@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import socket
import time

from select import select

import config

class User:
    def __init__(self, server, (sock, address)):
        self.socket = sock
        self.addr = address
        self.ip = self.addr[0]
        self.port = self.addr[1]
        
        self.server = server
        
        self.recvbuffer = ""
        self.sendbuffer = ""
        
        self.ping = time.time()
        
        self.nickname = "*"
        self.username = "unknown"
        self.realname = "Unknown"
        
        if self.server.hostcache.has_key(self.ip):
            self.hostname = self.server.hostcache[self.ip]
        else:
            try:
                self.hostname = socket.gethostbyaddr(self.ip)[0]
            except:
                self.hostname = self.ip
            self.server.hostcache[self.ip] = self.hostname
        
        self.away = False
        
        self.channels = []
    
    def __repr__(self):
        return "<User '%s'>" % self.fullname()
    
    def fileno(self):
        return self.socket.fileno()
    
    def fullname(self):
        return "%s!%s@%s" % (self.nickname, self.username, self.hostname)
    
    def parse_command(self, data):
        xwords = data.split(' ')
        words = []
        for i in range(len(xwords)):
            word = xwords[i]
            if word.startswith(':'):
                words.append(' '.join([word[1:]] + xwords[i+1:]))
                break
            words.append(word)
        return words
    
    def _send(self, data):
        self.sendbuffer += data + "\r\n"
    
    def send(self, command, data):
        self._send(":%s %s %s %s" % (self.server.hostname, command, self.nickname, data))
    
    def send_numeric(self, numeric, data):
        self.send(str(numeric).rjust(3, "0"), data)
    
    def broadcast(self, users, data):
        for user in users:
            user._send(":%s %s" % (self.fullname(), data))
    
    def welcome(self):
        self.send_numeric(001, ":Welcome to %s, %s" % (self.server.name, self.fullname()))
        self.send_numeric(002, ":Your host is %s, running version %s" % (self.server.hostname, self.server.version))
        self.send_numeric(003, ":This server was created %s" % self.server.creationtime)
        self.send_numeric(004, "%s %s  bohv" % (self.server.hostname, self.server.version))
        self.send_numeric(005, "CHANTYPES=# PREFIX=(ohv)@%+"+" CHANMODES=b,o,h,v NETWORK=%s CASEMAPPING=rfc1459" % self.server.name)
        # MOTD
        self.handle_MOTD(("MOTD",))
    
    def quit(self, reason):
        # Don't quit if already quitted
        if self not in self.server.users:
            return
        
        # Send error to user
        self._send("ERROR :Closing link: (%s) [%s]" % (self.fullname(), reason))
        
        # Send quit to all users in channels user is in
        users = []
        for channel in self.channels:
            for user in channel.users:
                if user not in users:
                    users.append(user)
        self.broadcast(users, "QUIT :%s" % reason)
        
        # Remove user from all channels
        for channel in self.channels:
            channel.users.remove(self)
        
        # Remove user from server users
        self.server.users.remove(self)
        
        # Close socket
        #self.socket.close()
        
        # This User object should now be garbage collected...
    
    def handle_recv(self):
        while self.recvbuffer.find("\n") != -1:
            recv = self.recvbuffer[:self.recvbuffer.find("\n")]
            self.recvbuffer = self.recvbuffer[self.recvbuffer.find("\n")+1:]
            
            self.ping = time.time()
            
            recv = recv.strip()
            
            if recv == '':
                continue
            
            #print self, recv
            
            parsed = self.parse_command(recv)
            command = parsed[0]
            if command.upper() == "PING":
                self.handle_PING(parsed)
            elif command.upper() == "PONG":
                pass
            elif command.upper() == "NICK":
                self.handle_NICK(parsed)
            elif command.upper() == "USER":
                self.handle_USER(parsed)
            elif self.nickname == '*' or self.username == 'unknown':
                self.send_numeric(451, "%s :You have not registered" % command)
            elif command.upper() == "MOTD":
                self.handle_MOTD(parsed)
            elif command.upper() == "PRIVMSG":
                self.handle_PRIVMSG(parsed)
            elif command.upper() == "NOTICE":
                self.handle_NOTICE(parsed)
            elif command.upper() == "JOIN":
                self.handle_JOIN(parsed)
            elif command.upper() == "PART":
                self.handle_PART(parsed)
            elif command.upper() == "NAMES":
                self.handle_NAMES(parsed)
            elif command.upper() == "TOPIC":
                self.handle_TOPIC(parsed)
            elif command.upper() == "ISON":
                self.handle_ISON(parsed)
            elif command.upper() == "AWAY":
                self.handle_AWAY(parsed)
            elif command.upper() == "MODE":
                self.handle_MODE(parsed)
            elif command.upper() == "QUIT":
                self.handle_QUIT(parsed)
            else:
                self.send_numeric(421, "%s :Unknown command" % command)
    
    def handle_PING(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "PING :Not enough parameters")
            return
        self._send(":%s PONG %s :%s" % (self.server.hostname, self.server.hostname, recv[1]))
    
    def handle_MOTD(self, recv):
        self.send_numeric(375, ":%s message of the day" % self.server.hostname)
        for line in self.server.motd.split("\n"):
            self.send_numeric(372, ":- %s" % line)
        self.send_numeric(376, ":End of message of the day.")
    
    def handle_NICK(self, recv):
        if len(recv) < 2:
            # No nickname given
            self.send_numeric(431, ":No nickname given")
            return
        nick = recv[1]
        
        if nick.strip() == '':
            # No nickname given
            self.send_numeric(431, ":No nickname given")
            return
        
        # Check if nick is valid
        valid = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`^-_[]{}|\\"
        for c in nick:
            if c not in valid:
                self.send_numeric(432, "%s :Erroneous Nickname" % nick)
                return
        
        # Check nick length
        if len(nick) > 16:
            self.send_numeric(432, "%s :Erroneous Nickname" % nick)
            return
        
        # Check if nick is already in use
        if nick.lower() in [user.nickname.lower() for user in self.server.users]:
            self.send_numeric(433, "%s :Nickname is already in use" % nick)
            return
        
        # Nick is AWWW RIGHT
        self.broadcast([self], "NICK :%s" % nick)
        # Broadcast to all channels user is in
        users = []
        for channel in self.channels:
            for user in channel.users:
                if user not in users and user != self:
                    users.append(user)
        self.broadcast(users, "NICK :%s" % nick)
        old = self.nickname
        self.nickname = nick
        
        if old == "*" and self.username != "unknown":
            self.welcome()
    
    def handle_USER(self, recv):
        if len(recv) < 5:
            self.send_numeric(461, "USER :Not enough parameters")
            return
        
        # Make sure user is not already registered
        if self.username != "unknown":
            self.send_numeric(462, ":You may not register")
            return
        
        username = recv[1]
        realname = recv[4]
        
        self.username = username
        self.realname = realname
        
        if self.nickname != '*':
            self.welcome()
    
    def handle_PRIVMSG(self, recv):
        if len(recv) < 2:
            self.send_numeric(411, ":No recipient given (PRIVMSG)")
            return
        elif len(recv) < 3:
            self.send_numeric(412, ":No text to send")
            return
        
        target = recv[1]
        msg = recv[2]
        
        # DEBUGGING (disable this)
        if target == "DEBUG" and self.ip == "127.0.0.1":
            try:
                self._send(":DEBUG!DEBUG@DEBUG PRIVMSG %s :%s" % (self.nickname, eval(msg)))
            except:
                try:
                    exec(msg)
                except:
                    pass
            return
        
        # PM to user
        if target[0] != "#":
            # Find user
            user = [user for user in self.server.users if user.nickname.lower() == target.lower()]
            
            # User does not exist
            if user == []:
                self.send_numeric(401, "%s :No such nick/channel" % target)
                return
            
            if user[0].away:
                self.send_numeric(301, "%s :%s" % (user[0].nickname, user[0].away))
            
            # Broadcast message
            self.broadcast(user, "PRIVMSG %s :%s" % (target, msg))
        else:
            # Find channel
            channel = [channel for channel in self.server.channels if channel.name.lower() == target.lower()]
            
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % target)
                return
            
            # Broadcast message
            self.broadcast([user for user in channel[0].users if user != self], "PRIVMSG %s :%s" % (target, msg))
    
    def handle_NOTICE(self, recv):
        if len(recv) < 2:
            self.send_numeric(411, ":No recipient given (NOTICE)")
            return
        elif len(recv) < 3:
            self.send_numeric(412, ":No text to send")
            return
        
        target = recv[1]
        msg = recv[2]
        
        # Notice to user
        if target[0] != "#":
            # Find user
            user = [user for user in self.server.users if user.nickname.lower() == target.lower()]
            
            # User does not exist
            if user == []:
                self.send_numeric(401, "%s :No such nick/channel" % target)
                return
            
            # Broadcast message
            self.broadcast(user, "NOTICE %s :%s" % (target, msg))
        else:
            # Find channel
            channel = [channel for channel in self.server.channels if channel.name.lower() == target.lower()]
            
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % target)
                return
            
            # Broadcast message
            self.broadcast([user for user in channel[0].users if user != self], "NOTICE %s :%s" % (target, msg))
    
    def handle_JOIN(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "JOIN :Not enough parameters")
            return
        
        # Channels must begin with #
        if recv[1][0] != '#':
            self.send_numeric(403, "%s :No such channel" % recv[1])
            return
        
        # Channel name must be less than 50
        if len(recv[1]) > 50:
            self.send_numeric(479, "%s :Illegal channel name" % recv[1])
            return
        
        # Check if channel name is valid
        valid = "abcdefghijklmnopqrstuvqxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`~!@#$%^&*()-=_+[]{}\\|;':\"./<>?"
        for c in recv[1]:
            if c not in valid:
                self.send_numeric(479, "%s :Illegal channel name" % recv[1])
                return
        
        channel = [channel for channel in self.server.channels if channel.name.lower() == recv[1].lower()]
        
        # Create non-existent channel
        if channel == []:
            new = Channel(recv[1])
            new.usermodes[self] = 'o'
            new.modes = "nt"
            self.server.channels.append(new)
            channel = [new]
        
        channel = channel[0]
        
        # Drop if already on channel
        if channel in self.channels:
            return
        
        if channel.users == []:
            channel.usermodes[self] = 'o'
        
        channel.users.append(self)
        self.channels.append(channel)
        
        self.broadcast(channel.users, "JOIN :%s" % channel.name)
        if channel.topic_time != 0:
            self.handle_TOPIC(("TOPIC", channel.name))
        self.handle_NAMES(("NAMES", channel.name))
    
    def handle_PART(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "PART :Not enough parameters")
            return
        
        target = recv[1]
        if len(recv) > 2:
            reason = recv[2]
        else:
            reason = ""
        
        channel = [channel for channel in self.channels if channel.name.lower() == target.lower()]
        
        if channel == []:
            self.send_numeric(442, "%s :You're not on that channel" % target)
            return
        
        channel = channel[0]
        self.broadcast(channel.users, "PART %s :%s" % (channel.name, reason))
        self.channels.remove(channel)
        channel.users.remove(self)
        if channel.usermodes.has_key(self):
            channel.usermodes[self] = ''
    
    def handle_NAMES(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "NAMES :Not enough parameters")
            return
        
        channel = [channel for channel in self.server.channels if channel.name == recv[1]]

        if channel == []:
            self.send_numeric(401, "%s :No such nick/channel" % recv[1])
            return
        
        channel = channel[0]
        
        users = []
        
        for user in channel.users:
            if channel.usermodes.has_key(user):
                if 'o' in channel.usermodes[user]:
                    users.append('@'+user.nickname)
                elif 'h' in channel.usermodes[user]:
                    users.append('%'+user.nickname)
                elif 'v' in channel.usermodes[user]:
                    users.append('+'+user.nickname)
                else:
                    users.append(user.nickname)
            else:
                users.append(user.nickname)
        
        self.send_numeric(353, "@ %s :%s" % (channel.name, " ".join(users)))
        self.send_numeric(366, "%s :End of /NAMES list." % channel.name)
    
    def handle_TOPIC(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "TOPIC :Not enough parameters")
            return
        
        if len(recv) < 3:
            # Send back topic
            channel = [channel for channel in self.server.channels if channel.name == recv[1]]
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % recv[1])
                return
            channel = channel[0]
            
            if channel.topic == '':
                self.send_numeric(331, "%s :No topic is set." % channel.name)
                return
            
            self.send_numeric(332, "%s :%s" % (channel.name, channel.topic))
            self.send_numeric(333, "%s %s %d" % (channel.name, channel.topic_author, channel.topic_time))
        else:
            # Set topic
            channel = [channel for channel in self.server.channels if channel.name == recv[1]]
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % recv[1])
                return
            channel = channel[0]
            
            # TODO: Make sure user is allowed to change topic (chanmode +t requires user to be op)
            
            channel.topic = recv[2]
            channel.topic_author = self.fullname()
            channel.topic_time = int(time.time())
            
            self.broadcast(channel.users, "TOPIC %s :%s" % (channel.name, channel.topic))
    
    def handle_ISON(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "ISON :Not enough parameters")
            return
        
        nicks = recv[1:]
        
        online = [nick for nick in nicks if nick.lower() in [user.nickname.lower() for user in self.server.users]]
        
        self.send_numeric(303, ":%s" % " ".join(online))
    
    def handle_AWAY(self, recv):
        if len(recv) < 2:
            self.away = False
            self.send_numeric(305, ":You are no longer marked as being away")
        else:
            self.away = recv[1]
            self.send_numeric(306, ":You have been marked as being away")
    
    def handle_MODE(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "MODE :Not enough parameters")
            return
        elif len(recv) == 2:
            # /mode #channel, send back channel modes
            
            channel = [channel for channel in self.server.channels if channel.name == recv[1]]
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % recv[1])
                return
            channel = channel[0]
            
            self.send_numeric(324, "%s +%s" % (channel.name, channel.modes))
            self.send_numeric(329, "%s %d" % (channel.name, channel.creation))
        elif len(recv) == 3:
            # /mode #channel +mnt
            
            channel = [channel for channel in self.server.channels if channel.name == recv[1]]
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % recv[1])
                return
            channel = channel[0]
            
            if not channel.usermodes.has_key(self):
                self.send_numeric(482, "%s :You're not a channel operator" % channel.name)
                return
            if 'o' not in channel.usermodes[self]:
                self.send_numeric(482, "%s :You're not a channel operator" % channel.name)
                return
            
            action = ''
            for m in recv[2]:
                if m == '+':
                    action = '+'
                elif m == '-':
                    action = '-'
                else:
                    if action == '+':
                        if m not in channel.modes:
                            channel.modes += m
                    elif action == '-':
                        channel.modes = channel.modes.replace(m, '')
            
            self.broadcast(channel.users, "MODE %s %s" % (channel.name, recv[2]))
        else:
            # /mode #channel +o-v user1 user2
            
            channel = [channel for channel in self.server.channels if channel.name == recv[1]]
            if channel == []:
                self.send_numeric(401, "%s :No such nick/channel" % recv[1])
                return
            channel = channel[0]
            
            if not channel.usermodes.has_key(self):
                self.send_numeric(482, "%s :You're not a channel operator" % channel.name)
                return
            if 'o' not in channel.usermodes[self]:
                self.send_numeric(482, "%s :You're not a channel operator" % channel.name)
                return
            
            modes = []
            action = ''
            for m in recv[2]:
                if m == '+':
                    action = '+'
                elif m == '-':
                    action = '-'
                elif m in "bohv":
                    modes.append(action + m)
            modes = zip(recv[3:], modes)
            
            for nick, mode in modes:
                user = [user for user in channel.users if user.nickname.lower() == nick.lower()]
                if user != []:
                    user = user[0]
                    if channel.usermodes.has_key(user):
                        if mode[0] == '+':
                            channel.usermodes[user] += mode[1]
                        else:
                            channel.usermodes[user] = channel.usermodes[user].replace(mode[1], "")
                    else:
                        if mode[0] == '+':
                            channel.usermodes[user] = mode[1]
            
            self.broadcast(channel.users, "MODE %s %s %s" % (channel.name, recv[2], ' '.join(recv[3:])))
    
    def handle_QUIT(self, recv):
        if len(recv) > 1:
            reason = recv[1]
        else:
            reason = self.nickname
        
        self.quit("Quit: " + reason)

class Channel:
    def __init__(self, name):
        self.name = name
        self.users = []
        self.modes = ''
        self.usermodes = {}
        self.topic = ""
        self.topic_author = ""
        self.topic_time = 0
        self.creation = int(time.time())
    
    def __repr__(self):
        return "<Channel '%s'>" % self.name

class Server(socket.socket):
    def __init__(self):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        
        self.users = []
        self.channels = []
        
        self.hostcache = {}
        
        self.hostname = config.hostname
        self.name = config.name
        self.creationtime = config.creation
        self.version = "omgircd-0.1.0"
        self.motd = config.motd
    
    def run(self):
        # Bind port and listen
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind((config.bind_host, config.bind_port))
        self.listen(5)
        
        # Main select loop (this is where the magic happens)
        while True:
            # Find users with pending send data
            sendable = [user for user in self.users if user.sendbuffer]
            
            read, write, error = select([self] + self.users, sendable, self.users, 25.0)
            
            for user in error:
                user.quit("Connection reset by peer")
            
            # Is there a new connection to accept?
            if self in read:
                # Accept connection and create new user object
                self.users.append(User(self, self.accept()))
            
            # Read from each user
            for user in [user for user in read if user != self]:
                try:
                    recv = user.socket.recv(4096)
                except socket.error, e:
                    user.quit("Connection reset by peer")
                if recv == '':
                    user.quit("Remote host closed the connection")
                user.recvbuffer += recv
                user.handle_recv()
            
            # Send to each user
            for user in write:
                try:
                    sent = user.socket.send(user.sendbuffer)
                    user.sendbuffer = user.sendbuffer[sent:]
                except socket.error, e:
                    user.quit("Connection reset by peer")
            
            # Garbage collection (Empty Channels)
            for channel in [channel for channel in self.channels if len(channel.users) == 0]:
                self.channels.remove(channel)
            
            # Ping timeouts
            for user in [user for user in self.users if time.time() - user.ping > 250.0]:
                user.quit("Ping timeout: %d seconds" % int(time.time() - user.ping))
            
            # Send out pings
            for user in [user for user in self.users if time.time() - user.ping > 125.0]:
                try:
                    user.socket.send("PING :%s\r\n" % self.hostname)
                except socket.error, e:
                    user.quit("Connection reset by peer")
    
    def shutdown(self):
        for user in self.users:
            user.quit("shutdown")
        self.close()

if __name__ == "__main__":
    server = Server()
    try:
        server.run()
    #except Exception, e:
    #    print e
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
