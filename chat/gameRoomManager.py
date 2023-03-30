from django.core.signals import request_started
from django.utils import timezone
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
from django.db import models
import random
import secrets
from itertools import product
from django.apps import apps
from round import Round
from spades_utils import *

def generate_room_id():
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    room_id = ''.join(secrets.choice(alphabet) for i in range(5))
    return room_id

channel_layer = get_channel_layer();

class GameRoomManager(models.Manager):
    def __init__(self) -> None:
        super().__init__()
    def create_room(self, creator):
        round_index = 1
        scores = [0, 0]
        bags = [0, 0]
        discarded_bags = [0, 0]
        rounds = []
        room = self.create(
            status='ACCEPTING',
            round_index=round_index,
            scores=scores,
            bags=bags,
            discarded_bags=discarded_bags,
            rounds=rounds,
            )
        return room
    
    def get_room(self, room_id):
        try:
            room = self.get(room_id=room_id)
            return room
        except:
            return None

    def join_room(self, room_id, creator,channel_name):
        try:
            room = self.get(room_id=room_id)
            User = apps.get_model('chat', 'User')
            Player = apps.get_model('chat', 'Player')
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
            return room
        except Exception as e: 
            print(e,"something went wrong")
            return None

    def leave_room(self, room_id, name):
        room = self.get(room_id=room_id)
        User = apps.get_model('chat', 'User')
        Player = apps.get_model('chat', 'Player')
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
        Player = apps.get_model('chat', 'Player')
        player = Player.objects.get(user_id=user_id,game_room_id=room_id)
        return player
        
    def send_message_to_player(self,room_name,username,data):
        User = apps.get_model('chat', 'User')
        room = self.get(room_id=room_name)
        user = User.objects.get(username=username)
        player = self.getPlayer(user.id,room.id)
        async_to_sync(channel_layer.send)(
            player.channel_name, data
        )        
    
    def receive_message(self,room_id,username,text_data_json):
        User = apps.get_model('chat', 'User')
        message = text_data_json["message"]
        message_type = text_data_json["message_type"]
        room = self.get(room_id=room_id)
        user = User.objects.get(username=username)
        player = self.getPlayer(user.id,room.id)
        if room['status']!='ACTIVE':
            self.send_message_to_player(room_id,username,{'type': 'game_status', 'game_status': 'Game is not active'});
            return;
        if message_type!=room['game_status']:
            self.send_message_to_player(room_id,username,{'type': 'game_status', 'game_status': 'It is not your turn'});
            return;
        if message_type == 'bid_type':
            room.game_status = 'bid_amt'
            room.save()
            return;

        elif message_type == 'bidding_amount':
            # if player index <3:
            room.game_status = 'bid_type'
            room.round_player_index = room.round_player_index + 1
            # elif player index == 3:
            #     room.game_status = 'tick'
            #      room.round_player_index = 0

        elif message_type == 'tick':
            card = text_data_json["card"]
            # if player index <3:
            room.game_status = 'tick'
            room.round_player_index = room.round_player_index + 1
            # elif player index == 3:
            # room.game_status = 'tick'
            # room.round_player_index = 0
            # room.round_tick_index = room.round_tick_index + 1
            # if room.round_tick_index == 13:
            # room.game_status = 'bid_type'
        else:
            # Handle unknown message types
            print(f"Unknown message type: {message_type}")
