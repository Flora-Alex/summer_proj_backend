from django.db import models
import uuid

# Create your models here.
class User(models.Model):
    userId = models.CharField(max_length=100)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    # avatar_url = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return self.username