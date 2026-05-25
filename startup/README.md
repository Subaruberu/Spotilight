<div align="center">

# 🎉 SpotlightIA
### Plataforma Inteligente de Gestão de Eventos Privados

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-534AB7?style=for-the-badge)](LICENSE)

**Agente de IA completo para planejamento, atendimento e gestão de eventos privados.**  
Construído com Streamlit, Groq (Llama 3.3 70B) e SQLite — 100% gratuito para rodar.

[🚀 Demo ao vivo](https://share.streamlit.io) · [📖 Documentação](#-documentação) · [🐛 Reportar bug](https://github.com/Subaruberu/start-up/issues)

</div>

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Instalação](#-instalação)
- [Deploy Gratuito](#-deploy-gratuito-streamlit-cloud)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Banco de Dados](#-banco-de-dados)
- [Configuração de API](#-configuração-de-api)
- [Planos SaaS](#-planos-saas)
- [Contribuição](#-contribuição)

---

## 🌟 Visão Geral

O **SpotlightIA** é uma plataforma SaaS completa para empresas de eventos privados. Com um agente de IA integrado (Groq · Llama 3.3 70B), a plataforma automatiza desde o primeiro contato com o cliente até a execução do evento — cobrindo atendimento, planejamento, vendas, logística e muito mais.

> **"Do orçamento ao pós-evento, tudo em um só lugar."**

### Por que SpotlightIA?

- ✅ **IA real integrada** — agente com memória de eventos e RSVPs, respostas contextualizadas
- ✅ **Dados persistentes** — banco SQLite com 9 tabelas, dados nunca se perdem
- ✅ **Multi-tenant** — cada empresa tem seu próprio painel isolado
- ✅ **100% gratuito** — Groq, Streamlit Cloud e SQLite sem custo
- ✅ **Multilíngue** — Português, English, Español
- ✅ **26 abas** cobrindo todo o ciclo de vida do evento

---

## 🎯 Funcionalidades

### 🤖 Inteligência Artificial
| Recurso | Descrição |
|---------|-----------|
| Chat com IA | Agente com memória completa de eventos e RSVPs |
| Memória contextual | Cita dados reais dos eventos cadastrados |
| Multilíngue | 🇧🇷 PT · 🇺🇸 EN · 🇪🇸 ES |
| Multi-provedor | Groq · Google Gemini · Hugging Face |
| Scoring de leads | Pontuação 0-100 com IA para priorizar prospects |
| Roteiro do MC | Gera roteiro completo para mestre de cerimônias |

### 📅 Gestão de Eventos
| Recurso | Descrição |
|---------|-----------|
| Cadastro de eventos | Casamentos, corporativos, VIP, hackathons, palestras |
| Checklist inteligente | Por tipo de evento com barra de progresso |
| Cronograma visual | Linha do tempo editável com status em tempo real |
| Mapa interativo | Planta baixa SVG com posicionamento livre de elementos |
| Documentos | Upload centralizado por evento (contratos, riders, plantas) |

### 👥 Relacionamento & Vendas
| Recurso | Descrição |
|---------|-----------|
| CRM completo | Histórico, LTV, aniversários e notas por cliente |
| Funil Kanban | Pipeline visual: Prospect → Concluído |
| RSVP público | Link único por evento para autoconfirmação |
| QR Code de entrada | Geração e validação de acesso no dia do evento |
| Página de captação | Landing page personalizável com formulário de leads |

### 💰 Financeiro & Operacional
| Recurso | Descrição |
|---------|-----------|
| Calculadora de orçamento | Por tipo, nível e cidade com multiplicadores automáticos |
| Pacotes pré-definidos | Essencial · Profissional · Premium · Luxo VIP |
| Gerador de contrato | Contrato HTML completo com cláusulas e área de assinatura |
| PIX & Pagamento | Geração de payload PIX real (BR Code) + QR Code |
| Dashboard executivo | KPIs, gráficos, RSVP, NPS e alertas de pendências |
| Relatório PDF | Relatório mensal configurável para download |

### 🔧 Infraestrutura & Técnica
| Recurso | Descrição |
|---------|-----------|
| Estrutura & AV | Som, iluminação, palco, gerador e camarim |
| Buffet & Gastronomia | Calculadora de quantidade + restrições alimentares |
| Logística | Calculadora de estacionamento + modos de transporte |
| Foto & Vídeo | Calculadora de cobertura + checklist de briefing |
| Widget para site | Chat embedável em qualquer site HTML/WordPress |
| Convite digital | 5 temas visuais com download em HTML |

---

## 🛠 Tecnologias

```
Frontend & Backend    → Streamlit 1.40+
IA Principal          → Groq API (Llama 3.3 70B) — gratuito
IA Alternativa        → Google Gemini 1.5 Flash — gratuito
IA Alternativa        → Hugging Face Inference API — gratuito
Banco de Dados        → SQLite (nativo Python)
Visualizações         → Pandas · Streamlit Charts
QR Code               → qrcode · Pillow
HTTP Requests         → requests
Linguagem             → Python 3.11+
```

---

## 🚀 Instalação

### Pré-requisitos
- Python 3.11+
- pip
- Conta Groq gratuita → [console.groq.com](https://console.groq.com)

### 1. Clone o repositório

```bash
git clone https://github.com/Subaruberu/start-up.git
cd start-up
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as credenciais

Edite o arquivo `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_sua_chave_aqui"

# Opcionais
GEMINI_API_KEY = "AIza_sua_chave_aqui"
HF_API_KEY     = "hf_sua_chave_aqui"
```

### 4. Inicialize o banco de dados

```bash
python migrate.py
```

### 5. Rode o app

```bash
streamlit run app.py
```

Acesse em: **http://localhost:8501**

---

## ☁️ Deploy Gratuito (Streamlit Cloud)

### Passo 1 — Suba no GitHub
```bash
git add .
git commit -m "SpotlightIA v1.0"
git push origin main
```

### Passo 2 — Deploy
1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. **New app** → selecione `Subaruberu/start-up`
3. Arquivo principal: `app.py`
4. Clique em **Deploy**

### Passo 3 — Configure os Secrets
No painel do app: **⋮ → Settings → Secrets**

```toml
GROQ_API_KEY = "gsk_sua_chave_aqui"
```

> ✅ O app carrega a API Key automaticamente — nenhum campo exposto na interface.

---

## 📁 Estrutura do Projeto

```
start-up/
│
├── app.py                  # Aplicação principal (26 abas, ~3800 linhas)
├── database.py             # Módulo SQLite — 9 tabelas, CRUD completo
├── migrate.py              # Script de inicialização do banco
├── deploy.sh               # Script de deploy automatizado
├── setup.sh                # Script de setup completo (install + migrate + run)
├── requirements.txt        # Dependências Python
├── .gitignore              # Arquivos ignorados
│
├── .streamlit/
│   ├── config.toml         # Tema roxo SpotlightIA
│   └── secrets.toml        # API Keys (nunca subir no Git!)
│
└── README.md               # Este arquivo
```

---

## 🗄 Banco de Dados

O banco SQLite (`spotlightia.db`) é criado automaticamente na primeira execução.

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `tenants` | Empresas cadastradas no SaaS |
| `eventos` | Eventos por tenant |
| `rsvps` | Confirmações de presença |
| `clientes_crm` | Base de clientes e prospects |
| `kanban` | Cards do funil de vendas |
| `documentos` | Arquivos anexados por evento |
| `cronogramas` | Itens de cronograma por evento |
| `leads` | Leads captados via landing page |
| `chat_historico` | Histórico de conversas com IA |

### Reiniciar o banco

```bash
rm spotlightia.db
python migrate.py
```

---

## 🔑 Configuração de API

### Groq (Recomendado — mais rápido)
1. Crie conta grátis em [console.groq.com](https://console.groq.com)
2. **API Keys → Create API Key**
3. Copie a chave `gsk_...`

**Limites gratuitos:** 500.000 tokens/dia · 30 req/min · Llama 3.3 70B

### Google Gemini (Alternativa)
1. Acesse [aistudio.google.com](https://aistudio.google.com)
2. **Get API Key → Create API Key**
3. Copie a chave `AIza...`

### Hugging Face (Alternativa)
1. Acesse [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. **New token → Read**
3. Copie a chave `hf_...`

---

## 💎 Planos SaaS

| Plano | Preço | Eventos | Recursos |
|-------|-------|---------|---------|
| **Free** | R$ 0/mês | 2 | Chat IA · RSVP · Checklist |
| **Essencial** | R$ 97/mês | 10 | + Dashboard · Convite digital · E-mail |
| **Profissional** | R$ 197/mês | 20 | + Orçamento · Contrato · Mapa · Foto&Vídeo |
| **Enterprise** | R$ 497/mês | ∞ | + Multi-usuário · Relatório PDF · Suporte prioritário |

> Cupom de demonstração: **SPOTLIGHT20** (20% de desconto)

**Login de demonstração:**
```
E-mail: admin@spotlight.com
Senha:  admin123
```

---

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'feat: adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

---

<div align="center">

Desenvolvido com 💜 por **Spotlight Eventos**

**SpotlightIA** · Powered by [Groq](https://groq.com) · Built with [Streamlit](https://streamlit.io)

⭐ Se este projeto te ajudou, deixe uma estrela no repositório!

</div>
