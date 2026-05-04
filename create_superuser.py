# create_superuser.py
import os, sys, django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

# NOVO ADMIN
email = 'aderitohare11@gmail.com'
password = 'bemvindo12#'

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        username='aderitohare11',
        password=password,
        first_name='Aderito',
        last_name='Hare',
        role='ADMIN',
        is_active=True,
        can_login=True,
        is_staff=True,
        is_superuser=True,
    )
    print(f'✅ Superusuário criado: {email}')
else:
    user = User.objects.get(email=email)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.role = 'ADMIN'
    user.save()
    print(f'✅ Superusuário atualizado: {email}')
    
