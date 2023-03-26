from django.shortcuts import render , redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from chat.forms import SignUpForm
from django.contrib.auth.forms import UserCreationForm
from .models import User,Room

def createRoom(request):
    roomkey = request.POST.get('roomkey')
    
    # validate form data
    if not roomkey:
        return render(request, 'chat/home.html', {'error': 'Room key is required.'})
    
    # check if room with roomkey already exists
    if Room.objects.filter(roomkey=roomkey).exists():
        return render(request, 'chat/home.html', {'error': 'Room with that key already exists.'})
    
    # create new room
    room = Room.objects.create(
        roomkey=roomkey,
        userIds='',
        status='active',
        winner='',
        PointsA=0,
        PointsB=0,
        PointsC=0,
        PointsD=0,
        Moves='',
        Turn=''
    )
    
    return redirect(f'/chat/{roomkey}') 

def joinRoom(request):
    roomkey = request.POST.get('roomkey')
    user = request.user
    try:
        room = Room.objects.get(roomkey=roomkey)
    except Room.DoesNotExist:
        return render(request, 'chat/home.html', {'error': 'Room with that key does not exist.'})
    if not room.userIds:
        room.userIds = str(user.id)
    else:
        user_ids = room.userIds.split(',')
        if len(user_ids) >= 4:
            return render(request, 'chat/home.html', {'error': 'Room is full.'})
        user_ids.append(str(user.id))
        room.userIds = ','.join(user_ids)
    room.save()
    
    return redirect('/chat/' + roomkey) 

def chatPage(request , *args , **kwargs) :
    if not request.user.is_authenticated : 
        return redirect("login-user")
    context = {}
    if request.method == 'POST':
        action = request.POST.get('action')
        if(action == 'create'):
            return createRoom(request)
        elif(action == 'join'):
            return joinRoom(request)
        else :
            return render(request, 'chat/home.html',{'error': 'Invalid action. select create or join'})
    else:
        return render(request, 'chat/home.html')

def room(request, room_name):
    if not request.user.is_authenticated : 
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
            return redirect('login-user') # replace 'home' with the name of your home view
    else:
        form = UserCreationForm()
    return render(request, 'chat/SignUpPage.html', {'form': form})