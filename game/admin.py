from django.contrib import admin
from .models.game_models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'status', 'boardmap')
