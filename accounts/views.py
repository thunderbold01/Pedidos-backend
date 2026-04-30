from django.shortcuts import render
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
import json

from .models import User

# Função para gerar código 2FA
def gerar_codigo_2fa():
    return str(random.randint(100000, 999999))

# Função para enviar email com código 2FA
def enviar_email_2fa(email, codigo):
    try:
        send_mail(
            'Código de Verificação 2FA',
            f'Seu código de acesso é: {codigo}\nVálido por 10 minutos.',
            'noreply@escola.com',
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        # Em desenvolvimento, apenas mostra no console
        print(f"\n=== CÓDIGO 2FA: {codigo} ===\n")
        return True

# Função para gerar tokens JWT
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'nome': user.get_full_name(),
        }
    }

# ========== VIEWS DE AUTENTICAÇÃO ==========

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login do usuário"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email e senha são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Autenticar usuário
        user = authenticate(username=email, password=password)
        
        if not user:
            return Response({
                'error': 'Email ou senha inválidos'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Se 2FA está ativado
        if user.two_factor_enabled:
            codigo = gerar_codigo_2fa()
            user.two_factor_code = codigo
            user.two_factor_expires = timezone.now() + timedelta(minutes=10)
            user.save()
            
            # Enviar email
            enviar_email_2fa(user.email, codigo)
            
            return Response({
                'require_2fa': True,
                'email': user.email,
                'message': 'Código 2FA enviado para seu email'
            })
        
        # Login normal (sem 2FA)
        tokens = get_tokens_for_user(user)
        return Response(tokens)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa_view(request):
    """Verificar código 2FA"""
    try:
        email = request.data.get('email')
        codigo = request.data.get('code')
        
        if not email or not codigo:
            return Response({
                'error': 'Email e código são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'Usuário não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar código
        if not user.two_factor_code:
            return Response({
                'error': 'Nenhum código 2FA solicitado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.two_factor_expires:
            return Response({
                'error': 'Código 2FA expirado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if user.two_factor_code != codigo:
            return Response({
                'error': 'Código 2FA inválido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Código correto - limpar e gerar tokens
        user.two_factor_code = None
        user.two_factor_expires = None
        user.save()
        
        tokens = get_tokens_for_user(user)
        return Response(tokens)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registrar novo usuário (apenas estudantes)"""
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        curso = request.data.get('curso', '')
        classe = request.data.get('classe', '')
        
        if not username or not email or not password:
            return Response({
                'error': 'Username, email e senha são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar se email já existe
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Este email já está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar usuário
        user = User.objects.create(
            username=username,
            email=email,
            role='ESTUDANTE',
            curso=curso,
            classe=classe
        )
        user.set_password(password)
        user.save()
        
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_me(request):
    """Dados do usuário logado"""
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'nome': user.get_full_name(),
        'curso': user.curso,
        'classe': user.classe,
        'ano_ingresso': user.ano_ingresso,
        'two_factor_enabled': user.two_factor_enabled,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout do usuário"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logout realizado com sucesso'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)