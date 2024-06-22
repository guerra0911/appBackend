from django.contrib import admin
from django.urls import path, include
from api.views import CreateUserView, CurrentUserView, UpdateUserProfileView, UserProfileView
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
    path("api/profile/user/<int:user_id>/", UserProfileView.as_view(), name="user-profile"),
]

