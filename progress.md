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

1. <strike>`/MODE`</strike>
2. `/WHOIS`
3. `/WHO`
4. `/USERHOST`
5. `/LIST`
6. `/KICK`
7. `/INVITE`

### Features

 * Channel bans
 * Server bans:
   * K-Line
   * Z-Line
 * Channel modes:
   * `+m` Moderated
   * `+t` Topic protection
   * `+n` No outside messages
 * Channel Operators:
   * Ability to `/KICK`
   * (__DONE__) Ability to set `/MODE`
   * Ability to `/TOPIC` if channel mode `+t` is set
 * Maximum connections from one IP
 * Detect excess flood and kill

### Fixes

 * (__DONE__) Disallow UTF-8 in nicks and channel names
 * Fix ping flooding
 * Separate `/NAMES` response into multiple replies
 * Move repetitive code to functions:
   * For finding a channel by name
   * For finding a user by name
   * For verifying the correct amount of arguments (maybe)
 * Add length limit on topics
 * Only allow topic setting by ops when channel mode `+t` is set
 * Only allow users on a channel to `/PRIVMSG` it when channel mode `+n` is set
