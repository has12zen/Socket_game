from django.forms import ValidationError
from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count
from .models import User, GameRoom, GameRoomManager, GameStats


def createRoom(request):
    room = GameRoom.game_manager.create_room(request.user)
    if room is None:
        return render(request, 'chat/createJoinRoom.html', {'error': 'Room could not be created'})
    return redirect(f'/chat/{room.room_id}')


def joinRoom(request):
    roomkey = request.POST.get('roomkey')
    try:
        room = GameRoom.game_manager.get_room(roomkey)
        if room is None:
            raise ValidationError('Room does not exist or is full')
    except ValidationError as e:
        return render(request, 'chat/createJoinRoom.html', {'error': e})

    return redirect('/chat/' + roomkey)


def home(request):
    if not request.user.is_authenticated:
        return redirect("login-user")
    user = request.user
    user = User.objects.get(username=user.username)
    print("user", user.id)
    try:
        game_stats = GameStats.objects.filter(user_id=user.id).values(
            'winOrLose').annotate(count=Count('id'))
        print(game_stats, 'gamestats')
        wins = 0
        losses = 0

        for stat in game_stats:
            if stat['winOrLose'] == True:
                wins = stat['count']
            elif stat['winOrLose'] == False:
                losses = stat['count']
    except Exception as e:
        print(e, "failed to get")
        wins = 0
        losses = 0

    return render(request, 'chat/home.html', {'wins': wins, 'losses': losses})


def completedGames(request):
    if not request.user.is_authenticated:
        return redirect("login-user")

    user = request.user
    user = User.objects.get(username=user.username)
    try:
        completed_games = GameStats.objects.filter(
            user=user).values('room_id', 'winOrLose')
    except Exception as e:
        print(e, "compltedGames")
        completed_games = None
    return render(request, 'chat/completed_games.html', {'completed_games': completed_games})


def roomHistory(request):
    if not request.user.is_authenticated:
        return redirect("login-user")
    room_id = request.GET.get('id', '')
    user = request.user
    user = User.objects.get(username=user.username)

    try:
        room = GameRoom.objects.get(room_id=room_id)
        gamestats = GameStats.objects.filter(
            game_room=room, user=user).order_by('id')
        print(gamestats, "gamestats")
    except (GameRoom.DoesNotExist, GameStats.DoesNotExist):
        print("room not found")
        return render(request, 'chat/roomHistory.html', {'room_id': room_id, 'error': 'Room not found.'})

    return render(request, 'chat/roomHistory.html', {'room': room, 'gamestats': gamestats})


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
    return render(request, "chat/chatPage.html", {"room_name": room_name})


def create_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = User.objects.create(
                username=form.cleaned_data.get('username'),
                wins=0,
                losses=0
            )
            # replace 'home' with the name of your home view
            return redirect('login-user')
    else:
        form = UserCreationForm()
    return render(request, 'chat/SignUpPage.html', {'form': form})
