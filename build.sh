cat > build.sh << 'EOF'
#!/usr/bin/env bash
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Instalando pip mais recente..."
pip install --upgrade pip

echo ""
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

echo ""
echo "📋 Verificando gunicorn..."
which gunicorn
gunicorn --version

echo ""
echo "🗄️  Criando migracoes..."
python manage.py makemigrations accounts pedidos --noinput

echo ""
echo "🗄️  Executando migracoes..."
python manage.py migrate --noinput

echo ""
echo "📁 Coletando arquivos estaticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Criando super usuario..."
python create_superuser.py

echo ""
echo "========================================="
echo "  ✅ BUILD CONCLUIDO!"
echo "========================================="
EOF
