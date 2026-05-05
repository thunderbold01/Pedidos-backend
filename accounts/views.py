# accounts/views.py - REGISTRO PENDENTE DE APROVAÇÃO

from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import re

from .models import User

# ==================== FUNÇÕES AUXILIARES ====================

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

def sanitizar_input(texto):
    if not texto:
        return texto
    texto = re.sub(r'<[^>]*>', '', texto)
    texto = re.sub(r'[<>\"\';]', '', texto)
    return texto.strip()

# ==================== VIEWS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login - apenas contas ATIVAS e APROVADAS"""
    try:
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        
        if not email or not password:
            return Response({'error': 'Email e senha são obrigatórios'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        # Verificar se conta está ATIVA (aprovada pelo admin)
        if not user.is_active:
            return Response({'error': 'Conta pendente de aprovação. Aguarde o administrador.'}, status=403)
        
        # Verificar se pode fazer login
        if not user.can_login:
            return Response({'error': 'Login não autorizado. Contate o administrador.'}, status=403)
        
        if user.is_locked():
            return Response({'error': 'Conta bloqueada. Tente mais tarde.'}, status=403)
        
        # Verificar senha
        if not user.check_password(password):
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        user.last_login = timezone.now()
        user.save()
        
        return Response(get_tokens_for_user(user))
        
    except Exception as e:
        return Response({'error': 'Erro interno'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registro - conta criada INATIVA, espera aprovação do ADMIN"""
    try:
        username = sanitizar_input(request.data.get('username', ''))
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        password2 = request.data.get('password2', '')
        first_name = sanitizar_input(request.data.get('first_name', ''))
        last_name = sanitizar_input(request.data.get('last_name', ''))
        curso = sanitizar_input(request.data.get('curso', ''))
        classe = sanitizar_input(request.data.get('classe', ''))
        
        if not username or not email or not password:
            return Response({'error': 'Usuário, email e senha são obrigatórios'}, status=400)
        
        if password != password2:
            return Response({'error': 'Senhas não coincidem'}, status=400)
        
        if len(password) < 6:
            return Response({'error': 'Senha deve ter 6+ caracteres'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email já registrado'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Usuário já existe'}, status=400)
        
        # Criar usuário INATIVO - espera aprovação do ADMIN
        user = User.objects.create(
            username=username,
            email=email,
            role='ESTUDANTE',
            first_name=first_name,
            last_name=last_name,
            curso=curso,
            classe=classe,
            is_active=False,      # INATIVO - precisa de aprovação
            can_login=False,       # Não pode fazer login
            email_verified=False,
        )
        user.set_password(password)
        user.save()
        
        return Response({
            'message': 'Conta criada com sucesso! Aguarde a aprovação do administrador.',
            'status': 'pending'
        }, status=201)
        
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
        'is_active': user.is_active,
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
