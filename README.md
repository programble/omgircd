Omgircd
=======

Omgircd is an Internet Relay Chat Daemon (IRCd) written in Python. It
is designed to be as simple as possible, while still providing a
complete IRC experience.

Usage
-----

Omgircd is still in development and therefore does not have a complete
launch script. The simplest way to launch Omgircd for now is to simply
run `ircd.py`

    python ircd.py

An alternative method to run Omgircd is using the `ircdreload.py`
script. This launch script provides a means to reload the IRCd code on
the fly while it is running. This script is only recommended for use
in development.

    python ircdreload.py

In order to reload the IRCd code, type Control+c (`C-c`). You will then
be prompted with `[r/q]`. Typing `r` at this prompt will cause all
IRCd code to be reloaded and the IRCd to continue to run. Typing `q`
at this prompt will cause the IRCd to shut down and exit.

Additionally, if an unhandled exception occurs in the IRCd code, it
will be caught by the script and its traceback will be printed
out. The same prompt will then appear in order to give an opportunity
to fix the code and then reload the fixed code, without the server
going down.

Configuration
-------------

In its current state, Omgircd is not very configurable. The main focus
has been to focus on getting the IRCd to run perfectly, and then make
it more configurable afterwards. The few configuration options
available are located in `config.py`.

Progress
--------

For documentation on development progress, see `progress.md`.
