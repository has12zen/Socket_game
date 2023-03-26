from django.db import models

# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    roomtoken = models.CharField(max_length=255)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)

class Room(models.Model):
    roomkey = models.CharField(max_length=255, unique=True)
    userIds = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    winner = models.CharField(max_length=255)
    PointsA = models.IntegerField(default=0)
    PointsB = models.IntegerField(default=0)
    PointsC = models.IntegerField(default=0)
    PointsD = models.IntegerField(default=0)
    Moves = models.CharField(max_length=255)
    Turn = models.CharField(max_length=255)