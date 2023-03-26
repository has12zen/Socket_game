from django.shortcuts import render , redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from chat.forms import SignUpForm

def chatPage(request , *args , **kwargs) :
    if not request.user.is_authenticated : 
        return redirect("login-user")
    context = {}
    return render(request , "chat/chatPage.html" , context)

# Sign Up View
class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login-user')
    template_name = 'chat/SignUpPage.html'