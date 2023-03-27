from django.forms import ValidationError
from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm
from .models import User, GameRoom, GameRoomManager


def createRoom(request):
    room = GameRoom.game_manager.create_room(request.user)
    if room is None:
        return render(request, 'chat/createJoinRoom.html', {'error': 'Room could not be created'})
    GameRoom.game_manager.join_room(room.room_id, request.user)
    return redirect(f'/chat/{room.room_id}')


def joinRoom(request):
    roomkey = request.POST.get('roomkey')
    user = request.user
    try:
        room = GameRoom.game_manager.join_room(roomkey, user)
        if room is None:
            raise ValidationError('Room does not exist or is full')
    except ValidationError as e:
        return render(request, 'chat/createJoinRoom.html', {'error': e})

    room.save()

    return redirect('/chat/' + roomkey)


def home(request):
    if not request.user.is_authenticated:
        return redirect("login-user")
    return render(request, 'chat/home.html',{})

def chatPage(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect("login-user")
    context = {}
    if request.method == 'POST':
        action = request.POST.get('action')
        if (action == 'create'):
            return createRoom(request)
        elif (action == 'join'):
            return joinRoom(request)
        else:
            return render(request, 'chat/createJoinRoom.html', {'error': 'Invalid action. select create or join'})
    else:
        return render(request, 'chat/createJoinRoom.html')


def room(request, room_name):
    if not request.user.is_authenticated:
        return redirect("login-user")
    return render(request, "chat/room.html", {"room_name": room_name})

# Sign Up View


def create_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = User.objects.create(
                username=form.cleaned_data.get('username'),
                roomtoken='',
                wins=0,
                losses=0
            )
            # replace 'home' with the name of your home view
            return redirect('login-user')
    else:
        form = UserCreationForm()
    return render(request, 'chat/SignUpPage.html', {'form': form})
