from django.core.signals import request_started
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
import secrets
from picklefield.fields import PickledObjectField
import random
from itertools import product

channel_layer = get_channel_layer();

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
        room = GameRoom.objects.create(status='ACCEPTING')
        return room
    
    def get_room(self, room_id):
        try:
            room = GameRoom.objects.get(room_id=room_id)
            return room
        except:
            return None

    def join_room(self, room_id, creator,channel_name):
        try:
            room = GameRoom.objects.get(room_id=room_id)
            user_instance = User.objects.get(username=creator.username)
            if room.status != 'ACCEPTING' and room.status!='ACTIVE':
                return None
            for player in room.players.all():
                if player.username == creator.username:
                    player = Player.objects.get(user=user_instance, game_room=room)
                    player.leave_time = None
                    player.channel_name = channel_name
                    player.save()
                    room.increment_playercount();
                    room.save()
                    # user is was disconnected
                    return room

            if room.players.count() >= 4:
                print("Room is full 444",room.players)
                return None
            player = Player.objects.create(user=user_instance, game_room=room)
            player.channel_name=channel_name;
            player.save();
            room.players.add(player.user)
            room.increment_playercount();
            room.save()
            if(room.players.count() == 4):
                print("start game")
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
                room.decrement_playercount();
                pl.save()
                print('Player left room', pl.leave_time)
                break;
        room.save()
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

    def getPlayer(self,user_id,room_id):
        player = Player.objects.get(user_id=user_id,game_room_id=room_id)
        return player
        
    def send_message_to_room(self,room_name,message):
        room = self.get(room_id=room_name)
        async_to_sync(channel_layer.group_send)(
            room.get_group_name(), {"type": "chat_message", "message": message}
        )
    
    def send_message_to_player(self,room_name,username,message):
        room = self.get(room_id=room_name)
        user = User.objects.get(username=username)
        player = self.getPlayer(user.id,room.id)
        async_to_sync(channel_layer.send)(
            player.channel_name, {"type": "chat_message", "message": message}
        )        
    
    def receive_message(self,room_id,username,message,channel_name):
        room = self.get(room_id=room_id)
        user = User.objects.get(username=username)
        player = self.getPlayer(user.id,room.id)
        # handle logic
        self.send_message_to_player(room_id,username,message)
        self.send_message_to_room(room_id,message)



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
    playercount = models.IntegerField(default=0)
    game_state = PickledObjectField(default=None, null=True)
    # Manager
    objects = models.Manager()
    game_manager = GameRoomManager()

    def get_group_name(self):
        return f"chat_{self.room_id}"

    def increment_playercount(self):
        if self.playercount<4:
            self.playercount += 1
        if self.playercount==4:
            print("Game can continue....");
        print("adding players",self.playercount)

    def decrement_playercount(self):
        if self.playercount>0:
            self.playercount -= 1
        if self.playercount!=4:
            print("Waiting for 4 players to join")
    

class Player(models.Model):
    # Player fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player_cards = models.JSONField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)