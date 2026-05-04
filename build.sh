
#!/usr/bin/env bash
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Atualizando pip..."
python -m pip install --upgrade pip

echo ""
echo "📦 Instalando dependencias FORCADO..."
python -m pip install --force-reinstall -r requirements.txt

echo ""
echo "📋 Verificando instalacao..."
python -m pip list | grep -i gunicorn
python -m pip list | grep -i django

echo ""
echo "🗄️  Migracoes..."
python manage.py makemigrations accounts pedidos --noinput
python manage.py migrate --noinput

echo ""
echo "📁 Estaticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Usuarios..."
python create_superuser.py

echo ""
echo "✅ BUILD CONCLUIDO!"
