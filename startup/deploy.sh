#!/bin/bash
# ── Deploy SpotlightIA → github.com/Subaruberu/start-up ──────────────────────

echo "🎉 Iniciando deploy do SpotlightIA..."

# 1. Clone o repositório
git clone https://github.com/Subaruberu/start-up.git
cd start-up

# 2. Copie os arquivos do app (ajuste o caminho onde você baixou os arquivos)
# Se estiver na mesma pasta, use: cp ../event_agent/* .
# Se baixou em Downloads:
# cp ~/Downloads/app.py .
# cp ~/Downloads/requirements.txt .
# cp ~/Downloads/.gitignore .

# Copie manualmente os arquivos baixados para esta pasta antes de continuar
echo "📁 Cole os arquivos baixados (app.py, requirements.txt, .gitignore) nesta pasta:"
echo "   $(pwd)"
echo ""
read -p "✅ Arquivos copiados? Pressione ENTER para continuar..."

# 3. Cria pasta .streamlit se não existir
mkdir -p .streamlit

# Cria config.toml
cat > .streamlit/config.toml << 'EOF'
[theme]
primaryColor = "#534AB7"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1A1A2E"
textColor = "#FAFAFA"
font = "sans serif"

[server]
maxUploadSize = 50
EOF

# Cria secrets.toml (NÃO será enviado ao GitHub)
cat > .streamlit/secrets.toml << 'EOF'
# Preencha com sua chave Groq
GROQ_API_KEY = "gsk_coloque_sua_chave_aqui"
GEMINI_API_KEY = "AIza_coloque_sua_chave_aqui"
HF_API_KEY = "hf_coloque_sua_chave_aqui"
EOF

echo "⚠️  Lembre-se de editar .streamlit/secrets.toml com sua API Key!"

# 4. Garante que secrets.toml está no .gitignore
grep -q "secrets.toml" .gitignore 2>/dev/null || echo ".streamlit/secrets.toml" >> .gitignore

# 5. Commit e push
git add .
git commit -m "🎉 SpotlightIA - Agente IA para Eventos Privados"
git push origin main

echo ""
echo "✅ Deploy concluído!"
echo "🌐 Repositório: https://github.com/Subaruberu/start-up"
echo ""
echo "📦 Próximo passo — publicar no Streamlit Cloud:"
echo "   1. Acesse https://share.streamlit.io"
echo "   2. Login com GitHub"
echo "   3. New app → Subaruberu/start-up → app.py"
echo "   4. Deploy!"
echo ""
echo "🔑 Não esqueça de adicionar sua GROQ_API_KEY nos Secrets do Streamlit Cloud:"
echo "   App → Settings → Secrets → GROQ_API_KEY = gsk_..."
