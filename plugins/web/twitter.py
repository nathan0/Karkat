import json, re, requests
from lxml import html
from bot.events import Callback, msghandler
from util.irc import Message

hcolor = "06"
mcolor = "11"
r = re.compile(r"^https?:\/\/twitter\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)")
n = re.compile(r"<.*?>",re.DOTALL)
m = re.compile("@(.*?)\)?\s")
h = re.compile("#(.*?)\s")

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
                tweet = html.fromstring(n.sub("",tweet.json()["html"])).text.split("—")[0]
                mentions = m.findall(tweet)
                hashtags = h.findall(tweet)
                for _m in mentions:
                    tweet = tweet.replace("@{}".format(_m),"\x03{}@{}\x03".format(mcolor,_m))
                for _h in hashtags:
                    tweet = tweet.replace("#{}".format(_h),"\x03{}#\x02\x02{}\x03".format(hcolor,_h))
                return "\x0300,10Tweet│\x03 {}".format(tweet)

__initialise__ = Twitter
