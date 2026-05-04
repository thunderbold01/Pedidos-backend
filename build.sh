cat > build.sh << 'EOF'
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
echo "🗄️  Resetando banco de dados..."
python reset_db.py

echo ""
echo "🗄️  Criando migracoes..."
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
EOF
