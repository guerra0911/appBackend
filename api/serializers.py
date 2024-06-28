from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Note, Profile, Comment, Tournament, Team, Bracket
import re
import uuid
import os

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['rating', 'following', 'image']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'confirm_password', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9._]{1,25}$', value):
            raise serializers.ValidationError(
                "Username must be between 1 and 25 characters and can only contain letters, numbers, periods, and underscores."
            )
        return value

    def validate_password(self, value):
        if len(value) < 6 or not re.search(r'\d', value):
            raise serializers.ValidationError(
                "Password must be at least 6 characters long and contain at least one number."
            )
        return value

    def validate(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        validated_data.pop('confirm_password', None)
        user = User.objects.create_user(**validated_data)
        if profile_data:
            Profile.objects.update_or_create(user=user, defaults=profile_data)
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        validated_data.pop('confirm_password', None)

        instance.username = validated_data.get('username', instance.username)
        instance.save()

        if profile_data:
            profile = instance.profile
            if 'image' in profile_data:
                profile.image = profile_data['image']
            profile.save()

            # Print image details without using `path`
            if 'image' in profile_data:
                print("Profile image updated to:", profile.image.url)
                print("Image details - Name:", profile.image.name)
                print("Image details - Size:", profile.image.size)

        return instance
    
class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    
    class Meta:
        model = Comment
        fields = ['id', 'note', 'author', 'content', 'created_at']
        extra_kwargs = {'note': {'write_only': True}}

class NoteSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes = serializers.StringRelatedField(many=True, read_only=True)
    dislikes = serializers.StringRelatedField(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Note
        fields = ["id", "content", "created_at", "author","likes", "dislikes", "comments"]
        extra_kwargs = {"author": {"read_only": True}}

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'logo']

class BracketSerializer(serializers.ModelSerializer):
    left_side_round_of_16_teams = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    left_side_quarter_finals = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    left_side_semi_finals = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    finals = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    right_side_semi_finals = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    right_side_quarter_finals = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    right_side_round_of_16_teams = serializers.ListField(
        child=serializers.DictField(allow_null=True), required=False
    )
    winner = TeamSerializer(allow_null=True)  # Ensure winner is serialized as a full object

    class Meta:
        model = Bracket
        fields = [
            'id', 'author', 'is_actual', 'left_side_round_of_16_teams',
            'left_side_quarter_finals', 'left_side_semi_finals', 'finals',
            'right_side_semi_finals', 'right_side_quarter_finals',
            'right_side_round_of_16_teams', 'winner', 'score'
        ]


class TournamentSerializer(serializers.ModelSerializer):
    teams = TeamSerializer(many=True, required=False)
    predicted_brackets = BracketSerializer(many=True, read_only=True)
    actual_bracket = BracketSerializer(read_only=True)

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'banner', 'logo', 'point_system', 'correct_score_bonus', 'winner_reward', 'loser_forfeit', 'teams', 'author', 'predicted_brackets', 'actual_bracket']

    def create(self, validated_data):
        teams_data = validated_data.pop('teams', [])
        banner = validated_data.pop('banner', None)
        logo = validated_data.pop('logo', None)
        
        tournament = Tournament.objects.create(**validated_data)
        
        if banner:
            tournament.banner = banner
        if logo:
            tournament.logo = logo
        tournament.save()

        for team_data in teams_data:
            Team.objects.create(tournament=tournament, **team_data)
        return tournament


