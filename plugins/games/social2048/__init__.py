import json

from math import log

from . import board as boards

from bot.events import Callback, command

class IRC2048(Callback):
    colors = [14, 15, 7, 4, 5, 8, 9, 3, 11, 10, 12]
    
    def __init__(self, server):
        self.savefile = server.get_config_dir("2048.json")
        try:
            self.games = json.load(open(self.savefile))
            for chan, game in self.games.items():
                self.games[chan] = getattr(boards, game["type"]).unserialise(game)
        except FileNotFoundError:
            self.games = {}
        super().__init__(server)

    def print_board(self, board):
        for y, row in enumerate(board.board):
            yield "│%s%s" % ("\x1f" if y != board.size[1]-1 else "", "".join(("\x03,%.2d%s\x03│" % (self.colors[int(log(cell, 2)) - 1], str(cell).center(5))) if cell is not None else "    " for cell in row))

    @command("2048 1024 512 256 128 64 32 16 8")
    def start(self, server, msg):
        if server.lower(msg.context) not in self.games:
            self.games[server.lower(msg.context)] = boards.Board(goal=int(msg.command))
        board = self.games[server.lower(msg.context)]
        self.savestate()
        yield from self.print_board(board)

    @command("up down left right u d l r")
    def move(self, server, msg):
        if server.lower(msg.context) not in self.games:
            self.games[server.lower(msg.context)] = boards.Board()
        board = self.games[server.lower(msg.context)]
        board.move({"up":"^", "down":"v", "left":"<", "right":">", "u":"^", "d":"v", "l":"<", "r":">"}[msg.command])
        if board.is_endgame():
            if board.won():
                yield """1413╷ 13╷╭4─╮4╷ 8╷   12╷ 12╷╭13─╮13┌─9╮
144╰┬4╯│8 │8│ 12│   13││13││9 │9│ 11│
148 ╵8 ╰12─╯12╰─13┘   9╰┴9┘╰11─╯11╵ 12╵"""
            else:
                yield """╻  ┏━┓┏━┓┏━━┏┓
┃  ┃ ┃┗━┓┣━ ┣┻┓
┗━━┗━┛┗━┛┗━━╹ ╹"""
            del self.games[server.lower(msg.context)]
        self.savestate()
        yield from self.print_board(board)

    def savestate(self):
        with open(self.savefile, "w") as f:
            json.dump({k: v.serialise() for k, v in self.games.items()}, f)

__initialise__ = IRC2048