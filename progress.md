Progress
========

Implemented commands
--------------------

 * `/PING`
 * `/PONG`
 * `/NICK`
 * `/USER`
 * `/MOTD`
 * `/PRIVMSG`
 * `/NOTICE`
 * `/JOIN`
 * `/PART`
 * `/NAMES`
 * `/TOPIC`
 * `/ISON`
 * `/AWAY`
 * `/QUIT`
 * `/MODE`

Todo
----

### Commands

In order of priority:

1. `/WHOIS`
2. `/WHO`
3. `/USERHOST`
4. `/KICK`
5. `/LIST`
6. `/INVITE`

### Features

 * Channel bans
 * Server bans:
   * K-Line
   * Z-Line
 * Channel modes:
   * (__DONE__) `+m` Moderated
   * (__DONE__) `+t` Topic protection
   * (__DONE__) `+n` No outside messages
 * Channel Operators:
   * Ability to `/KICK`
   * (__DONE__) Ability to set `/MODE`
   * (__DONE__) Ability to `/TOPIC` if channel mode `+t` is set
 * (__DONE__) Maximum connections from one IP
 * Detect excess flood and kill

### Fixes

 * (__DONE__) Disallow UTF-8 in nicks and channel names
 * Fix ping flooding
 * Separate `/NAMES` response into multiple replies
 * Move repetitive code to functions:
   * For finding a channel by name
   * For finding a user by name
   * For verifying the correct amount of arguments (maybe)
 * (__DONE__) Add length limit on topics
 * (__DONE__) Only allow topic setting by ops when channel mode `+t` is set
 * (__DONE__) Only allow users on a channel to `/PRIVMSG` it when channel mode `+n` is set
