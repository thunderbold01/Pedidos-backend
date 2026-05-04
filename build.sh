cat > build.sh << 'EOF'
#!/usr/bin/env bash
set -o errexit

echo "========================================="
echo "  BUILD SISTEMA DE PEDIDOS"
echo "========================================="

echo ""
echo "📦 Instalando dependencias..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

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

chmod +x build.sh
