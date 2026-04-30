#!/usr/bin/env bash
# build.sh

echo "Iniciando build..."

# Instalar dependências
pip install -r requirements.txt

# Coletar arquivos estáticos
python manage.py collectstatic --noinput

# Aplicar migrações
python manage.py migrate

echo "Build concluído!"