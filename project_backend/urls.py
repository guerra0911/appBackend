from django.contrib import admin
from django.urls import path, include
from api.views import CreateUserView, CurrentUserView, UpdateUserProfileView, UserProfileView, CreateTournamentView, TournamentViewSet, FollowView, UnfollowView, AcceptFollowRequestView, DeclineFollowRequestView, UnRequestView, requested_by, requesting
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/user/register/", CreateUserView.as_view(), name="register"),
    path("api/token/", TokenObtainPairView.as_view(), name="get_token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include("api.urls")),
    path("api/user/me/", CurrentUserView.as_view(), name="current_user"),
    path("api/user/me/update/", UpdateUserProfileView.as_view(), name="update_user_profile"),
    path("api/user/me/requests/", requested_by, name="requested-by"),
    path("api/user/me/requesting/", requesting, name="requesting"),
    path("api/profile/user/<int:user_id>/", UserProfileView.as_view(), name="user-profile"),
    path('api/user/follow/<int:user_id>/', FollowView.as_view(), name='follow_request'),
    path('api/user/accept_follow/<int:user_id>/', AcceptFollowRequestView.as_view(), name='accept_follow_request'),
    path('api/user/decline_follow/<int:user_id>/', DeclineFollowRequestView.as_view(), name='decline_follow_request'),
    path('api/user/unfollow/<int:user_id>/', UnfollowView.as_view(), name='unfollow'),
    path('api/user/unrequest/<int:user_id>/', UnRequestView.as_view(), name='unrequest'),
    path("api/tournaments/create/", CreateTournamentView.as_view(), name="create-tournament"),
    path("api/tournaments/", TournamentViewSet.as_view({'get': 'list'}), name="tournament-list"),
    path("api/tournaments/<int:pk>/", TournamentViewSet.as_view({'get': 'retrieve'}), name="tournament-detail"),
    path("api/tournaments/<int:pk>/submit_prediction/", TournamentViewSet.as_view({'post': 'submit_prediction'}), name="submit-prediction"),
    path("api/tournaments/<int:pk>/update_actual_bracket/", TournamentViewSet.as_view({'post': 'update_actual_bracket'}), name="update-actual-bracket"),
]