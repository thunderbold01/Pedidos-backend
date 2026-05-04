#!/usr/bin/env bash
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Atualizando pip..."
python -m pip install --upgrade pip --quiet

echo ""
echo "📦 Instalando dependencias..."
python -m pip install -r requirements.txt --quiet

echo ""
echo "📋 Verificando instalacao..."
python -m pip list | grep -E "gunicorn|Django" | head -5

echo ""
echo "🗄️  Resetando migracoes..."
# Remover migrações antigas do banco
python manage.py migrate --fake accounts zero --noinput 2>/dev/null || true
python manage.py migrate --fake pedidos zero --noinput 2>/dev/null || true
python manage.py migrate --fake admin zero --noinput 2>/dev/null || true
python manage.py migrate --fake auth zero --noinput 2>/dev/null || true
python manage.py migrate --fake contenttypes zero --noinput 2>/dev/null || true
python manage.py migrate --fake sessions zero --noinput 2>/dev/null || true

echo ""
echo "🗄️  Criando novas migracoes..."
python manage.py makemigrations accounts --noinput
python manage.py makemigrations pedidos --noinput

echo ""
echo "🗄️  Aplicando migracoes..."
python manage.py migrate --noinput

echo ""
echo "📁 Coletando estaticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Criando usuarios..."
python create_superuser.py

echo ""
echo "========================================="
echo "  ✅ BUILD CONCLUIDO!"
echo "========================================="
