import sys
import yaml
import requests

from bot.events import command


try:
    apikeys = yaml.safe_load(open("config/apikeys.conf"))["yo"]
except:
    print("Error: invalid or nonexistant yo api key.", file=sys.stderr)
    raise ImportError("Could not load module.")

@command("yo", r"(\S+)")
def yo(server, message, username):
    data = requests.post("http://api.justyo.co/yo/", data={"api_token": list(apikeys.values())[0], 'username':username})
    try:
        data = data.json()
    except:
        return "04│🖐│ Yo's fucked up."
    else:
        if "success" in data:
           return "13│🖐│ Yo'd at %s" % username
        else:
            return "04│🖐│ " + data["error"]

__callbacks__ = {"privmsg": [yo]}
