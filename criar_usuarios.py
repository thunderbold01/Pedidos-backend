import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

def criar_usuarios():
    usuarios = [
        {
            'email': 'admin@escola.com',
            'username': 'admin',
            'password': 'Admin123',
            'role': 'ADMIN',
            'first_name': 'Administrador',
            'last_name': 'Sistema',
            'two_factor': False,
            'is_staff': True,
            'is_superuser': True,
        },
        {
            'email': 'administracao@escola.com',
            'username': 'administracao',
            'password': 'Admin123',
            'role': 'ADMINISTRACAO',
            'first_name': 'Administração',
            'last_name': 'Geral',
            'two_factor': False,
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'email': 'direcao@escola.com',
            'username': 'direcao',
            'password': 'Direcao123',
            'role': 'DIRECAO',
            'first_name': 'Diretor',
            'last_name': 'Geral',
            'two_factor': True,
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'email': 'dite@escola.com',
            'username': 'dite',
            'password': 'Dite12345',
            'role': 'DITE',
            'first_name': 'Técnico',
            'last_name': 'DITE',
            'two_factor': True,
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'email': 'estudante@escola.com',
            'username': 'estudante',
            'password': 'Estudante123',
            'role': 'ESTUDANTE',
            'first_name': 'João',
            'last_name': 'Silva',
            'two_factor': True,
            'is_staff': False,
            'is_superuser': False,
        },
    ]
    
    for dados in usuarios:
        try:
            user = User.objects.get(email=dados['email'])
            user.username = dados['username']
            user.role = dados['role']
            user.first_name = dados['first_name']
            user.last_name = dados['last_name']
            user.two_factor_enabled = dados['two_factor']
            user.is_active = True
            user.is_staff = dados['is_staff']
            user.is_superuser = dados['is_superuser']
            user.set_password(dados['password'])
            user.save()
            print(f'✅ Atualizado: {dados["email"]} ({dados["role"]})')
        except User.DoesNotExist:
            if dados['is_superuser']:
                user = User.objects.create_superuser(
                    username=dados['username'],
                    email=dados['email'],
                    password=dados['password'],
                    first_name=dados['first_name'],
                    last_name=dados['last_name'],
                    role=dados['role'],
                    two_factor_enabled=dados['two_factor'],
                    is_active=True,
                    is_staff=dados['is_staff'],
                    is_superuser=dados['is_superuser'],
                )
            else:
                user = User.objects.create_user(
                    username=dados['username'],
                    email=dados['email'],
                    password=dados['password'],
                    first_name=dados['first_name'],
                    last_name=dados['last_name'],
                    role=dados['role'],
                    two_factor_enabled=dados['two_factor'],
                    is_active=True,
                    is_staff=dados['is_staff'],
                    is_superuser=dados['is_superuser'],
                )
            print(f'✅ Criado: {dados["email"]} ({dados["role"]})')
    
    print('\n🎉 Todos os usuários configurados!')
    print('\n📋 Credenciais:')
    print('  👑 Admin:          admin@escola.com / Admin123')
    print('  🏛️  Administração:  administracao@escola.com / Admin123')
    print('  👨‍💼 Direção:        direcao@escola.com / Direcao123')
    print('  💻 DITE:           dite@escola.com / Dite12345')
    print('  🎓 Estudante:      estudante@escola.com / Estudante123')

if __name__ == '__main__':
    criar_usuarios()