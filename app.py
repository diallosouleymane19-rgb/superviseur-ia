import streamlit as st
import requests
import json
import base64
import re
import sqlite3
import os
import feedparser
from datetime import datetime

st.set_page_config(page_title="Superviseur IA", page_icon="🤖", layout="centered")

# ==================== CONFIGURATION ====================
def get_api_key():
    try:
        return st.secrets["MISTRAL_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ Clé API manquante. Ajoutez MISTRAL_API_KEY dans .streamlit/secrets.toml")
        st.stop()

# ==================== BASE DE DONNÉES (historique) ====================
DB_PATH = "historique_factures.db"

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
            compte_suggere TEXT
        )
    """)
    conn.commit()
    conn.close()

def sauvegarder_facture(infos: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO factures (date_analyse, num_facture, fournisseur, montant_ht, tva, montant_ttc, compte_suggere)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        infos.get("num_facture", ""),
        infos.get("fournisseur", ""),
        parse_montant(infos.get("montant_ht", 0)),
        parse_montant(infos.get("tva", 0)),
        parse_montant(infos.get("montant_ttc", 0)),
        infos.get("compte_suggere", ""),
    ))
    conn.commit()
    conn.close()

def charger_historique():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM factures ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return rows

init_db()

# ==================== UTILITAIRES ====================
def parse_montant(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[€$£\s]", "", str(val))
    cleaned = cleaned.replace(",", ".")
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

def appel_mistral(messages: list, json_mode: bool = False, timeout: int = 30) -> dict:
    API_KEY = get_api_key()
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("⏱️ L'API Mistral ne répond pas (timeout 30s). Réessayez.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        msg = {
            401: "Clé API invalide ou expirée.",
            429: "Quota API dépassé. Patientez avant de réessayer.",
            500: "Erreur interne du serveur Mistral.",
        }.get(code, str(e))
        st.error(f"❌ Erreur API {code} : {msg}")
        st.stop()
    except requests.exceptions.ConnectionError:
        st.error("🌐 Impossible de joindre l'API Mistral. Vérifiez votre connexion.")
        st.stop()

def generer_fec(infos: dict) -> str:
    date_raw = infos.get("date", datetime.now().strftime("%d/%m/%Y"))
    try:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                date_obj = datetime.strptime(date_raw, fmt)
                date_fec = date_obj.strftime("%Y%m%d")
                break
            except ValueError:
                continue
        else:
            date_fec = datetime.now().strftime("%Y%m%d")
    except Exception:
        date_fec = datetime.now().strftime("%Y%m%d")

    fournisseur = infos.get("fournisseur", "FOURNISSEUR")
    num_facture = infos.get("num_facture", "FAC000")
    compte = infos.get("compte_suggere", "606300")
    ht  = parse_montant(infos.get("montant_ht", 0))
    tva = parse_montant(infos.get("tva", 0))
    ttc = parse_montant(infos.get("montant_ttc", 0))

    colonnes = (
        "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|"
        "CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|"
        "EcritureLet|DateLet|ValidDate|Montantdevise|Idevise"
    )

    def ligne(ecriture_num, compte_num, compte_lib, debit, credit):
        return (
            f"ACH|Achats|{ecriture_num}|{date_fec}|{compte_num}|{compte_lib}|"
            f"||{num_facture}|{date_fec}|{fournisseur}|"
            f"{debit:.2f}|{credit:.2f}|||||"
        )

    lignes = [
        colonnes,
        ligne("1", compte,   "Achat",          ht,  0),
        ligne("2", "445660", "TVA déductible", tva, 0),
        ligne("3", "401000", "Fournisseur",     0, ttc),
    ]
    return "\n".join(lignes)

# ==================== MENU ====================
menu = st.sidebar.selectbox("Menu", ["📄 Factures", "📰 Veille fiscale", "🗂️ Historique"])

# ==================== FACTURES ====================
if menu == "📄 Factures":
    st.title("🤖 Superviseur IA - Agent Comptable")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()

    if "texte_facture" not in st.session_state:
        st.session_state.texte_facture = ""
    if "dernier_mode" not in st.session_state:
        st.session_state.dernier_mode = ""

    mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG, PNG)", "📄 PDF - Copier le texte"])

    st.subheader("📄 Saisie de la facture")

    if mode != st.session_state.dernier_mode:
        st.session_state.texte_facture = ""
        st.session_state.dernier_mode = mode

    if mode == "📝 Texte manuel":
        exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
        texte = st.text_area(
            "Collez le texte de la facture :",
            value=st.session_state.texte_facture if st.session_state.texte_facture else exemple,
            height=150,
            key="texte_manuel"
        )
        st.session_state.texte_facture = texte

    elif mode == "📎 Upload Image (JPG, PNG)":
        fichier = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])

        if fichier is not None:
            st.success(f"✅ Fichier chargé : {fichier.name}")
            bytes_data = fichier.read()
            if len(bytes_data) > 5 * 1024 * 1024:
                st.error("❌ Image trop volumineuse (max 5 Mo). Compressez-la avant l'envoi.")
                st.stop()
            ext = fichier.name.lower().split(".")[-1]
            mime = "image/png" if ext == "png" else "image/jpeg"
            base64_data = base64.b64encode(bytes_data).decode()

            with st.spinner("🔍 OCR en cours..."):
                result = appel_mistral([{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrais le texte de cette facture de façon fidèle et complète."},
                        {"type": "image_url", "image_url": f"data:{mime};base64,{base64_data}"}
                    ]
                }])
                texte_extrait = extraire_contenu_mistral(result).strip()
                if not texte_extrait:
                    st.error("❌ Impossible d'extraire du texte de l'image. Vérifiez la qualité de la facture.")
                    st.stop()
                st.session_state.texte_facture = texte_extrait
                st.success("✅ Texte extrait avec succès !")
                st.text_area("Texte extrait :", value=texte_extrait, height=150)

    elif mode == "📄 PDF - Copier le texte":
        st.info("Ouvrez votre PDF, copiez le texte et collez-le ci-dessous.")
        texte = st.text_area(
            "Texte extrait du PDF",
            value=st.session_state.texte_facture,
            height=150,
            key="texte_pdf"
        )
        st.session_state.texte_facture = texte

    if st.button("🔍 Analyser", type="primary"):
        texte_a_analyser = st.session_state.texte_facture

        if not texte_a_analyser.strip():
            st.error("Veuillez entrer le texte d'une facture.")
        else:
            with st.spinner("Analyse en cours..."):
                result = appel_mistral(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un expert-comptable français. "
                                "Extrais les informations de la facture et retourne UNIQUEMENT un objet JSON valide avec ces clés : "
                                "num_facture, date (format DD/MM/YYYY), fournisseur, montant_ht (nombre), tva (nombre), montant_ttc (nombre), compte_suggere. "
                                "Règles de ventilation : marchandises→601000, fournitures bureau→606300, services→604000, télécom→626000, transport→624000. "
                                "Si un montant est absent, calcule-le (TTC = HT + TVA). "
                                "Retourne uniquement le JSON, sans texte autour."
                            )
                        },
                        {"role": "user", "content": texte_a_analyser[:4000]}
                    ],
                    json_mode=True
                )

                contenu = extraire_contenu_mistral(result)
                try:
                    infos = json.loads(contenu)
                except (json.JSONDecodeError, TypeError) as e:
                    st.error(f"❌ Réponse IA invalide : {e}")
                    st.stop()

                champs_requis = ["fournisseur", "montant_ttc"]
                manquants = [c for c in champs_requis if not infos.get(c)]
                if manquants:
                    st.warning(f"⚠️ Champs non détectés : {', '.join(manquants)}. Vérifiez la facture.")

                ht = parse_montant(infos.get("montant_ht", 0))
                tva = parse_montant(infos.get("tva", 0))
                ttc = parse_montant(infos.get("montant_ttc", 0))

                if abs((ht + tva) - ttc) > 0.05 and ht and tva:
                    ttc = round(ht + tva, 2)
                    infos["montant_ttc"] = ttc
                    st.info("ℹ️ Montant TTC recalculé à partir de HT + TVA.")

                st.success("✅ Analyse terminée")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("Date", infos.get("date", "?"))
                    st.metric("N° facture", infos.get("num_facture", "?"))
                with col2:
                    st.metric("Montant HT",  f"{ht:.2f} €")
                    st.metric("TVA",         f"{tva:.2f} €")
                    st.metric("Montant TTC", f"{ttc:.2f} €")

                compte = infos.get("compte_suggere", "606300")
                st.info(f"📝 Compte comptable suggéré : **{compte}**")

                fec = generer_fec(infos)
                st.download_button(
                    "📥 Télécharger le fichier FEC",
                    fec,
                    f"FEC_{infos.get('num_facture', 'facture')}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

                sauvegarder_facture(infos)
                st.caption("✔️ Facture sauvegardée dans l'historique.")

# ==================== VEILLE FISCALE ====================
elif menu == "📰 Veille fiscale":
    st.title("📰 Veille Fiscale Hebdomadaire")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()

    st.markdown("**Analyse automatique des publications officielles (JO, BOFiP, URSSAF)**")

    SOURCES_RSS = [
        {"nom": "Journal Officiel", "url": "https://www.legifrance.gouv.fr/rss/jo.rss"},
        {"nom": "BOFiP",            "url": "https://bofip.impots.gouv.fr/bofip/rss.xml"},
        {"nom": "URSSAF",           "url": "https://www.urssaf.fr/portail/home/actualites/rss.rss"},
    ]

    if st.button("📡 Générer la veille de la semaine", type="primary"):
        with st.spinner("🔍 Récupération des sources officielles..."):
            articles_bruts = []
            for source in SOURCES_RSS:
                try:
                    feed = feedparser.parse(source["url"])
                    for entry in feed.entries[:5]:
                        articles_bruts.append({
                            "source": source["nom"],
                            "titre": entry.title,
                            "lien": entry.link
                        })
                except Exception:
                    articles_bruts.append({
                        "source": source["nom"],
                        "titre": f"[Flux non disponible - {source['nom']}]",
                        "lien": "#"
                    })

            if not articles_bruts:
                st.warning("Aucun article récupéré. Vérifiez votre connexion.")
                st.stop()

            titres_str = "\n".join([f"- [{a['source']}] {a['titre']}" for a in articles_bruts])
            result = appel_mistral(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un expert-comptable et fiscaliste français. "
                            "Pour chaque titre d'article fourni, évalue son impact pour un cabinet comptable et suggère une action concrète. "
                            "Retourne UNIQUEMENT un JSON valide : liste d'objets avec les clés : source, titre, impact, action. "
                            "Sois concis (1 phrase par champ). Ne retourne que le JSON."
                        )
                    },
                    {"role": "user", "content": titres_str}
                ],
                json_mode=True
            )

            contenu = extraire_contenu_mistral(result)
            try:
                parsed = json.loads(contenu)
                articles = parsed if isinstance(parsed, list) else parsed.get("articles", parsed.get("items", []))
            except (json.JSONDecodeError, TypeError):
                st.error("❌ L'IA n'a pas pu analyser les articles. Réessayez.")
                st.stop()

            st.success(f"✅ {len(articles)} articles analysés")

            for i, article in enumerate(articles):
                lien = articles_bruts[i]["lien"] if i < len(articles_bruts) else "#"
                with st.expander(f"📌 {article.get('titre', '?')} — {article.get('source', '?')}"):
                    st.markdown(f"**Impact :** {article.get('impact', 'N/A')}")
                    st.markdown(f"**Action :** {article.get('action', 'N/A')}")
                    if lien != "#":
                        st.markdown(f"[📖 Lire l'article original]({lien})")

            html_parts = ["<html><head><meta charset='utf-8'></head><body>"]
            html_parts.append(f"<h1>Veille fiscale — {datetime.now().strftime('%d/%m/%Y')}</h1>")
            for a in articles:
                html_parts.append(
                    f"<h3>{a.get('titre','')}</h3>"
                    f"<p><b>Impact :</b> {a.get('impact','')}</p>"
                    f"<p><b>Action :</b> {a.get('action','')}</p><hr>"
                )
            html_parts.append("</body></html>")

            st.download_button(
                "📥 Télécharger la veille (HTML)",
                "\n".join(html_parts),
                f"veille_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html"
            )

# ==================== HISTORIQUE ====================
elif menu == "🗂️ Historique":
    st.title("🗂️ Historique des factures analysées")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()

    rows = charger_historique()

    if not rows:
        st.info("Aucune facture analysée pour l'instant.")
    else:
        st.markdown(f"**{len(rows)} facture(s) enregistrée(s)**")

        cols = st.columns([1, 2, 2, 1.5, 1.5, 1.5, 1.5])
        for col, label in zip(cols, ["ID", "Date analyse", "Fournisseur", "HT (€)", "TVA (€)", "TTC (€)", "Compte"]):
            col.markdown(f"**{label}**")
        st.divider()

        for row in rows:
            id_, date_a, num_fac, fournisseur, ht, tva, ttc, compte = row
            cols = st.columns([1, 2, 2, 1.5, 1.5, 1.5, 1.5])
            cols[0].write(id_)
            cols[1].write(date_a)
            cols[2].write(fournisseur or "—")
            cols[3].write(f"{ht:.2f}" if ht else "—")
            cols[4].write(f"{tva:.2f}" if tva else "—")
            cols[5].write(f"{ttc:.2f}" if ttc else "—")
            cols[6].write(compte or "—")

        st.divider()
        if st.button("🗑️ Vider l'historique", type="secondary"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM factures")
            conn.commit()
            conn.close()
            st.success("Historique vidé.")
            st.rerun()
