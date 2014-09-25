#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import choice
from crypt import crypt
from datetime import datetime

NOW_UNIX = datetime.now().strftime("%s")

def __make_des_salt():
    """Generate a random DES salt."""
    saltChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./"
    return choice(saltChars) + choice(saltChars)

def __crypt_cleartext(text, salt=None):
    """Return cleartext text, crypted with salt salt."""
    if not salt:
        salt = __make_des_salt()
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

def nick_db_writer(nickdbfile, nicks):
    header = "; Hybserv2 NickServ database auto-generated from edX data on {}\n".format(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    with open(nickdbfile, 'wb') as dbfile:
        dbfile.write(header)
        for nick in sorted(nicks.keys()):
            dbfile.write(nick_db_entry(nicks[nick]))

def chan_db_writer(chandbfile, channels):
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

def nick_db_reader(nickdbfile):
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
                #nicks[nick] = {"nick": nick, "interval": interval, "ctime": ctime, "seen": seen, 'otherlines': []}
                nicks[nick] = {"nick": nick, "interval": interval, "ctime": ctime, "seen": NOW_UNIX, 'otherlines': []}
            elif line[:2] == "->":
                if not nick:
                    raise RuntimeError, "Malformed nick.db file, at least one bad stanza definition"
                if line[:6] == "->PASS":
                    nicks[nick]['pass'] = line[7:]
                else:
                    nicks[nick]['otherlines'].append(line)
    return nicks

def chan_db_reader(chandbfile):
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
                #chans[channel] = {'channel': channel, 'dummy0': dummy0, 'founded': founded, 'updated': updated, 
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

def very_bad_writer():
    """Write out correctly-formatted data garnered in a very bad way."""
    nick_file_name="/tmp/nick.db"
    chan_file_name="/tmp/chan.db"
    nick_file_name_new="/tmp/nick.db.new"
    chan_file_name_new="/tmp/chan.db.new"
    courseops = {"Engineering/EE-292L/Fall2014": 
                    [("aneeshnainani", '713965ac70d378ef90461dc1fd0c9ecc0502474b'),
                     ("gbruhns", '713965ac70d378ef90461dc1fd0c9ecc0502474b'),
                     ("JennKal79", '713965ac70d378ef90461dc1fd0c9ecc0502474b'),],
                 "HumanitiesSciences/HUMBIO89/Fall2014":
                    [('gbruhns', 'f8578ead81ec01ae8aae0099c2465b24f4551388'),
                     ('kristinsainani', 'f8578ead81ec01ae8aae0099c2465b24f4551388'),
                     ('JWallach', 'f8578ead81ec01ae8aae0099c2465b24f4551388'),
                     ('vajpayee', 'f8578ead81ec01ae8aae0099c2465b24f4551388'),
                    ],
                }
    userlist = []
    chanlist = []
    nicks = nick_db_reader(nick_file_name)
    chans = chan_db_reader(chan_file_name)
    def_opslist = {'sysop': (None, '50', '1403044603', '1403044603', '*As'),}
    for course in sorted(courseops.keys()):
        userlist.extend(courseops[course])
        opslist = def_opslist.copy()
        for user, dummy in courseops[course]:
            opslist[user] = chanlist_default_useropts()
        chanlist.append({'channel': ircify_coursename(course), 'ops_users': opslist})
    nicks = add_users_to(userlist, nicks)
    chans = add_channels_to(chanlist, chans)
    nick_db_writer(nick_file_name_new, nicks)
    chan_db_writer(chan_file_name_new, chans)

def chanlist_default_useropts():
    return ('~webchat@*', '11', '1403306438', '1405369523', 'sysop')

def ircify_coursename(course):
    """i.e., Engineering/EE-292L/Fall2014 -> #Engineering.EE-292L.Fall2014"""
    return '#' + '.'.join( course.split('/') )

def main():
    # Use argparse to parse arguments
    # If called with --test, run doctests
    # If called with a particular courseid, 
    #     get info for that course
    # If called with no courseid, scrape homepage and do all of those course
    #
    # Preserve existing entries unless called with a do-everything flag
    very_bad_writer()


if __name__ == "__main__":
    main()
