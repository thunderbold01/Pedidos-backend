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
import re

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

def validar_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_senha(password):
    """Valida força da senha"""
    if len(password) < 8:
        return False, 'A senha deve ter pelo menos 8 caracteres'
    if not re.search(r'[A-Z]', password):
        return False, 'A senha deve conter pelo menos uma letra maiúscula'
    if not re.search(r'[a-z]', password):
        return False, 'A senha deve conter pelo menos uma letra minúscula'
    if not re.search(r'[0-9]', password):
        return False, 'A senha deve conter pelo menos um número'
    return True, ''

def sanitizar_input(texto):
    """Remove caracteres perigosos para prevenir injection"""
    if not texto:
        return texto
    # Remove tags HTML e scripts
    texto = re.sub(r'<[^>]*>', '', texto)
    texto = re.sub(r'[<>\"\';]', '', texto)
    return texto.strip()

# ==================== VIEWS SEGURAS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login seguro - apenas email e senha, sem 2FA"""
    try:
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        
        # Validações de segurança
        if not email or not password:
            return Response({'error': 'Email e senha são obrigatórios'}, status=400)
        
        if not validar_email(email):
            return Response({'error': 'Formato de email inválido'}, status=400)
        
        if len(password) > 128:
            return Response({'error': 'Senha muito longa'}, status=400)
        
        # Buscar usuário
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        # Verificações de conta
        if not user.is_active:
            return Response({'error': 'Conta desativada'}, status=403)
        
        if user.is_locked():
            tempo_restante = (user.locked_until - timezone.now()).seconds // 60
            return Response({
                'error': f'Conta bloqueada. Tente novamente em {tempo_restante} minutos.'
            }, status=403)
        
        if not user.can_login:
            return Response({'error': 'Login não permitido para esta conta'}, status=403)
        
        # Verificar senha
        if not user.check_password(password):
            user.increment_login_attempts()
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        # Login bem-sucedido
        user.reset_login_attempts()
        user.last_login = timezone.now()
        user.save()
        
        return Response(get_tokens_for_user(user))
        
    except Exception as e:
        print(f'Erro no login: {e}')
        return Response({'error': 'Erro interno do servidor'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registro seguro com validações anti-injection"""
    try:
        # Sanitizar inputs
        username = sanitizar_input(request.data.get('username', ''))
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        password2 = request.data.get('password2', '')
        first_name = sanitizar_input(request.data.get('first_name', ''))
        last_name = sanitizar_input(request.data.get('last_name', ''))
        curso = sanitizar_input(request.data.get('curso', ''))
        classe = sanitizar_input(request.data.get('classe', ''))
        
        # Validações de campos obrigatórios
        if not username or not email or not password:
            return Response({'error': 'Usuário, email e senha são obrigatórios'}, status=400)
        
        # Validar username
        if len(username) < 3:
            return Response({'error': 'Usuário deve ter pelo menos 3 caracteres'}, status=400)
        if len(username) > 30:
            return Response({'error': 'Usuário muito longo (máx. 30 caracteres)'}, status=400)
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return Response({'error': 'Usuário deve conter apenas letras, números e underscore'}, status=400)
        
        # Validar email
        if not validar_email(email):
            return Response({'error': 'Formato de email inválido'}, status=400)
        
        # Validar senha
        if password != password2:
            return Response({'error': 'As senhas não coincidem'}, status=400)
        
        senha_valida, msg = validar_senha(password)
        if not senha_valida:
            return Response({'error': msg}, status=400)
        
        # Validar nomes
        if len(first_name) < 2:
            return Response({'error': 'Nome muito curto'}, status=400)
        if len(last_name) < 2:
            return Response({'error': 'Sobrenome muito curto'}, status=400)
        
        # Verificar se email já existe
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Este email já está registrado'}, status=400)
        
        # Verificar se username já existe
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Este nome de usuário já está em uso'}, status=400)
        
        # Criar usuário
        user = User.objects.create(
            username=username,
            email=email,
            role='ESTUDANTE',
            first_name=first_name,
            last_name=last_name,
            curso=curso,
            classe=classe,
            two_factor_enabled=False,  # 2FA desativado por padrão
            is_active=True,
            can_login=True,
            email_verified=False,
        )
        user.set_password(password)
        user.save()
        
        # Gerar token e retornar
        tokens = get_tokens_for_user(user)
        return Response({
            **tokens,
            'message': 'Conta criada com sucesso!'
        }, status=201)
        
    except Exception as e:
        print(f'Erro no registro: {e}')
        return Response({'error': 'Erro interno do servidor'}, status=500)


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
    """Logout seguro"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logout realizado com sucesso'})
    except:
        return Response({'message': 'Logout realizado'})
