import json, re, requests
from lxml import html
from bot.events import Callback, msghandler
from util.irc import Message

hcolor = "06"
mcolor = "11"
r = re.compile(r"^https?:\/\/twitter\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)")
n = re.compile(r"<.*?>",re.DOTALL)
m = re.compile("(@[a-z0-9_]+)",re.I)
h = re.compile("(#\x02\x02[a-z0-9_]+)",re.I)
s = re.compile("\s+")

class Twitter(Callback):

    def __init__(self, server):
        self.server = server
        super().__init__(server)

    @Callback.inline
    @msghandler
    def trigger(self, server, line):
        link = r.search(line.text)
        if link:
            tweet = requests.get("https://api.twitter.com/1/statuses/oembed.json",params={"id":link.group(2)})
            if tweet.ok:
                tweet = s.sub(" ",html.fromstring(n.sub("",tweet.json()["html"])).text.split("—")[0].replace("\n"," ")).replace("#","#\x02\x02")
                tweet = m.sub("\x03{}\g<0>\x03".format(mcolor),tweet)
                tweet = h.sub("\x03{}\g<0>\x03".format(hcolor),tweet)
                return "\x0310│\x03 {}".format(tweet)

__initialise__ = Twitter
