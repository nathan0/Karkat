import time
import json
import traceback
import random
import os
import re
import hashlib
import subprocess
import zipfile
import uuid

from io import BytesIO

import pysnap
from pysnap.utils import encrypt, make_media_id
import requests
from PIL import Image, ImageDraw, ImageFont

from util.text import pretty_date, ircstrip
from util import scheduler
from bot.events import Callback, command

snapfolder = "/var/www"
public_url = "http://xe.tetrap.us/"
prefix = "\x0308│\U0001f47b│\x03 "

try:
    cache = json.load(open(snapfolder + "/cache.json"))
except:
    cache = {}

colors = [(204, 204, 204), (0, 0, 0), (53, 53, 179), (42, 140, 42), (195, 59, 59), (199, 50, 50), (128, 38, 127), (102, 54, 31), (217, 166, 65), (61, 204, 61), (25, 85, 85), (46, 140, 116), (69, 69, 230), (176, 55, 176), (76, 76, 76), (149, 149, 149)]

fonts = {"arial": {"regular": "data/fonts/Arial.ttf", "bold": "data/fonts/Arial_Bold.ttf"},
         "comic sans": {"regular": "data/fonts/Comic_Sans_MS.ttf", "bold": "data/fonts/Comic_Sans_MS_Bold.ttf"},
         "dejavu sans": {"regular": "data/fonts/DejaVuSans.ttf", "bold": "data/fonts/DejaVuSans-Bold.ttf"},
         "dejavu sans mono": {"regular": "data/fonts/DejaVuSansMono.ttf", "bold": "data/fonts/DejaVuSansMono-Bold.ttf"},
         "impact": {"regular": "data/fonts/Impact.ttf"},
         "symbola": {"regular": "data/fonts/Symbola.ttf"},   
         "ubuntu": {"regular": "data/fonts/Ubuntu-R.ttf", "bold": "data/fonts/Ubuntu-B.ttf"}
        }

def drawtext(img, text, minsize=13, maxsize=100, wrap=True, outline=True, fonts=fonts["dejavu sans mono"]):
    lines = None
    size = maxsize + 5
    while size > minsize and not lines:
        size -= 5
        font = ImageFont.truetype(fonts["regular"], size)
        if wrap:
            lines = textwrap(img.size, font, text)
            if lines:
                lineheight, lines = lines
                break
        else:
            lines = ["<" + i if not re.match("^[>|<]", i) else i for i in text.split("\n")]
            lineheight = max(linesize(font, i[1:])[1] for i in lines) + 10
            if lineheight * len(lines) < img.size[1] and all(linesize(font, i[1:])[0] < img.size[0] for i in lines):
                break
            lines = None

    if not lines: return
    draw = ImageDraw.Draw(img)
    if "bold" in fonts:
        boldfont = ImageFont.truetype(fonts["bold"], size)
    else:
        boldfont = font
    color = None
    bold = False
    underline = False
    background = None
    i = -5
    while lines:
        line = lines.pop(0)
        align = line[0]
        line = line[1:]
        if not line:
            i = img.size[1] - (len(lines) * lineheight)
            continue
        if bold or "\x02" in line:
            f = boldfont
        else:
            f = font

        linewidth = linesize(f, line)[0]
        j = {"|": (img.size[0] - linewidth)//2,
             ">": (img.size[0] - linewidth - 5),
             "<": 5}[align]

        line = list(line)
        while line:
            char = line.pop(0)
            if char == "\x03":
                reset = True
                if line and line[0] in "0123456789":
                    reset = False
                    color = int(line.pop(0))
                    if line and line[0] in "0123456789":
                        color *= 10
                        color += int(line.pop(0))
                if len(line) > 1 and line[0] == "," and line[1] in "0123456789":
                    reset = False
                    line.pop(0)
                    background = int(line.pop(0))
                    if line and line[0] in "0123456789":
                        background *= 10
                        background += int(line.pop(0))
                if reset:
                    color = None
                    background = None
                    
            elif char == "\x0f":
                bold = False
                color = None
                underline = False
                background = None
            elif char == "\x1f":
                underline = not underline
            elif char == "\x02":
                bold = not bold
            else:
                if bold:
                    f = boldfont
                else:
                    f = font

                cwidth = f.getsize(char)[0]

                if background is not None:
                    bg = colors[background % len(colors)]
                    draw.rectangle([(j, i), (j+cwidth, i+lineheight)], fill=bg)

                if color == None:
                    c = (255, 255, 255)
                else:
                    c = colors[color % len(colors)]

                if underline:
                    draw.line([(j,i+lineheight), (j+cwidth, i+lineheight)], fill=c, width=3)

                if outline:
                    # draw outline
                    o = (c[0] + c[1] + c[2])/3
                    o = 0 if o > 127 else 255
                    draw.text((j-2, i-2), char, (o,o,o), font=f)
                    draw.text((j-2, i+2), char, (o,o,o), font=f)
                    draw.text((j+2, i+2), char, (o,o,o), font=f)
                    draw.text((j+2, i-2), char, (o,o,o), font=f)

                draw.text((j, i), char, c, font=f)
                j += cwidth
        i += lineheight

    return img

def textwrap(dim, font, text):
    width, height = dim[0] - 10, dim[1]
    text = text.split("\n")
    alines = []
    for line in text:
        align = "<"
        if re.match(r"^[>|<]", line):
            align = line[0]
            line = line[1:]
        line = line.split(" ")
        if any(linesize(font, i)[0] > width for i in line):
            return
        lines = [align + line[0]]
        for i in line[1:]:
            if linesize(font, (lines[-1] + " " + i)[1:])[0] > width:
                lines.append(align + i)
            else:
                lines[-1] += " " + i
        alines.extend(lines)
    lineheight = max(linesize(font, i[1:])[1] for i in lines) + 10
    if lineheight * len(alines) <= height:
        return lineheight, alines

def linesize(font, text):
    return font.getsize(ircstrip(text))


def save(data, fmt):
    sig = hashlib.md5(data).hexdigest()
    if sig in cache:
        return cache[sig].rsplit(".", 1)[0]
    fchars =  "abcdefghijklmnopqrstuvwxyz-_+=~ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    template = snapfolder + "/%s." + fmt
    fname = random.choice(fchars)
    while os.path.exists(template % fname):
        fname += random.choice(fchars)
    with open(template % fname, "wb") as f:
        f.write(data)
    cache.update({sig: fname + "." + fmt})
    with open(snapfolder + "/cache.json", "w") as c:
        json.dump(cache, c)
    return fname

def save_as(data, fmt):
    if fmt == "gif":
        return gifify(save(data, "mp4"))
    else:
        return save(data, fmt)

def gifify(fname):
    var = {"pid": os.getpid(), "id": fname, "folder": snapfolder}
    subprocess.call("ffmpeg -i '%(folder)s/%(id)s.mp4' -vf scale=320:-1 -r 12 '/tmp/snapchat-%(pid)s-%(id)s.%%04d.png'" % var, shell=True)
    subprocess.call("convert -delay 25x300 -loop 0 /tmp/snapchat-%(pid)s-%(id)s.*.png '%(folder)s/%(id)s.gif'" % var, shell=True)
    subprocess.call("rm /tmp/snapchat-%(pid)s-%(id)s.*.png" % var, shell=True)
    return fname

class Snap(Callback):

    SETTINGS_FILE = "snapchat.json"
    DELETION_FILE = "snapchat-deletion.json"
    USERS_FILE = "snapchat-users.json"

    def __init__(self, server):
        self.settingsf = server.get_config_dir(self.SETTINGS_FILE)
        try:
            self.settings = json.load(open(self.settingsf))
        except FileNotFoundError:
            self.settings = {}
        
        self.deletionf = server.get_config_dir(self.DELETION_FILE)
        try:
            self.deletion = json.load(open(self.deletionf))
        except FileNotFoundError:
            self.deletion = {}

        self.usersf = server.get_config_dir(self.USERS_FILE)
        try:
            self.users = json.load(open(self.usersf))
        except FileNotFoundError:
            self.users = {}

        self.unverified = {}

        self.accounts = {i: pysnap.Snapchat() for i in self.settings}
        for i in self.settings:
            self.accounts[i].login(self.settings[i]["username"], self.settings[i]["password"])
        self.cache = {}
        self.checker = scheduler.schedule_after(45, self.checksnaps, args=(server,), stop_after=None)
        self.server = server

        super().__init__(server)

    def add_deletion(self, username, id, link):
        self.deletion.setdefault(username.lower(), {}).update({id: link})
        
        json.dump(self.deletion, open(self.deletionf, "w"))
        
    def snapsave(self, data, media_type):
        sig = hashlib.md5(data).hexdigest()
        if sig in self.cache:
            return self.cache[sig]
        res = None

        filetype = ["jpg", "mp4", "gif"][media_type]

        res = public_url + save_as(data, filetype) + "." + filetype

        self.cache[sig] = res
        return res

    @command("snapassoc", r"([^ ]+)\s+([^ ]+)\s+([^ ]+)", admin=True)
    def associate(self, server, message, channel, username, password):
        # try to login
        res = pysnap.Snapchat()
        if not res.login(username, password):
            return prefix + "\x0304Could not log in."
        channel = server.lower(channel)
        if channel in self.accounts:
            self.accounts[channel].logout()
        self.accounts[channel] = res
        self.settings[server.lower(channel)] = {"username": username, "password": password, "snaps": {}, "last": time.time(), "history":[]}
        json.dump(self.settings, open(self.settingsf, "w"))
        return prefix + "\x0304Associated %s with username %s successfully." % (channel, username)

    def newsnaps(self, channel):
        account = self.accounts[channel]

        if channel not in self.accounts or channel not in self.settings:
            return
        self.settings[channel]["last"] = time.time()
        snaps = account.get_snaps(self.settings[channel]["last"])
        for snap in snaps:
            try:
                if snap["id"] in self.settings[channel]["snaps"]:
                    continue
                blob = account.get_blob(snap["id"])
                if not blob:
                    self.settings[channel]["snaps"][snap["id"]] = None
                    continue
                self.unverified = {k:v for k, v in self.unverified.items() if v[0].lower() != snap["sender"].lower()}
                print(snap)
                print("*** Saving", snap["id"])
                url = self.snapsave(blob, snap["media_type"])
                print("*** URL:", url)
                self.settings[channel]["snaps"][snap["id"]] = url
                self.settings[channel].setdefault("history", []).append(snap)
                account.mark_viewed(snap["id"])
                self.server.lasturl = url
                username = [k for k, v in self.users.items() if v.lower() == snap["sender"].lower()] + [i for i in self.settings if self.settings[i]["username"].lower() == snap["sender"].lower()]
                yield prefix + "\x0312\x1f%s\x1f\x0f · from %s · \u231a %s" % (url, snap["sender"] + (" (%s)" % username[0] if username else ""), pretty_date(time.time() - snap["sent"]/1000) if snap["sent"] else "Unknown")
            except:
                traceback.print_exc()
        json.dump(self.settings, open(self.settingsf, "w"))

    @Callback.background
    @command("update")
    def getnewsnaps(self, server, message):
        channel = server.lower(message.context)

        yield from self.newsnaps(channel)

    def checksnaps(self, server):
        for channel in self.settings:
            for i in self.newsnaps(channel):
                for chan in self.settings[channel].get("linked", []):
                    server.message(i, chan)
                server.message(i, channel)

    @command("block", "(.*)", admin=True)
    def block(self, server, message, username):
        channel = server.lower(message.context)
        if channel not in self.accounts:
            return prefix + "\x0304No associated snapchat for this channel."
        account = self.accounts[channel]
        if account.block(username):
            return prefix + "Blocked %s." % username
        else:
            return prefix + "\x0304Could not block %s." % username


    def send(self, acc, img, user, time=10):
        media_id = make_media_id(acc.username)
        r = acc._request('upload', {
            'username': acc.username,
            'media_id': media_id,
            'type': 0
            }, files={'data': encrypt(img.read())})
        if len(r.content) != 0:
            raise Exception("Failed to upload snap.")
        acc.send(media_id, user, time=time)
        
    @command("reply", r"(?:(-[maciulrdsbfpw1-9]+)\s+)?(https?://\S+|:.+?:)?\s*(.+)?")
    def snapreply(self, server, message, flags, background, text):
        user = self.settings[server.lower(message.context)]["history"][-1]["sender"]
        yield from self.snap.funct(self, server, message, flags, user, background, text)

    #@command("rotate", r"(\.jpg?)")

    @command("snap", r"(?:(-[maciulrdsbfpw1-9]+)\s+)?(\S+(?:,\s*\S+)*)(?:\s+(https?://\S+|:.+?:))?(?:\s+(.+))?")
    def snap(self, server, message, flags, user, background, text):
        acc = self.accounts[server.lower(message.context)]
        if server.lower(message.address.nick) not in self.users:
            yield prefix + "\x0304You must verify your snapchat username with .setsnap <username> to use this command."
            return
        else:
            username = self.users[server.lower(message.address.nick)]

        user = user.replace(" ", "")

        font = fonts["dejavu sans"]
        wrap = True
        outline = True
        bg = None
        copy = True
        time = 10
        force = False
        doge = False
        watermark = True
        if flags:
            for i in flags[1:]:
                if i in "123456789":
                    time = int(i)
                elif i in "macius":
                    font = fonts[{"m": "dejavu sans mono", "a": "arial", "c": "comic sans", "i": "impact", "u": "ubuntu", "s": "symbola"}[i]]
                elif i == "l":
                    background = server.lasturl
                elif i == "r":
                    wrap = False
                elif i == "d":
                    font = fonts["comic sans"]
                    outline = False
                    bg = Image.open("data/images/doge.jpg")
                    wrap = False
                    doge = True
                elif i == "p":
                    copy = False
                elif i == "b":
                    outline = False     
                elif i == "f":
                    force = True
                elif i == "w":
                    watermark = False

        if not text and not background and not bg:
            background = server.lasturl

        if background:
            if background.startswith(":"):
                params = {
                    "safe": "off",
                    "v": "1.0",
                    "rsz": 1,
                    "q": background[1:-1]
                }
                background = requests.get(
                  "https://ajax.googleapis.com/ajax/services/search/images",
                  params=params
                ).json()["responseData"]["results"][0]["url"] 
            bg = Image.open(BytesIO(requests.get(background).content))
        elif not bg:
            bg = Image.new("RGBA", (720, 1184), (0, 0, 0))
        if bg.size[0] > 4096 or bg.size[1] > 4096:
            yield prefix + "\x0304Image too large."
            return

        if doge:
            if not text: text = "wow, such snapchat"
            dogified = ""
            for i in text.split(",") + [random.choice("wow, such very many so".split()) + " " + username]:
                i = i.strip()
                if random.random() < 0.75:
                    dogified += " \n"
                if random.random() < 0.4:
                    dogified += (">\x03%.2d" % random.randrange(2, 14)) + i + (random.randrange(len(i)//2) * " ")
                elif random.random() < 0.8:
                    dogified += ("<\x03%.2d" % random.randrange(2, 14)) + (random.randrange(len(i)//2) * " ") + i
                else:
                    dogified += random.choice(">|<") + ("\x03%.2d" % random.randrange(2, 14)) + (random.randrange(len(i)) * " ") + i + (random.randrange(len(i)) * " ")
                dogified += "\n"
            text = dogified[:-1]
        elif text:
            text = text.replace("\\", "\n")
            if watermark:
                text += "\n\n>\x0f -%s" % username
        elif watermark:
            text = "\n>via\xa0%s" % username

        users = [self.users[server.lower(i)] if server.lower(i) in self.users else i for i in user.split(",")]

        omitted = ""

        if not force:
            allusers = len(users)
            history = self.settings[server.lower(message.context)]["history"]
            history = {i["sender"].lower() for i in history} | set(self.users.keys())
            users = [i for i in users if i.lower() in history]
            if len(users) != allusers:
                omitted = "Omitted %d unknown users. Use -f to force, or check your syntax is correct." % (allusers - len(users))

        if not users:
            users += [username]
        user = ",".join(users)


        if text:
            img = drawtext(bg, text, fonts=font, wrap=wrap, outline=outline)
        else:
            img = bg
        if not img:
            yield prefix + "\x0304Could not fit text on the image."
            return

        try:
            f = BytesIO()
            img.save(f, "jpeg")
            f.seek(0)
            if img.size[0] > img.size[1]:
                rotated = BytesIO()
                img.rotate(-90).save(rotated, "jpeg")
                rotated.seek(0)
                self.send(acc, rotated, user, time=time)
            else:
                self.send(acc, f, user, time=time)
        except:
            yield prefix + "\x0304Failed to upload snap."
            return

        if copy:
            f.seek(0)
            i = "\x0312\x1f%s%s.jpg\x0f" % (public_url, save(f.read(), "jpg"))
        else:
            i = "snap"
        if "," in user:
            user = "%s and %s" % (", ".join(user.split(",")[:-1]), user.split(",")[-1])

        yield prefix + "Sent %s to %s. %s" % (i, user, omitted)
        
    @command("setsnap", r"([^, ]+)")
    def setsnap(self, server, message, username):
        snapuser = self.settings[server.lower(message.context)]["username"]
        acc = self.accounts[server.lower(message.context)]
        key = server.lower(message.address.nick)
        if key in self.unverified:
            return prefix + "This username is already being verified. Please send a snapchat to %s to reset." % snapuser
        if username.lower() in [i.lower() for i in self.users.values()] + [self.settings[i]["username"].lower() for i in self.settings]:
            return prefix + "This username is already verified. Type .unverify to reset your verification."
        password = random.choice(open("/usr/share/dict/words").read().split()).lower()
        self.unverified[key] = [username, password]
        img = drawtext(Image.new("RGBA", (720, 1184), (0, 0, 0)),
                       "Type\n \n|\x0308.verify %s\x0f\n \nto complete \nusername verification." % password, wrap=False)
        f = BytesIO()
        img.save(f, "jpeg")
        f.seek(0)
        self.send(acc, f, username)
        return prefix + "A verification code has been sent to your snapchat. Type \x02.verify <code>\x02 to complete username verification."



    @command("unverify")
    def unverify(self, server, message):
        key = server.lower(message.address.nick)
        del self.users[key]
        return prefix + "Unverified."

    @command("verify", "(.+)")
    def verify(self, server, message, code):
        key = server.lower(message.address.nick)
        if code.lower() == self.unverified[key][1].lower():
            self.users[key] = self.unverified[key][0]
            del self.unverified[key]
            json.dump(self.users, open(self.usersf, "w"))
            return prefix + "Verification successful."
        else:
            return prefix + "\x0304Wrong verification code."

    @command("snaplink", "(.+)", admin=True)
    def link(self, server, msg, chan):
        self.settings[server.lower(chan)].setdefault("linked", []).append(msg.context)
        json.dump(self.settings, open(self.settingsf, "w"))

    @command("snapunlink", "(.+)", admin=True)
    def unlink(self, server, msg, chan):
        self.settings[server.lower(chan)].setdefault("linked", []).remove(msg.context)
        json.dump(self.settings, open(self.settingsf, "w"))

    @command("snapexport")
    def export(self, server, message):
        acc = self.accounts[server.lower(message.context)]
        if server.lower(message.address.nick) not in self.users:
            return prefix + "\x0304You must verify your snapchat username with .setsnap <username> to use this command."
        else:
            username = self.users[server.lower(message.address.nick)]
        filename = uuid.uuid4().hex
        with zipfile.ZipFile(snapfolder + "/" + filename + ".zip", "w") as archive:
            for channel in self.settings:
                chansnap = self.settings[channel]["username"]
                snaps = [i for i in self.settings[channel]["history"] if i["sender"].lower() == username.lower()]
                snaps = [[i, self.settings[channel]["snaps"].get(i["id"], None)] for i in snaps]
                for snap, url in snaps:
                    print("Downloading %s" % url)
                    try:
                        archive.writestr("%s/%s-%s" % (chansnap, snap["id"], url.rsplit("/")[-1]), requests.get(url).content)
                    except:
                        print("Couldn't download")
                archive.writestr(chansnap + "/meta.js", json.dumps(snaps))
        return prefix + "Archive saved to \x0312\x1f%s.zip\x1f\x0f" % (public_url + filename)

    @command("snaps", r"^(?:(last|first)\s+(?:(?:(\d+)(?:-|\s+to\s+))?(\d*))\s*)?((?:gifs|videos|snaps|pics|clips)(?:(?:\s+or\s+|\s+and\s+|\s*/\s*|\s*\+\s*)(?:gifs|videos|snaps|pics|clips))*)?(?:\s*(?:from|by)\s+(\S+(?:(?:\s+or\s+|\s+and\s+|\s*/\s*|\s*\+\s*)\S+)*))?(?:\s*to\s+(\S+))?$", templates={Callback.USAGE: prefix + "\x0304Usage: .snaps [first/last index] [type] [by user] [to channel]"})
    def search(self, server, message, anchor, frm, to, typefilter, users, context):
        if not context:
            context = message.context
        elif "#" not in context:
            target = [i for i in self.settings if self.settings[i]["username"].lower() == context.lower()]
            if not target:
                yield prefix + "\x0304No associated channel for that snapchat account."
                return
            context = target[0]
        context = server.lower(context)
        if context not in self.settings:
            yield prefix + "\x0304No associated snapchat for this channel."
            return

        new = []
        if not any((anchor, frm, to, typefilter, users)):
            new = list(self.newsnaps(context))
            for i in new:
                yield i + " [NEW]"
                if context != server.lower(message.context):
                    server.message(i, message.context)
            new = [i.rsplit("·", 1)[0] for i in new]

        if not anchor:
            frm, to, anchor = -1, -2 if message.prefix == "." else -5, -1
        elif anchor.lower() == "last":
            frm, to, anchor = -int(frm or 1), -int(to)-1 if to else None, -1
        elif anchor.lower() == "first":
            frm, to, anchor = int(frm or 1)-1, int(to) if to else None, 1
        types = {"gifs": {2},
                 "videos": {1},
                 "snaps": {0, 1, 2},
                 "pics": {0},
                 "clips": {1, 2}}
        filtr = set()
        if not typefilter: typefilter = "snaps"
        for i in re.split(r"\s+or\s+|\s+and\s+|\s*/\s*|\s*\+\s*", typefilter):
            filtr |= types[i.lower()]
        if users:
            users = {i.lower() for i in re.split(r"\s+or\s+|\s+and\s+|\s*/\s*|\s*\+\s*", users)}
        history = self.settings[context]["history"]
        history = [i for i in history if (i["media_type"] in filtr) and ((not users) or (i["sender"].lower() in users))]
        results = history[frm:to:anchor][:1 if message.prefix == "." else 5]
        for i in results:
            server.lasturl = self.settings[context]["snaps"][i["id"]]
            res = prefix + "\x0312\x1f%s\x1f\x0f · from %s · \u231a %s" % (self.settings[context]["snaps"][i["id"]], i["sender"], pretty_date(time.time() - i["sent"]/1000) if i["sent"] else "Unknown")
            if res.rsplit("·", 1)[0] not in new:
                yield res

    def __destroy__(self, server):
        self.checker.cancel()

__initialise__ = Snap