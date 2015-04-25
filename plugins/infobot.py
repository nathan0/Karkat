from bot.events import command
import json

infofile = "info.json"
protectionfile = "users.json"

def isprotected(server, user):
    try:
        protected = json.load(open(server.get_config_dir(protectionfile)))
    except:
        protected = {}
    return server.lower(user) in protected and protected[server.lower(user)]

def set_protected(server, user):
    """ Add protection if not defined """
    try:
        protected = json.load(open(server.get_config_dir(protectionfile)))
    except:
        protected = {}
    if server.lower(user) not in protected:
        protected[server.lower(user)] = True
    json.dump(protected, open(server.get_config_dir(protectionfile), "w"))

@command("protect", r"(on|off|none)?")
def toggle_protection(server, msg, state):
    user = msg.address.nick
    luser = server.lower(user)
    registered = server.registered.get(luser, False)
    try:
        protected = json.load(open(server.get_config_dir(protectionfile)))
    except:
        protected = {}
    if state == "on":
        protected[luser] = True
    elif state == "off":
        protected[luser] = False
    elif state == "none":
        del protected[luser]
    else:
        protected[luser] = not protected.get(luser, False)
    json.dump(protected, open(server.get_config_dir(protectionfile), "w"))
    return "│ Account protection for %s is %s" %(user, "CLEARED" if luser not in protected else ["OFF", "ON"][protected[luser]])
    

@command("info", r"(.*)", prefixes=("", "."))
def info(server, msg, user):
    try:
        data = json.load(open(server.get_config_dir(infofile)))
    except:
        data = {}
    user = user or msg.address.nick
    luser = server.lower(user)
    protected = isprotected(server, user)
    if luser not in data:
        return "I don't have info about %s. %s can use \x0312!setinfo \x1fblurb\x0f to add their info, or try !info %s if another bot provides this service." % (user, user, user)
    elif protected:
        return "\x0312%s\x03: %s" % (user, data[luser])
    else:
        return "%s: %s" % (user, data[luser])

@command("setinfo", r"(.*)", prefixes=("!", "."))
def setinfo(server, msg, info):
    try:
        data = json.load(open(server.get_config_dir(infofile)))
    except:
        data = {}
    user = msg.address.nick
    luser = server.lower(user)
    protected = isprotected(server, user)
    registered = server.registered.get(luser, False)

    if protected and registered:
        if msg.prefix != "!":
            yield "│ This nickname is protected by the owner. Please identify with NickServ to update your info."
        return

    if not info:
        del data[luser]
        yield "│ Your information has been deleted."
    else:
        data[luser] = info
        if msg.prefix != "!":
            yield "│ Your information has been updated."

    if registered:
        set_protected(server, user)

    json.dump(data, open(server.get_config_dir(infofile), "w"))

__callbacks__ = {"privmsg": [info, setinfo, toggle_protection]}