# accounts/views.py

from django.shortcuts import render
from django.contrib.auth import authenticate
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
import json

from .models import User

# ==================== FUNÇÕES AUXILIARES ====================

def gerar_codigo_2fa():
    """Gera código 2FA de 6 dígitos"""
    return str(random.randint(100000, 999999))

def enviar_email_2fa(email, codigo):
    """Envia email com código 2FA"""
    try:
        send_mail(
            subject='🔐 Código de Verificação - Sistema de Pedidos',
            message=f'Seu código de acesso é: {codigo}\n\nVálido por 10 minutos.\n\nNão compartilhe este código com ninguém.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f"✅ Email 2FA enviado para {email}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        print(f"📧 CÓDIGO 2FA ({email}): {codigo}")
        return True  # Retorna True mesmo com erro para não quebrar o fluxo

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
            return Response({
                'error': 'Email e senha são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Buscar usuário
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'Email ou senha inválidos'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verificar conta bloqueada
        if user.is_locked():
            return Response({
                'error': 'Conta bloqueada. Tente novamente em 15 minutos.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar se pode fazer login
        if not user.can_login:
            return Response({
                'error': 'Login não permitido para esta conta.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Autenticar
        user = authenticate(username=email, password=password)
        
        if not user:
            try:
                user_temp = User.objects.get(email=email)
                user_temp.increment_login_attempts()
            except:
                pass
            return Response({
                'error': 'Email ou senha inválidos'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Resetar tentativas
        user.reset_login_attempts()
        
        # Admin faz login direto, sem 2FA
        if user.role == 'ADMIN':
            tokens = get_tokens_for_user(user)
            return Response(tokens)
        
        # Se 2FA está ativado
        if user.two_factor_enabled:
            codigo = gerar_codigo_2fa()
            user.two_factor_code = codigo
            user.two_factor_expires = timezone.now() + timedelta(minutes=10)
            user.save()
            
            # Enviar email com código
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
        print(f"❌ Erro no login: {e}")
        return Response({
            'error': 'Erro interno do servidor'
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
        
        # Verificar se existe código 2FA pendente
        if not user.two_factor_code:
            return Response({
                'error': 'Nenhum código 2FA solicitado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar expiração
        if timezone.now() > user.two_factor_expires:
            user.two_factor_code = None
            user.two_factor_expires = None
            user.save()
            return Response({
                'error': 'Código 2FA expirado. Faça login novamente.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar código
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
        print(f"❌ Erro na verificação 2FA: {e}")
        return Response({
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Registrar novo usuário (apenas estudantes)"""
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
        
        # Validações
        if not username or not email or not password:
            return Response({
                'error': 'Username, email e senha são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if password != password2:
            return Response({
                'error': 'As senhas não coincidem'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(password) < 8:
            return Response({
                'error': 'A senha deve ter pelo menos 8 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Este email já está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Este nome de usuário já está em uso'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar usuário
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
        
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"❌ Erro no registro: {e}")
        return Response({
            'error': 'Erro interno do servidor'
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
        'nome': user.get_full_name() or user.username,
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
