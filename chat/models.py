import json
from django.db import models
from pathlib import Path
from .gameRoomManager import GameRoomManager, generate_room_id


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

    def initialize_game_header(self):
        players = self.players.all()
        user_ids = [player.user_id for player in players]

        initial_round = self.read_template_file("round_template.json")
        initial_tick = self.read_template_file("tick_template.json")

        initial_round["ticks"].append(initial_tick)

        initial_game_state = {
            "player_count": 0,
            "cards_distributed": False,
            "winning_value": 500,
            "game_score": [0, 0],
            "game_order": user_ids,
            "game_bags": [0, 0],
            "discarded_bags": [0, 0],
            "current_round_index": 0,
            "game_players": user_ids,
            "rounds": [initial_round]
        }
        self.game_header = initial_game_state
        self.game_header_initialized = True
        self.save()

    def get_player_index(self, user_id):
        return self.game_header["game_order"].index(user_id)

    def get_current_player_id(self):
        return self.game_header["game_order"][self.round_player_index]


class Player(models.Model):
    # Player fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player_cards = models.JSONField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)
