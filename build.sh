
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
echo "🗄️  Apagando TODAS as tabelas do banco..."
python manage.py sqlflush | python manage.py dbshell 2>/dev/null || true

echo ""
echo "🗄️  Recriando migracoes do zero..."
# Apagar migracoes antigas
find . -path "*/migrations/0*.py" -delete 2>/dev/null || true
find . -path "*/migrations/0*.pyc" -delete 2>/dev/null || true

echo ""
echo "🗄️  Makemigrations..."
python manage.py makemigrations accounts --noinput
python manage.py makemigrations pedidos --noinput

echo ""
echo "🗄️  Migrate..."
python manage.py migrate --noinput

echo ""
echo "📁 Collectstatic..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Criando usuarios..."
python create_superuser.py

echo ""
echo "✅ BUILD CONCLUIDO!"
