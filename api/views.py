from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics, status, viewsets
from .serializers import UserSerializer, NoteSerializer, CommentSerializer, ProfileSerializer, TournamentSerializer, TeamSerializer, BracketSerializer, ChallengeSerializer, SubSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Note, Profile, Comment, Tournament, Team, Bracket, Challenge, Sub
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, F
from django.db import transaction
from django.utils import timezone
import json
from django.http import JsonResponse
from django.core.cache import cache

import logging

logger = logging.getLogger(__name__)


### USERS ###
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user.profile.calculate_rating()
        user_serializer = UserSerializer(user)
        profile_serializer = ProfileSerializer(user.profile)
        notes_serializer = NoteSerializer(user.notes.all(), many=True)
        return Response({
            'id': user_serializer.data['id'],
            'username': user_serializer.data['username'],
            'profile': profile_serializer.data,
            'posts': notes_serializer.data,
        })
    
### PROFILE ###
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.profile.calculate_rating()
            user_serializer = UserSerializer(user)
            profile_serializer = ProfileSerializer(user.profile)
            notes_serializer = NoteSerializer(user.notes.all(), many=True)
            return Response({
                'userData': user_serializer.data,
                'profile': profile_serializer.data,
                'posts': notes_serializer.data,
            })
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        if query:
            users = User.objects.filter(username__icontains=query)[:5]
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        return Response([])

@api_view(['GET'])
def followed_by(request, profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        users = profile.followers.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def following(request, profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        users = profile.following.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def requested_by(request):
    try:
        user = request.user
        users = user.profile.requests.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def requesting(request):
    try:
        user = request.user
        users = user.profile.requesting.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['GET'])
def blocked_by(request):
    try:
        user = request.user
        users = user.profile.blocked_by.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def blocking(request):
    try:
        user = request.user
        users = user.profile.blocking.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


### PROFILE ACTIONS ###       
class UpdateUserProfileView(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        data = request.data

        profile_data = {}
        if 'bio' in data:
            profile_data['bio'] = data['bio']
        if 'location' in data:
            profile_data['location'] = data['location']
        if 'birthday' in data:
            profile_data['birthday'] = data['birthday']
        if 'spotify_url' in data:
            profile_data['spotify_url'] = data['spotify_url']
        if 'imdb_url' in data:
            profile_data['imdb_url'] = data['imdb_url']
        if 'website_url' in data:
            profile_data['website_url'] = data['website_url']
        if 'privacy_flag' in data:
            profile_data['privacy_flag'] = data['privacy_flag'].lower() == 'true'
        if 'notification_flag' in data:
            profile_data['notification_flag'] = data['notification_flag'].lower() == 'true'
        if 'email' in data:
            profile_data['email'] = data['email']
        if 'auto_accept_challenges' in data:
            profile_data['auto_accept_challenges'] = data['auto_accept_challenges'].lower() == 'true'
        
        if 'image' in request.FILES:
            profile_data['image'] = request.FILES['image']

        profile_serializer = ProfileSerializer(user.profile, data=profile_data, partial=True)
        user_serializer = UserSerializer(user, data=data, partial=True)

        if profile_serializer.is_valid() and user_serializer.is_valid():
            # Handle privacy flag logic
            if 'privacy_flag' in profile_data:
                new_privacy_flag = profile_data['privacy_flag']
                if new_privacy_flag == False:  # Public profile
                    for requester in user.profile.requests.all():
                        requester.profile.requesting.remove(user)
                        requester.profile.following.add(user)
                        user.profile.followers.add(requester)
                    user.profile.requests.clear()

            # Handle auto-accept challenges logic
            if 'auto_accept_challenges' in profile_data and profile_data['auto_accept_challenges']:
                pending_challenges = user.profile.challenge_requests.filter(pending=True)
                current_time = timezone.now()

                for challenge in pending_challenges:
                    challenge.pending = False
                    challenge.accepted = True
                    challenge.declined = False
                    challenge.created_at = current_time
                    challenge.challenger_note.created_at = current_time
                    challenge.challenger_note.save()
                    challenge.save()

                    user.profile.challenge_requests.remove(challenge)
                    user.profile.active_challenges_received.add(challenge)
                    challenge.challenger_note.author.profile.active_challenges_made.add(challenge)
                    challenge.challenger_note.author.profile.challenges_sent.remove(challenge)

            profile_serializer.save()
            user_serializer.save()
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        else:
            profile_errors = profile_serializer.errors if not profile_serializer.is_valid() else {}
            user_errors = user_serializer.errors if not user_serializer.is_valid() else {}
            return Response({
                'profile_errors': profile_errors,
                'user_errors': user_errors
            }, status=status.HTTP_400_BAD_REQUEST)


class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_follow = User.objects.get(id=user_id)
            current_user = request.user

            if to_follow.profile.privacy_flag:
                to_follow.profile.requests.add(current_user)
                current_user.profile.requesting.add(to_follow)
                return Response({'status': 'request_sent'}, status=status.HTTP_200_OK)
            else:
                to_follow.profile.followers.add(current_user)
                current_user.profile.following.add(to_follow)
                return Response({'status': 'following'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
 
class UnfollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_unfollow = User.objects.get(id=user_id)
            current_user = request.user

            if to_unfollow in current_user.profile.following.all() and current_user in to_unfollow.profile.followers.all():
                current_user.profile.following.remove(to_unfollow)
                to_unfollow.profile.followers.remove(current_user)
                return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
            return Response({'error': 'not_following'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
class UnRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_unrequest = User.objects.get(id=user_id)
            current_user = request.user

            if to_unrequest in current_user.profile.requesting.all() and current_user in to_unrequest.profile.requests.all():
                current_user.profile.requesting.remove(to_unrequest)
                to_unrequest.profile.requests.remove(current_user)
                return Response({'status': 'unrequested'}, status=status.HTTP_200_OK)
            return Response({'error': 'not_requesting'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
class AcceptFollowRequestView(APIView): #Called From Current User
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_accept = User.objects.get(id=user_id)
            current_user = request.user
            
            if to_accept in current_user.profile.requests.all():
                current_user.profile.requests.remove(to_accept)
                to_accept.profile.requesting.remove(current_user)
                current_user.profile.followers.add(to_accept)
                to_accept.profile.following.add(current_user)
                return Response({'status': 'accepted'}, status=status.HTTP_200_OK)
            return Response({'error': 'request_not_found'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class DeclineFollowRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_decline = User.objects.get(id=user_id)
            current_user = request.user
            
            if to_decline in current_user.profile.requests.all():
                current_user.profile.requests.remove(to_decline)
                to_decline.profile.requesting.remove(current_user)
                return Response({'status': 'declined'}, status=status.HTTP_200_OK)
            return Response({'error': 'request_not_found'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class BlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_block = User.objects.get(id=user_id)
            current_user = request.user

            # Remove from following/followers/requests/requesting lists
            if to_block in current_user.profile.following.all():
                current_user.profile.following.remove(to_block)
                to_block.profile.followers.remove(current_user)
            if to_block in current_user.profile.followers.all():
                current_user.profile.followers.remove(to_block)
                to_block.profile.following.remove(current_user)
            if to_block in current_user.profile.requests.all():
                current_user.profile.requests.remove(to_block)
                to_block.profile.requesting.remove(current_user)
            if to_block in current_user.profile.requesting.all():
                current_user.profile.requesting.remove(to_block)
                to_block.profile.requests.remove(current_user)

            # Add to blocking/blocked_by lists
            current_user.profile.blocking.add(to_block)
            to_block.profile.blocked_by.add(current_user)

            # Fetch and delete relevant challenges
            challenge_lists = [
                current_user.profile.challenge_requests,
                current_user.profile.challenges_sent,
                current_user.profile.challenges_declined,
                current_user.profile.active_challenges_made,
                current_user.profile.active_challenges_received
            ]
            
            for challenge_list in challenge_lists:
                challenges_to_delete = challenge_list.filter(
                    Q(original_note__author=to_block) | Q(challenger_note__author=to_block)
                )
                for challenge in challenges_to_delete:
                    challenge.delete()

            return Response({'status': 'user blocked'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
class UnblockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_unblock = User.objects.get(id=user_id)
            current_user = request.user

            if to_unblock in current_user.profile.blocking.all() and current_user in to_unblock.profile.blocked_by.all():
                current_user.profile.blocking.remove(to_unblock)
                to_unblock.profile.blocked_by.remove(current_user)
                return Response({'status': 'unblocked'}, status=status.HTTP_200_OK)
            return Response({'error': 'not_blocking'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

### NOTES ###     
class NoteListCreate(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)

    def perform_create(self, serializer):
        if serializer.is_valid():
            note = serializer.save(author=self.request.user)
            images = self.request.FILES.getlist('images')
            if images:
                for idx, image in enumerate(images):
                    setattr(note, f'image{idx + 1}', image)
                note.save()
        else:
            print(serializer.errors)

class UserNotesView(generics.ListAPIView):  #ProfilePages
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        queryset = Note.objects.filter(author_id=user_id, is_challenger=False, is_subber=False)
        
        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('dislikes')).order_by('-dislikes_count')
        
        return queryset.order_by('-created_at')
    
class AllNotesView(generics.ListAPIView):   #Home Page
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Note.objects.filter(
            Q(author__profile__privacy_flag=False) |  # Public profiles
            Q(author__id__in=following_ids) |         # Followed users
            Q(author__id=user.id)                     # Current user's posts
        ).exclude(
            Q(author__id__in=blocking_ids) |          # Users the current user is blocking
            Q(author__id__in=blocked_by_ids)          # Users who are blocking the current user
        ).filter(is_challenger=False, is_subber=False)

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class FollowingNotesView(generics.ListAPIView):  #Home Page
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        
        following_ids = user.profile.following.values_list('id', flat=True)

        queryset = Note.objects.filter(author_id__in=following_ids, is_challenger=False, is_subber=False)

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class NoteDelete(generics.DestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)


### NOTES ACTIONS ###
@api_view(['POST'])
def like_post(request, note_id):
    try:
        note = Note.objects.get(id=note_id)
        user = request.user

        if user in note.dislikes.all():
            note.dislikes.remove(user)
        if user not in note.likes.all():
            note.likes.add(user)
        else:
            note.likes.remove(user)

        note.save()
        return Response({'likes': note.likes.count(), 'dislikes': note.dislikes.count()}, status=status.HTTP_200_OK)
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def dislike_post(request, note_id):
    try:
        note = Note.objects.get(id=note_id)
        user = request.user

        if user in note.likes.all():
            note.likes.remove(user)
        if user not in note.dislikes.all():
            note.dislikes.add(user)
        else:
            note.dislikes.remove(user)

        note.save()
        return Response({'likes': note.likes.count(), 'dislikes': note.dislikes.count()}, status=status.HTTP_200_OK)
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def liked_by(request, note_id):
    try:
        note = Note.objects.get(id=note_id)
        users = note.likes.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def disliked_by(request, note_id):
    try:
        note = Note.objects.get(id=note_id)
        users = note.dislikes.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)


### SUBS ###   
class CreateSubView(generics.CreateAPIView):
    serializer_class = SubSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # The original note being subbed
        original_note = Note.objects.get(pk=self.request.data['original_note'])

        # The sub note
        sub_note = Note.objects.get(pk=self.request.data['sub_note'])

        # Save the sub linking the original and sub notes
        serializer.save(original_note=original_note, sub_note=sub_note)

def get_serializer_for_instance(instance):
    if isinstance(instance, Note):
        return NoteSerializer
    elif isinstance(instance, Challenge):
        return ChallengeSerializer
    elif isinstance(instance, Sub):
        return SubSerializer
    return NoteSerializer
   
class UserSubsView(generics.ListAPIView):
    serializer_class = SubSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        
        user_profile = User.objects.get(id=user_id).profile
        blocking_ids = user_profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user_profile.blocked_by.values_list('id', flat=True)

        queryset = Sub.objects.filter(
            sub_note__author_id=user_id
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(sub_note__author__id__in=blocking_ids) |
            Q(sub_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('sub_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('sub_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class AllSubsView(generics.ListAPIView):
    serializer_class = SubSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Sub.objects.filter(
            Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id),
            Q(sub_note__author__profile__privacy_flag=False) |
            Q(sub_note__author__id__in=following_ids) |
            Q(sub_note__author__id=user.id)
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(sub_note__author__id__in=blocking_ids) |
            Q(sub_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('sub_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('sub_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class FollowingSubsView(generics.ListAPIView):
    serializer_class = SubSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Sub.objects.filter(
            Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id),
            Q(sub_note__author__id__in=following_ids)
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(sub_note__author__id__in=blocking_ids) |
            Q(sub_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('sub_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('sub_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class RelatedSubsView(generics.ListAPIView):
    serializer_class = SubSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        note_id = self.kwargs['note_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Sub.objects.filter(
            original_note_id=note_id
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(sub_note__author__id__in=blocking_ids) |
            Q(sub_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('sub_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('sub_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')
 

### CHALLENGE ###   
class CreateChallengeView(generics.CreateAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        original_note = Note.objects.get(pk=self.request.data['original_note'])
        challenger_note = Note.objects.get(pk=self.request.data['challenger_note'])
        challenge = serializer.save(original_note=original_note, challenger_note=challenger_note, wager=self.request.data.get('wager', 0))
        
        with transaction.atomic():
            original_note.author.profile.challenge_requests.add(challenge)
            challenger_note.author.profile.challenges_sent.add(challenge)
            
            if original_note.author.profile.auto_accept_challenges:
                current_time = timezone.now()
                challenge.pending = False
                challenge.accepted = True
                challenge.declined = False
                challenge.created_at = current_time
                challenge.challenger_note.created_at = current_time
                challenge.challenger_note.save()
                challenge.save()
                original_note.author.profile.challenge_requests.remove(challenge)
                original_note.author.profile.active_challenges_received.add(challenge)
                challenger_note.author.profile.active_challenges_made.add(challenge)
                challenger_note.author.profile.challenges_sent.remove(challenge)
    
class UserChallengesView(generics.ListAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        
        user_profile = User.objects.get(id=user_id).profile
        blocking_ids = user_profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user_profile.blocked_by.values_list('id', flat=True)

        queryset = Challenge.objects.filter(
            challenger_note__author_id=user_id,
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(challenger_note__author__id__in=blocking_ids) |
            Q(challenger_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('challenger_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('challenger_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class AllChallengesView(generics.ListAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Challenge.objects.filter(
            (Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id)) &
            (Q(challenger_note__author__profile__privacy_flag=False) |
            Q(challenger_note__author__id__in=following_ids) |
            Q(challenger_note__author__id=user.id)),
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(challenger_note__author__id__in=blocking_ids) |
            Q(challenger_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('challenger_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('challenger_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')
    
class FollowingChallengesView(generics.ListAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Challenge.objects.filter(
            (Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id)) &
            Q(challenger_note__author__id__in=following_ids),
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(challenger_note__author__id__in=blocking_ids) |
            Q(challenger_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('challenger_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('challenger_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class RelatedChallengesView(generics.ListAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        note_id = self.kwargs['note_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        queryset = Challenge.objects.filter(
            original_note_id=note_id,
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(challenger_note__author__id__in=blocking_ids) |
            Q(challenger_note__author__id__in=blocked_by_ids)
        )

        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('challenger_note__likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('challenger_note__dislikes')).order_by('-dislikes_count')

        return queryset.order_by('-created_at')

class ChallengeRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        challenge_requests = user.profile.challenge_requests.filter(pending=True)
        serializer = ChallengeSerializer(challenge_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ChallengesSentView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        challenges_sent = user.profile.challenges_sent.filter(pending=True)
        serializer = ChallengeSerializer(challenges_sent, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ChallengesDeclinedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        challenges_declined = user.profile.challenges_declined.filter(declined=True)
        serializer = ChallengeSerializer(challenges_declined, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActiveChallengesMadeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        active_challenges_made = user.profile.active_challenges_made.filter(accepted=True)
        serializer = ChallengeSerializer(active_challenges_made, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActiveChallengesReceivedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        active_challenges_received = user.profile.active_challenges_received.filter(accepted=True)
        serializer = ChallengeSerializer(active_challenges_received, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


### CHALLENGE ACTIONS ###
class AcceptChallengeView(APIView): # Called From Current User
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            current_time = timezone.now()
            challenge.pending = False
            challenge.accepted = True
            challenge.declined = False
            challenge.created_at = current_time  # Update the created_at of the challenge
            challenge.challenger_note.created_at = current_time  # Update the created_at of the challenger_note
            challenge.challenger_note.save()  # Save the updated challenger_note
            challenge.save()  # Save the updated challenge
            
            # Update challenge request list
            challenge.original_note.author.profile.challenge_requests.remove(challenge)
            challenge.original_note.author.profile.active_challenges_received.add(challenge)
            challenge.challenger_note.author.profile.active_challenges_made.add(challenge)
            challenge.challenger_note.author.profile.challenges_sent.remove(challenge)
            
            return Response({'status': 'accepted'}, status=status.HTTP_200_OK)
        except Challenge.DoesNotExist:
            return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DeclineChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            challenge.pending = False
            challenge.accepted = False
            challenge.declined = True
            challenge.save()
            
            # Update challenge request list
            challenge.original_note.author.profile.challenge_requests.remove(challenge)
            challenge.challenger_note.author.profile.challenges_sent.remove(challenge)
            challenge.challenger_note.author.profile.challenges_declined.add(challenge)         
            
            return Response({'status': 'declined'}, status=status.HTTP_200_OK)
        except Challenge.DoesNotExist:
            return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ResubmitChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            challenge.pending = True
            challenge.accepted = False
            challenge.declined = False
            
            if challenge.original_note.author.profile.auto_accept_challenges:
                current_time = timezone.now()
                challenge.pending = False
                challenge.accepted = True
                challenge.declined = False
                challenge.created_at = current_time
                challenge.challenger_note.created_at = current_time
                challenge.challenger_note.save()

                # Update challenge lists
                challenge.challenger_note.author.profile.challenges_declined.remove(challenge)
                challenge.original_note.author.profile.active_challenges_received.add(challenge)
                challenge.challenger_note.author.profile.active_challenges_made.add(challenge)
            else:
                challenge.challenger_note.author.profile.challenges_declined.remove(challenge)
                challenge.challenger_note.author.profile.challenges_sent.add(challenge)
                challenge.original_note.author.profile.challenge_requests.add(challenge)
                

            challenge.save()
            return Response({'status': 'resubmitted'}, status=status.HTTP_200_OK)
        except Challenge.DoesNotExist:
            return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DeleteChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            challenge.delete()
            return Response({'status': 'deleted'}, status=status.HTTP_200_OK)
        except Challenge.DoesNotExist:
            return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcceptAllChallengeRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        pending_challenges = user.profile.challenge_requests.filter(pending=True)
        current_time = timezone.now()

        for challenge in pending_challenges:
            challenge.pending = False
            challenge.accepted = True
            challenge.declined = False
            challenge.created_at = current_time
            challenge.challenger_note.created_at = current_time
            challenge.challenger_note.save()
            challenge.save()

            user.profile.challenge_requests.remove(challenge)
            user.profile.active_challenges_received.add(challenge)
            challenge.challenger_note.author.profile.active_challenges_made.add(challenge)
            challenge.challenger_note.author.profile.challenges_sent.remove(challenge)

        return Response({'status': 'all_accepted'}, status=status.HTTP_200_OK)


class DeclineAllChallengeRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        pending_challenges = user.profile.challenge_requests.filter(pending=True)

        for challenge in pending_challenges:
            challenge.pending = False
            challenge.accepted = False
            challenge.declined = True
            challenge.save()

            user.profile.challenge_requests.remove(challenge)
            challenge.challenger_note.author.profile.challenges_sent.remove(challenge)
            challenge.challenger_note.author.profile.challenges_declined.add(challenge)

        return Response({'status': 'all_declined'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def pick_original(request, challenge_id):
    try:
        challenge = Challenge.objects.get(id=challenge_id)
        user = request.user

        if user in challenge.challenger_picks.all():
            challenge.challenger_picks.remove(user)
        if user not in challenge.original_picks.all():
            challenge.original_picks.add(user)
        else:
            challenge.original_picks.remove(user)

        challenge.save()
        return Response({'original_picks': challenge.original_picks.count(), 'challenger_picks': challenge.challenger_picks.count()}, status=status.HTTP_200_OK)
    except Challenge.DoesNotExist:
        return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def pick_challenger(request, challenge_id):
    try:
        challenge = Challenge.objects.get(id=challenge_id)
        user = request.user

        if user in challenge.original_picks.all():
            challenge.original_picks.remove(user)
        if user not in challenge.challenger_picks.all():
            challenge.challenger_picks.add(user)
        else:
            challenge.challenger_picks.remove(user)

        challenge.save()
        return Response({'original_picks': challenge.original_picks.count(), 'challenger_picks': challenge.challenger_picks.count()}, status=status.HTTP_200_OK)
    except Challenge.DoesNotExist:
        return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_original_picks(request, challenge_id):
    try:
        challenge = Challenge.objects.get(id=challenge_id)
        users = challenge.original_picks.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Challenge.DoesNotExist:
        return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_challenger_picks(request, challenge_id):
    try:
        challenge = Challenge.objects.get(id=challenge_id)
        users = challenge.challenger_picks.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Challenge.DoesNotExist:
        return Response({'error': 'Challenge not found'}, status=status.HTTP_404_NOT_FOUND)

### COMBINED ###
class UserCombinedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        user = User.objects.get(id=user_id)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        notes = Note.objects.filter(author_id=user_id, is_challenger=False, is_subber=False)
        challenges = Challenge.objects.filter(
            Q(challenger_note__author_id=user_id),
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids)
        )
        subs = Sub.objects.filter(
            Q(sub_note__author_id=user_id)
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids)
        )

        all_posts = list(notes) + list(challenges) + list(subs)

        if sort_by == 'most_likes':
            all_posts.sort(key=lambda x: getattr(x, 'likes_count', 0), reverse=True)
        elif sort_by == 'most_dislikes':
            all_posts.sort(key=lambda x: getattr(x, 'dislikes_count', 0), reverse=True)
        else:
            all_posts.sort(key=lambda x: x.created_at, reverse=True)

        return all_posts

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializers = [get_serializer_for_instance(instance)(instance) for instance in page]
            return self.get_paginated_response([serializer.data for serializer in serializers])

        serializers = [get_serializer_for_instance(instance)(instance) for instance in queryset]
        return Response([serializer.data for serializer in serializers])

class AllCombinedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        notes = Note.objects.filter(
            Q(author__profile__privacy_flag=False) |
            Q(author__id__in=following_ids) |
            Q(author__id=user.id)
        ).exclude(
            Q(author__id__in=blocking_ids) |
            Q(author__id__in=blocked_by_ids)
        ).filter(is_challenger=False, is_subber=False)

        challenges = Challenge.objects.filter(
            (Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id) |
            Q(challenger_note__author__profile__privacy_flag=False) |
            Q(challenger_note__author__id__in=following_ids) |
            Q(challenger_note__author__id=user.id)),
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(challenger_note__author__id__in=blocking_ids) |
            Q(challenger_note__author__id__in=blocked_by_ids)
        )

        subs = Sub.objects.filter(
            Q(original_note__author__profile__privacy_flag=False) |
            Q(original_note__author__id__in=following_ids) |
            Q(original_note__author__id=user.id) |
            Q(sub_note__author__profile__privacy_flag=False) |
            Q(sub_note__author__id__in=following_ids) |
            Q(sub_note__author__id=user.id)
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids) |
            Q(sub_note__author__id__in=blocking_ids) |
            Q(sub_note__author__id__in=blocked_by_ids)
        )

        all_posts = list(notes) + list(challenges) + list(subs)

        if sort_by == 'most_likes':
            all_posts.sort(key=lambda x: getattr(x, 'likes_count', 0), reverse=True)
        elif sort_by == 'most_dislikes':
            all_posts.sort(key=lambda x: getattr(x, 'dislikes_count', 0), reverse=True)
        else:
            all_posts.sort(key=lambda x: x.created_at, reverse=True)

        return all_posts

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializers = [get_serializer_for_instance(instance)(instance) for instance in page]
            return self.get_paginated_response([serializer.data for serializer in serializers])

        serializers = [get_serializer_for_instance(instance)(instance) for instance in queryset]
        return Response([serializer.data for serializer in serializers])

class FollowingCombinedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        sort_by = self.request.query_params.get('sort_by', 'created_at')

        following_ids = user.profile.following.values_list('id', flat=True)
        blocking_ids = user.profile.blocking.values_list('id', flat=True)
        blocked_by_ids = user.profile.blocked_by.values_list('id', flat=True)

        notes = Note.objects.filter(author_id__in=following_ids, is_challenger=False, is_subber=False)
        challenges = Challenge.objects.filter(
            Q(challenger_note__author__id__in=following_ids),
            pending=False,
            accepted=True,
            declined=False
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids)
        )
        subs = Sub.objects.filter(
            Q(sub_note__author__id__in=following_ids)
        ).exclude(
            Q(original_note__author__id__in=blocking_ids) |
            Q(original_note__author__id__in=blocked_by_ids)
        )

        all_posts = list(notes) + list(challenges) + list(subs)

        if sort_by == 'most_likes':
            all_posts.sort(key=lambda x: getattr(x, 'likes_count', 0), reverse=True)
        elif sort_by == 'most_dislikes':
            all_posts.sort(key=lambda x: getattr(x, 'dislikes_count', 0), reverse=True)
        else:
            all_posts.sort(key=lambda x: x.created_at, reverse=True)

        return all_posts

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializers = [get_serializer_for_instance(instance)(instance) for instance in page]
            return self.get_paginated_response([serializer.data for serializer in serializers])

        serializers = [get_serializer_for_instance(instance)(instance) for instance in queryset]
        return Response([serializer.data for serializer in serializers])


### COMMENTS ###
class CommentCreate(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        note_id = self.kwargs['note_id']
        note = Note.objects.get(id=note_id)
        serializer.save(author=self.request.user, note=note)


### TEAMS ###
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


### BRACKET ###
class BracketViewSet(viewsets.ModelViewSet):
    queryset = Bracket.objects.all()
    serializer_class = BracketSerializer


### TOURNAMENT ###
class CreateTournamentView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.dict()
        print("Received data:", data)
        
        team_size = int(data.get('team_size', 16))  # Default to 16 if not specified
        print("Parsed team size:", team_size)
        
        teams_data = []

        for key, value in data.items():
            if key.startswith('teams['):
                index = int(key.split('[')[1].split(']')[0])
                field_name = key.split('][')[1][:-1]

                while len(teams_data) <= index:
                    teams_data.append({})

                teams_data[index][field_name] = value

        # Log the teams_data to inspect it
        print("Parsed teams data:", teams_data)

        # Remove any potential duplicate teams
        seen_teams = set()
        unique_teams_data = []
        for team in teams_data:
            team_identifier = (team['name'], team.get('logo'))
            if team_identifier not in seen_teams:
                seen_teams.add(team_identifier)
                unique_teams_data.append(team)

        # Log unique teams data
        print("Unique teams data:", unique_teams_data)

        data['teams'] = unique_teams_data
        serializer = TournamentSerializer(data=data)

        if serializer.is_valid():
            print("Serializer is valid")
            with transaction.atomic():
                tournament = serializer.save(author=request.user)
                print("Tournament saved:", tournament)

                # Create and save teams
                teams = Team.objects.bulk_create(
                    [Team(tournament=tournament, **team_data) for team_data in unique_teams_data]
                )
                print("Teams created:", teams)

                # Create actual bracket
                actual_bracket = Bracket.objects.create(
                    author=request.user,
                    tournament=tournament,
                    is_actual=True,
                    team_size=team_size
                )
                print("Actual bracket created:", actual_bracket)

                # Initialize lists with None values
                left_side_teams = [None] * (team_size // 2)
                right_side_teams = [None] * (team_size // 2)

                # Assign teams to the initialized lists
                for i, team in enumerate(teams[:team_size//2]):
                    left_side_teams[i] = {
                        "id": team.id,
                        "name": team.name,
                        "logo": team.logo.url if team.logo else None
                    }
                for i, team in enumerate(teams[team_size//2:team_size]):
                    right_side_teams[i] = {
                        "id": team.id,
                        "name": team.name,
                        "logo": team.logo.url if team.logo else None
                    }

                # Log the initialized teams for bracket
                print("Left side teams:", left_side_teams)
                print("Right side teams:", right_side_teams)

                # Assign lists to actual bracket JSON fields
                actual_bracket.left_side_round_of_16_teams = left_side_teams if team_size == 16 else []
                actual_bracket.right_side_round_of_16_teams = right_side_teams if team_size == 16 else []
                actual_bracket.left_side_quarter_finals = left_side_teams if team_size == 8 else []
                actual_bracket.right_side_quarter_finals = right_side_teams if team_size == 8 else []

                actual_bracket.save()
                print("Actual bracket saved with teams")

                tournament.actual_bracket = actual_bracket
                tournament.save()
                print("Tournament updated with actual bracket")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_prediction(self, request, pk=None):
        user = request.user
        data = request.data
        tournament_id = pk

        print("User:", user)
        print("Data received:", data)
        print("Tournament ID:", tournament_id)

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            print("Tournament found:", tournament)
        except Tournament.DoesNotExist:
            print("Tournament not found with ID:", tournament_id)
            return Response({'error': 'Tournament not found'}, status=404)

        bracket, created = Bracket.objects.get_or_create(
            author=user,
            tournament=tournament,
            is_actual=False  
        )
        print("Bracket:", bracket)
        print("Bracket created:", created)

        def get_team_data(team_list):
            print("Processing team list:", team_list)
            return [
                {
                    "id": team['id'],
                    "name": team['name'],
                    "logo": team['logo']
                } if team else None for team in team_list
            ]

        bracket.left_side_round_of_16_teams = get_team_data(data.get('left_side_round_of_16_teams', []))
        bracket.left_side_quarter_finals = get_team_data(data.get('left_side_quarter_finals', []))
        bracket.left_side_semi_finals = get_team_data(data.get('left_side_semi_finals', []))
        bracket.right_side_round_of_16_teams = get_team_data(data.get('right_side_round_of_16_teams', []))
        bracket.right_side_quarter_finals = get_team_data(data.get('right_side_quarter_finals', []))
        bracket.right_side_semi_finals = get_team_data(data.get('right_side_semi_finals', []))
        bracket.finals = get_team_data(data.get('finals', []))

        print("Bracket teams after processing:")
        print("Left side round of 16 teams:", bracket.left_side_round_of_16_teams)
        print("Left side quarter finals:", bracket.left_side_quarter_finals)
        print("Left side semi finals:", bracket.left_side_semi_finals)
        print("Right side round of 16 teams:", bracket.right_side_round_of_16_teams)
        print("Right side quarter finals:", bracket.right_side_quarter_finals)
        print("Right side semi finals:", bracket.right_side_semi_finals)
        print("Finals:", bracket.finals)

        winner_id = data.get('winner')
        if winner_id:
            bracket.winner_id = winner_id
            print("Winner ID set:", winner_id)

        team_size = data.get('team_size')
        if team_size is None:
            print("Error: team_size is required")
            return Response({'error': 'team_size is required'}, status=400)
        bracket.team_size = team_size
        print("Team size set:", team_size)

        bracket.save()
        print("Bracket saved:", bracket)

        tournament.predicted_brackets.add(bracket)
        tournament.save()
        print("Tournament updated with predicted bracket.")

        return Response({'status': 'prediction submitted', 'bracket': BracketSerializer(bracket).data})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_actual_bracket(self, request, pk=None):
        user = request.user
        data = request.data
        try:
            tournament = Tournament.objects.get(id=pk)
        except Tournament.DoesNotExist:
            return Response({'error': 'Tournament not found'}, status=404)

        if tournament.author != user:
            return Response({'error': 'Only the creator can update the actual bracket'}, status=403)

        actual_bracket = tournament.actual_bracket

        # Directly assign the lists to the JSON fields
        actual_bracket.left_side_round_of_16_teams = data.get('left_side_round_of_16_teams', [])
        actual_bracket.left_side_quarter_finals = data.get('left_side_quarter_finals', [])
        actual_bracket.left_side_semi_finals = data.get('left_side_semi_finals', [])
        actual_bracket.right_side_round_of_16_teams = data.get('right_side_round_of_16_teams', [])
        actual_bracket.right_side_quarter_finals = data.get('right_side_quarter_finals', [])
        actual_bracket.right_side_semi_finals = data.get('right_side_semi_finals', [])
        actual_bracket.finals = data.get('finals', [])

        winner_id = data.get('winner')
        if winner_id:
            actual_bracket.winner_id = winner_id

        actual_bracket.save()
        
        # Recalculate scores for all predicted brackets
        self.recalculate_scores(tournament)

        return Response({'status': 'actual bracket updated', 'bracket': BracketSerializer(actual_bracket).data})

    def recalculate_scores(self, tournament):
        actual_bracket = tournament.actual_bracket
        point_system = json.loads(tournament.point_system)  # Parse JSON string to list
        point_system = list(map(int, point_system))  # Convert list items to integers

        for bracket in tournament.predicted_brackets.all():
            score = 0

            if tournament.team_size == 16:
                # Quarter finals
                score += self.calculate_round_score(bracket.left_side_quarter_finals, actual_bracket.left_side_quarter_finals, point_system[0])
                score += self.calculate_round_score(bracket.right_side_quarter_finals, actual_bracket.right_side_quarter_finals, point_system[0])

                # Semi finals
                score += self.calculate_round_score(bracket.left_side_semi_finals, actual_bracket.left_side_semi_finals, point_system[1])
                score += self.calculate_round_score(bracket.right_side_semi_finals, actual_bracket.right_side_semi_finals, point_system[1])
                
            elif tournament.team_size == 8:
                # Semi finals
                score += self.calculate_round_score(bracket.left_side_semi_finals, actual_bracket.left_side_semi_finals, point_system[1])
                score += self.calculate_round_score(bracket.right_side_semi_finals, actual_bracket.right_side_semi_finals, point_system[1])

            # Finals
            score += self.calculate_round_score(bracket.finals, actual_bracket.finals, point_system[2])

            # Winner
            if bracket.winner and actual_bracket.winner and bracket.winner.id == actual_bracket.winner.id:
                score += point_system[3]

            bracket.score = score if score != 0 else 0
            bracket.save()

    def calculate_round_score(self, predicted_round, actual_round, points_per_correct_prediction):
        score = 0
        for predicted, actual in zip(predicted_round, actual_round):
            if predicted and actual and predicted['id'] == actual['id']:
                score += points_per_correct_prediction
        return score