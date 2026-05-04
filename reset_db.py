
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

print("=" * 50)
print("  RESETANDO BANCO DE DADOS")
print("=" * 50)

cursor = connection.cursor()

# Listar todas as tabelas
cursor.execute("""
    SELECT tablename FROM pg_tables 
    WHERE schemaname = 'public'
""")
tables = cursor.fetchall()

print(f"\n📋 Tabelas encontradas: {len(tables)}")

# Apagar todas as tabelas
cursor.execute("DROP SCHEMA public CASCADE;")
cursor.execute("CREATE SCHEMA public;")
cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
cursor.execute("GRANT ALL ON SCHEMA public TO public;")

print("✅ Todas as tabelas foram apagadas!")
print("=" * 50)
