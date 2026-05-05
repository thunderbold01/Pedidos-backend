#!/usr/bin/env bash
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Instalando dependencias..."
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

echo ""
echo "🗄️  Verificando migracoes..."
# NÃO apaga nada, só cria se não existir
python manage.py makemigrations accounts --noinput 2>/dev/null || true
python manage.py makemigrations pedidos --noinput 2>/dev/null || true

echo ""
echo "🗄️  Aplicando migracoes..."
python manage.py migrate --noinput

echo ""
echo "📁 Coletando estaticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Verificando usuarios..."
python create_superuser.py

echo ""
echo "========================================="
echo "  ✅ BUILD CONCLUIDO!"
echo "========================================="
