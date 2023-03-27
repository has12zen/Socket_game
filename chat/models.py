from django.core.signals import request_started
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import secrets
import random
from itertools import product


# Create your models here.

class User(models.Model):
    objects = models.Manager()
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    roomtoken = models.CharField(max_length=255)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)


def generate_room_id():
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    room_id = ''.join(secrets.choice(alphabet) for i in range(5))
    return room_id


class GameRoomManager(models.Manager):
    def create_room(self, creator):
        room = self.model(status='ACCEPTING')
        room.save()
        return room

    def join_room(self, room_id, creator):
        try:
            room = GameRoom.objects.get(room_id=room_id)
            user_instance = User.objects.get(username=creator.username)
            if room.status != 'ACCEPTING' and room.status!='ACTIVE':
                return None
            for player in room.players.all():
                if player.username == creator.username:
                    player = Player.objects.get(user=user_instance, game_room=room)
                    player.leave_time = None
                    player.save();
                    return room

            if room.players.count() >= 4:
                print("Room is full 444",room.players)
                return None
            player = Player.objects.create(user=user_instance, game_room=room)
            room.players.add(player.user)
            room.save()
            return room
        except Exception as e: 
            print(e,"something went wrong")
            return None

    def leave_room(self, room_id, name):
        room = self.get(room_id=room_id)
        user_instance = User.objects.get(username=name)
        for player in room.players.all():
            if player.username == name:
                pl = Player.objects.get(user=user_instance, game_room=room)
                pl.leave_time = datetime.now()
                pl.save()
                print('Player left room', pl.leave_time)
                break;
        return room

    def make_move(self, room_id, player_id, move):
        room = self.get(room_id=room_id)
        if room.status != 'ACTIVE':
            raise ValidationError('This room is already inactive')
        if player_id != room.turn:
            raise ValidationError('It is not your turn')
        return room

    def kick_out_inactive_players(self):
        rooms = self.filter(status='ACTIVE')
        print('Kicking out inactive players')
        for room in rooms:
            players = room.players.all()
            loserList = []
            for index,player in enumerate(players):
                if player.leave_time and (datetime.now() - player.leave_time > timedelta(minutes=5)):
                    # Kick out player
                    player.leave_time = None
                    player.save()
                    loserList.append(index + 1)
                    room.status = 'Complete'
                    # Record loss for not present player
            if room.status == 'Complete':
                for i in range(1, 5):
                    if i not in loserList:
                        if i == 1:
                            room.winnerList = room.winnerList + str(room.player_one) + ','
                        elif i == 2:
                            room.winnerList = room.winnerList + str(room.player_two) + ','
                        elif i == 3:
                            room.winnerList = room.winnerList + str(room.player_three) + ','
                        elif i == 4:
                            room.winnerList = room.winnerList + str(room.player_four) + ','
                room.save()

    def shuffle_cards(self):
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
        deck = list(product(suits, ranks))
        random.shuffle(deck)
        return deck

class GameRoom(models.Model):
    ROOM_STATUS = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('COMPLETE', 'Complete'),
        ('ACCEPTING', 'Accepting')
    )

    room_id = models.CharField(max_length=6, unique=True, default=generate_room_id)
    players = models.ManyToManyField(User, through='Player')
    moves = models.TextField(null=True, blank=True)
    turn = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ROOM_STATUS, default='INACTIVE')
    winnerList = models.TextField(null=True, blank=True)
    looserList = models.TextField(null=True, blank=True)
    cards = models.JSONField(null=True, blank=True)
    cards_distributed = models.BooleanField(default=False)
    # Manager
    objects = models.Manager()
    game_manager = GameRoomManager()
    

    def save(self, *args, **kwargs):
        if not self.id:
            game_manager = GameRoomManager()
            self.cards = game_manager.shuffle_cards()

        if self.status == 'active' and not self.cards_distributed:
            players = self.players.all()
            cards_per_player = len(self.cards) // len(players)
            for i, player in enumerate(players):
                player_cards = self.cards[i * cards_per_player:(i + 1) * cards_per_player]
                player.player_cards = player_cards
                player.save()
            self.cards_distributed = True

        if self.status == 'inactive' and self.cards:
            self.cards = None
            self.cards_distributed = False
            for player in self.players.all():
                player.player_cards = None
                player.leave_time = timezone.now()
                player.save()
            self.last_reset_time = timezone.now()

        super().save(*args, **kwargs)

class Player(models.Model):
    # Player fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player_cards = models.JSONField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)