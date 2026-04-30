from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import pyotp
import secrets

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('DIRECAO', 'Direção'),
        ('DITE', 'DITE'),
        ('ESTUDANTE', 'Estudante'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ESTUDANTE')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    curso = models.CharField(max_length=100, blank=True, null=True)
    classe = models.CharField(max_length=50, blank=True, null=True)
    ano_ingresso = models.IntegerField(null=True, blank=True)
    foto = models.ImageField(upload_to='fotos/', null=True, blank=True)
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=True)  # Sempre ativo para estudantes
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    two_factor_code = models.CharField(max_length=6, blank=True, null=True)
    two_factor_expires = models.DateTimeField(null=True, blank=True)
    
    # Segurança
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    # Datas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def generate_2fa_code(self):
        """Gera código 2FA seguro"""
        if not self.two_factor_secret:
            self.two_factor_secret = pyotp.random_base32()
        
        totp = pyotp.TOTP(self.two_factor_secret, interval=600)  # 10 minutos
        code = totp.now()
        
        self.two_factor_code = code
        self.two_factor_expires = timezone.now() + timedelta(minutes=10)
        self.save()
        
        return code
    
    def verify_2fa_code(self, code):
        """Verifica código 2FA"""
        if not self.two_factor_code or not self.two_factor_expires:
            return False
        
        if timezone.now() > self.two_factor_expires:
            self.two_factor_code = None
            self.two_factor_expires = None
            self.save()
            return False
        
        if self.two_factor_code != code:
            return False
        
        # Código correto - limpar
        self.two_factor_code = None
        self.two_factor_expires = None
        self.save()
        
        return True
    
    def is_locked(self):
        """Verifica se conta está bloqueada"""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def increment_login_attempts(self):
        """Incrementa tentativas de login falhadas"""
        self.login_attempts += 1
        
        # Bloquear após 5 tentativas
        if self.login_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=15)
            self.login_attempts = 0
        
        self.save()
    
    def reset_login_attempts(self):
        """Reseta tentativas de login"""
        self.login_attempts = 0
        self.locked_until = None
        self.save()