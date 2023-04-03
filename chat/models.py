import json
from django.db import models
from .card import Card
from pathlib import Path
import random
from .gameRoomManager import GameRoomManager, generate_room_id
from ChatApp.constants import PLAYER_COUNT


# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    objects = models.Manager()


class GameRoom(models.Model):
    ROOM_STATUS = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('COMPLETE', 'Complete'),
        ('ACCEPTING', 'Accepting')
    )
    GAME_ACTION = (
        ('BID_TYPE', 'bid_type'),
        ('BID_AMOUNT', 'bid_amount'),
        ('TICK', 'tick'),
    )

    room_id = models.CharField(
        max_length=6, unique=True, default=generate_room_id)
    players = models.ManyToManyField(User, through='Player')
    moves = models.TextField(null=True, blank=True)
    turn = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=ROOM_STATUS, default='INACTIVE')
    winnerList = models.TextField(null=True, blank=True)
    looserList = models.TextField(null=True, blank=True)
    game_header_initialized = models.BooleanField(default=False)
    game_header = models.JSONField(default=dict)
    game_action = models.CharField(
        max_length=10, choices=GAME_ACTION, default='BID_TYPE')
    round_player_index = models.PositiveIntegerField(default=0)
    round_tick_index = models.PositiveIntegerField(default=0)

    # Manager
    objects = models.Manager()
    game_manager = GameRoomManager()

    def get_group_name(self):
        return f"chat_{self.room_id}"

    @staticmethod
    def read_template_file(file_name):
        templates_dir = Path(__file__).resolve().parent / "templates"
        file_path = templates_dir / file_name
        print(file_path)
        with file_path.open() as f:
            return json.load(f)

    def deal_round_hands(self):
        try:
            current_round_index = self.game_header["current_round_index"]
            deck = [Card(i) for i in range(52)]
            random.shuffle(deck)
            for i, player in enumerate(self.game_header['game_order']):
                hand = [c.to_dict() for c in deck[(i*13):((i+1) * 13)]]
                hand.sort(key=(lambda k: k['id']))
                self.game_header["rounds"][current_round_index]["hands"][player] = hand
            self.save()
        except Exception as e:
            print(e, "deal_round_hands")

    def initialize_round(self):
        try:
            initial_round = self.read_template_file("round_template.json")
            current_round_index = self.game_header["current_round_index"]
            initial_round["round_order"] = self.game_header["game_order"]
            for player in self.game_header["game_order"]:
                initial_round['round_winnings'][player] = 0
            initial_round['round_number'] = current_round_index
            self.game_header["rounds"].append(initial_round)
            self.save()
        except Exception as e:
            print(e, "initialize_round")

    def initialize_tick(self):
        initial_tick = self.read_template_file("tick_template.json")
        current_round_index = self.game_header["current_round_index"]
        current_tick_index = self.game_header["rounds"][current_round_index]["current_tick_index"]
        initial_tick["tick_number"] = current_tick_index
        self.game_header["rounds"][current_round_index]["ticks"].append(
            initial_tick)
        self.save()

    def initialize_play_tick(self):
        initial_play_tick = self.read_template_file("play_tick_template.json")
        current_round_index = self.game_header["current_round_index"]
        current_tick_index = self.game_header["rounds"][current_round_index]["current_tick_index"]
        initial_play_tick["tick_number"] = current_tick_index
        initial_play_tick['player'] = self.get_round_player_id()
        self.game_header["rounds"][current_round_index]["ticks"].append(
            initial_play_tick)
        self.save()

    def get_room_players(self, room_id):
        players = Player.objects.filter(game_room_id=room_id)
        return players

    def can_player_see_hand(self, user_id):
        current_round_index = self.game_header["current_round_index"]
        current_round = self.game_header["rounds"][current_round_index]
        round_order = current_round["round_order"]
        user_index = round_order.index(user_id)
        team = self.game_header["game_player_dict"][user_id]
        index1 = 0
        if team[0] == "B":
            index1 = 1
        index2 = 0
        if team[1] == "2":
            index2 = 1

        game_action = self.game_action
        if game_action == "BID_TYPE" or game_action == 'BID_AMOUNT':
            return not current_round['round_contract'][index1]['blinds'][index2]
        return True

    def send_player_hand(self, user_id):
        if self.can_player_see_hand(user_id):
            selectable = self.get_selectable_cards(user_id)
            return selectable
        else:
            return None

    def initialize_game_header(self):
        try:
            players = self.get_room_players(self.id)
            user_ids = [player.user_id for player in players]
            teams = ["A1", "A2", "B1", "B2"]
            game_player_dict = {}
            for index, user_id in enumerate(user_ids):
                game_player_dict[user_id] = teams[index]

            initial_game_state = {
                "player_count": 0,
                "cards_distributed": False,
                "winning_value": 500,
                "game_score": [0, 0],
                "game_player_dict": game_player_dict,
                "game_order": user_ids,
                "game_bags": [0, 0],
                "game_discarded_bags": [0, 0],
                "current_round_index": 0,
                "game_players": user_ids,
                "game_history": [],
                "rounds": []
            }
            self.game_header = initial_game_state
            self.game_header_initialized = True
            self.status = "ACTIVE"
            self.save()
        except Exception as e:
            print(e, "error in initialize_game_header")

    def get_player_index(self, user_id):
        return self.game_header["game_order"].index(user_id)

    def get_current_player_id(self):
        return self.game_header["game_order"][self.round_player_index]

    def get_round_player_id(self):
        round_player_index = self.round_player_index
        round_index = self.game_header["current_round_index"]
        return self.game_header["rounds"][round_index]["round_order"][round_player_index]

    def set_player_bid_type(self, bid_type):
        try:
            game_player_dict = self.game_header['game_player_dict']
            player_id = self.get_round_player_id()
            round_index = self.game_header["current_round_index"]
            team = game_player_dict[player_id]
            team_index = team[0]-'A'
            number = int(team[1])-1
            self.game_header['game_history'].append(
                f"{player_id} set bid type as {bid_type}")
            if bid_type == True:
                self.game_header['rounds'][round_index]['contract'][team_index]['bidString'][number] += 'b'
            self.game_header['rounds'][round_index]['contract'][team_index]['blind'][number] = bid_type
            self.game_action = "BID_AMOUNT"
            self.save()
            return True
        except Exception as e:
            print(e, "Failed to set player bid type in GameRoom Model")
            return False

    def set_player_bid_amount(self, amount):
        try:
            game_player_dict = self.game_header['game_player_dict']
            player_id = self.get_round_player_id()
            round_index = self.game_header["current_round_index"]
            team = game_player_dict[player_id]
            team_index = team[0]-'A'
            number = int(team[1])-1
            self.game_header['rounds'][round_index]['contract'][team_index]['bids'][number] = amount
            self.game_action = "BID_TYPE"
            self.round_player_index += 1
            self.game_header['game_history'].append(
                f"{player_id} set bid amount as {amount}")
            if self.round_player_index == PLAYER_COUNT:
                self.round_player_index = 0
                self.game_action = "TICK"
                self.initialize_tick()
                self.initialize_play_tick()
            self.save()
            return True
        except Exception as e:
            print(e, "Failed to set player bid type in GameRoom Model")
            return False

    def get_card_index(self, card_id):
        round_index = self.game_header["current_round_index"]
        player_id = self.get_round_player_id()
        for index, card in enumerate(self.game_header['rounds'][round_index]['hands'][player_id]):
            if card['id'] == card_id:
                return index
        return -1

    def get_playable_cards(self, player_id):
        round_index = self.game_header["current_round_index"]
        tick_index = self.game_header["rounds"][round_index]["current_tick_index"]
        cards = self.game_header['rounds'][round_index]['hands'][player_id]
        cards = [card for card in cards if card['card_played'] == False]
        lead_suite = self.game_header['rounds'][round_index]['ticks'][tick_index]['tick_lead_suit']
        spade_in_play = self.game_header['rounds'][round_index]['round_spade_in_play']
        selectable = []
        for i, card in enumerate(cards):
            if (lead_suite == -1 and spade_in_play):
                # Everything is good for first card when a spade has been played
                selectable.append(card.id)
            elif (lead_suite == -1 and card.suiteID != 3):
                # Everything is good for first card but spades before a spade has been played
                selectable.append(card.id)
            elif (lead_suite == card.suiteID):
                # Otherwise, try to match the lead suite
                selectable.append(card.id)

        if (len(selectable) == 0):
            # If nothing was playable, all cards are fair game!
            selectable = [card.id for card in cards]
        else:
            for i, card in enumerate(cards):
                if (card.suiteID == 3 and spade_in_play):
                    selectable.append(i)

        return selectable

    def score_tick(self, round_index, tick_index):
        try:
            ticks = self.game_header['rounds'][round_index]['ticks'][tick_index]['tick']
            if len(ticks) != PLAYER_COUNT:
                raise Exception("Tick not complete")

            lead_suite = self.game_header['rounds'][round_index]['ticks'][tick_index]['tick_lead_suit']
            best_card = ticks[0]['card']
            winner = ticks[0]['player']

            for i, tick in enumerate(ticks):
                if tick['card']['suiteID'] == lead_suite:
                    if ((tick['card']['orderID'] > best_card['orderID']) or (best_card['suiteID'] != lead_suite)):
                        best_card = tick['card']
                        winner = tick['player']
            ret_obj = {}
            ret_obj['best_card'] = best_card
            self.game_header['rounds'][round_index]['round_winnings'][winner] += 1
            # rotate the round_order till winner is first
            while self.game_header['rounds'][round_index]['round_order'][0] != winner:
                self.game_header['rounds'][round_index]['round_order'].append(
                    self.game_header['rounds'][round_index]['round_order'].pop(0))
            self.save()
            return ret_obj

        except Exception as e:
            print(e, "Failed to score tick")
            return False

    def get_player_from_team(self, team_name):
        game_player_dict = self.game_header['game_player_dict']
        for player_id, team in game_player_dict.items():
            if team == team_name:
                return player_id
        return None

    def score_contract(self, round_index, team_index):
        try:
            player_1 = self.get_player_from_team('A1')
            player_2 = self.get_player_from_team('A2')
            contract = self.game_header['rounds'][round_index]['contract'][team_index]
            if team_index == 1:
                player_1 = self.get_player_from_team('B1')
                player_2 = self.get_player_from_team('B2')
            win1 = self.game_header['rounds'][round_index]['round_winnings'][player_1]
            win2 = self.game_header['rounds'][round_index]['round_winnings'][player_2]

            score = 0
            bags = 0
            wins = [win1, win2]

            overflow = (win1 + win2) - contract.sum
            for i, bid in enumerate(contract.bids):
                # Nil case
                if (bid == 0):
                    if (overflow > 0 or (wins[i] != 0)):
                        # Lost nil
                        score -= 100
                        if (contract.blinds[i]):
                            # Lost nil AND blind
                            score -= 100
                    else:
                        # Met nil
                        score += 100
                        if (contract.blinds[i]):
                            # Met nil AND blind
                            score += 100
                # General win case
                elif (overflow >= 0):
                    if (contract.blinds[i]):
                        # Blinds are PERSONAL!
                        if (wins[i] - bid < 0):
                            score -= 100
                        else:
                            score += 100
                    else:
                        # Award points for bid
                        score += bid * 10
                else:
                    # Doc as many points as is appropriate
                    if (contract.blinds[i]):
                        score -= 100
                    else:
                        score -= bid * 10

            # Handle Bags
            if (overflow > 0):
                for i, bid in enumerate(contract.bids):
                    diff = wins[i] - bid
                    if (diff > 0):
                        # One bag/point per extra hand
                        score += diff
                        # Blinds don't get bags
                        if (not contract.blinds[i]):
                            bags += diff
            return score, bags
        except Exception as e:
            return False, False

    def score_round(self, round_index):
        try:
            scoreA, bagsA = self.score_contract(round_index, 0)
            scoreB, bagsB = self.score_contract(round_index, 1)
            if (scoreA == False or scoreB == False):
                return False
            self.game_header['rounds'][round_index]['round_score'] = [
                scoreA, bagsA]
            self.game_header['rounds'][round_index]['round_bags'] = [
                scoreB, bagsB]
            self.game_header['game_score'][0] += scoreA
            self.game_header['game_score'][1] += scoreB
            self.game_header['game_bags'][0] += bagsA
            self.game_header['game_bags'][1] += bagsB
            for i in range(2):
                while (self.game_header['game_bags'][i] >= 7):
                    self.game_header['game_bags'][i] -= 7
                    self.game_header['game_discarded_bags'][i] += 1
                    self.game_header['game_score'][i] -= 100

            self.game_header["game_order"].append(
                self.game_header["game_order"].pop(0))
            # check game winner
            res = ""
            if self.game_header['game_score'][0] >= self.game_header['winning_value'] or self.game_header['game_score'][1] >= self.game_header['winning_value']:
                if self.game_header['game_score'][0] > self.game_header['game_score'][1]:
                    res = "A"
                elif self.game_header['game_score'][0] < self.game_header['game_score'][1]:
                    res = "B"
                else:
                    if self.game_header['game_bags'][0]+self.game_header['game_discarded_bags'][0] < self.game_header['game_bags'][1]+self.game_header['game_discarded_bags'][1]:
                        res = "A"
                    elif self.game_header['game_bags'][0]+self.game_header['game_discarded_bags'][0] > self.game_header['game_bags'][1]+self.game_header['game_discarded_bags'][1]:
                        res = "B"
            if res != "":
                if res == "A":
                    player_1 = self.get_player_from_team('A1')
                    player_2 = self.get_player_from_team('A2')
                    player_3 = self.get_player_from_team('B1')
                    player_4 = self.get_player_from_team('B2')
                elif res == "B":
                    player_1 = self.get_player_from_team('B1')
                    player_2 = self.get_player_from_team('B2')
                    player_3 = self.get_player_from_team('A1')
                    player_4 = self.get_player_from_team('A2')
                self.game_header['game_history'].append(
                    f"{player_1} {player_2} win the game\n {player_3} {player_4} loose the game")
                u1 = User.objects.get(id=player_1)
                u2 = User.objects.get(id=player_2)
                u3 = User.objects.get(id=player_3)
                u4 = User.objects.get(id=player_4)
                GameStats.objects.create(user=u1, game_room=self, win=True,room_id=self.room_id)
                GameStats.objects.create(user=u2, game_room=self, win=True,room_id=self.room_id)
                GameStats.objects.create(user=u3, game_room=self, win=False,room_id=self.room_id)
                GameStats.objects.create(user=u4, game_room=self, win=False,room_id=self.room_id)
            self.save()
            return res
        except Exception as e:
            print(e, "Score round models.py")

    def play_player_card(self, message):
        try:
            card_id = int(message)
            card_index = self.get_card_index(card_id)
            player_id = self.get_round_player_id()
            selectable = self.get_playable_cards(player_id)
            if card_index not in selectable:
                raise Exception("Card not playable")
            card = self.game_header['rounds'][self.game_header["current_round_index"]
                                              ]['hands'][player_id][card_index]
            self.game_header['rounds'][self.game_header["current_round_index"]
                                       ]['hands'][player_id][card_index].card_played = True
            round_index = self.game_header["current_round_index"]
            tick_index = self.game_header["rounds"][round_index]["current_tick_index"]
            self.game_header['rounds'][round_index]['ticks'][tick_index]['tick']['card'] = card
            # Update lead suite
            lead_suite = self.game_header['rounds'][round_index]['ticks'][tick_index]['tick_lead_suit']
            if (lead_suite == -1):
                self.game_header['rounds'][round_index]['ticks'][tick_index]['tick_lead_suit'] = card.suiteID
            if (card.suiteID == 3):
                self.game_header['rounds'][round_index]['ticks'][tick_index]['tick_lead_suit'] = 3
                self.game_header['rounds'][round_index]['round_spade_in_play'] = True
            self.round_player_index += 1
            flag_tick_end = False
            flag_round_end = False

            if self.round_player_index == PLAYER_COUNT:
                self.round_player_index = 0
                self.round_tick_index += 1
                self.game_header["rounds"][round_index]["round_tick_index"] += 1
                flag_tick_end = True
            if self.round_tick_index == 13:
                self.round_tick_index = 0
                self.game_header["current_round_index"] += 1
                flag_round_end = True
                self.game_action = "BID_TYPE"
            self.game_header['game_history'].append(
                f"{player_id} played {card}")
            self.save()
            res = ""
            if flag_tick_end:
                self.score_tick(round_index, tick_index)
            if flag_round_end:
                res = self.score_round(round_index)

            if flag_round_end:
                self.initialize_round()

            if flag_tick_end:
                self.initialize_tick()

            self.initialize_play_tick()
            return res
        except Exception as e:
            print(e, "Failed to pay player card in GameRoom Model")
            return ""


class Player(models.Model):
    # Player fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player_cards = models.JSONField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)


class GameStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    winOrLose = models.BooleanField(default=False)
    room_id = models.CharField(
        max_length=6, unique=True,default="")
