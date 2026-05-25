"""
database.py — Módulo de banco de dados SQLite para SpotlightIA
Gerencia persistência de todos os dados do app.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get("SPOTLIGHT_DB", "spotlightia.db")


def get_conn():
    """Retorna conexão com o banco, criando o arquivo se necessário."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # acesso por nome de coluna
    return conn


def init_db():
    """Cria todas as tabelas se não existirem."""
    conn = get_conn()
    c = conn.cursor()

    # ── Tenants (empresas/clientes SaaS) ─────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id          TEXT PRIMARY KEY,
        nome        TEXT NOT NULL,
        email       TEXT UNIQUE NOT NULL,
        senha       TEXT NOT NULL,
        plano       TEXT DEFAULT 'free',
        cor         TEXT DEFAULT '#534AB7',
        logo        TEXT DEFAULT '🎉',
        vencimento  TEXT DEFAULT '2026-12-31',
        max_eventos INTEGER DEFAULT 2,
        criado_em   TEXT DEFAULT (datetime('now'))
    )""")

    # ── Eventos ───────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        nome        TEXT NOT NULL,
        tipo        TEXT,
        data        TEXT,
        local       TEXT,
        convidados  INTEGER DEFAULT 0,
        status      TEXT DEFAULT 'pending',
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── RSVPs ─────────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS rsvps (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        evento_nome TEXT NOT NULL,
        nome        TEXT NOT NULL,
        email       TEXT NOT NULL,
        acomp       INTEGER DEFAULT 0,
        restricao   TEXT DEFAULT 'Nenhuma',
        status      TEXT DEFAULT 'Pendente',
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── CRM de clientes ───────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes_crm (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id       TEXT NOT NULL,
        nome            TEXT NOT NULL,
        empresa         TEXT,
        email           TEXT,
        tel             TEXT,
        tipo            TEXT,
        eventos         INTEGER DEFAULT 0,
        valor_total     REAL DEFAULT 0,
        status          TEXT DEFAULT 'Prospect',
        aniversario     TEXT,
        notas           TEXT,
        ultima_interacao TEXT,
        criado_em       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── Kanban ────────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS kanban (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        cliente     TEXT NOT NULL,
        evento      TEXT NOT NULL,
        valor       REAL DEFAULT 0,
        tipo        TEXT,
        contato     TEXT,
        nota        TEXT,
        coluna      TEXT DEFAULT 'Prospect',
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── Documentos ────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS documentos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        evento_nome TEXT NOT NULL,
        nome        TEXT NOT NULL,
        tipo        TEXT,
        descricao   TEXT,
        tamanho     TEXT,
        mime        TEXT,
        dados       BLOB,
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── Cronogramas ───────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS cronogramas (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        evento_nome TEXT NOT NULL,
        hora        TEXT NOT NULL,
        atividade   TEXT NOT NULL,
        responsavel TEXT,
        status      TEXT DEFAULT '⏳ Pendente',
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── Leads da landing page ─────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        nome        TEXT NOT NULL,
        email       TEXT,
        tel         TEXT,
        tipo        TEXT,
        data_evento TEXT,
        convidados  INTEGER,
        mensagem    TEXT,
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    # ── Histórico de chat ─────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_historico (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   TEXT NOT NULL,
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        criado_em   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )""")

    conn.commit()
    conn.close()

    # Insere tenant demo se não existir
    _seed_demo()


def _seed_demo():
    """Insere dados de demonstração se o banco estiver vazio."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM tenants WHERE id = 'spotlight'")
    if not c.fetchone():
        c.execute("""INSERT INTO tenants (id,nome,email,senha,plano,cor,logo,max_eventos)
                     VALUES ('spotlight','Spotlight Eventos','admin@spotlight.com','admin123','enterprise','#534AB7','🎯',999)""")
        c.execute("""INSERT INTO tenants (id,nome,email,senha,plano,cor,logo,max_eventos)
                     VALUES ('festavip','Festa VIP Produções','admin@festavip.com','festa123','profissional','#B8860B','⭐',20)""")

        # Eventos demo
        eventos_demo = [
            ('spotlight','Casamento Silva & Pereira','casamento','12/07/2025','Villa Giardini, SP',180,'confirmed'),
            ('spotlight','Hackathon TechCorp 2025','hackathon','20/08/2025','Centro de Convenções, SP',240,'pending'),
            ('spotlight','Jantar VIP Investidores','vip','05/09/2025','Restaurante Fasano, SP',30,'vip'),
        ]
        c.executemany("INSERT INTO eventos (tenant_id,nome,tipo,data,local,convidados,status) VALUES (?,?,?,?,?,?,?)", eventos_demo)

        # CRM demo
        crm_demo = [
            ('spotlight','Ana Lima','Lima Eventos','ana@lima.com','(11)99001-0001','Casamento',3,45000,'Ativo','15/03','Prefere WhatsApp','10/05/2026'),
            ('spotlight','Carlos Mendes','TechCorp','carlos@techcorp.com','(11)99002-0002','Corporativo',5,120000,'Ativo','22/08','Gosta de relatórios','15/05/2026'),
            ('spotlight','Beatriz Costa','VIP Produções','bea@vip.com','(11)99003-0003','VIP',2,80000,'Prospect','05/11','Interesse no pacote Luxo','18/05/2026'),
        ]
        c.executemany("INSERT INTO clientes_crm (tenant_id,nome,empresa,email,tel,tipo,eventos,valor_total,status,aniversario,notas,ultima_interacao) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", crm_demo)

        conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# TENANTS
# ═══════════════════════════════════════════════════════════════════════════════

def tenant_login(email: str, senha: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tenants WHERE email=? AND senha=?", (email, senha)).fetchone()
    conn.close()
    return dict(row) if row else None

def tenant_criar(id_: str, nome: str, email: str, senha: str, plano: str):
    from planos import PLANOS
    max_ev = PLANOS.get(plano, {}).get("max_eventos", 2)
    conn = get_conn()
    try:
        conn.execute("INSERT INTO tenants (id,nome,email,senha,plano,max_eventos) VALUES (?,?,?,?,?,?)",
                     (id_, nome, email, senha, plano, max_ev))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def tenant_atualizar_plano(tenant_id: str, plano: str, max_eventos: int):
    conn = get_conn()
    conn.execute("UPDATE tenants SET plano=?, max_eventos=? WHERE id=?", (plano, max_eventos, tenant_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def eventos_listar(tenant_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM eventos WHERE tenant_id=? ORDER BY data", (tenant_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def evento_criar(tenant_id: str, nome: str, tipo: str, data: str, local: str, convidados: int):
    conn = get_conn()
    conn.execute("INSERT INTO eventos (tenant_id,nome,tipo,data,local,convidados) VALUES (?,?,?,?,?,?)",
                 (tenant_id, nome, tipo, data, local, convidados))
    conn.commit()
    conn.close()

def evento_atualizar_status(evento_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE eventos SET status=? WHERE id=?", (status, evento_id))
    conn.commit()
    conn.close()

def evento_deletar(evento_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM eventos WHERE id=?", (evento_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# RSVPs
# ═══════════════════════════════════════════════════════════════════════════════

def rsvps_listar(tenant_id: str, evento_nome: str = None):
    conn = get_conn()
    if evento_nome:
        rows = conn.execute("SELECT * FROM rsvps WHERE tenant_id=? AND evento_nome=?", (tenant_id, evento_nome)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM rsvps WHERE tenant_id=? ORDER BY criado_em DESC", (tenant_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def rsvp_upsert(tenant_id: str, evento_nome: str, nome: str, email: str, acomp: int, restricao: str, status: str):
    conn = get_conn()
    existe = conn.execute("SELECT id FROM rsvps WHERE tenant_id=? AND evento_nome=? AND email=?",
                           (tenant_id, evento_nome, email)).fetchone()
    if existe:
        conn.execute("UPDATE rsvps SET nome=?,acomp=?,restricao=?,status=? WHERE id=?",
                     (nome, acomp, restricao, status, existe["id"]))
    else:
        conn.execute("INSERT INTO rsvps (tenant_id,evento_nome,nome,email,acomp,restricao,status) VALUES (?,?,?,?,?,?,?)",
                     (tenant_id, evento_nome, nome, email, acomp, restricao, status))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CRM
# ═══════════════════════════════════════════════════════════════════════════════

def crm_listar(tenant_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM clientes_crm WHERE tenant_id=? ORDER BY nome", (tenant_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def crm_criar(tenant_id: str, dados: dict):
    conn = get_conn()
    conn.execute("""INSERT INTO clientes_crm
        (tenant_id,nome,empresa,email,tel,tipo,status,aniversario,notas,ultima_interacao)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (tenant_id, dados["nome"], dados.get("empresa","—"), dados.get("email",""),
         dados.get("tel","—"), dados.get("tipo",""), dados.get("status","Prospect"),
         dados.get("aniversario","—"), dados.get("notas","—"),
         datetime.today().strftime("%d/%m/%Y")))
    conn.commit()
    conn.close()

def crm_atualizar_nota(cliente_id: int, nota: str):
    conn = get_conn()
    conn.execute("UPDATE clientes_crm SET notas=?, ultima_interacao=? WHERE id=?",
                 (nota, datetime.today().strftime("%d/%m/%Y"), cliente_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN
# ═══════════════════════════════════════════════════════════════════════════════

def kanban_listar(tenant_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM kanban WHERE tenant_id=? ORDER BY criado_em", (tenant_id,)).fetchall()
    conn.close()
    # Agrupa por coluna
    resultado = {col: [] for col in ["Prospect","Proposta enviada","Negociação","Fechado","Em execução","Concluído"]}
    for r in rows:
        d = dict(r)
        if d["coluna"] in resultado:
            resultado[d["coluna"]].append(d)
    return resultado

def kanban_adicionar(tenant_id: str, dados: dict):
    conn = get_conn()
    conn.execute("INSERT INTO kanban (tenant_id,cliente,evento,valor,tipo,contato,nota,coluna) VALUES (?,?,?,?,?,?,?,?)",
                 (tenant_id, dados["cliente"], dados["evento"], dados.get("valor",0),
                  dados.get("tipo",""), dados.get("contato",""), dados.get("nota",""),
                  dados.get("coluna","Prospect")))
    conn.commit()
    conn.close()

def kanban_mover(card_id: int, nova_coluna: str):
    conn = get_conn()
    conn.execute("UPDATE kanban SET coluna=? WHERE id=?", (nova_coluna, card_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT HISTÓRICO
# ═══════════════════════════════════════════════════════════════════════════════

def chat_salvar(tenant_id: str, role: str, content: str):
    conn = get_conn()
    conn.execute("INSERT INTO chat_historico (tenant_id,role,content) VALUES (?,?,?)",
                 (tenant_id, role, content))
    conn.commit()
    conn.close()

def chat_carregar(tenant_id: str, limite: int = 50):
    conn = get_conn()
    rows = conn.execute("""SELECT role, content FROM chat_historico
                           WHERE tenant_id=? ORDER BY criado_em DESC LIMIT ?""",
                        (tenant_id, limite)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def chat_limpar(tenant_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM chat_historico WHERE tenant_id=?", (tenant_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# LEADS
# ═══════════════════════════════════════════════════════════════════════════════

def lead_criar(tenant_id: str, dados: dict):
    conn = get_conn()
    conn.execute("""INSERT INTO leads (tenant_id,nome,email,tel,tipo,data_evento,convidados,mensagem)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (tenant_id, dados["nome"], dados.get("email",""), dados.get("tel",""),
                  dados.get("tipo",""), dados.get("data",""), dados.get("convidados",0),
                  dados.get("mensagem","")))
    conn.commit()
    conn.close()

def leads_listar(tenant_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM leads WHERE tenant_id=? ORDER BY criado_em DESC", (tenant_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# CRONOGRAMA
# ═══════════════════════════════════════════════════════════════════════════════

def cronograma_listar(tenant_id: str, evento_nome: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cronogramas WHERE tenant_id=? AND evento_nome=? ORDER BY hora",
                        (tenant_id, evento_nome)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def cronograma_adicionar(tenant_id: str, evento_nome: str, hora: str, atividade: str, responsavel: str):
    conn = get_conn()
    conn.execute("INSERT INTO cronogramas (tenant_id,evento_nome,hora,atividade,responsavel) VALUES (?,?,?,?,?)",
                 (tenant_id, evento_nome, hora, atividade, responsavel))
    conn.commit()
    conn.close()

def cronograma_atualizar_status(item_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE cronogramas SET status=? WHERE id=?", (status, item_id))
    conn.commit()
    conn.close()

def cronograma_deletar(item_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM cronogramas WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

def exportar_json(tenant_id: str) -> str:
    """Exporta todos os dados do tenant em JSON."""
    return json.dumps({
        "eventos":   eventos_listar(tenant_id),
        "rsvps":     rsvps_listar(tenant_id),
        "clientes":  crm_listar(tenant_id),
        "kanban":    kanban_listar(tenant_id),
        "leads":     leads_listar(tenant_id),
    }, ensure_ascii=False, indent=2)

def stats_tenant(tenant_id: str) -> dict:
    """Retorna métricas rápidas do tenant."""
    conn = get_conn()
    ev    = conn.execute("SELECT COUNT(*) FROM eventos WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
    rsvp  = conn.execute("SELECT COUNT(*) FROM rsvps WHERE tenant_id=? AND status='Confirmado'", (tenant_id,)).fetchone()[0]
    cli   = conn.execute("SELECT COUNT(*) FROM clientes_crm WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
    leads = conn.execute("SELECT COUNT(*) FROM leads WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
    conn.close()
    return {"eventos": ev, "rsvps_confirmados": rsvp, "clientes": cli, "leads": leads}


# Inicializa o banco ao importar o módulo
init_db()
