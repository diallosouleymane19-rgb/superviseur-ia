import streamlit as st
import requests
import json
import base64
import re
import sqlite3
import feedparser
from datetime import datetime

st.set_page_config(
    page_title="Superviseur IA Compta",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== STYLE ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .main { background: #0f1117; }
    .stApp { background: #0f1117; color: #e8e8e8; }
    .block-container { padding: 2rem 3rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #161b27 !important;
        border-right: 1px solid #2a2f3e;
    }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

    /* Cards */
    .card {
        background: #161b27;
        border: 1px solid #2a2f3e;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .card-accent {
        border-left: 3px solid #58a6ff;
    }
    .card-warning {
        border-left: 3px solid #f0883e;
        background: #1f1a14;
    }
    .card-success {
        border-left: 3px solid #3fb950;
        background: #0f1f12;
    }
    .card-danger {
        border-left: 3px solid #f85149;
        background: #1f0f0f;
    }

    /* Métriques */
    [data-testid="stMetric"] {
        background: #161b27;
        border: 1px solid #2a2f3e;
        border-radius: 8px;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stMetricValue"] { color: #e8e8e8 !important; font-family: 'IBM Plex Mono', monospace !important; }

    /* Boutons */
    .stButton > button {
        background: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-family: 'IBM Plex Sans', sans-serif;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #30363d;
        border-color: #58a6ff;
        color: #58a6ff;
    }
    [data-testid="baseButton-primary"] > button,
    .stButton > button[kind="primary"] {
        background: #1f6feb !important;
        color: white !important;
        border: none !important;
    }

    /* Inputs */
    .stTextArea textarea, .stTextInput input {
        background: #0d1117 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }

    /* Titres */
    h1 { color: #e8e8e8 !important; font-weight: 600 !important; letter-spacing: -0.02em; }
    h2 { color: #c9d1d9 !important; font-weight: 400 !important; }
    h3 { color: #8b949e !important; font-size: 0.85rem !important; text-transform: uppercase; letter-spacing: 0.08em; }

    /* Badge */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
    }
    .badge-blue { background: #1f3a5f; color: #58a6ff; }
    .badge-green { background: #0f2d17; color: #3fb950; }
    .badge-orange { background: #2d1f0a; color: #f0883e; }
    .badge-red { background: #2d0f0f; color: #f85149; }

    /* Header */
    .app-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.5rem 0 2rem 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 2rem;
    }
    .app-logo {
        font-size: 2rem;
    }
    .app-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #e8e8e8;
    }
    .app-subtitle {
        font-size: 0.8rem;
        color: #8b949e;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Divider */
    hr { border-color: #21262d !important; }

    /* Selectbox */
    .stSelectbox select, [data-baseweb="select"] {
        background: #0d1117 !important;
        color: #c9d1d9 !important;
        border-color: #30363d !important;
    }

    /* Info, warning boxes */
    .stAlert { border-radius: 6px !important; }

    /* Table */
    .dataframe { background: #161b27 !important; color: #c9d1d9 !important; }
    thead th { background: #21262d !important; color: #8b949e !important; }
</style>
""", unsafe_allow_html=True)

# ==================== CONFIG API ====================
def get_api_key():
    try:
        return st.secrets["MISTRAL_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ Clé API manquante. Ajoutez MISTRAL_API_KEY dans .streamlit/secrets.toml")
        st.stop()

# ==================== BASE DE DONNÉES ====================
DB_PATH = "superviseur_compta.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_analyse TEXT,
            num_facture TEXT,
            fournisseur TEXT,
            montant_ht REAL,
            tva REAL,
            montant_ttc REAL,
            compte_suggere TEXT,
            statut TEXT DEFAULT 'validé'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_detection TEXT,
            type_anomalie TEXT,
            description TEXT,
            montant REAL,
            statut TEXT DEFAULT 'en attente'
        )
    """)
    conn.commit()
    conn.close()

def extraire_compte_valide(valeur) -> str:
    if isinstance(valeur, dict):
        valeur = valeur.get("compte") or valeur.get("suggestion") or "606300"
        for v in (valeur if isinstance(valeur, dict) else {}).values():
            if isinstance(v, str) and re.match(r"^\d{6}$", v):
                return v
    if isinstance(valeur, (int, float)):
        return f"{int(valeur):06d}"
    if isinstance(valeur, str):
        cleaned = re.sub(r"[^0-9]", "", valeur)
        if len(cleaned) >= 6:
            return cleaned[:6]
    return "606300"

def sauvegarder_facture(infos: dict, statut: str = "validé"):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO factures (date_analyse, num_facture, fournisseur, montant_ht, tva, montant_ttc, compte_suggere, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            str(infos.get("num_facture", "")),
            str(infos.get("fournisseur", "")),
            float(infos.get("montant_ht", 0.0)),
            float(infos.get("tva", 0.0)),
            float(infos.get("montant_ttc", 0.0)),
            extraire_compte_valide(infos.get("compte_suggere", "606300")),
            statut
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"⚠️ Sauvegarde impossible : {e}")

def sauvegarder_anomalie(type_anomalie: str, description: str, montant: float = 0.0):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO anomalies (date_detection, type_anomalie, description, montant)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M"), type_anomalie, description, montant))
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"⚠️ Anomalie non sauvegardée : {e}")

def charger_historique():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM factures ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return rows

def charger_anomalies():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM anomalies ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return rows

def stats_dashboard():
    conn = sqlite3.connect(DB_PATH)
    nb_factures = conn.execute("SELECT COUNT(*) FROM factures").fetchone()[0]
    total_ht = conn.execute("SELECT SUM(montant_ht) FROM factures").fetchone()[0] or 0
    total_tva = conn.execute("SELECT SUM(tva) FROM factures").fetchone()[0] or 0
    nb_anomalies = conn.execute("SELECT COUNT(*) FROM anomalies WHERE statut='en attente'").fetchone()[0]
    conn.close()
    return nb_factures, total_ht, total_tva, nb_anomalies

init_db()

# ==================== UTILITAIRES ====================
def parse_montant(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[€$£\s]", "", str(val)).replace(",", ".")
    cleaned = re.sub(r"\.(?=.*\.)", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def extraire_contenu_mistral(result: dict) -> str:
    try:
        msg = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return ""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, list):
        for part in msg:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")
    return ""

def appel_mistral(messages: list, json_mode: bool = False, timeout: int = 40) -> dict:
    API_KEY = get_api_key()
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": "mistral-small-latest", "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        st.error("⏱️ API Mistral ne répond pas. Réessayez.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        msg = {401: "Clé API invalide.", 429: "Quota dépassé."}.get(code, str(e))
        st.error(f"❌ Erreur API {code} : {msg}")
        st.stop()
    except requests.exceptions.ConnectionError:
        st.error("🌐 Problème de connexion réseau.")
        st.stop()

def generer_fec(infos: dict) -> tuple[str, str]:
    date_raw = infos.get("date", datetime.now().strftime("%d/%m/%Y"))
    date_fec = datetime.now().strftime("%Y%m%d")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            date_fec = datetime.strptime(date_raw, fmt).strftime("%Y%m%d")
            break
        except:
            continue

    fournisseur = infos.get("fournisseur", "FOURNISSEUR")
    num_facture = infos.get("num_facture", "FAC000")
    compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))
    ht = parse_montant(infos.get("montant_ht", 0))
    tva = parse_montant(infos.get("tva", 0))
    ttc = parse_montant(infos.get("montant_ttc", 0))

    colonnes = "JournalCode;JournalLib;EcritureNum;EcritureDate;CompteNum;CompteLib;CompAuxNum;CompAuxLib;PieceRef;PieceDate;EcritureLib;Debit;Credit;EcritureLet;DateLet;ValidDate;Montantdevise;Idevise"

    def ligne(enum, cnum, clib, debit, credit):
        return f"ACH;Achats;{enum};{date_fec};{cnum};{clib};;;{num_facture};{date_fec};{fournisseur};{debit:.2f};{credit:.2f};;;;;"

    libelle = "Achat marchandise" if compte == "601000" else "Achat"
    lignes = [
        colonnes,
        ligne("1", compte, libelle, ht, 0),
        ligne("2", "445660", "TVA déductible", tva, 0),
        ligne("3", "401000", "Fournisseur", 0, ttc),
    ]
    contenu_csv = "\n".join(lignes).encode("utf-8-sig").decode("utf-8")
    nom = f"FEC_{num_facture}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return contenu_csv, nom

# ==================== VEILLE FISCALE ====================
FLUX_RSS = [
    {
        "nom": "DGFiP - Actualités fiscales",
        "url": "https://www.impots.gouv.fr/portail/files/media/flux_rss/actualites.xml",
        "icon": "🏛️"
    },
    {
        "nom": "Légifrance - Textes fiscaux",
        "url": "https://www.legifrance.gouv.fr/api/feed/loda",
        "icon": "⚖️"
    },
    {
        "nom": "Economie.gouv.fr",
        "url": "https://www.economie.gouv.fr/rss.xml",
        "icon": "📊"
    },
    {
        "nom": "Compta-Online",
        "url": "https://www.compta-online.com/rss.xml",
        "icon": "📰"
    },
    {
        "nom": "Francis Lefebvre",
        "url": "https://www.efl.fr/rss/actualites.xml",
        "icon": "📚"
    },
]

ECHEANCES_FISCALES = [
    {"date": "15/05/2026", "libelle": "Déclaration TVA CA3 — Avril 2026", "type": "TVA", "urgence": "normal"},
    {"date": "15/06/2026", "libelle": "Déclaration TVA CA3 — Mai 2026", "type": "TVA", "urgence": "normal"},
    {"date": "15/05/2026", "libelle": "Acompte IS — 1er acompte 2026", "type": "IS", "urgence": "urgent"},
    {"date": "30/06/2026", "libelle": "Liasse fiscale 2025 — dépôt limite", "type": "Liasse", "urgence": "critique"},
    {"date": "15/09/2026", "libelle": "Acompte IS — 2ème acompte 2026", "type": "IS", "urgence": "normal"},
    {"date": "01/09/2026", "libelle": "Facturation électronique obligatoire — PME", "type": "Réforme", "urgence": "critique"},
    {"date": "15/12/2026", "libelle": "Acompte IS — 3ème acompte 2026", "type": "IS", "urgence": "normal"},
]

def jours_restants(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, "%d/%m/%Y")
        return (d - datetime.now()).days
    except:
        return 999

# ==================== MENU SIDEBAR ====================
st.sidebar.markdown("""
<div style="padding: 1rem 0;">
    <div style="font-size: 1.5rem; font-weight: 700; color: #e8e8e8; letter-spacing: -0.02em;">
        🧾 Superviseur IA
    </div>
    <div style="font-size: 0.7rem; color: #58a6ff; font-family: 'IBM Plex Mono', monospace; margin-top: 0.2rem;">
        SMD Consulting — Souleymane Diallo
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()

menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Tableau de bord", "📄 Analyse factures", "🔍 Détection anomalies", "📰 Veille fiscale", "🗂️ Historique"],
    label_visibility="collapsed"
)

st.sidebar.divider()
st.sidebar.markdown("""
<div style="font-size: 0.7rem; color: #484f58; padding: 0.5rem 0;">
    <div>Version 2.0 — Avril 2026</div>
    <div style="margin-top: 0.3rem;">Moteur : Mistral AI</div>
    <div style="margin-top: 0.3rem;">SYSCOHADA · PCG · FEC</div>
</div>
""", unsafe_allow_html=True)

# ==================== TABLEAU DE BORD ====================
if menu == "🏠 Tableau de bord":
    st.markdown("""
    <div class="app-header">
        <div class="app-logo">🧾</div>
        <div>
            <div class="app-title">Superviseur IA Comptable</div>
            <div class="app-subtitle">SMD Consulting · Agent IA · PCG France</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    nb_factures, total_ht, total_tva, nb_anomalies = stats_dashboard()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Factures analysées", nb_factures)
    with col2:
        st.metric("Total HT traité", f"{total_ht:,.2f} €")
    with col3:
        st.metric("TVA collectée", f"{total_tva:,.2f} €")
    with col4:
        st.metric("⚠️ Anomalies en attente", nb_anomalies)

    st.markdown("<br>", unsafe_allow_html=True)

    # Échéances proches
    st.markdown("### Échéances fiscales à surveiller")
    echeances_proches = sorted(ECHEANCES_FISCALES, key=lambda x: jours_restants(x["date"]))

    for e in echeances_proches[:4]:
        j = jours_restants(e["date"])
        if j < 0:
            continue
        couleur = "card-danger" if j <= 15 else "card-warning" if j <= 30 else "card-accent"
        badge = "badge-red" if j <= 15 else "badge-orange" if j <= 30 else "badge-blue"
        st.markdown(f"""
        <div class="card {couleur}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="badge {badge}">{e['type']}</span>
                    <span style="margin-left:0.7rem; color:#e8e8e8; font-weight:500;">{e['libelle']}</span>
                </div>
                <div style="font-family:'IBM Plex Mono',monospace; color:#8b949e; font-size:0.85rem;">
                    {e['date']} — <strong style="color:{'#f85149' if j<=15 else '#f0883e' if j<=30 else '#58a6ff'}">J-{j}</strong>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Modules disponibles")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card card-success">
            <div style="font-size:1.5rem;">📄</div>
            <div style="font-weight:600; margin-top:0.5rem; color:#e8e8e8;">Analyse factures</div>
            <div style="font-size:0.8rem; color:#8b949e; margin-top:0.3rem;">OCR · JSON · FEC · PCG</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="card card-warning">
            <div style="font-size:1.5rem;">🔍</div>
            <div style="font-weight:600; margin-top:0.5rem; color:#e8e8e8;">Détection anomalies</div>
            <div style="font-size:0.8rem; color:#8b949e; margin-top:0.3rem;">Doublons · Écarts · Alertes</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="card card-accent">
            <div style="font-size:1.5rem;">📰</div>
            <div style="font-weight:600; margin-top:0.5rem; color:#e8e8e8;">Veille fiscale</div>
            <div style="font-size:0.8rem; color:#8b949e; margin-top:0.3rem;">DGFiP · Légifrance · RSS</div>
        </div>
        """, unsafe_allow_html=True)

# ==================== ANALYSE FACTURES ====================
elif menu == "📄 Analyse factures":
    st.title("📄 Analyse de factures")
    st.markdown("<div style='color:#8b949e; margin-bottom:1.5rem;'>Extraction automatique · Imputation PCG · Export FEC</div>", unsafe_allow_html=True)

    if "texte_facture" not in st.session_state:
        st.session_state.texte_facture = ""
    if "dernier_mode" not in st.session_state:
        st.session_state.dernier_mode = ""

    mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG, PNG)", "📄 PDF - Copier le texte"], horizontal=True)

    if mode != st.session_state.dernier_mode:
        st.session_state.texte_facture = ""
        st.session_state.dernier_mode = mode

    st.markdown("<br>", unsafe_allow_html=True)

    if mode == "📝 Texte manuel":
        exemple = "CARREFOUR MARKET\nTicket n° 12345\nDate: 25/04/2026\nMontant HT: 37.92 €\nTVA 20%: 7.58 €\nMontant TTC: 45.50 €"
        texte = st.text_area("Contenu de la facture :", value=st.session_state.texte_facture or exemple, height=180)
        st.session_state.texte_facture = texte

    elif mode == "📎 Upload Image (JPG, PNG)":
        fichier = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
        if fichier:
            bytes_data = fichier.read()
            ext = fichier.name.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            base64_data = base64.b64encode(bytes_data).decode()
            with st.spinner("Extraction OCR en cours..."):
                result = appel_mistral([{"role": "user", "content": [
                    {"type": "text", "text": "Extrais tout le texte visible de cette facture."},
                    {"type": "image_url", "image_url": f"data:{mime};base64,{base64_data}"}
                ]}])
                st.session_state.texte_facture = extraire_contenu_mistral(result).strip()
            st.success("✅ Texte extrait avec succès")

    elif mode == "📄 PDF - Copier le texte":
        st.info("💡 Ouvrez votre PDF, sélectionnez tout (Ctrl+A), copiez (Ctrl+C) et collez ci-dessous.")
        st.session_state.texte_facture = st.text_area("Texte du PDF :", value=st.session_state.texte_facture, height=180)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔍 Analyser la facture", type="primary"):
        texte = st.session_state.texte_facture
        if not texte.strip():
            st.error("⚠️ Veuillez entrer le contenu d'une facture.")
        else:
            with st.spinner("Analyse IA en cours..."):
                result = appel_mistral(
                    messages=[
                        {"role": "system", "content": (
                            "Tu es un expert-comptable français spécialisé PCG. "
                            "Retourne UNIQUEMENT un JSON valide avec exactement ces clés : "
                            "num_facture (string), date (DD/MM/YYYY), fournisseur (string), "
                            "montant_ht (number), tva (number), montant_ttc (number), "
                            "compte_suggere (string 6 chiffres), description (string courte). "
                            "Règles de comptes : marchandises/réassort → 601000 ; "
                            "fournitures/papeterie/bureau → 606300 ; "
                            "services/SaaS/abonnement → 604000 ; télécom → 626000 ; "
                            "transport/livraison → 624000 ; restaurant/repas → 625100 ; "
                            "carburant → 624100 ; loyer → 613000 ; assurance → 616000."
                        )},
                        {"role": "user", "content": texte[:4000]}
                    ],
                    json_mode=True
                )
                try:
                    infos = json.loads(extraire_contenu_mistral(result))
                except:
                    st.error("❌ Erreur d'analyse. Vérifiez le contenu saisi.")
                    st.stop()

                ht = parse_montant(infos.get("montant_ht", 0))
                tva = parse_montant(infos.get("tva", 0))
                ttc = parse_montant(infos.get("montant_ttc", 0))
                if ht and tva and abs((ht + tva) - ttc) > 0.05:
                    ttc = round(ht + tva, 2)
                    infos["montant_ttc"] = ttc

                compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="card card-success">', unsafe_allow_html=True)
                st.markdown("**✅ Analyse terminée**")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("N° facture", infos.get("num_facture", "?"))
                with col2:
                    st.metric("Date", infos.get("date", "?"))
                    st.metric("Compte PCG", compte)
                with col3:
                    st.metric("HT", f"{ht:.2f} €")
                    st.metric("TVA", f"{tva:.2f} €")

                st.metric("TTC", f"{ttc:.2f} €")

                if infos.get("description"):
                    st.markdown(f"<div style='color:#8b949e; font-size:0.85rem; margin-top:0.5rem;'>📝 {infos.get('description')}</div>", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                fec, nom_fec = generer_fec(infos)
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button("📥 Télécharger FEC (.csv)", fec, nom_fec, mime="text/csv")
                with col_dl2:
                    if st.button("💾 Sauvegarder dans l'historique"):
                        sauvegarder_facture(infos)
                        st.success("Sauvegardé !")

                # Vérification anomalie TTC
                if ttc > 10000:
                    sauvegarder_anomalie("Montant élevé", f"Facture {infos.get('num_facture')} — {infos.get('fournisseur')} — {ttc:.2f} €", ttc)
                    st.markdown("""
                    <div class="card card-warning">
                        ⚠️ <strong>Alerte superviseur</strong> — Montant TTC supérieur à 10 000 €. Vérification recommandée.
                    </div>
                    """, unsafe_allow_html=True)

# ==================== DÉTECTION ANOMALIES (3 MODULES) ====================
elif menu == "🔍 Détection anomalies":
    st.title("🔍 Détection d'anomalies")
    st.markdown("<div style='color:#8b949e; margin-bottom:1.5rem;'>Module 1 : Historique SQLite · Module 2 : Upload CSV/Excel · Module 3 : Temps réel</div>", unsafe_allow_html=True)

    # ── Fonctions utilitaires partagées ──────────────────────────────────────

    def afficher_resultats_analyse(analyse: dict):
        score = analyse.get("score_fiabilite", 0)
        couleur_score = "#3fb950" if score >= 80 else "#f0883e" if score >= 60 else "#f85149"
        resume = analyse.get("résumé", analyse.get("resume", ""))
        st.markdown(f"""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.75rem; color:#8b949e; text-transform:uppercase; letter-spacing:0.05em;">Score de fiabilité</div>
                    <div style="font-size:2.5rem; font-weight:700; color:{couleur_score}; font-family:'IBM Plex Mono',monospace;">{score}/100</div>
                </div>
                <div style="flex:1; margin-left:2rem; color:#c9d1d9;">{resume}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        anomalies = analyse.get("anomalies", [])
        if anomalies:
            st.markdown(f"#### {len(anomalies)} anomalie(s) détectée(s)")
            for a in anomalies:
                niveau = a.get("niveau_risque", "moyen")
                couleur_carte = {"critique": "card-danger", "élevé": "card-danger", "moyen": "card-warning", "faible": "card-accent"}.get(niveau, "card-accent")
                badge_couleur = {"critique": "badge-red", "élevé": "badge-red", "moyen": "badge-orange", "faible": "badge-blue"}.get(niveau, "badge-blue")
                montant = a.get("montant", 0)
                st.markdown(f"""
                <div class="card {couleur_carte}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div style="flex:1;">
                            <span class="badge {badge_couleur}">{niveau.upper()}</span>
                            <span style="margin-left:0.7rem; font-weight:600; color:#e8e8e8;">{a.get('type','')}</span>
                            <div style="margin-top:0.5rem; color:#8b949e; font-size:0.9rem;">{a.get('description','')}</div>
                        </div>
                        {f'<div style="font-family:IBM Plex Mono,monospace;color:#f0883e;white-space:nowrap;">{float(montant):.2f} €</div>' if montant else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                sauvegarder_anomalie(a.get("type",""), a.get("description",""), float(montant) if montant else 0.0)
        else:
            st.markdown('<div class="card card-success">✅ Aucune anomalie détectée.</div>', unsafe_allow_html=True)

        recommandations = analyse.get("recommandations", [])
        if recommandations:
            st.markdown("#### Recommandations superviseur")
            for i, r in enumerate(recommandations, 1):
                st.markdown(f"""
                <div class="card" style="padding:0.8rem 1.2rem;">
                    <span style="color:#58a6ff;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;">#{i:02d}</span>
                    <span style="margin-left:0.7rem;color:#c9d1d9;">{r}</span>
                </div>
                """, unsafe_allow_html=True)

    def lancer_analyse_ia(donnees_texte: str, type_analyse: str, seuil: float) -> dict | None:
        result = appel_mistral(
            messages=[
                {"role": "system", "content": (
                    "Tu es un expert-comptable et auditeur français. "
                    f"Type d'analyse : {type_analyse}. Seuil d'alerte : {seuil} €. "
                    "Retourne UNIQUEMENT un JSON valide avec : "
                    "résumé (string), "
                    "anomalies (liste d'objets : type, description, montant, niveau_risque parmi faible/moyen/élevé/critique), "
                    "recommandations (liste de strings), "
                    "score_fiabilite (integer 0-100)."
                )},
                {"role": "user", "content": donnees_texte[:7000]}
            ],
            json_mode=True
        )
        try:
            return json.loads(extraire_contenu_mistral(result))
        except:
            st.error("❌ Erreur d'analyse IA.")
            return None

    def verifier_doublon(fournisseur: str, montant_ttc: float, num_facture: str) -> list:
        """Cherche des doublons potentiels dans l'historique SQLite."""
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT num_facture, fournisseur, montant_ttc, date_analyse
            FROM factures
            WHERE fournisseur = ? AND ABS(montant_ttc - ?) < 0.10 AND num_facture != ?
            ORDER BY id DESC LIMIT 5
        """, (fournisseur, montant_ttc, num_facture)).fetchall()
        conn.close()
        return rows

    # ── Onglets des 3 modules ─────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🗄️ Module 1 — Historique SQLite",
        "📂 Module 2 — Upload CSV/Excel",
        "⚡ Module 3 — Temps réel (nouvelle facture)"
    ])

    # ═══════════════════════════════════════════════════════════════
    # MODULE 1 — Analyse automatique de l'historique SQLite
    # ═══════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Analyse de l'historique enregistré")
        st.markdown("<div style='color:#8b949e; font-size:0.85rem; margin-bottom:1rem;'>L'agent analyse toutes les factures déjà sauvegardées en base et détecte les anomalies automatiquement — sans rien coller.</div>", unsafe_allow_html=True)

        # Charger et afficher un aperçu de la base
        rows = charger_historique()
        nb = len(rows)

        if nb == 0:
            st.markdown('<div class="card card-accent">ℹ️ Aucune facture en base. Analysez d\'abord des factures dans le menu <strong>📄 Analyse factures</strong>.</div>', unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Factures en base", nb)
            col2.metric("Total HT", f"{sum(r[4] or 0 for r in rows):,.2f} €")
            col3.metric("Total TTC", f"{sum(r[6] or 0 for r in rows):,.2f} €")

            st.markdown("<br>", unsafe_allow_html=True)

            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                type_analyse_sql = st.selectbox("Type d'analyse", [
                    "Détection complète (recommandé)",
                    "Doublons de factures",
                    "Écarts TVA suspects",
                    "Comptes PCG mal imputés",
                    "Montants aberrants",
                ], key="type_sql")
            with col_opt2:
                seuil_sql = st.number_input("Seuil d'alerte (€)", min_value=0, value=5000, step=500, key="seuil_sql")

            if st.button("🔍 Analyser l'historique", type="primary", key="btn_sql"):
                # Construire un texte structuré depuis la base
                lignes = ["ID | Date | N°Facture | Fournisseur | HT | TVA | TTC | Compte"]
                for r in rows:
                    lignes.append(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]:.2f} | {r[5]:.2f} | {r[6]:.2f} | {r[7]}")

                # Détection de doublons algorithmique (sans IA)
                doublons_detectes = []
                vus = {}
                for r in rows:
                    cle = (str(r[3]).lower().strip(), round(float(r[6] or 0), 2))
                    if cle in vus:
                        doublons_detectes.append((r, vus[cle]))
                    else:
                        vus[cle] = r

                if doublons_detectes:
                    st.markdown(f"""
                    <div class="card card-danger">
                        <strong>🔴 {len(doublons_detectes)} doublon(s) détecté(s) algorithmiquement</strong>
                        <div style="font-size:0.85rem; color:#8b949e; margin-top:0.3rem;">Même fournisseur + même montant TTC</div>
                    </div>
                    """, unsafe_allow_html=True)
                    for d1, d2 in doublons_detectes:
                        st.markdown(f"""
                        <div class="card card-warning" style="padding:0.8rem 1.2rem;">
                            <span class="badge badge-red">DOUBLON</span>
                            <span style="margin-left:0.7rem; color:#e8e8e8;">{d1[3]}</span>
                            <span style="color:#484f58; margin:0 0.5rem;">·</span>
                            <span style="font-family:'IBM Plex Mono',monospace; color:#f0883e;">{d1[6]:.2f} €</span>
                            <div style="font-size:0.8rem; color:#484f58; margin-top:0.3rem;">
                                Facture #{d1[0]} ({d1[1]}) ↔ Facture #{d2[0]} ({d2[1]})
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        sauvegarder_anomalie("Doublon", f"Fournisseur {d1[3]} — {d1[6]:.2f} € en double (#{d1[0]} et #{d2[0]})", d1[6])

                # Analyse IA complémentaire
                with st.spinner("Analyse IA approfondie de l'historique..."):
                    analyse = lancer_analyse_ia("\n".join(lignes), type_analyse_sql, seuil_sql)
                    if analyse:
                        afficher_resultats_analyse(analyse)

    # ═══════════════════════════════════════════════════════════════
    # MODULE 2 — Upload fichier CSV / Excel
    # ═══════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Analyse d'un fichier export")
        st.markdown("<div style='color:#8b949e; font-size:0.85rem; margin-bottom:1rem;'>Exportez votre journal depuis Sage, Cegid, Pennylane ou EBP et uploadez le fichier directement.</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="card card-accent" style="padding:0.8rem 1.2rem; margin-bottom:1rem;">
            <div style="font-size:0.8rem; color:#8b949e;">Formats acceptés :</div>
            <div style="margin-top:0.3rem; color:#c9d1d9;">
                <span class="badge badge-blue">CSV</span>
                <span class="badge badge-blue" style="margin-left:0.5rem;">XLS / XLSX</span>
                <span class="badge badge-blue" style="margin-left:0.5rem;">TXT</span>
                <span class="badge badge-blue" style="margin-left:0.5rem;">FEC</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        fichier_upload = st.file_uploader(
            "Choisissez votre export comptable",
            type=["csv", "txt", "xls", "xlsx"],
            key="upload_anomalie"
        )

        col1, col2 = st.columns(2)
        with col1:
            type_analyse_up = st.selectbox("Type d'analyse", [
                "Détection complète (recommandé)",
                "Doublons de factures",
                "Écarts TVA suspects",
                "Comptes PCG mal imputés",
                "Rapprochement bancaire",
                "Anomalies de montants",
            ], key="type_up")
        with col2:
            seuil_up = st.number_input("Seuil d'alerte (€)", min_value=0, value=5000, step=500, key="seuil_up")

        if fichier_upload:
            ext = fichier_upload.name.split(".")[-1].lower()
            contenu_texte = ""

            try:
                if ext in ["csv", "txt"]:
                    # Détecter l'encodage
                    raw = fichier_upload.read()
                    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
                        try:
                            contenu_texte = raw.decode(enc)
                            break
                        except:
                            continue

                elif ext in ["xls", "xlsx"]:
                    try:
                        import pandas as pd
                        df = pd.read_excel(fichier_upload, nrows=500)
                        contenu_texte = df.to_csv(index=False, sep=";")
                        st.markdown(f"""
                        <div class="card card-success" style="padding:0.8rem 1.2rem; margin-bottom:0.5rem;">
                            ✅ Fichier Excel chargé — {len(df)} lignes · {len(df.columns)} colonnes
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander("Aperçu des données (10 premières lignes)"):
                            st.dataframe(df.head(10), use_container_width=True)
                    except ImportError:
                        st.error("❌ pandas non installé. Lancez : pip install pandas openpyxl")
                        st.stop()

            except Exception as e:
                st.error(f"❌ Erreur de lecture : {e}")
                st.stop()

            if contenu_texte:
                nb_lignes = len(contenu_texte.splitlines())
                st.markdown(f"<div style='color:#8b949e; font-size:0.85rem; margin-bottom:1rem;'>📄 {fichier_upload.name} · {nb_lignes} lignes chargées</div>", unsafe_allow_html=True)

                if st.button("🔍 Lancer la détection sur le fichier", type="primary", key="btn_upload"):
                    with st.spinner("Analyse IA du fichier..."):
                        analyse = lancer_analyse_ia(contenu_texte, type_analyse_up, seuil_up)
                        if analyse:
                            afficher_resultats_analyse(analyse)
        else:
            st.markdown("""
            <div class="card" style="text-align:center; padding:2rem; border-style:dashed;">
                <div style="font-size:2rem; margin-bottom:0.5rem;">📂</div>
                <div style="color:#8b949e;">Glissez-déposez votre fichier export ou cliquez pour parcourir</div>
                <div style="font-size:0.75rem; color:#484f58; margin-top:0.5rem;">Sage · Cegid · Pennylane · EBP · Export FEC DGFiP</div>
            </div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # MODULE 3 — Détection temps réel (vérification avant sauvegarde)
    # ═══════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### Vérification en temps réel")
        st.markdown("<div style='color:#8b949e; font-size:0.85rem; margin-bottom:1rem;'>Saisissez les informations d'une nouvelle facture avant de l'enregistrer. L'agent vérifie instantanément les doublons, la cohérence TVA et l'imputation PCG.</div>", unsafe_allow_html=True)

        with st.form("form_temps_reel"):
            col1, col2 = st.columns(2)
            with col1:
                tr_fournisseur = st.text_input("Fournisseur", placeholder="ORANGE SA")
                tr_num = st.text_input("N° facture", placeholder="FAC-2026-001")
                tr_date = st.text_input("Date (DD/MM/YYYY)", placeholder="27/04/2026")
            with col2:
                tr_ht = st.number_input("Montant HT (€)", min_value=0.0, step=0.01, format="%.2f")
                tr_tva = st.number_input("TVA (€)", min_value=0.0, step=0.01, format="%.2f")
                tr_compte = st.text_input("Compte PCG suggéré", placeholder="626000")

            tr_ttc = round(tr_ht + tr_tva, 2)
            st.markdown(f"<div style='color:#58a6ff; font-family:IBM Plex Mono,monospace;'>TTC calculé : <strong>{tr_ttc:.2f} €</strong></div>", unsafe_allow_html=True)

            submitted = st.form_submit_button("⚡ Vérifier maintenant", type="primary")

        if submitted and tr_fournisseur and tr_ht > 0:
            alertes = []

            # ── Vérification 1 : Doublon algorithmique ──
            doublons = verifier_doublon(tr_fournisseur, tr_ttc, tr_num)
            if doublons:
                for d in doublons:
                    alertes.append({
                        "niveau": "critique",
                        "titre": "Doublon potentiel détecté",
                        "detail": f"Facture #{d[0]} du {d[3]} — même fournisseur ({d[1]}) — même montant TTC ({d[2]:.2f} €)",
                        "badge": "badge-red",
                        "card": "card-danger"
                    })

            # ── Vérification 2 : Cohérence TVA ──
            if tr_ht > 0 and tr_tva > 0:
                taux_tva = round((tr_tva / tr_ht) * 100, 1)
                taux_attendus = [20.0, 10.0, 5.5, 2.1]
                taux_ok = any(abs(taux_tva - t) < 0.5 for t in taux_attendus)
                if not taux_ok:
                    alertes.append({
                        "niveau": "élevé",
                        "titre": f"Taux TVA inhabituel : {taux_tva}%",
                        "detail": f"Taux calculé : {taux_tva}% — Taux légaux FR : 20%, 10%, 5.5%, 2.1%. Vérifiez la facture.",
                        "badge": "badge-red",
                        "card": "card-danger"
                    })
                else:
                    alertes.append({
                        "niveau": "ok",
                        "titre": f"TVA cohérente : {taux_tva}%",
                        "detail": "Taux conforme aux taux légaux français.",
                        "badge": "badge-green",
                        "card": "card-success"
                    })

            # ── Vérification 3 : Montant élevé ──
            if tr_ttc > 10000:
                alertes.append({
                    "niveau": "moyen",
                    "titre": "Montant élevé",
                    "detail": f"TTC de {tr_ttc:.2f} € — Vérification superviseur recommandée au-delà de 10 000 €.",
                    "badge": "badge-orange",
                    "card": "card-warning"
                })

            # ── Vérification 4 : Compte PCG via IA ──
            if tr_compte and tr_fournisseur:
                with st.spinner("Vérification du compte PCG..."):
                    result_pcg = appel_mistral([
                        {"role": "system", "content": (
                            "Tu es expert-comptable PCG. "
                            "Retourne UNIQUEMENT un JSON avec : "
                            "compte_correct (boolean), "
                            "compte_recommande (string 6 chiffres), "
                            "explication (string courte)."
                        )},
                        {"role": "user", "content": f"Fournisseur : {tr_fournisseur}. Compte saisi : {tr_compte}. HT : {tr_ht}€. Est-ce correct selon le PCG ?"}
                    ], json_mode=True)
                    try:
                        pcg_check = json.loads(extraire_contenu_mistral(result_pcg))
                        if not pcg_check.get("compte_correct", True):
                            alertes.append({
                                "niveau": "moyen",
                                "titre": f"Compte PCG à vérifier — Recommandé : {pcg_check.get('compte_recommande', '?')}",
                                "detail": pcg_check.get("explication", ""),
                                "badge": "badge-orange",
                                "card": "card-warning"
                            })
                        else:
                            alertes.append({
                                "niveau": "ok",
                                "titre": f"Compte PCG validé : {tr_compte}",
                                "detail": pcg_check.get("explication", ""),
                                "badge": "badge-green",
                                "card": "card-success"
                            })
                    except:
                        pass

            # ── Affichage des alertes ──
            st.markdown("<br>", unsafe_allow_html=True)
            nb_alertes = sum(1 for a in alertes if a["niveau"] not in ["ok"])

            if nb_alertes == 0:
                st.markdown('<div class="card card-success">✅ <strong>Aucune anomalie détectée.</strong> Facture conforme — vous pouvez l\'enregistrer.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="card card-warning">
                    ⚠️ <strong>{nb_alertes} point(s) à vérifier</strong> avant enregistrement
                </div>
                """, unsafe_allow_html=True)

            for a in alertes:
                st.markdown(f"""
                <div class="card {a['card']}" style="padding:0.8rem 1.2rem;">
                    <span class="badge {a['badge']}">{a['niveau'].upper()}</span>
                    <span style="margin-left:0.7rem; font-weight:600; color:#e8e8e8;">{a['titre']}</span>
                    <div style="margin-top:0.4rem; color:#8b949e; font-size:0.85rem;">{a['detail']}</div>
                </div>
                """, unsafe_allow_html=True)

            # Sauvegarder les anomalies critiques
            for a in alertes:
                if a["niveau"] in ["critique", "élevé"]:
                    sauvegarder_anomalie(a["titre"], a["detail"], tr_ttc)

        elif submitted:
            st.error("⚠️ Veuillez renseigner au minimum le fournisseur et le montant HT.")

# ==================== VEILLE FISCALE ====================
elif menu == "📰 Veille fiscale":
    st.title("📰 Veille fiscale")
    st.markdown("<div style='color:#8b949e; margin-bottom:1.5rem;'>Actualités DGFiP · Légifrance · Échéances 2026</div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📅 Échéances fiscales", "📡 Flux RSS", "🤖 Résumé IA"])

    with tab1:
        st.markdown("### Calendrier fiscal 2026")
        echeances_triees = sorted(ECHEANCES_FISCALES, key=lambda x: jours_restants(x["date"]))
        for e in echeances_triees:
            j = jours_restants(e["date"])
            if j < -7:
                continue
            couleur = "card-danger" if j <= 15 else "card-warning" if j <= 30 else "card-accent"
            badge = "badge-red" if j <= 15 else "badge-orange" if j <= 30 else "badge-blue"
            statut = "PASSÉ" if j < 0 else f"J-{j}"
            st.markdown(f"""
            <div class="card {couleur}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="badge {badge}">{e['type']}</span>
                        <span style="margin-left:0.7rem; color:#e8e8e8; font-weight:500;">{e['libelle']}</span>
                    </div>
                    <div style="text-align:right; min-width:120px;">
                        <div style="font-family:'IBM Plex Mono',monospace; color:#8b949e; font-size:0.8rem;">{e['date']}</div>
                        <div style="font-family:'IBM Plex Mono',monospace; font-weight:700; color:{'#f85149' if j<=15 else '#f0883e' if j<=30 else '#58a6ff'};">{statut}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.markdown("### Sources d'actualité fiscale")
        if st.button("📡 Charger les flux RSS"):
            articles_trouves = 0
            for source in FLUX_RSS:
                try:
                    with st.spinner(f"Chargement {source['nom']}..."):
                        feed = feedparser.parse(source["url"])
                        if feed.entries:
                            st.markdown(f"**{source['icon']} {source['nom']}**")
                            for entry in feed.entries[:3]:
                                titre = entry.get("title", "Sans titre")
                                lien = entry.get("link", "#")
                                date_pub = entry.get("published", "")
                                st.markdown(f"""
                                <div class="card" style="padding:0.8rem 1.2rem;">
                                    <a href="{lien}" target="_blank" style="color:#58a6ff; text-decoration:none; font-weight:500;">{titre}</a>
                                    <div style="font-size:0.75rem; color:#484f58; margin-top:0.2rem; font-family:'IBM Plex Mono',monospace;">{date_pub}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                articles_trouves += 1
                        else:
                            st.caption(f"⚠️ {source['nom']} — flux non disponible")
                except Exception as ex:
                    st.caption(f"⚠️ {source['nom']} — erreur : {ex}")

            if articles_trouves == 0:
                st.info("Certains flux RSS nécessitent un accès réseau. Consultez directement impots.gouv.fr ou legifrance.gouv.fr")

        else:
            st.markdown("""
            <div class="card card-accent">
                <div style="color:#8b949e;">Sources configurées :</div>
                <ul style="color:#c9d1d9; margin-top:0.5rem;">
                    <li>🏛️ DGFiP — impots.gouv.fr</li>
                    <li>⚖️ Légifrance — legifrance.gouv.fr</li>
                    <li>📊 Économie.gouv.fr</li>
                    <li>📰 Compta-Online</li>
                    <li>📚 Francis Lefebvre</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.markdown("### Résumé IA de l'actualité fiscale")
        theme = st.selectbox("Thème", ["TVA 2026", "Impôt sur les sociétés", "Facturation électronique obligatoire", "Cotisations sociales", "Fiscalité internationale PME"])
        if st.button("🤖 Générer le résumé IA", type="primary"):
            with st.spinner("Génération en cours..."):
                result = appel_mistral([
                    {"role": "system", "content": "Tu es un expert-comptable et fiscaliste français. Fournis une synthèse claire, structurée et à jour sur le thème demandé, adaptée aux TPE/PME françaises en 2026. Inclus les points clés, les obligations légales et les conseils pratiques."},
                    {"role": "user", "content": f"Synthèse fiscale sur : {theme}. Date : {datetime.now().strftime('%B %Y')}."}
                ])
                resume = extraire_contenu_mistral(result)
                st.markdown(f"""
                <div class="card card-accent">
                    <div style="font-size:0.75rem; color:#58a6ff; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:1rem;">Synthèse IA · {theme}</div>
                    <div style="color:#c9d1d9; line-height:1.7;">{resume.replace(chr(10), '<br>')}</div>
                </div>
                """, unsafe_allow_html=True)

# ==================== HISTORIQUE ====================
elif menu == "🗂️ Historique":
    st.title("🗂️ Historique")

    tab1, tab2 = st.tabs(["📄 Factures analysées", "⚠️ Anomalies détectées"])

    with tab1:
        rows = charger_historique()
        if not rows:
            st.info("Aucune facture dans l'historique.")
        else:
            st.markdown(f"<div style='color:#8b949e; margin-bottom:1rem;'>{len(rows)} facture(s) enregistrée(s)</div>", unsafe_allow_html=True)
            # Totaux
            total_ht = sum(r[4] for r in rows if r[4])
            total_tva = sum(r[5] for r in rows if r[5])
            total_ttc = sum(r[6] for r in rows if r[6])
            col1, col2, col3 = st.columns(3)
            col1.metric("Total HT", f"{total_ht:,.2f} €")
            col2.metric("Total TVA", f"{total_tva:,.2f} €")
            col3.metric("Total TTC", f"{total_ttc:,.2f} €")
            st.markdown("<br>", unsafe_allow_html=True)

            for r in rows:
                st.markdown(f"""
                <div class="card" style="padding:0.8rem 1.2rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-family:'IBM Plex Mono',monospace; color:#58a6ff; font-size:0.8rem;">#{r[0]:04d}</span>
                            <span style="margin-left:0.7rem; color:#e8e8e8; font-weight:500;">{r[3] or '?'}</span>
                            <span style="margin-left:0.5rem; color:#484f58;">·</span>
                            <span style="margin-left:0.5rem; color:#8b949e; font-size:0.85rem;">{r[2] or ''}</span>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-family:'IBM Plex Mono',monospace; color:#3fb950; font-weight:600;">{(r[6] or 0):.2f} €</div>
                            <div style="font-size:0.75rem; color:#484f58;">Compte {r[7] or '?'} · {r[1] or ''}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        anomalies = charger_anomalies()
        if not anomalies:
            st.markdown('<div class="card card-success">✅ Aucune anomalie enregistrée.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color:#8b949e; margin-bottom:1rem;'>{len(anomalies)} anomalie(s) enregistrée(s)</div>", unsafe_allow_html=True)
            for a in anomalies:
                st.markdown(f"""
                <div class="card card-warning">
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <span class="badge badge-orange">{a[2] or 'Anomalie'}</span>
                            <div style="margin-top:0.4rem; color:#c9d1d9; font-size:0.9rem;">{a[3] or ''}</div>
                            <div style="font-size:0.75rem; color:#484f58; margin-top:0.2rem; font-family:'IBM Plex Mono',monospace;">{a[1] or ''}</div>
                        </div>
                        <div style="font-family:'IBM Plex Mono',monospace; color:#f0883e;">
                            {f"{float(a[4]):.2f} €" if a[4] else ''}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
