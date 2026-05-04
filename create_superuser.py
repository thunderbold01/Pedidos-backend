
import os
import sys
import django

# Configurar o Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

print("=" * 50)
print("  CRIANDO USUARIOS PADRAO")
print("=" * 50)

# SUPERUSUARIO
if not User.objects.filter(email='admin@escola.com').exists():
    User.objects.create_superuser(
        email='admin@escola.com',
        username='admin',
        password='Admin@123456',
        first_name='Admin',
        last_name='Sistema',
        role='ADMIN',
        is_active=True,
        can_login=True,
    )
    print('✅ ADMIN: admin@escola.com / Admin@123456')
else:
    print('✅ ADMIN ja existe')

# USUARIOS PADRAO
usuarios = [
    ('dite@escola.com', 'dite', 'Dite@123', 'DITE', 'User', 'DITE'),
    ('direcao@escola.com', 'direcao', 'Direcao@123', 'Direcao', 'User', 'DIRECAO'),
    ('administracao@escola.com', 'administracao', 'Admin@123', 'Administracao', 'User', 'ADMINISTRACAO'),
    ('seguranca@escola.com', 'seguranca', 'Seguranca@123', 'Seguranca', 'User', 'SEGURANCA'),
    ('estudante@escola.com', 'estudante', 'Estudante@123', 'Estudante', 'Teste', 'ESTUDANTE'),
]

for email, username, password, first_name, last_name, role in usuarios:
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            can_login=True,
        )
        print(f'✅ {role}: {email} / {password}')
    else:
        print(f'✅ {role} ja existe: {email}')

print("=" * 50)
print("  ✅ TODOS USUARIOS PRONTOS!")
print("=" * 50)
print("")
print("CREDENCIAIS:")
print("  ADMIN:       admin@escola.com / Admin@123456")
print("  DITE:        dite@escola.com / Dite@123")
print("  DIRECAO:     direcao@escola.com / Direcao@123")
print("  ADMINISTR:   administracao@escola.com / Admin@123")
print("  SEGURANCA:   seguranca@escola.com / Seguranca@123")
print("  ESTUDANTE:   estudante@escola.com / Estudante@123")
print("")

