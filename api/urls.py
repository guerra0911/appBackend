from django.urls import path
from . import views

urlpatterns = [
    path("notes/", views.NoteListCreate.as_view(), name="note-list"),
    path("notes/delete/<int:pk>/", views.NoteDelete.as_view(), name="delete-note"),
    path("notes/<int:note_id>/comments/", views.CommentCreate.as_view(), name="create-comment"),
    path("notes/user/<int:user_id>/", views.UserNotesView.as_view(), name="user-notes"),
    path("notes/all/", views.AllNotesView.as_view(), name="all-notes"),
    path("notes/following/", views.FollowingNotesView.as_view(), name="following-notes"), 
    path("notes/<int:note_id>/like/", views.like_post, name="like-post"),
    path("notes/<int:note_id>/dislike/", views.dislike_post, name="dislike-post"),
    path("notes/<int:note_id>/liked_by/", views.liked_by, name='liked-by'),
    path("notes/<int:note_id>/disliked_by/", views.disliked_by, name='disliked-by'),
    path("profile/<int:profile_id>/followed_by/", views.followed_by, name='followed-by'),
    path("profile/<int:profile_id>/following/", views.following, name='following'),
    path("challenges/user/<int:user_id>/", views.UserChallengesView.as_view(), name="user-challenges"),
    path("challenges/all/", views.AllChallengesView.as_view(), name="all-challenges"),
    path("challenges/following/", views.FollowingChallengesView.as_view(), name="following-challenges"),
    path("challenges/related/<int:note_id>/", views.RelatedChallengesView.as_view(), name="related-challenges"),
    path("challenges/create/", views.CreateChallengeView.as_view(), name='create-challenge'),
    path("challenges/accept/<int:challenge_id>/", views.AcceptChallengeView.as_view(), name='accept-challenge'),
    path("challenges/decline/<int:challenge_id>/", views.DeclineChallengeView.as_view(), name='decline-challenge'),
    path("challenges/resubmit/<int:challenge_id>/", views.ResubmitChallengeView.as_view(), name='resubmit-challenge'),
    path("challenges/delete/<int:challenge_id>/", views.DeleteChallengeView.as_view(), name='delete-challenge'),
    path("challenges/requests/", views.ChallengeRequestsView.as_view(), name="challenge-requests"),
    path("challenges/requesting/", views.RequestingChallengeView.as_view(), name="requesting-challenges"),
    path("challenges/declined/", views.DeclinedChallengeView.as_view(), name="declined-challenges"),
    path("challenges/<int:challenge_id>/pick_original/", views.pick_original, name='pick-original'),
    path("challenges/<int:challenge_id>/pick_challenger/", views.pick_challenger, name='pick-challenger'),
    path("challenges/<int:challenge_id>/get_original_picks/", views.get_original_picks, name='get-original-picks'),
    path("challenges/<int:challenge_id>/get_challenger_picks/", views.get_challenger_picks, name='get-challenger-picks'),
    path("subs/all/", views.AllSubsView.as_view(), name="all-subs"),
    path("subs/user/<int:user_id>/", views.UserSubsView.as_view(), name="user-subs"),
    path("subs/following/", views.FollowingSubsView.as_view(), name="following-subs"),
    path("subs/related/<int:note_id>/", views.RelatedSubsView.as_view(), name="related-subs"),
    path("subs/create/", views.CreateSubView.as_view(), name='create-sub'),
    path("notes/all/combined/", views.AllCombinedView.as_view(), name="all-combined"),
    path("notes/user/<int:user_id>/combined/", views.UserCombinedView.as_view(), name="user-combined"),
    path("notes/following/combined/", views.FollowingCombinedView.as_view(), name="following-combined"),
]
