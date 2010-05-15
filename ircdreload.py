#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       ircdreload.py
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

import traceback

import ircd

server = ircd.Server()
while True:
    try:
        server.run()
    except (KeyboardInterrupt, Exception):
        traceback.print_exc()
        x = raw_input("[r/q] ")
        if x == 'q':
            break
        else:
            reload(ircd)
            reload(ircd.config)
            old = server
            server = ircd.Server()
            server.channels = old.channels
            server.hostcache = old.hostcache
            for olduser in old.users:
                newuser = ircd.User(server, (olduser.socket, olduser.addr))
                newuser.nickname = olduser.nickname
                newuser.username = olduser.nickname
                newuser.realname = olduser.realname
                newuser.away = olduser.away
                for channel in olduser.channels:
                    try:
                        channel.users.remove(olduser)
                    except ValueError:
                        continue
                    channel.users.append(newuser)
                    channel.usermodes[newuser] = channel.usermodes[olduser]
                    channel.usermodes.pop(olduser)
                    newuser.channels.append(channel)
                #server.users.append(newuser)
            old.close()
            continue
server.shutdown()
