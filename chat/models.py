from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import secrets


# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    roomtoken = models.CharField(max_length=255)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)




def generate_room_id():
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    room_id = ''.join(secrets.choice(alphabet) for i in range(5))
    return room_id


class GameRoomManager(models.Manager):
    def create_room(self, player_one):
        room = self.model(player_one=player_one, status='ACTIVE')
        room.room_id = generate_room_id()
        room.save()
        return room

    def join_room(self, room_id, player_id):
        room = self.get(room_id=room_id)
        if room.status == 'INACTIVE':
            raise ValidationError('This room is already inactive')
        if player_id in [room.player_one, room.player_two, room.player_three, room.player_four]:
            return room;
        if room.player_four:
            raise ValidationError('This room is already full')
        if not room.player_two:
            room.player_two = player_id
        elif not room.player_three:
            room.player_three = player_id
        elif not room.player_four:
            room.player_four = player_id
        room.save()
        return room

    def leave_room(self, room_id, player_id):
        room = self.get(room_id=room_id)
        if player_id == room.player_one:
            room.delete()
        elif player_id == room.player_two:
            room.player_two = None
        elif player_id == room.player_three:
            room.player_three = None
        elif player_id == room.player_four:
            room.player_four = None
        room.save()
        return room

    def make_move(self, room_id, player_id, move):
        room = self.get(room_id=room_id)
        if room.status == 'INACTIVE':
            raise ValidationError('This room is already inactive')
        if player_id != room.turn:
            raise ValidationError('It is not your turn')
        room.moves += f'{move},'
        if room.turn == room.player_one:
            room.turn = room.player_two
        elif room.turn == room.player_two:
            room.turn = room.player_three
        elif room.turn == room.player_three:
            room.turn = room.player_four
        elif room.turn == room.player_four:
            room.turn = room.player_one
        room.save()
        return room

    def check_player_disconnection(self, room_id, player_id):
        room = self.get(room_id=room_id)
        if player_id == room.turn:
            if player_id == room.player_one:
                room.turn = room.player_two
            elif player_id == room.player_two:
                room.turn = room.player_three
            elif player_id == room.player_three:
                room.turn = room.player_four
            elif player_id == room.player_four:
                room.turn = room.player_one
        room.save()
        return room

    def check_room_timeout(self, room_id):
        room = self.get(room_id=room_id)
        created_at = room.created_at
        now = timezone.now()
        time_difference = now - created_at
        if time_difference.seconds >= 300:
            room.status = 'INACTIVE'
            room.save()
        return room

class GameRoom(models.Model):
    objects = GameRoomManager()
    ROOM_STATUS = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )
    room_id = models.CharField(max_length=10, unique=True)
    player_one = models.CharField(max_length=100)
    player_two = models.CharField(max_length=100, blank=True, null=True)
    player_three = models.CharField(max_length=100, blank=True, null=True)
    player_four = models.CharField(max_length=100, blank=True, null=True)
    moves = models.TextField(blank=True, null=True)
    turn = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=ROOM_STATUS, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)