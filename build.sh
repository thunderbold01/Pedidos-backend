#!/usr/bin/env bash
# build.sh
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Instalando dependências..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "🗄️  Executando migrações..."
python manage.py migrate --noinput

echo ""
echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Criando usuários padrão..."
python manage.py create_default_users

echo ""
echo "========================================="
echo "  ✅ BUILD CONCLUÍDO!"
echo "========================================="
