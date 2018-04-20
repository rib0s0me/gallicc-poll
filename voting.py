#!/usr/bin/env python3
import hashlib
from datetime import datetime
from operator import attrgetter


class Vote(object):
    def __init__(self, poll, result):
        self._poll = poll
        self._result = result if (type(result) == bool) else False
        self._timestamp = datetime.now()

    def __repr__(self):
        return "<Vote: {}, {}, {}>".format(self._poll, self._result, self._timestamp)

    @property
    def poll(self):
        return self._poll

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        if (type(value) == bool) and (self._result != value):
            self._result = value
            self._timestamp = datetime.now()


class Selection(Vote):
    def __init__(self, poll, result):
        super(Selection, self).__init__(poll, result)

    def __repr__(self):
        return "<Selection: {}, {}, {}>".format(self._poll, self._result, self._timestamp)


class Player(object):
    _count = 0

    def __init__(self, name, nick="", num=0, active=True, water_active=True, umpiring_active=True):
        Player._count += 1
        self.name = name
        self.nick =  nick or name
        self.num = num or Player._count
        self.active = active
        self.water_active = water_active
        self.umpiring_active = umpiring_active
        self.water_votes = []
        self.water_selections = []
        self.umpiring_votes = []
        self.umpiring_selections = []
        self.game_votes = []
        self.game_selections = []
        m = hashlib.md5()
        m.update((self.name + str(self.num)).encode())
        self.id = m.hexdigest()

    def __repr__(self):
        return "<Player: {}, {}>".format(self.name, self.nick)

    def _find_vote(self, votes, poll):
        for vote in votes:
            if vote.poll == poll:
                return vote
        return None

    def _find_selection(self, selections, poll):
        for selection in selections:
            if selection.poll == poll:
                return selection
        return None

    def add_vote(self, poll, result=True):
        ret = False
        if type(poll) == Poll:
            if not self.active or (poll.type == "water" and not self.water_active) or (poll.type == "umpiring" and not self.umpiring_active):
                return ret
            votes = getattr(self, "{}_votes".format(poll.type), None)
            if votes is None:
                return ret
            ret = True
            vote = self._find_vote(votes, poll)
            if vote:
                vote.result = result
            else:
                votes.append(Vote(poll, result))
        return ret

    def add_selection(self, poll, result=True):
        ret = False
        if type(poll) == Poll:
            if not self.active or (poll.type == "water" and not self.water_active) or (poll.type == "umpiring" and not self.umpiring_active):
                return ret
            votes = getattr(self, "{}_votes".format(poll.type), None)
            if votes is None:
                return ret
            vote = self._find_vote(votes, poll)
            if vote and vote.result:
                selections = getattr(self, "{}_selections".format(poll.type), None)
                if selections is None:
                    return ret
                ret = True
                selection = self._find_selection(selections, poll)
                if selection:
                    selection.result = result
                else:
                    selections.append(Selection(poll, result))
        return ret

    @property
    def num_game_selections(self):
        return len([selection for selection in self.game_selections if selection.result])

    @property
    def num_water_selections(self):
        return len([selection for selection in self.water_selections if selection.result])

    @property
    def num_umpiring_selections(self):
        return len([selection for selection in self.umpiring_selections if selection.result])


class Roster(object):
    def __init__(self, players=None):
        self.players = players or [Player("Ishan Mandrekar", "Ishan"),
                                   Player("Pavan Sibal", "Pavan"),
                                   Player("Avinash Sridhar", "Avi"),
                                   Player("Gajendra Mehta", "Gaju")]

    def get_game_active_players(self):
        return [player for player in self. players if player.active]

    def get_water_active_players(self):
        return [player for player in self. players if player.active and player.water_active]

    def get_umpiring_active_players(self):
        return [player for player in self. players if player.active and player.umpiring_active]


class Poll(object):
    _count = 0
    _types = {"game", "water", "umpiring"}
    _roster = Roster()

    def __init__(self, type, desc="",open=True, roster=None):
        Poll._count += 1
        self.id = Poll._count
        self.type = type if type in Poll._types else "game"
        self.desc = desc if desc else "galli cc {} poll id: {}".format(self.type, self.id)
        self.open_timestamp = datetime.now() if open else None
        self.close_timestamp = None
        self.finalize_timestamp = None
        self._roster = roster or Poll._roster
        self.players = {}
        if self.type == "game":
            for player in self._roster.get_game_active_players():
                self.players[player.id] = player
        elif self.type == "water":
            for player in self._roster.get_water_active_players():
                self.players[player.id] = player
        else:
            for player in self._roster.get_umpiring_active_players():
                self.players[player.id] = player

    def __repr__(self):
        return "<Poll: {}, {}, {}>".format(self.id, self.type, self.desc)

    def _is_voting_open(self):
        if self.open_timestamp and not self.close_timestamp and not self.finalize_timestamp:
            return True
        return False

    def _is_selection_open(self):
        if self.open_timestamp and self.close_timestamp and not self.finalize_timestamp:
            return True
        return False

    def open(self):
        """
        opening a poll signals the start of voting
        """
        if not self.open_timestamp:
            self.open_timestamp = datetime.now()

    def close(self):
        """
        closing a poll signals the end of voting
        """
        if self.open_timestamp and not self.close_timestamp:
            self.close_timestamp = datetime.now()

    def finalize(self):
        """
        finalizing a poll signals the end of selection
        """
        if self.open_timestamp and not self.finalize_timestamp:
            self.finalize_timestamp = datetime.now()

    def log_vote(self, player_id, result=True):
        """
        attempt to log a single vote
        :param: player_id: str
        :param: result: bool
        return: whether voting was successful
        rtype: bool
        """
        if not self._is_voting_open():
            return False
        ret = False
        if player_id in self.players.keys():
            player = self.players[player_id]
            ret = player.add_vote(self, result)
        return ret

    def log_selection(self, player_id, result=True):
        """
        attempt to log a single selection
        :param: player_id: str
        :param: result: bool
        return: whether selection was successful
        rtype: bool
        """
        if not self._is_selection_open():
            return False
        ret = False
        if player_id in self.players.keys():
            player = self.players[player_id]
            ret = player.add_selection(self, result)
        return ret

    def auto_vote(self):
        """
        log votes for all active players on the roster
        return: players who voted
        rtype: list of Player objects
        """
        voted = []
        if not self._is_voting_open():
            return voted
        for player_id, player in self.players.items():
            ret = self.log_vote(player_id)
            if ret:
                voted.append(player)
        return voted

    def auto_select(self):
        """
        log one or more selections using a pre-defined algorithm
        return: selected players
        rtype: list of Player objects
        """
        selected = []
        if not self._is_selection_open():
            return selected
        if self.type == "game":
            players = self.get_voted_players()
            # sort by previously recorded num_game_selections in ascending order
            players.sort(key=attrgetter("num_game_selections"))
            # select upto 11 players
            for player in players[:11]:
                ret = self.log_selection(player.id)
                if ret:
                    selected.append(player)
        elif self.type == "water":
            players = self.get_voted_players()
            # sort by previously recorded num_water_selections in ascending order
            players.sort(key=attrgetter("num_water_selections"))
            # get the first player
            player = players[0] if len(players) else None
            if player:
                ret = self.log_selection(player.id)
                if ret:
                    selected.append(player)
        elif self.type == "umpiring":
            players = self.get_voted_players()
            # sort by previously recorded num_umpiring_selections in ascending order
            players.sort(key=attrgetter("num_umpiring_selections"))
            if len(players) >= 2:
                # get the first 2 players
                player1, player2 = players[0], players[1]
                ret = self.log_selection(player1.id)
                if ret:
                    selected.append(player1)
                ret = self.log_selection(player2.id)
                if ret:
                    selected.append(player2)
        return selected

    def get_voted_players(self):
        """
        return: voted players
        rtype: list of Player objects
        """
        voted_players = []
        for player in self.players.values():
            votes = getattr(player, "{}_votes".format(self.type), [])
            for vote in votes:
                if (vote.poll == self):
                    if vote.result:
                        voted_players.append(player)
                    break
        return voted_players

    def get_selected_players(self):
        """
        return: selected players
        rtype: list of Player objects
        """
        selected_players = []
        for player in self.players.values():
            selections = getattr(player, "{}_selections".format(self.type), [])
            for selection in selections:
                if (selection.poll == self):
                    if selection.result:
                        selected_players.append(player)
                    break
        return selected_players


if __name__ == "__main__":
    players = [Player("p1"), Player("p2"), Player("p3"), Player("p4"),
               Player("p5"), Player("p6"), Player("p7"), Player("p8"),
               Player("p9"), Player("p10"),Player("p11"),Player("p12"),
               Player("p13"),Player("p14"),Player("p15"),Player("p16")]
    roster = Roster(players=players)

    # water
    poll = Poll(type="water", desc="Test Water Poll 1", open=True)
    voted = poll.auto_vote()
    poll.close()
    selected = poll.auto_select()
    print("water selection: {}".format(selected))
    poll.finalize()

    # umpiring
    poll = Poll(type="umpiring", desc="Test Umpiring Poll 1", open=True)
    poll.auto_vote()
    poll.close()
    selected = poll.auto_select()
    print("umpiring selection: {}".format(selected))
    poll.finalize()
    # umpiring
    poll = Poll(type="umpiring", desc="Test Umpiring Poll 2", open=True)
    poll.auto_vote()
    poll.close()
    selected = poll.auto_select()
    print("umpiring selection: {}".format(selected))
    poll.finalize()

    # game
    poll = Poll(type="game", desc="Test Game Poll 1", open=True, roster=roster)
    # first 14 vote yes
    players = players[:14]
    for player in players:
        poll.log_vote(player.id)
    poll.close()
    selected = poll.auto_select()
    print("game selection: {}".format(selected))
    poll.finalize()
    # game
    poll = Poll(type="game", desc="Test Game Poll 2", open=True, roster=roster)
    # last 14 vote yes
    players = players[-14:]
    for player in players:
        poll.log_vote(player.id)
    poll.close()
    selected = poll.auto_select()
    print("auto game selection: {}".format(selected))
    # tweak the auto selection
    unselected = list(set(players) - set(selected))
    poll.log_selection(selected[0].id, False)
    poll.log_selection(unselected[0].id, True)
    print("tweaked game selection: {}".format(poll.get_selected_players()))
    poll.finalize()
