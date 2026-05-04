# create_superuser.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

# Criar superusuário
if not User.objects.filter(email='admin@escola.com').exists():
    User.objects.create_superuser(
        email='Aderitohare11@gmail.com',
        username='aderito',
        password='Bemvindo12#',
        first_name='Admin',
        last_name='Sistema',
        role='ADMIN'
    )
    print('✅ Superusuário criado com sucesso!')
    print('📧 Email: admin@escola.com')
    print('🔑 Senha: Admin123')
else:
    print('✅ Superusuário já existe!')

# Criar outros usuários de teste se necessário
roles = ['DITE', 'DIRECAO', 'ADMINISTRACAO', 'SEGURANCA', 'ESTUDANTE']
for role in roles:
    email = f'{role.lower()}@escola.com'
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(
            email=email,
            username=role.lower(),
            password=f'{role.capitalize()}123',
            first_name=role.capitalize(),
            last_name='User',
            role=role,
            is_active=True
        )
        print(f'✅ Usuário {role} criado: {email} / {role.capitalize()}123')
