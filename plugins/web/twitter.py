import json, re, requests
from lxml import html
from bot.events import Callback, msghandler
from util.irc import Message

class Twitter(Callback):

    def __init__(self, server):
        self.server = server
        super().__init__(server)

    @Callback.inline
    @msghandler
    def trigger(self, server, line):
        msg = line.text
        link = re.search("^https?:\/\/twitter\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)",msg)
        if link:
            id = link.group(2)
            tweet = requests.get("https://api.twitter.com/1/statuses/oembed.json",params={"id":id})
            if tweet.ok:
                p = re.compile(r'<.*?>',re.DOTALL)
                return "\x0308│\x03 {}".format(html.fromstring(p.sub("",tweet.json()["html"])).text)

__initialise__ = Twitter
