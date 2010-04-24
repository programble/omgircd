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
        
        self.nickname = "*"
        self.username = "unknown"
        self.realname = "Unknown"
        
        try:
            self.hostname = socket.gethostbyaddr(self.ip)[0]
        except:
            self.hostname = self.ip
        
        self.channels = []
    
    def fileno(self):
        return self.socket.fileno()
    
    def fullname(self):
        return "%s!%s@%s" % (self.nickname, self.username, self.hostname)
    
    def parse_command(self, data):
        xwords = data.split()
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
        self.send_numeric(375, ":%s message of the day" % self.server.hostname)
        for line in self.server.motd.split("\n"):
            self.send_numeric(372, ":- %s" % line)
        self.send_numeric(376, ":End of message of the day.")
    
    def handle_recv(self):
        while self.recvbuffer.find("\r\n") != -1:
            recv = self.recvbuffer[:self.recvbuffer.find("\r\n")]
            self.recvbuffer = self.recvbuffer[self.recvbuffer.find("\r\n")+2:]
            
            parsed = self.parse_command(recv)
            command = parsed[0]
            if command == "PING":
                self.handle_PING(parsed)
            elif command == "NICK":
                self.handle_NICK(parsed)
            elif command == "USER":
                self.handle_USER(parsed)
            elif command == "PRIVMSG":
                self.handle_PRIVMSG(parsed)
            elif command == "JOIN":
                self.handle_JOIN(parsed)
            else:
                self.send_numeric(421, "%s :Unknown command" % command)
    
    def handle_PING(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "PING :Not enough parameters")
            return
        self._send(":%s PONG %s :%s" % (self.server.hostname, self.server.hostname, recv[1]))
    
    def handle_NICK(self, recv):
        if len(recv) < 2:
            # No nickname given
            self.send_numeric(431, ":No nickname given")
            return
        nick = recv[1]
        
        # Check if nick is valid
        for invalid in "!@#$%&*()=~:;'\".,/?+":
            if invalid in nick:
                self.send_numeric(432, "%s :Erroneous Nickname" % nick)
                return
        
        # Check if nick is already in use
        if nick.lower() in [user.nickname.lower() for user in self.server.users]:
            self.send_numeric(433, "%s :Nickname is already in use" % nick)
            return
        
        # Nick is AWWW RIGHT
        self.broadcast([self], "NICK :%s" % nick)
        self.nickname = nick
        
        if self.username != "unknown":
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
        
        # PM to user
        if target[0] != "#":
            # Find user
            user = [user for user in self.server.users if user.nickname.lower() == target.lower()]
            
            # User does not exist
            if user == []:
                self.send_numeric(401, "%s :No such nick/channel" % target)
                return
            
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
    
    def handle_JOIN(self, recv):
        if len(recv) < 2:
            self.send_numeric(461, "JOIN :Not enough parameters")
            return
        
        channel = [channel for channel in self.server.channels if channel.name == recv[1]]
        
        # Create non-existent channel
        if channel == []:
            new = Channel(recv[1])
            self.server.channels.append(new)
            channel = [new]
        
        channel = channel[0]
        channel.users.append(self)
        self.channels.append(channel)
        
        self.broadcast(channel.users, "JOIN :%s" % recv[1])
        self._send(":%s MODE %s +%s" % (self.server.hostname, channel.name, ''.join(channel.modes)))
        # FIXME:
        self.send_numeric(353, "@ %s :%s" % (channel.name, " ".join([user.nickname for user in channel.users])))
        self.send_numeric(366, "%s :End of /NAMES list." % channel.name)
        

class Channel:
    def __init__(self, name):
        self.name = name
        self.users = []
        self.modes = []
        self.usermodes = []
        self.topic = ""
        self.topic_author = ""
        self.topic_time = 0

class Server(socket.socket):
    def __init__(self):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        
        self.users = []
        self.channels = []
        
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
            
            read, write, error = select([self] + self.users, sendable, [self] + self.users)
            
            # Is there a new connection to accept?
            if self in read:
                # Accept connection and create new user object
                self.users.append(User(self, self.accept()))
            
            # Read from each user
            for user in [user for user in read if user != self]:
                try:
                    recv = user.socket.recv(4096)
                except socket.error, e:
                    # TODO: Broadcast quit
                    self.users.remove(user)
                if recv == '':
                    # TODO: Broadcast quit
                    self.users.remove(user)
                user.recvbuffer += recv
                user.handle_recv()
            
            # Send to each user
            for user in write:
                try:
                    sent = user.socket.send(user.sendbuffer)
                    user.sendbuffer = user.sendbuffer[sent:]
                except socket.error, e:
                    # TODO: Broadcast quit
                    self.users.remove(user)
                    
    def shutdown(self):
        for user in self.users:
            user.socket.close()
        self.close()

if __name__ == "__main__":
    server = Server()
    try:
        server.run()
    except Exception, e:
        print e
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
