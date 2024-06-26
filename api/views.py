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
from django.db import transaction
import json

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
        print("Received data:", data)  # Debug log

        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            print("Profile updated for user:", user.id)  # Debug log
            return Response(serializer.data, status=200)
        else:
            print("Error updating profile:", serializer.errors)  # Debug log
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