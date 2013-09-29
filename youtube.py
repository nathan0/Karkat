"""
Functions for manipulating urls.
"""
from irc import Message

import yaml
import json
import functools
import requests
import time
import sys
import re

try:
    apikeys = yaml.safe_load(open("apikeys.conf"))["youtube"]
except:
    print("Warning: invalid or nonexistant api key.", file=sys.stderr)
    print("Youtube module not loaded.", file=sys.stderr)
    raise ImportError


class Youtube(object):
    refresh = apikeys["channel"]
    appid = apikeys["appid"]
    secret = apikeys["secret"]

    def __init__(self):
        self.refresh_tokens()

    def request_auth(self):
        import webbrowser
        webbrowser.open("https://accounts.google.com/o/oauth2/auth?client_id=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/youtube" % self.appid)

    def get_auth_tokens(self, authtoken):
        payload = {"code": authtoken,
                   "client_id": self.appid,
                   "client_secret": self.secret,
                   "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                   "grant_type": "authorization_code"}
        answer = requests.post("https://accounts.google.com/o/oauth2/token", data=payload).json()
        self.token = answer["access_token"]
        self.refresh = answer["refresh_token"]
        self.refresh_after = time.time() + int(answer["expires_in"])
        return answer

    def refresh_tokens(self):
        payload = {"client_id": self.appid,
                   "client_secret": self.secret,
                   "refresh_token": self.refresh,
                   "grant_type": "refresh_token"}
        answer = requests.post("https://accounts.google.com/o/oauth2/token", data=payload).json()
        self.token = answer["access_token"]
        self.refresh_after = time.time() + int(answer["expires_in"])
        return answer

    def tokensExpired(self):
        return time.time() > self.refresh_after

    def apimethod(funct):
        @functools.wraps(funct)
        def wrapper(self, *args, **kwargs):
            if self.tokensExpired():
                self.refresh_tokens()
            return funct(self, *args, **kwargs)
        return wrapper

    @apimethod
    def get_playlist_id(self, channel):
        payload = {"part": "snippet", "mine": "true", "maxResults":"50", "access_token": self.token}
        answer = requests.get("https://www.googleapis.com/youtube/v3/playlists", params=payload).json()
        for result in answer["items"]:
            if result["snippet"]["title"] == channel:
                return result["id"]

    @apimethod
    def create_playlist(self, playlist):
        payload = {
                    "snippet": {
                            "title": playlist
                            },
                    "status": {
                                "privacyStatus": "public"
                                }
                    }
        params = {"part": "snippet,status", "access_token": self.token}
        answer = requests.post("https://www.googleapis.com/youtube/v3/playlists", params=params, data=json.dumps(payload), headers={"Content-Type": "application/json"}).json()
        return answer["id"]

    @apimethod
    def playlist_insert(self, playlist, item):
        params = {"part": "snippet", "access_token": self.token}

        payload = {
                    "snippet": {
                        "playlistId": playlist,
                        "resourceId": {
                            "videoId": item,
                            "kind": "youtube#video"
                            }
                        }
                    }
        answer = requests.post("https://www.googleapis.com/youtube/v3/playlistItems", data=json.dumps(payload), params=params, headers={"Content-Type": "application/json"}).json()
        return answer

    @apimethod
    def get_music_video(self, song):
        p = {"part": "snippet", "access_token": self.token, "maxResults":"1", "q": song, "videoCategoryId": "10", "type":"video"}
        answer = requests.get("https://www.googleapis.com/youtube/v3/search", params=p).json()
        return (answer["items"][0]["snippet"]["title"], answer["items"][0]["id"]["videoId"])


    def trigger(self, words, line):
        message = Message(line)
        videos = re.findall("(?:youtube\.com/watch\?(?:.+&)?v=|youtu\.be/)([a-zA-Z0-9-_]+)", message.message)
        if videos:
            playlist = self.get_playlist_id(message.context) or self.create_playlist(message.context)
            for video in videos:
                self.playlist_insert(playlist, video)
