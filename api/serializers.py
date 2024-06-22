from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Note, Profile, Comment

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['rating', 'following', 'image']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        user = User.objects.create_user(**validated_data)
        if profile_data:
            Profile.objects.update_or_create(user=user, defaults=profile_data)
        return user
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        instance.username = validated_data.get('username', instance.username)
        instance.save()
        if profile_data:
            Profile.objects.update_or_create(user=instance, defaults=profile_data)
        return instance

class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    
    class Meta:
        model = Comment
        fields = ['id', 'note', 'author', 'content', 'created_at']
        extra_kwargs = {'note': {'write_only': True}}

class NoteSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    likes = serializers.StringRelatedField(many=True, read_only=True)
    dislikes = serializers.StringRelatedField(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Note
        fields = ["id", "content", "created_at", "author","likes", "dislikes", "comments"]
        extra_kwargs = {"author": {"read_only": True}}

    