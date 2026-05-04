#!/usr/bin/env bash
# build.sh
set -o errexit

echo "Instalando dependências..."
pip install -r requirements.txt

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Executando migrações..."
python manage.py migrate --noinput

echo "Criando superusuário se não existir..."
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(email='admin@escola.com').exists():
    User.objects.create_superuser('admin@escola.com', 'Admin123')
    print('Superusuário criado!')
else:
    print('Superusuário já existe.')
"

echo "Build concluído!"
