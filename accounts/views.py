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
    texto = re.sub(r'<[^>]*>', '', texto)
    texto = re.sub(r'[<>\"\';]', '', texto)
    return texto.strip()

# ==================== VIEWS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login - apenas email e senha"""
    try:
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        
        if not email or not password:
            return Response({'error': 'Email e senha são obrigatórios'}, status=400)
        
        if not validar_email(email):
            return Response({'error': 'Formato de email inválido'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        if not user.is_active:
            return Response({'error': 'Conta desativada. Verifique seu email.'}, status=403)
        
        if user.is_locked():
            tempo = (user.locked_until - timezone.now()).seconds // 60
            return Response({'error': f'Conta bloqueada. Tente em {tempo} min.'}, status=403)
        
        if not user.can_login:
            return Response({'error': 'Login não permitido'}, status=403)
        
        if not user.check_password(password):
            user.increment_login_attempts()
            return Response({'error': 'Email ou senha inválidos'}, status=401)
        
        user.reset_login_attempts()
        user.last_login = timezone.now()
        user.save()
        
        return Response(get_tokens_for_user(user))
        
    except Exception as e:
        print(f'Erro login: {e}')
        return Response({'error': 'Erro interno'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registro com 2FA - envia código por email"""
    try:
        username = sanitizar_input(request.data.get('username', ''))
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        password2 = request.data.get('password2', '')
        first_name = sanitizar_input(request.data.get('first_name', ''))
        last_name = sanitizar_input(request.data.get('last_name', ''))
        curso = sanitizar_input(request.data.get('curso', ''))
        classe = sanitizar_input(request.data.get('classe', ''))
        
        # Validações
        if not username or not email or not password:
            return Response({'error': 'Usuário, email e senha são obrigatórios'}, status=400)
        
        if len(username) < 3:
            return Response({'error': 'Usuário deve ter 3+ caracteres'}, status=400)
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return Response({'error': 'Usuário: apenas letras, números e _'}, status=400)
        
        if not validar_email(email):
            return Response({'error': 'Email inválido'}, status=400)
        
        if password != password2:
            return Response({'error': 'Senhas não coincidem'}, status=400)
        
        valida, msg = validar_senha(password)
        if not valida:
            return Response({'error': msg}, status=400)
        
        if len(first_name) < 2 or len(last_name) < 2:
            return Response({'error': 'Nome e sobrenome obrigatórios'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email já registrado'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Usuário já existe'}, status=400)
        
        # Criar usuário INATIVO
        user = User.objects.create(
            username=username,
            email=email,
            role='ESTUDANTE',
            first_name=first_name,
            last_name=last_name,
            curso=curso,
            classe=classe,
            two_factor_enabled=True,
            is_active=False,
            can_login=False,
            email_verified=False,
        )
        user.set_password(password)
        user.save()
        
        # Gerar código 2FA
        codigo = gerar_codigo_2fa()
        user.two_factor_code = codigo
        user.two_factor_expires = timezone.now() + timedelta(minutes=10)
        user.save()
        
        # Enviar email
        try:
            send_mail(
                '🔐 Código de Verificação - Sistema de Pedidos',
                f'Olá {first_name}!\n\n'
                f'Seu código de verificação é: {codigo}\n\n'
                f'Digite este código para ativar sua conta.\n'
                f'Válido por 10 minutos.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            print(f'✅ Email enviado para {email}')
        except Exception as e:
            print(f'❌ Erro email: {e}')
        
        return Response({
            'require_2fa': True,
            'email': user.email,
            'message': f'Código enviado para {email}',
            'code': codigo
        }, status=201)
        
    except Exception as e:
        print(f'Erro registro: {e}')
        return Response({'error': 'Erro interno'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa_view(request):
    """Verificar código 2FA e ativar conta"""
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
            return Response({'error': 'Nenhum código solicitado'}, status=400)
        
        if user.two_factor_expires and timezone.now() > user.two_factor_expires:
            user.two_factor_code = None
            user.two_factor_expires = None
            user.save()
            return Response({'error': 'Código expirado. Registre-se novamente.'}, status=400)
        
        if user.two_factor_code != codigo:
            return Response({'error': 'Código inválido'}, status=400)
        
        # ATIVAR CONTA
        user.two_factor_code = None
        user.two_factor_expires = None
        user.is_active = True
        user.can_login = True
        user.email_verified = True
        user.save()
        
        tokens = get_tokens_for_user(user)
        return Response({
            **tokens,
            'message': 'Conta ativada com sucesso!'
        })
        
    except Exception as e:
        print(f'Erro 2FA: {e}')
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
