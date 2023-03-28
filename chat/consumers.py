from django.core.signals import request_started
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from .models import GameRoom


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope["user"].is_authenticated:
            self.close()
            return;
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name
        try:
            room = GameRoom.game_manager.join_room(self.room_name, self.scope["user"])
            if room is None:
                raise Exception("Something went wrong")
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name, self.channel_name
            )
            self.accept()
        except Exception as e:
            print(e)
            self.close()


    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )
        print("disconnecting",  self.room_name,self.scope["user"].username)
        GameRoom.game_manager.leave_room(self.room_name, self.scope["user"].username)

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        GameRoom.game_manager.receive_message(self.room_name,self.scope["user"].username,message,self.channel_name)

    # Receive message from room group
    def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))