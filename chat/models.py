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
        current_round_index = self.game_header["current_round_index"]
        deck = [Card(i) for i in range(52)]
        random.shuffle(deck)
        for i, player in enumerate(self.game_header['game_order']):
            hand = [c.to_dict() for c in deck[(i*13):((i+1) * 13)]]
            hand.sort(key=(lambda k: k['id']))
            self.game_header["rounds"][current_round_index]["hands"][player] = hand
        self.save()

    def initialize_round(self):
        initial_round = self.read_template_file("round_template.json")
        current_round_index = self.game_header["current_round_index"]
        initial_round["round_order"] = self.game_header["game_order"]
        initial_round['round_number'] = current_round_index
        self.game_header["rounds"].append(initial_round)
        self.save()

    def initialize_game_header(self):
        players = self.players.all()
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
            "discarded_bags": [0, 0],
            "current_round_index": 0,
            "game_players": user_ids,
            "rounds": []
        }
        self.game_header = initial_game_state
        self.game_header_initialized = True
        self.status = "ACTIVE"
        self.save()

    def get_player_index(self, user_id):
        return self.game_header["game_order"].index(user_id)

    def get_current_player_id(self):
        return self.game_header["game_order"][self.round_player_index]

    def rotate_game_order(self):
        self.game_header["game_order"].append(
            self.game_header["game_order"].pop(0))
        self.save()

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
            if bid_type == True:
                self.game_header['rounds'][round_index]['contract'][team_index]['bidString'][number] += 'b'
            self.game_header['rounds'][round_index]['contract'][team_index]['blind'][number] = bid_type
            self.game_action = "BID_AMOUNT"
            self.save()
            return True
        except Exception as e:
            print(e, "Failed to set player bid type in GameRoom Model")
            return False
    
    def set_player_bid_amount(self,amount):
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
            if self.round_player_index == PLAYER_COUNT:
                self.round_player_index = 0
                self.game_action = "TICK"
            self.save()
            return True
        except Exception as e:
            print(e, "Failed to set player bid type in GameRoom Model")
            return False
    
    def get_card_index(self,card_id):
        round_index = self.game_header["current_round_index"]
        player_id = self.get_round_player_id()
        for index,card in enumerate(self.game_header['rounds'][round_index]['hands'][player_id]):
            if card['id'] == card_id:
                return index
        return -1
        
    
    def pay_player_card(self,message):
        try:
            card_id = int(message)
            card_index  = self.get_card_index(card_id)
            if card_index ==-1:
                raise Exception("Card not found")
            card = self.game_header['rounds'][self.game_header["current_round_index"]]['hands'][self.get_round_player_id()][card_index]
            if card.card_played:
                raise Exception("Card already played")
            self.game_header['rounds'][self.game_header["current_round_index"]]['hands'][self.get_round_player_id()][card_index].card_played = True
            self.round_player_index += 1
            flag_tick_end = False
            flag_round_end = False
            if self.round_player_index == PLAYER_COUNT:
                self.round_player_index = 0
                self.round_tick_index += 1
                flag_tick_end = True
            if self.round_tick_index == 13:
                self.round_tick_index = 0
                self.game_header["current_round_index"] += 1
                flag_round_end = True
                self.game_action = "BID_TYPE"
            
            self.save();
            if flag_tick_end:
                # self.tick_end()
                print("Tick end")
            if flag_round_end:
                print("Round end")
            return True
        except Exception as e:
            print(e,"Failed to pay player card in GameRoom Model")
            return False
        


class Player(models.Model):
    # Player fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player_cards = models.JSONField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)
