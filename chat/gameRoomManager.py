from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
from django.db import models
import secrets
from django.apps import apps
from ChatApp.constants import PLAYER_COUNT


def generate_room_id():
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    room_id = ''.join(secrets.choice(alphabet) for i in range(5))
    return room_id


channel_layer = get_channel_layer()


class GameRoomManager(models.Manager):
    def __init__(self) -> None:
        super().__init__()

    def create_room(self, creator):
        room = self.create(status='ACCEPTING')
        return room

    def get_room(self, room_id):
        try:
            room = self.get(room_id=room_id)
            return room
        except:
            print("something went wrong while getting room")
            return None

    def join_room(self, room_id, creator, channel_name):
        try:
            room = self.get(room_id=room_id)
            Player = apps.get_model('chat', 'Player')
            User = apps.get_model('chat', 'User')
            user_instance = User.objects.get(username=creator.username)
            if room.status != 'ACCEPTING' and room.status != 'ACTIVE':
                return None
            for player in room.players.all():
                if player.username == creator.username:
                    player = Player.objects.get(
                        user=user_instance, game_room=room)
                    player.leave_time = None
                    player.channel_name = channel_name
                    player.save()
                    room.save()
                    # user is was disconnected
                    return room

            if room.players.count() >= PLAYER_COUNT:
                print("Room is full 444", room.players)
                return None
            player = Player.objects.create(user=user_instance, game_room=room)
            player.channel_name = channel_name
            player.save()
            room.players.add(player.user)
            room.save()
            return room
        except Exception as e:
            print(e, "something went wrong while joining room")
            return None

    def check_if_game_can_start_or_resume(self, room):
        try:
            if room.status == 'ACTIVE':
                if room.players.filter(leave_time=None).count() == PLAYER_COUNT:
                    if room.game_header_initialized == False:
                        room.initialize_game_header()
                        room.initialize_round()
                        room.deal_round_hands()
                        print("Game Start!")
                    elif room.game_header_initialized == True:
                        print("resume game")
            return False
        except Exception as e:
            print(e, "something went wrong while checking if game can start")

    def leave_room(self, room_id, name):
        try:
            room = self.get(room_id=room_id)
            User = apps.get_model('chat', 'User')
            Player = apps.get_model('chat', 'Player')
            user_instance = User.objects.get(username=name)
            for player in room.players.all():
                if player.username == name:
                    pl = Player.objects.get(user=user_instance, game_room=room)
                    pl.leave_time = datetime.now()
                    pl.save()
                    print('Player left room', pl.leave_time)
                    break
            room.save()
            return room
        except Exception as e:
            print(e, "something went wrong while leaving room")
            return

    def kick_out_inactive_players(self):
        rooms = self.filter(status='ACTIVE')
        print('Kicking out inactive players')
        for room in rooms:
            players = room.players.all()
            for index, player in enumerate(players):
                if player.leave_time and (datetime.now() - player.leave_time > timedelta(minutes=5)):
                    # Kick out player
                    player.leave_time = None
                    player.save()
                    room.status = 'Complete'
            room.save()

    def getPlayer(self, user_id, room_id):
        Player = apps.get_model('chat', 'Player')
        player = Player.objects.get(user_id=user_id, game_room_id=room_id)
        return player

    def send_message_to_player(self, room_name, username, data):
        User = apps.get_model('chat', 'User')
        room = self.get(room_id=room_name)
        user = User.objects.get(username=username)
        player = self.getPlayer(user.id, room.id)
        print("Sending message to player", data)
        async_to_sync(channel_layer.send)(
            player.channel_name, {
                'type': 'chat_message',
                'message': data
            }
        )

    def send_message_to_all_players(self, room_name, data):
        print("Sending message to all players", data)
        async_to_sync(channel_layer.group_send)(
            room_name, {
                'type': 'chat_message',
                'message': data
            }
        )

    def find_bid_type(self, message):
        if message in ["Y", 'y', "Yes", "yes", "YES"]:
            return True
        elif message in ["N", 'n', "No", "no", "NO"]:
            return False
        else:
            return None

    def find_bid_amount(self, message):
        try:
            bid = int(message)
            if bid >= 0 and bid <= 13:
                return bid
            else:
                raise ValueError
        except ValueError:
            return None

    def receive_message(self, room_id, username, text_data_json):
        try:
            User = apps.get_model('chat', 'User')
            message_type = text_data_json["message_type"]
            message = text_data_json["message"]
            room = self.get(room_id=room_id)
            game_room_id = 'chat_%s' % str(room_id)
            round_player_index = room.round_player_index
            user = User.objects.get(username=username)
            player = self.getPlayer(user.id, room.id)
            if message_type == 'get_hands':
                res = room.send_player_hand(user.id)
                if res != None:
                    self.send_message_to_player(
                        room_id, username, {'type': 'hands', 'hands': res})
                    return
                return
            if room.game_header_initialized == False or room['status'] != 'ACTIVE':
                self.send_message_to_player(
                    room_id, username, {'type': 'game_status', 'game_status': 'Game is not active'})
                return
            if message_type != room['game_action']:
                self.send_message_to_player(room_id, username, {
                                            'type': 'game_status', 'game_status': 'It is not your turn'})
                return
            current_round_index = room.game_header['current_round_index']
            round_player = room.game_header['rounds'][current_round_index]['round_order'][round_player_index]
            if round_player != user.id:
                self.send_message_to_player(room_id, username, {
                    'type': 'game_status', 'game_status': 'It is not your turn'
                })

            if message_type == 'bid_type':
                bid_type = self.find_bid_type(message)
                if bid_type != None:
                    res = room.game_manager.set_player_bid_type(bid_type)
                    if res == True:
                        if bid_type == True:
                            self.send_message_to_player(room_id, username, {
                                'type': 'game_status', 'game_status': 'Bid type set successfully',
                            })
                        elif bid_type == False:
                            self.send_message_to_player(room_id, username, {
                                'type': 'hands', 'game_status': 'Bid type set successfully',
                                'hands': room.game_header['rounds'][current_round_index]['round_hands'][round_player_index]
                            })
                        return
                    # something went wrong
                self.send_message_to_player(room_id, username, {
                    'type': 'game_status', 'game_status': 'Invalid input please enter yes or no'
                })
                return

            elif message_type == 'bid_amount':
                amount = self.find_bid_amount(message)
                if amount != None:
                    res = room.game_manager.set_player_bid_amount(amount)
                    if res == True:
                        self.send_message_to_player(room_id, username, {
                            'type': 'game_status', 'game_status': 'Bid amount set successfully!\n Good Luck bidding blind', 'hand': room.game_header['rounds'][current_round_index]['round_hands'][round_player_index]
                        })
                        return
                    self.send_message_to_player(room_id, username, {
                        'type': 'game_status', 'game_status': 'Invalid input please enter a number between 0 and 13'
                    })

            elif message_type == 'tick':
                res = room.play_player_card(message)
                if res != "":
                    if res == "A":
                        self.send_message_to_all_players(
                            game_room_id, {'type': 'game_status', 'game_status': 'Team A won the game'})
                    elif res == "B":
                        self.send_message_to_all_players(
                            game_room_id, {'type': 'game_status', 'game_status': 'Team B won the game'})
            else:
                # Handle unknown message types
                print(f"Unknown message type: {message_type}")
                self.send_message_to_player(room_id, username, {
                                            'type': 'game_status', 'game_status': f'You are doing wrong action you should {room.game_action}'})
        except Exception as e:
            print(e.__cause__, e.__module__,
                  e.__context__, "something went wrong")
