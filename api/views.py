from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics, status
from .serializers import UserSerializer, NoteSerializer, CommentSerializer, ProfileSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Note, Profile, Comment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from django.db.models import Count

import logging

logger = logging.getLogger(__name__)

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
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
        
# views.py
class UpdateUserProfileView(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        data = request.data
        print("Received data: %s", data)  # Debug log

        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            print("Profile updated for user: %s", user.id)  # Debug log
            return Response(serializer.data, status=200)
        else:
            print("Error updating profile: %s", serializer.errors)  # Debug log
            return Response(serializer.errors, status=400)


class NoteListCreate(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)
    
    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(author=self.request.user)
        else:
            print(serializer.errors)
            
class UserNotesView(generics.ListAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        queryset = Note.objects.filter(author_id=user_id)
        
        if sort_by == 'most_likes':
            return queryset.annotate(likes_count=Count('likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return queryset.annotate(dislikes_count=Count('dislikes')).order_by('-dislikes_count')
        
        return queryset.order_by('-created_at')

class FollowedUsersNotesView(generics.ListAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        followed_users = user.profile.following.all()
        return Note.objects.filter(author__profile__in=followed_users)

class AllNotesView(generics.ListAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        if sort_by == 'most_likes':
            return Note.objects.all().annotate(likes_count=Count('likes')).order_by('-likes_count')
        elif sort_by == 'most_dislikes':
            return Note.objects.all().annotate(dislikes_count=Count('dislikes')).order_by('-dislikes_count')
        return Note.objects.all().order_by('-created_at')


class NoteDelete(generics.DestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)

class CommentCreate(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        note_id = self.kwargs['note_id']
        note = Note.objects.get(id=note_id)
        serializer.save(author=self.request.user, note=note)
        
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