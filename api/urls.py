from django.urls import path
from . import views

urlpatterns = [
    path("notes/", views.NoteListCreate.as_view(), name="note-list"),
    path("notes/delete/<int:pk>/", views.NoteDelete.as_view(), name="delete-note"),
    path("notes/<int:note_id>/comments/", views.CommentCreate.as_view(), name="create-comment"),
    path("notes/user/<int:user_id>/", views.UserNotesView.as_view(), name="user-notes"),
    path("notes/all/", views.AllNotesView.as_view(), name="all-notes"),
    path("notes/<int:note_id>/like/", views.like_post, name="like-post"),
    path("notes/<int:note_id>/dislike/", views.dislike_post, name="dislike-post"),
    path("notes/<int:note_id>/liked_by/", views.liked_by, name='liked-by'),
    path("notes/<int:note_id>/disliked_by/", views.disliked_by, name='disliked-by'),
    path("profile/<int:profile_id>/followed_by/", views.followed_by, name='followed-by'),
    path("profile/<int:profile_id>/following/", views.following, name='following'),
]
