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
        self.send_numeric(004, "%s  bohv" % self.server.version)
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
        if nick in [user.nickname for user in self.server.users]:
            self.send_numeric(433, "%s :Nickname is already in use" % nick)
            return
        
        # Nick is AWWW RIGHT
        self.broadcast([self], "NICK :%s" % nick)
        self.nickname = nick
    
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
        
        self.welcome()

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
                user.recvbuffer += user.socket.recv(4096)
                user.handle_recv()
            
            # Send to each user
            for user in write:
                sent = user.socket.send(user.sendbuffer)
                user.sendbuffer = user.sendbuffer[sent:]

if __name__ == "__main__":
    server = Server()
    server.run()
