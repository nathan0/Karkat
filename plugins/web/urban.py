"""
Get definitions from urbandictionary
A James module.
"""
from bot.events import command, Callback
from util.services.url import shorten, format
import requests
import random
import re


@command(['urban', 'urbandictionary', 'ud'], r"^(.+?)(\s+\d+)?$",
         templates={Callback.USAGE: "04urban dictionary│ Usage: urban <phrase> [index]"})
def urban_lookup(bot, msg, arg, index):
    ''' UrbanDictionary lookup. '''

    url = 'http://www.urbandictionary.com/iphone/search/define'
    params = {'term': arg}
    nick = msg.address.nick
    try:
        index = int(index.strip()) - 1
    except:
        index = 0

    request = requests.get(url, params=params)

    data = request.json()
    defs = None
    output = ""
    try:
        defs = data['list']

        if data['result_type'] == 'no_results':
            return failmsg() % (nick, params['term'])

        output = "%s 15│ %s" % (defs[index]['word'], re.sub(r"\[(.+?)\]", "\x02\\1\x02", re.sub(r"\[word\](.+?)\[/word\]", "\x02\\1\x02", defs[index]['definition'])))
    except:
        return failmsg() % params['term']

    output = " ".join(output.split())
    sentences = re.split("([!.?]+)", output)
    output = sentences.pop(0)
    i = 1
    while sentences:
        s = sentences.pop(0)
        if i % 2 or len(output) + len(s) < 350:
            output += s
        else:
            sentences = [s] + sentences # put it back gently
            break
        i += 1

    if sentences:
        output += '\n15│ Read more: %s' % format(shorten(defs[index]['permalink']))

    return "15│ %s" % output

def failmsg():
    return random.choice([
        "15│ No definition found for %s.",
        "15│ The heck is '%s'?!",
        "15│ %s. wut.",
        "15│ %s? I dunno...",
        "15│ Stop searching weird things. What even is '%s'?",
        "15│ Computer says no. '%s' not found.",
        "15│ This is a family channel. Don't look up '%s'",
        "15│ Trust me, you don't want to know what '%s' means.",
        "15│ %s [1]: Something looked up by n00bs.",
        "15│ %s [1]: An obscure type of fish."])

#@command(['urbanrandom', 'urbandictionaryrandom', 'udr'])
#def urban_random(server, message):
#    ''' Random UrbanDictionary lookup. '''
#    word = requests.get("http://api.urbandictionary.com/v0/random").json()['list'][0]['word']
#    urban_lookup(server, ":" + message.message.split(":", 2)[1] + ":.ud " + word)

__callbacks__ = {"privmsg": [urban_lookup]}