"""
migrate.py — Migra dados de exemplo para o banco SQLite
Execute uma vez: python migrate.py
"""
import database as db

print("🗄️  Inicializando banco de dados SpotlightIA...")
db.init_db()
print("✅  Tabelas criadas com sucesso!")
print("✅  Dados de demonstração inseridos!")
print("")
print("📊  Stats do tenant 'spotlight':")
stats = db.stats_tenant("spotlight")
for k, v in stats.items():
    print(f"   {k}: {v}")
print("")
print("🚀  Banco pronto! Rode: streamlit run app.py")
