from django.urls import path
from . import views

urlpatterns = [
    path("notes/", views.NoteListCreate.as_view(), name="note-list"),
    path("notes/delete/<int:pk>/", views.NoteDelete.as_view(), name="delete-note"),
    path("notes/<int:note_id>/comments/", views.CommentCreate.as_view(), name="create-comment"),
    path("notes/user/<int:user_id>/", views.UserNotesView.as_view(), name="user-notes"),
    path("notes/following/", views.FollowedUsersNotesView.as_view(), name="followed-notes"),
    path("notes/all/", views.AllNotesView.as_view(), name="all-notes"),
]
