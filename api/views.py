from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics, status, viewsets
from .serializers import UserSerializer, NoteSerializer, CommentSerializer, ProfileSerializer, TournamentSerializer, TeamSerializer, BracketSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Note, Profile, Comment, Tournament, Team, Bracket
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.response import Response
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

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

class BracketViewSet(viewsets.ModelViewSet):
    queryset = Bracket.objects.all()
    serializer_class = BracketSerializer

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_prediction(self, request, pk=None):
        user = request.user
        data = request.data
        tournament_id = data.get('tournament_id')

        if not tournament_id:
            return Response({'error': 'Tournament ID is required'}, status=400)

        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({'error': 'Tournament not found'}, status=404)

        # Check if the user already has a prediction for this tournament
        bracket, created = Bracket.objects.get_or_create(
            author=user,
            tournament=tournament,
            defaults={'author': user, 'tournament': tournament}
        )
        
        # If bracket already exists, clear its many-to-many fields
        if not created:
            bracket.left_side_round_of_16_teams.clear()
            bracket.left_side_quarter_finals.clear()
            bracket.left_side_semi_finals.clear()
            bracket.right_side_round_of_16_teams.clear()
            bracket.right_side_quarter_finals.clear()
            bracket.right_side_semi_finals.clear()
            bracket.finals.clear()

        # Helper function to extract IDs from the team objects
        def get_team_ids(team_list):
            return [team['id'] for team in team_list if team]

        # Set the new prediction data
        bracket.left_side_round_of_16_teams.set(get_team_ids(data.get('left_side_round_of_16_teams', [])))
        bracket.left_side_quarter_finals.set(get_team_ids(data.get('left_side_quarter_finals', [])))
        bracket.left_side_semi_finals.set(get_team_ids(data.get('left_side_semi_finals', [])))
        bracket.right_side_round_of_16_teams.set(get_team_ids(data.get('right_side_round_of_16_teams', [])))
        bracket.right_side_quarter_finals.set(get_team_ids(data.get('right_side_quarter_finals', [])))
        bracket.right_side_semi_finals.set(get_team_ids(data.get('right_side_semi_finals', [])))
        bracket.finals.set(get_team_ids(data.get('finals', [])))
        
        winner_id = data.get('winner')
        if winner_id:
            bracket.winner_id = winner_id

        bracket.save()

        # Ensure the bracket is associated with the tournament's predicted_brackets
        tournament.predicted_brackets.add(bracket)
        tournament.save()
        
        return Response({'status': 'prediction submitted', 'bracket': BracketSerializer(bracket).data})

    
class CreateTournamentView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.dict()  # Convert QueryDict to regular dict
        teams_data = []
        
        for key, value in data.items():
            if key.startswith('teams['):
                index = int(key.split('[')[1].split(']')[0])
                field_name = key.split('][')[1][:-1]
                
                while len(teams_data) <= index:
                    teams_data.append({})
                
                teams_data[index][field_name] = value
        
        data['teams'] = teams_data
        serializer = TournamentSerializer(data=data)

        if serializer.is_valid():
            tournament = serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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