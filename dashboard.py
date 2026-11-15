import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import random
from io import BytesIO

st.set_page_config(page_title="EazyADS Control Panel", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.main-header { font-size: 2.3rem; font-weight: 700; background: linear-gradient(90deg,#fff,#e879f9); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.badge { background: linear-gradient(135deg,#7e22ce,#db2777); color:white; padding:0.3rem 0.8rem; border-radius:16px; font-weight:600; }
div[data-testid="stSidebar"] { background: linear-gradient(180deg,#0f0a1a,#1a0b2e); }
div[data-testid="stSidebar"] * { color:#f3e8ff !important; }
.stButton>button { background: linear-gradient(90deg,#7e22ce,#db2777); color:white; border:none; border-radius:8px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

DB = "eazyads.db"

def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, company TEXT, role TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS proxies (id TEXT PRIMARY KEY, host TEXT, port TEXT, username TEXT, password TEXT, country TEXT, company TEXT, created TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY, name TEXT, proxy_id TEXT, status TEXT, farming_day INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0, daily_actions INTEGER DEFAULT 0, daily_limit INTEGER DEFAULT 30,
        cookies TEXT, notes TEXT, company TEXT, created TEXT, ready_date TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, name TEXT, nation TEXT, description TEXT, posts_count INTEGER DEFAULT 0, comments_count INTEGER DEFAULT 0, company TEXT, created TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS comments (id TEXT PRIMARY KEY, product_id TEXT, text TEXT, company TEXT, created TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, product_id TEXT, url TEXT, status TEXT DEFAULT 'pending', company TEXT, created TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, profile TEXT, action TEXT, detail TEXT, company TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bot_status (company TEXT PRIMARY KEY, running INTEGER DEFAULT 0, last_update TEXT)""")
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,company,role) VALUES ('admin','admin123','EazyADS','admin')")
    c.commit(); c.close()

init()

def login():
    if "user" not in st.session_state:
        st.session_state.user = None
    if not st.session_state.user:
        st.markdown('<p class="main-header">EazyADS</p>', unsafe_allow_html=True)
        st.markdown('<span class="badge">Control Panel</span>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Accedi", use_container_width=True):
                row = db().execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone()
                if row:
                    st.session_state.user = dict(row)
                    st.rerun()
                else:
                    st.error("Credenziali errate")
        st.caption("Test: admin / admin123")
        st.stop()

login()
user = st.session_state.user
COMP = user["company"]

with st.sidebar:
    st.markdown("### 🚀 EazyADS")
    st.caption(f"{user['username']} · {user['role']}")
    page = st.radio("Menu", [
        "Dashboard", "Profili", "Proxy", "Prodotti", "Commenti", "Post", "Log", "Bot"
    ], label_visibility="collapsed")
    if st.button("Esci", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.markdown(f'<p class="main-header">{page}</p>', unsafe_allow_html=True)

if page == "Dashboard":
    c = db()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Proxy", c.execute("SELECT COUNT(*) FROM proxies WHERE company=?", (COMP,)).fetchone()[0])
    m2.metric("Profili", c.execute("SELECT COUNT(*) FROM profiles WHERE company=?", (COMP,)).fetchone()[0])
    m3.metric("Prodotti", c.execute("SELECT COUNT(*) FROM products WHERE company=?", (COMP,)).fetchone()[0])
    m4.metric("Post in coda", c.execute("SELECT COUNT(*) FROM posts WHERE company=? AND status='pending'", (COMP,)).fetchone()[0])
    ready = c.execute("SELECT COUNT(*) FROM profiles WHERE company=? AND status='ready'", (COMP,)).fetchone()[0]
    warming = c.execute("SELECT COUNT(*) FROM profiles WHERE company=? AND status='warming'", (COMP,)).fetchone()[0]
    st.write(f"**Ready:** {ready}  **Warming:** {warming}")
    df = pd.read_sql_query("SELECT name, status, farming_day, score, daily_actions, daily_limit FROM profiles WHERE company=?", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Profili":
    c = db()
    proxies = c.execute("SELECT id, host, port FROM proxies WHERE company=?", (COMP,)).fetchall()
    c.close()
    proxy_opts = [f"{p['host']}:{p['port']}" for p in proxies]
    pmap = {opt: p["id"] for opt, p in zip(proxy_opts, proxies)}

    with st.expander("Aggiungi account FB", expanded=True):
        with st.form("add_prof"):
            name = st.text_input("Nome / Username")
            proxy = st.selectbox("Proxy", [""] + proxy_opts)
            limit = st.number_input("Limite azioni giornaliere", 5, 100, 30)
            notes = st.text_area("Note")
            if st.form_submit_button("Crea profilo"):
                c = db()
                c.execute("""INSERT INTO profiles (id,name,proxy_id,status,farming_day,score,daily_actions,daily_limit,notes,company,created)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (str(uuid.uuid4())[:8], name, pmap.get(proxy,""), "new", 0, 0, 0, limit, notes, COMP, datetime.now().isoformat()))
                c.commit(); c.close()
                st.success("Profilo creato")
                st.rerun()

    c = db()
    df = pd.read_sql_query("SELECT name, status, farming_day, score, daily_actions, daily_limit FROM profiles WHERE company=?", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.subheader("Gestione profilo")
        sel = st.selectbox("Seleziona profilo", df["name"].tolist())
        if sel:
            col1, col2 = st.columns(2)
            with col1:
                cookies = st.text_area("Cookies (JSON o testo)", height=120, placeholder="Incolla qui i cookies dopo il login manuale")
                if st.button("Salva cookies"):
                    c = db()
                    c.execute("UPDATE profiles SET cookies=? WHERE name=? AND company=?", (cookies, sel, COMP))
                    c.commit()
                    c.close()
                    st.success("Cookies salvati")
            with col2:
                st.write("**Farming singolo**")
                if st.button("Farma ora (simula sessione)"):
                    actions = random.randint(4, 12)
                    score_add = random.randint(5, 15)
                    c = db()
                    c.execute("""UPDATE profiles SET 
                                 score = score + ?, 
                                 daily_actions = daily_actions + ?, 
                                 farming_day = MIN(farming_day + 1, 7),
                                 status = CASE WHEN farming_day + 1 >= 7 THEN 'ready' ELSE 'warming' END
                                 WHERE name=? AND company=?""",
                              (score_add, actions, sel, COMP))
                    c.execute("INSERT INTO logs (timestamp, profile, action, detail, company) VALUES (?,?,?,?,?)",
                              (datetime.now().isoformat(), sel, "Farming session", 
                               f"{actions} azioni (scroll/like/stories), +{score_add} score", COMP))
                    c.commit()
                    c.close()
                    st.success(f"Sessione registrata: {actions} azioni, +{score_add} score")
                    st.rerun()
            c = db()
            row = c.execute("SELECT cookies, score, farming_day, status FROM profiles WHERE name=? AND company=?", (sel, COMP)).fetchone()
            c.close()
            if row and row["cookies"]:
                st.caption("Cookies attuali salvati")
                st.code(row["cookies"][:300] + "..." if len(row["cookies"] or "") > 300 else row["cookies"], language="json")
            st.info(f"Stato: **{row['status']}** | Giorno: {row['farming_day']}/7 | Score: {row['score']}")

elif page == "Proxy":
    with st.expander("Import massivo (host:port:user:pass)", expanded=True):
        bulk = st.text_area("Uno per riga", height=120)
        if st.button("Importa proxy"):
            lines = [l.strip() for l in bulk.splitlines() if l.strip()]
            c = db()
            for line in lines:
                parts = line.split(":")
                host = parts[0] if len(parts)>0 else ""
                port = parts[1] if len(parts)>1 else ""
                un = parts[2] if len(parts)>2 else ""
                pw = parts[3] if len(parts)>3 else ""
                c.execute("INSERT INTO proxies (id,host,port,username,password,country,company,created) VALUES (?,?,?,?,?,?,?,?)",
                          (str(uuid.uuid4())[:8], host, port, un, pw, "", COMP, datetime.now().isoformat()))
            c.commit(); c.close()
            st.success(f"Importati {len(lines)} proxy")
            st.rerun()

    c = db()
    df = pd.read_sql_query("SELECT host, port, username, country, created FROM proxies WHERE company=?", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Prodotti":
    with st.expander("Crea prodotto"):
        with st.form("add_prod"):
            name = st.text_input("Nome")
            nation = st.text_input("Nazione", "IT")
            desc = st.text_area("Descrizione")
            if st.form_submit_button("Salva"):
                c = db()
                c.execute("INSERT INTO products (id,name,nation,description,company,created) VALUES (?,?,?,?,?,?)",
                          (str(uuid.uuid4())[:8], name, nation, desc, COMP, datetime.now().isoformat()))
                c.commit(); c.close()
                st.success("Prodotto creato")
                st.rerun()

    c = db()
    df = pd.read_sql_query("SELECT name, nation, posts_count, comments_count FROM products WHERE company=?", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Commenti":
    c = db()
    prods = c.execute("SELECT id, name FROM products WHERE company=?", (COMP,)).fetchall()
    c.close()
    if not prods:
        st.warning("Crea prima un prodotto")
    else:
        prod_map = {p["name"]: p["id"] for p in prods}
        with st.expander("Pool commenti (uno per riga)"):
            prod = st.selectbox("Prodotto", list(prod_map.keys()))
            bulk = st.text_area("Commenti", height=140)
            if st.button("Salva pool"):
                lines = [l.strip() for l in bulk.splitlines() if l.strip()]
                c = db()
                for line in lines:
                    c.execute("INSERT INTO comments (id,product_id,text,company,created) VALUES (?,?,?,?,?)",
                              (str(uuid.uuid4())[:8], prod_map[prod], line, COMP, datetime.now().isoformat()))
                c.commit(); c.close()
                st.success(f"Aggiunti {len(lines)} commenti")
                st.rerun()

    c = db()
    df = pd.read_sql_query("""SELECT p.name as prodotto, c.text, c.created FROM comments c
                              JOIN products p ON c.product_id = p.id WHERE c.company=? ORDER BY c.created DESC""", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Post":
    c = db()
    prods = c.execute("SELECT id, name FROM products WHERE company=?", (COMP,)).fetchall()
    c.close()
    if prods:
        prod_map = {p["name"]: p["id"] for p in prods}
        with st.expander("Aggiungi URL post"):
            prod = st.selectbox("Prodotto", list(prod_map.keys()))
            urls = st.text_area("URL Facebook (uno per riga)", height=120)
            if st.button("Aggiungi in coda"):
                lines = [l.strip() for l in urls.splitlines() if l.strip()]
                c = db()
                for u in lines:
                    c.execute("INSERT INTO posts (id,product_id,url,status,company,created) VALUES (?,?,?,?,?,?)",
                              (str(uuid.uuid4())[:8], prod_map[prod], u, "pending", COMP, datetime.now().isoformat()))
                c.commit(); c.close()
                st.success(f"Aggiunti {len(lines)} post")
                st.rerun()

    c = db()
    df = pd.read_sql_query("""SELECT p.url, pr.name as prodotto, p.status, p.created FROM posts p
                              JOIN products pr ON p.product_id = pr.id WHERE p.company=? ORDER BY p.created DESC""", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Log":
    c = db()
    df = pd.read_sql_query("SELECT timestamp, profile, action, detail FROM logs WHERE company=? ORDER BY timestamp DESC LIMIT 100", c, params=(COMP,))
    c.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna attività registrata")

elif page == "Bot":
    c = db()
    row = c.execute("SELECT running FROM bot_status WHERE company=?", (COMP,)).fetchone()
    running = row["running"] if row else 0
    c.close()

    st.subheader("Controllo Bot")
    if running:
        st.success("Bot in esecuzione")
        if st.button("Ferma bot", type="primary"):
            c = db()
            c.execute("INSERT OR REPLACE INTO bot_status (company, running, last_update) VALUES (?,?,?)", (COMP, 0, datetime.now().isoformat()))
            c.execute("INSERT INTO logs (timestamp,profile,action,detail,company) VALUES (?,?,?,?,?)",
                      (datetime.now().isoformat(), "SYSTEM", "Bot stopped", "", COMP))
            c.commit(); c.close()
            st.rerun()
    else:
        st.warning("Bot fermo")
        if st.button("Avvia bot", type="primary"):
            c = db()
            c.execute("INSERT OR REPLACE INTO bot_status (company, running, last_update) VALUES (?,?,?)", (COMP, 1, datetime.now().isoformat()))
            c.execute("INSERT INTO logs (timestamp,profile,action,detail,company) VALUES (?,?,?,?,?)",
                      (datetime.now().isoformat(), "SYSTEM", "Bot started", "", COMP))
            c.commit(); c.close()
            st.rerun()

    st.info("""
    **Flusso consigliato**
    1. Aggiungi proxy
    2. Crea profili e assegna proxy
    3. (Consigliato) Login manuale e salva cookies
    4. Crea prodotti
    5. Inserisci commenti nel pool del prodotto
    6. Aggiungi URL dei post
    7. Avvia il bot
    """)

    st.caption("Farming 7 giorni strutturato: Day1 scroll → Day2 stories → Day3 likes → Day4 search → Day5-6 engagement → Day7 Ready")
    st.markdown("""
    **Dettaglio farming per giorno**
    - **Giorno 1**: Solo presenza (scroll feed)
    - **Giorno 2**: Scroll + visualizza storie
    - **Giorno 3**: + Like leggeri
    - **Giorno 4**: + Ricerche
    - **Giorno 5-6**: + Visite pagine, engagement medio
    - **Giorno 7**: Warm-up completo → stato **Ready**
    """)
