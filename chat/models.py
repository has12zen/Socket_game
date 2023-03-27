from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
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
        room = self.model(player_one=player_one, status='ACCEPTING')
        room.room_id = generate_room_id()
        room.save()
        return room

    def join_room(self, room_id, player_id):
        room = self.get(room_id=room_id)
        if room.status != 'ACCEPTING':
            raise ValidationError('This room is inactive or Full')
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
        if room.player_two and room.player_three and room.player_four:
            room.turn = room.player_one
            room.status = 'ACTIVE'
        if player_id == room.player_one:
            room.player_one_leave_time = None
        elif player_id == room.player_two:
            room.player_two_leave_time = None
        elif player_id == room.player_three:
            room.player_three_leave_time = None
        elif player_id == room.player_four:
            room.player_four_leave_time = None

        room.save()
        return room

    def leave_room(self, room_id, player_id):
        room = self.get(room_id=room_id)

        # Record leave time when player leaves
        if player_id == room.player_one:
            room.player_one_leave_time = datetime.now()
        elif player_id == room.player_two:
            room.player_two_leave_time = datetime.now()
        elif player_id == room.player_three:
            room.player_three_leave_time = datetime.now()
        elif player_id == room.player_four:
            room.player_four_leave_time = datetime.now()
        room.save()
        return room

    def make_move(self, room_id, player_id, move):
        room = self.get(room_id=room_id)
        if room.status != 'ACTIVE':
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

    def kick_out_inactive_players(self):
        rooms = self.filter(status='ACTIVE')
        print('Kicking out inactive players')
        for room in rooms:
            leave_times = [room.player_one_leave_time, room.player_two_leave_time, room.player_three_leave_time, room.player_four_leave_time]
            loserList = []
            for i in range(1, 5):
                if leave_times[i-1] and (datetime.now() - leave_times[i-1] > timedelta(minutes=5)):
                    # Kick out player
                    if i == 1:
                        room.loserList = room.loserList + str(room.player_one) + ','
                        loserList.append(1)
                    elif i == 2:
                        room.loserList = room.loserList + str(room.player_two) + ','
                        loserList.append(2)
                    elif i == 3:
                        room.loserList = room.loserList + str(room.player_three) + ','
                        loserList.append(3)
                    elif i == 4:
                        room.loserList = room.loserList + str(room.player_four) + ','
                        loserList.append(4)
                    leave_times[i-1] = None
                    
                        
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
class GameRoom(models.Model):
    ROOM_STATUS = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('COMPLETE', 'Complete'),
        ('ACCEPTING', 'Accepting')
    )
    objects = GameRoomManager()

    room_id = models.CharField(max_length=6, unique=True, default=generate_room_id)
    player_one = models.IntegerField()
    player_two = models.IntegerField(null=True, blank=True)
    player_three = models.IntegerField(null=True, blank=True)
    player_four = models.IntegerField(null=True, blank=True)
    moves = models.TextField(null=True, blank=True)
    turn = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ROOM_STATUS, default='INACTIVE')
    player_one_leave_time = models.DateTimeField(null=True, blank=True)
    player_two_leave_time = models.DateTimeField(null=True, blank=True)
    player_three_leave_time = models.DateTimeField(null=True, blank=True)
    player_four_leave_time = models.DateTimeField(null=True, blank=True)
    winnerList = models.TextField(null=True, blank=True)
    looserList = models.TextField(null=True, blank=True)