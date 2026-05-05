# accounts/views.py

from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random

from .models import User

# ==================== FUNÇÕES AUXILIARES ====================

def gerar_codigo_2fa():
    """Gera código 2FA de 6 dígitos"""
    return str(random.randint(100000, 999999))

def get_tokens_for_user(user):
    """Gera tokens JWT para o usuário"""
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

# ==================== VIEWS DE AUTENTICAÇÃO ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login do usuário"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({'error': 'Email e senha são obrigatórios'}, status=400)
        
        # Buscar usuário
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        # Verificar conta bloqueada
        if user.is_locked():
            return Response({'error': 'Conta bloqueada. Tente em 15 minutos.'}, status=403)
        
        # Verificar login permitido
        if not user.can_login:
            return Response({'error': 'Login não permitido.'}, status=403)
        
        # Verificar senha
        if not user.check_password(password):
            user.increment_login_attempts()
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        # Resetar tentativas
        user.reset_login_attempts()
        
        # Admin - login direto
        if user.role == 'ADMIN':
            return Response(get_tokens_for_user(user))
        
        # 2FA ativado - gerar código
        if user.two_factor_enabled:
            codigo = gerar_codigo_2fa()
            user.two_factor_code = codigo
            user.two_factor_expires = timezone.now() + timedelta(minutes=10)
            user.save()
            
            # Retornar código na resposta
            return Response({
                'require_2fa': True,
                'email': user.email,
                'message': f'Código: {codigo}',
                'code': codigo
            })
        
        # Login sem 2FA
        return Response(get_tokens_for_user(user))
        
    except Exception as e:
        return Response({'error': 'Erro interno'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa_view(request):
    """Verificar código 2FA"""
    try:
        email = request.data.get('email')
        codigo = request.data.get('code')
        
        if not email or not codigo:
            return Response({'error': 'Email e código obrigatórios'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Usuário não encontrado'}, status=404)
        
        if not user.two_factor_code:
            return Response({'error': 'Nenhum código solicitado. Faça login novamente.'}, status=400)
        
        if user.two_factor_expires and timezone.now() > user.two_factor_expires:
            user.two_factor_code = None
            user.two_factor_expires = None
            user.save()
            return Response({'error': 'Código expirado. Faça login novamente.'}, status=400)
        
        if user.two_factor_code != codigo:
            return Response({'error': 'Código inválido'}, status=400)
        
        # Código correto
        user.two_factor_code = None
        user.two_factor_expires = None
        user.save()
        
        return Response(get_tokens_for_user(user))
        
    except Exception as e:
        return Response({'error': 'Erro interno'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registrar novo estudante"""
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        curso = request.data.get('curso', '')
        classe = request.data.get('classe', '')
        ano_ingresso = request.data.get('ano_ingresso', None)
        
        if not username or not email or not password:
            return Response({'error': 'Username, email e senha obrigatórios'}, status=400)
        
        if password != password2:
            return Response({'error': 'Senhas não coincidem'}, status=400)
        
        if len(password) < 8:
            return Response({'error': 'Senha deve ter 8+ caracteres'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email já registrado'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username já em uso'}, status=400)
        
        user = User.objects.create(
            username=username,
            email=email,
            role='ESTUDANTE',
            first_name=first_name,
            last_name=last_name,
            curso=curso,
            classe=classe,
            ano_ingresso=ano_ingresso,
            two_factor_enabled=True,
            is_active=True,
            can_login=True,
        )
        user.set_password(password)
        user.save()
        
        return Response(get_tokens_for_user(user), status=201)
        
    except Exception as e:
        return Response({'error': 'Erro interno'}, status=500)


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
        'nome': user.get_full_name() or user.username,
        'curso': user.curso,
        'classe': user.classe,
        'ano_ingresso': user.ano_ingresso,
        'two_factor_enabled': user.two_factor_enabled,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logout realizado'})
    except:
        return Response({'message': 'Logout realizado'})
