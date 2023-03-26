from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# Sign Up Form
class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username', 
            'password1', 
            'password2', 
            ]