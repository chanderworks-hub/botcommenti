import streamlit as st
import json
import os
from datetime import datetime
import random
import uuid
import re
import pandas as pd
from io import BytesIO

# Page config
st.set_page_config(
    page_title="BotCV Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
    }
    div[data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    div[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "proxies": os.path.join(DATA_DIR, "proxies.json"),
    "profiles": os.path.join(DATA_DIR, "profiles.json"),
    "products": os.path.join(DATA_DIR, "products.json"),
    "comments_library": os.path.join(DATA_DIR, "comments_library.json"),
    "generated_comments": os.path.join(DATA_DIR, "generated_comments.json"),
    "activity_log": os.path.join(DATA_DIR, "activity_log.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
}

def load_json(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

for path in FILES.values():
    if not os.path.exists(path):
        save_json(path, [])

if not load_json(FILES["users"]):
    save_json(FILES["users"], [
        {"username": "admin", "password": "admin123", "company": "Azienda Demo", "role": "admin"},
        {"username": "demo", "password": "demo123", "company": "Test Company", "role": "operator"},
    ])

SYNONYMS = {
    "ottimo": ["fantastico", "eccellente", "perfetto", "top", "super"],
    "bello": ["carino", "piacevole", "gradevole", "interessante", "figo"],
    "buono": ["valido", "utile", "efficace", "positivo"],
    "consiglio": ["raccomando", "suggerisco", "provare"],
    "davvero": ["veramente", "realmente", "proprio"],
    "great": ["awesome", "excellent", "amazing", "perfect"],
    "good": ["nice", "solid", "decent", "useful"],
    "love": ["like", "enjoy", "appreciate"],
}

def generate_original_comment(base_text, nation="IT"):
    text = base_text.strip()
    if not text:
        return text
    words = text.split()
    for i, word in enumerate(words):
        clean = re.sub(r'[^\w]', '', word.lower())
        if clean in SYNONYMS and random.random() < 0.45:
            replacement = random.choice(SYNONYMS[clean])
            if word and word[0].isupper():
                replacement = replacement.capitalize()
            words[i] = replacement
    text = " ".join(words)
    prefixes = ["", "Davvero ", "Veramente ", "Assolutamente ", "Personalmente "] if nation.upper() in ["IT", "ITA"] else ["", "Really ", "Honestly ", "Definitely "]
    suffixes = ["", " 👍", " 🔥", "!", "."]
    if random.random() < 0.5:
        text = random.choice(prefixes) + text
    text += random.choice(suffixes)
    return text.strip()

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

    if not st.session_state.logged_in:
        st.markdown('<p class="main-header">BotCV</p>', unsafe_allow_html=True)
        st.subheader("Accedi al pannello")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Entra", use_container_width=True):
                    users = load_json(FILES["users"])
                    user = next((u for u in users if u["username"] == username and u["password"] == password), None)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Credenziali errate")
        st.info("Test: admin / admin123 oppure demo / demo123")
        st.stop()

check_login()

user = st.session_state.user
company = user["company"]

with st.sidebar:
    st.markdown(f"### 🤖 BotCV")
    st.markdown(f"**{company}**")
    st.caption(f"Operatore: {user['username']} ({user['role']})")
    st.divider()

    page = st.radio(
        "Navigazione",
        ["Overview", "Proxy", "Profili", "Prodotti", "Libreria Commenti", "Genera Commenti", "Log Attività", "Strumenti"],
        label_visibility="collapsed"
    )

    st.divider()
    if st.button("Esci", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

st.markdown(f'<p class="main-header">{page}</p>', unsafe_allow_html=True)
st.caption(f"Azienda: {company}")

def get_data(key):
    return load_json(FILES[key])

if page == "Overview":
    proxies = get_data("proxies")
    profiles = get_data("profiles")
    products = get_data("products")
    lib = get_data("comments_library")
    gen = get_data("generated_comments")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Proxy", len(proxies))
    c2.metric("Profili", len(profiles))
    c3.metric("Prodotti", len(products))
    c4.metric("Libreria", len(lib))
    c5.metric("Commenti generati", len(gen))

    ready = sum(1 for p in profiles if p.get("status") == "Ready")
    farming = sum(1 for p in profiles if "Farming" in str(p.get("status", "")))
    st.write(f"**Profili Ready:** {ready}  **In Farming:** {farming}")

    if profiles:
        st.subheader("Elenco profili")
        st.dataframe(pd.DataFrame(profiles), use_container_width=True, hide_index=True)

elif page == "Proxy":
    proxies = get_data("proxies")
    with st.expander("Aggiungi nuovo proxy", expanded=True):
        with st.form("add_proxy"):
            c1, c2 = st.columns(2)
            ip = c1.text_input("IP / Host")
            port = c2.text_input("Porta")
            user_p = st.text_input("Username (opzionale)")
            pwd = st.text_input("Password (opzionale)", type="password")
            country = st.text_input("Nazione (IT, US, DE...)")
            if st.form_submit_button("Salva proxy"):
                proxies.append({
                    "id": str(uuid.uuid4())[:8],
                    "ip": ip, "port": port, "user": user_p, "password": pwd,
                    "country": country.upper(), "company": company,
                    "created": datetime.now().isoformat()
                })
                save_json(FILES["proxies"], proxies)
                st.success("Proxy aggiunto")
                st.rerun()

    if proxies:
        st.dataframe(pd.DataFrame(proxies), use_container_width=True, hide_index=True)

elif page == "Profili":
    profiles = get_data("profiles")
    proxies = get_data("proxies")
    proxy_opts = [f"{p['ip']}:{p['port']} ({p.get('country','')})" for p in proxies]
    proxy_map = {opt: p["id"] for opt, p in zip(proxy_opts, proxies)}

    with st.expander("Aggiungi profilo", expanded=True):
        with st.form("add_profile"):
            name = st.text_input("Nome / Username")
            assigned = st.text_input("Assegnato a")
            proxy_choice = st.selectbox("Proxy", [""] + proxy_opts)
            notes = st.text_area("Note")
            if st.form_submit_button("Salva profilo"):
                profiles.append({
                    "id": str(uuid.uuid4())[:8],
                    "name": name, "assigned_to": assigned,
                    "proxy_id": proxy_map.get(proxy_choice, ""),
                    "status": "New", "farming_day": 0,
                    "notes": notes, "company": company,
                    "created": datetime.now().isoformat(), "ready_date": None
                })
                save_json(FILES["profiles"], profiles)
                st.success("Profilo aggiunto")
                st.rerun()

    if profiles:
        st.dataframe(pd.DataFrame(profiles), use_container_width=True, hide_index=True)

        st.subheader("Aggiorna stato farming")
        names = [p["name"] for p in profiles]
        sel = st.selectbox("Seleziona profilo", names)
        if sel:
            idx = names.index(sel)
            day = st.slider("Giorno farming", 0, 7, profiles[idx].get("farming_day", 0))
            if st.button("Aggiorna stato"):
                profiles[idx]["farming_day"] = day
                if day == 0:
                    profiles[idx]["status"] = "New"
                elif day < 7:
                    profiles[idx]["status"] = f"Farming Day {day}"
                else:
                    profiles[idx]["status"] = "Ready"
                    profiles[idx]["ready_date"] = datetime.now().isoformat()
                save_json(FILES["profiles"], profiles)
                st.success("Stato aggiornato")
                st.rerun()

elif page == "Prodotti":
    products = get_data("products")
    with st.expander("Aggiungi prodotto"):
        with st.form("add_product"):
            name = st.text_input("Nome prodotto")
            nation = st.text_input("Nazione target", "IT")
            desc = st.text_area("Descrizione")
            if st.form_submit_button("Salva"):
                products.append({
                    "id": str(uuid.uuid4())[:8],
                    "name": name, "nation": nation.upper(),
                    "description": desc,
                    "posts_count": 0, "comments_count": 0,
                    "company": company,
                    "created": datetime.now().isoformat()
                })
                save_json(FILES["products"], products)
                st.success("Prodotto aggiunto")
                st.rerun()

    if products:
        st.dataframe(pd.DataFrame(products), use_container_width=True, hide_index=True)

elif page == "Libreria Commenti":
    lib = get_data("comments_library")
    with st.expander("Aggiungi commento base"):
        with st.form("add_lib"):
            text = st.text_area("Testo commento", height=120)
            category = st.text_input("Categoria / Prodotto")
            if st.form_submit_button("Aggiungi alla libreria"):
                if text.strip():
                    lib.append({
                        "id": str(uuid.uuid4())[:8],
                        "text": text.strip(),
                        "category": category,
                        "company": company,
                        "created": datetime.now().isoformat()
                    })
                    save_json(FILES["comments_library"], lib)
                    st.success("Aggiunto")
                    st.rerun()

    if lib:
        st.dataframe(pd.DataFrame(lib), use_container_width=True, hide_index=True)

elif page == "Genera Commenti":
    lib = get_data("comments_library")
    products = get_data("products")
    gen = get_data("generated_comments")

    if not lib:
        st.warning("Aggiungi prima dei commenti nella Libreria.")
    else:
        c1, c2, c3 = st.columns(3)
        prod_names = [p["name"] for p in products] if products else ["Generico"]
        product = c1.selectbox("Prodotto", prod_names)
        nation = c2.text_input("Nazione", "IT")
        n = c3.number_input("Quanti generarne", 1, 20, 5)

        if st.button("Genera commenti originali", type="primary"):
            generated = []
            bases = [c["text"] for c in lib]
            for _ in range(n):
                base = random.choice(bases)
                text = generate_original_comment(base, nation)
                generated.append({
                    "id": str(uuid.uuid4())[:8],
                    "product": product,
                    "nation": nation.upper(),
                    "text": text,
                    "base_preview": base[:80],
                    "company": company,
                    "created": datetime.now().isoformat()
                })
            gen.extend(generated)
            save_json(FILES["generated_comments"], gen)
            st.success(f"Generati {n} commenti")
            for g in generated:
                st.markdown(f"**{g['text']}**")
                st.caption(f"Da: {g['base_preview']}")

    if gen:
        st.subheader("Commenti generati")
        st.dataframe(pd.DataFrame(gen[-20:]), use_container_width=True, hide_index=True)

elif page == "Log Attività":
    log = get_data("activity_log")
    with st.form("add_log"):
        profile = st.text_input("Profilo")
        action = st.selectbox("Azione", ["Like", "Scroll", "Commento leggero", "Commento prodotto", "Post", "Altro"])
        product = st.text_input("Prodotto")
        note = st.text_input("Nota")
        if st.form_submit_button("Registra attività"):
            log.append({
                "timestamp": datetime.now().isoformat(),
                "profile": profile, "action": action,
                "product": product, "note": note,
                "company": company
            })
            save_json(FILES["activity_log"], log)
            st.success("Registrato")
            st.rerun()

    if log:
        st.dataframe(pd.DataFrame(log[::-1]), use_container_width=True, hide_index=True)

elif page == "Strumenti":
    st.subheader("Export dati")
    all_data = {k: load_json(FILES[k]) for k in ["proxies", "profiles", "products", "comments_library", "generated_comments", "activity_log"]}

    def to_excel():
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for name, data in all_data.items():
                if data:
                    pd.DataFrame(data).to_excel(writer, sheet_name=name[:31], index=False)
        return output.getvalue()

    st.download_button(
        "Scarica Excel completo",
        data=to_excel(),
        file_name=f"botcv_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.subheader("Importa libreria commenti")
    bulk = st.text_area("Incolla commenti (uno per riga)", height=150)
    if st.button("Importa"):
        lines = [l.strip() for l in bulk.splitlines() if l.strip()]
        lib = load_json(FILES["comments_library"])
        for line in lines:
            lib.append({
                "id": str(uuid.uuid4())[:8],
                "text": line,
                "category": "import",
                "company": company,
                "created": datetime.now().isoformat()
            })
        save_json(FILES["comments_library"], lib)
        st.success(f"Importati {len(lines)} commenti")
        st.rerun()

    st.info("Prototipo BotCV – dati salvati localmente nella cartella `data`")
