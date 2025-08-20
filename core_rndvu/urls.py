from django.urls import path
from core_rndvu.views import *

urlpatterns = [
    path('player-info/', PlayerInfoView.as_view(), name='player_info'),
    path("player/gender/", PlayerGenderUpdateView.as_view(), name='player_gender'),
    path("player/profile/", UserProfileView.as_view(), name='user_profile'),
    path("photo-reaction/", PhotoReactionView.as_view(), name='photo_reaction'),
    path("game/users/", GameUsersView.as_view(), name='game_users'),
    path("sympathy/", SympathyView.as_view(), name='sympathy'),
    path("favorites/", FavoriteView.as_view(), name='favorites'),
    path("player/profile/detail/", ProfileDetailView.as_view(), name="profile-detail"),
]
