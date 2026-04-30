from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from .models import User
import re

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'role', 'curso', 'classe', 'ano_ingresso', 'two_factor_enabled']
        read_only_fields = ['id', 'role']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 
                  'last_name', 'curso', 'classe', 'ano_ingresso']
    
    def validate_email(self, value):
        """Valida email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email já está registado.")
        return value
    
    def validate_password(self, value):
        """Valida força da senha"""
        if len(value) < 8:
            raise serializers.ValidationError("A senha deve ter pelo menos 8 caracteres.")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("A senha deve conter pelo menos uma letra maiúscula.")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("A senha deve conter pelo menos uma letra minúscula.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("A senha deve conter pelo menos um número.")
        return value
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "As senhas não coincidem."})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User.objects.create(
            role='ESTUDANTE',  # Sempre ESTUDANTE
            two_factor_enabled=True,  # 2FA sempre ativo
            **validated_data
        )
        user.set_password(password)
        user.save()
        
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

class TwoFactorSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=6, min_length=6)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])