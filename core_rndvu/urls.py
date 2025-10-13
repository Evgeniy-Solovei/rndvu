from django.urls import path
from core_rndvu.views import *
from core_rndvu.yookassa_webhook import YookassaWebhookView

urlpatterns = [
    path('player-info/', PlayerInfoView.as_view(), name='player_info'),
    path("player/gender/", PlayerGenderUpdateView.as_view(), name='player_gender'),
    path("player/profile/", UserProfileView.as_view(), name='user_profile'),
    path("player/main_photo/", UserMainPhotoView.as_view(), name='user_profile'),
    # path("photo-reaction/", PhotoReactionView.as_view(), name='photo_reaction'),
    path("game/users/", GameUsersView.as_view(), name='game_users'),
    path("sympathy/", SympathyView.as_view(), name='sympathy'),
    path("favorites/", FavoriteView.as_view(), name='favorites'),
    path("player/profile/detail/", ProfileDetailView.as_view(), name="profile-detail"),
    path('events/', EventPlayerView.as_view(), name='events'),  # GET все, POST создать
    path('events/<int:event_id>/', EventPlayerView.as_view(), name='event-detail'),  # GET один, PATCH, DELETE
    path('events/opposite/', OppositeGenderEventsView.as_view(), name='opposite-events'),
    path('events/opposite/<int:event_id>/', OppositeGenderEventsView.as_view(), name='opposite-event'),
    path('user-likes/', UserLikeView.as_view(), name='user-likes'),
    path('update-verification/', UpdateVerificationView.as_view(), name='update-verification'),

    path("payment-create/", CreatePaymentView.as_view(), name='yookassa-create'),
    path('payment/webhook/', YookassaWebhookView.as_view(), name='yookassa-webhook'),
]
