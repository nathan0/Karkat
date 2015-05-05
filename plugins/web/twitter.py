import json, re, requests
from lxml import html
from bot.events import Callback, msghandler
from util.irc import Message

class Twitter(Callback):

    r = re.compile("^https?:\/\/twitter\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)")
    n = re.compile(r"<.*?>",re.DOTALL)

    def __init__(self, server):
        self.server = server
        super().__init__(server)

    @Callback.inline
    @msghandler
    def trigger(self, server, line):
        link = self.r.search(line.text)
        if link:
            tweet = requests.get("https://api.twitter.com/1/statuses/oembed.json",params={"id":link.group(2)})
            if tweet.ok:
                return "\x0308│\x03 {}".format(html.fromstring(self.n.sub("",tweet.json()["html"])).text)

__initialise__ = Twitter
