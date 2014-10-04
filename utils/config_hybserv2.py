#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from random import choice
from crypt import crypt
from datetime import datetime
import os

from path import path
import yaml

NOW_UNIX = datetime.now().strftime("%s")
ROOT_PATH = path(__file__).abspath().dirname()
CONFIG_FILE = ROOT_PATH.joinpath('config.yaml')

def __crypt_cleartext(text, salt=None):
    """Return cleartext text, crypted with salt salt."""
    saltChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./"
    if not salt:
        # Produce a random DES salt
        salt = choice(saltChars) + choice(saltChars)
    return crypt(text, salt)

def add_users_to(userslist, nicks={}):
    """Given nicks dict, produce new nicks dict with userlist added.

    Allows user info update by specifying existing nicknames."""
    def_hostline = "->HOST *~webchat@*.us-west-1.compute.internal"
    for username, cleartext in userslist:
        if not nicks.has_key(username):
            nicks[username] = {'nick': username, 'interval': 14600, 'ctime': NOW_UNIX,
                               'seen': NOW_UNIX, 'otherlines': [def_hostline]}
        nicks[username]['pass'] = __crypt_cleartext(cleartext)
    return nicks

def add_channels_to(chanupdates, chandata={}):
    new_chandata = chandata.copy()
    defaults = {'channel': '', 'dummy0': '4', 'founded': NOW_UNIX, 'updated': NOW_UNIX,
                'otherlines': ['->FNDR sysop {}'.format(NOW_UNIX),
                               '->PASS LZ5SxAssB3LX2',
                               '->ALVL -1 5 8 5 5 8 10 10 10 8 15 20 25 40 50'],
                'ops_users': {'sysop': (None, '50', NOW_UNIX, NOW_UNIX, '*As')}}
    for update_data in chanupdates:
        channel = update_data['channel']
        if new_chandata.has_key(channel):
            new_chandata[channel].update(update_data)
        else:
            new_update = defaults.copy()
            new_update.update(update_data)
            new_chandata[channel] = new_update
    return new_chandata

def nick_db_entry(nickconfig):
    output = "{nick} {interval} {ctime} {seen}\n->PASS {pass}\n".format(**nickconfig)
    output += "\n".join(nickconfig['otherlines']) + "\n"
    return output

def write_nickdb(nickdbfile, nicks):
    header = "; Hybserv2 NickServ database auto-generated from edX data on {}\n".format(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    with open(nickdbfile, 'wb') as dbfile:
        dbfile.write(header)
        for nick in sorted(nicks.keys()):
            dbfile.write(nick_db_entry(nicks[nick]))

def write_chandb(chandbfile, channels):
    header = "; Hybserv2 ChanServ database auto-generated from edX data on {}\n".format(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    with open(chandbfile, 'wb') as dbfile:
        dbfile.write(header)
        for ircchan in sorted(channels.keys()):
            chandata = channels[ircchan]
            output = "{channel} {dummy0} {founded} {updated}\n".format(**chandata)
            output += "\n".join(chandata['otherlines']) + "\n"
            for username in sorted(chandata['ops_users']):
                hostspec, alvl, ctime, mtime, addedby = chandata['ops_users'][username]
                if hostspec:
                    hostspec = '!' + hostspec.split('@')[0] + '@*'
                else:
                    hostspec = ''
                output += "->ACCESS {}{} {} {} {} {}\n".format(username, hostspec, alvl, ctime, mtime, addedby)
            dbfile.write(output)

def read_nickdb(nickdbfile):
    """Read a nick.db file and return a dictionary of configured users and their user data"""
    nicks = {}
    with open(nickdbfile, 'rb') as nickdb:
        nick = ''
        for line in nickdb:
            if line[0] == ';': continue
            line = line.rstrip()
            if line[:2] != "->":
                nick, interval, ctime, seen = line.split(' ')
                if nicks.has_key(nick):
                    raise RuntimeError, "Malformed nick.db file detected - {} more than once in file".format(nick)
                nicks[nick] = {"nick": nick, "interval": interval, "ctime": ctime, "seen": NOW_UNIX, 'otherlines': []}
            elif line[:2] == "->":
                if not nick:
                    raise RuntimeError, "Malformed nick.db file, at least one bad stanza definition"
                if line[:6] == "->PASS":
                    nicks[nick]['pass'] = line[7:]
                else:
                    nicks[nick]['otherlines'].append(line)
    return nicks

def read_chandb(chandbfile):
    """Read a nick.db file and return a dictionary of configured users and their user data"""
    chans = {}
    with open(chandbfile, 'rb') as chandb:
        for line in chandb:
            if line[0] == ';': continue
            line = line.rstrip()
            if line[:2] != "->":
                channel, dummy0, founded, updated = line.split(' ')
                if chans.has_key(channel):
                    raise RuntimeError, "Malformed chan.db file detected - {} more than once in file".format(channel)
                chans[channel] = {'channel': channel, 'dummy0': dummy0, 'founded': founded, 'updated': NOW_UNIX,
                                  'ops_users': {}, 'otherlines': []}
            elif line[:2] == "->":
                if line[:8] == "->ACCESS":
                    splitline = line.split(' ')
                    if len(splitline) < 6: # Can this ever happen? Not sure...
                        splitline.extend([None] * (6-len(splitline)))
                    access, user_host, alvl, ctime, mtime, addedby = splitline
                    user_host = user_host.split('!')
                    if len(user_host) < 2: # this can definitely happen
                        user_host.append(None)
                    username, host = user_host
                    chans[channel]['ops_users'][username] = (host, alvl, ctime, mtime, addedby)
                else:
                    chans[channel]['otherlines'].append(line)
    return chans

def read_config(cfile=CONFIG_FILE, chandata={}):
    """Read channel configuration from cfile, use settings to shadow vars in shadow.

    If no configuration file found at specified path, and if chandata is non-empty,
    a new configuration file containing chandata will be created."""
    if os.path.exists(cfile):
        with open(cfile, 'rb') as c:
            return yaml.load(c)

    new_config = {}
    for chan in sorted(chandata.keys()):
        chan = irc_to_course(chan)
        new_config[chan] = [
                "bad password. update this from https://class.stanford.edu/courses/COURSE_ID_TRIPLE/instructor/api/irc_instructor_auth_token",
            sorted([x for x in chandata[chan]['ops_users']])]
    if new_config:
        print "Missing file at {}".format(cfile)
        print "Warning, no configuration file found. One will be created from your current"
        print "    database files, and your database files will only get written to update"
        print "    sort entries and update usage timestamps."
        with open(cfile, 'wb') as c:
            yaml.dump(new_config, c, width=120, indent=2, canonical=False, default_flow_style=False)
    return new_config

def merge_dbs_configs(nick_db_in, chan_db_in, config):
    """Merge data from config into data from dbs, return new db data."""
    userlist = []
    chanlist = []
    def_opslist = {'sysop': (None, '50', '1403044603', '1403044603', '*As'),}
    def_useropts = ('~webchat@*', '11', '1403306438', '1405369523', 'sysop')
    for course in sorted(config.keys()):
        coursepass = config[course][0]
        courseusers = sorted(config[course][1])
        opslist = def_opslist.copy()
        for user in courseusers:
            userlist.append((user, coursepass))
            opslist[user] = def_useropts
        chanlist.append({'channel': course_to_irc(course), 'ops_users': opslist})
    nick_db_out = add_users_to(userlist, nick_db_in)
    chan_db_out = add_channels_to(chanlist, chan_db_in)
    return nick_db_out, chan_db_out

def course_to_irc(course):
    """i.e., Engineering/EE-292L/Fall2014 -> #Engineering.EE-292L.Fall2014"""
    return '#' + '.'.join( course.split('/') )

def irc_to_course(course):
    """i.e.,#Engineering.EE-292L.Fall2014 -> Engineering/EE-292L/Fall2014"""
    return '/'.join(course.lstrip('#').split('.'))

DESCRIPTION = "Generate hybserv2 v.1.9.4-release nick.db and chan.db files."

def get_parsed_args():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
    )
    parser.add_argument(
        'nickfile',
        default='/tmp/nick.db',
        help="path to a nick.db file",
    )
    parser.add_argument(
        'chanfile',
        default='/tmp/chan.db',
        help="path to a chan.db file",
    )
    parser.add_argument(
        'configfile',
        default=CONFIG_FILE,
        help="path to course admin configuration",
    )
    parser.add_argument(
        '--suffix',
        default='.new',
        help='output_file = input_file + suffix',
    )
    return parser.parse_args()

def main():
    """Drive. Parse arguments, do file I/o, set up work."""
    args = get_parsed_args()

    nicks = read_nickdb(args.nickfile)
    chans = read_chandb(args.chanfile)
    config = read_config(cfile=args.configfile)

    nicks, chans = merge_dbs_configs(nicks, chans, config)

    write_nickdb(args.nickfile + args.suffix, nicks)
    write_chandb(args.chanfile + args.suffix, chans)

if __name__ == "__main__":
    main()

