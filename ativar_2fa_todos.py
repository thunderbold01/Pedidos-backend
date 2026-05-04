# ativar_2fa_todos.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

def ativar_2fa_todos_usuarios():
    """Ativa 2FA para todos os usuários existentes"""
    
    usuarios = User.objects.all()
    count = 0
    
    for user in usuarios:
        if not user.two_factor_enabled:
            user.two_factor_enabled = True
            if not user.two_factor_secret:
                import pyotp
                user.two_factor_secret = pyotp.random_base32()
            user.save()
            count += 1
            print(f'✅ 2FA ativado para: {user.email} ({user.get_role_display()})')
        else:
            print(f'⏭️ 2FA já ativo: {user.email} ({user.get_role_display()})')
    
    print(f'\n🎉 2FA ativado para {count} usuários!')
    print(f'Total de usuários: {usuarios.count()}')

if __name__ == '__main__':
    ativar_2fa_todos_usuarios()