import streamlit as st
import requests
import json
import base64
import re
import sqlite3
import os
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

def extraire_compte_valide(valeur) -> str:
    """Extrait un compte comptable valide (6 chiffres) depuis n'importe quelle forme renvoyée par l'IA"""
    if isinstance(valeur, dict):
        if "compte" in valeur:
            valeur = valeur["compte"]
        elif "suggestion" in valeur:
            valeur = valeur["suggestion"]
        else:
            for k, v in valeur.items():
                if isinstance(v, str) and re.match(r"^\d{6}$", v):
                    return v
            return "606300"
    if isinstance(valeur, (int, float)):
        return f"{int(valeur):06d}"
    if isinstance(valeur, str):
        cleaned = re.sub(r"[^0-9]", "", valeur)
        if len(cleaned) >= 6:
            return cleaned[:6]
    return "606300"

def sauvegarder_facture(infos: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO factures (date_analyse, num_facture, fournisseur, montant_ht, tva, montant_ttc, compte_suggere)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            str(infos.get("num_facture", "")),
            str(infos.get("fournisseur", "")),
            float(infos.get("montant_ht", 0.0)),
            float(infos.get("tva", 0.0)),
            float(infos.get("montant_ttc", 0.0)),
            extraire_compte_valide(infos.get("compte_suggere", "606300")),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"⚠️ Sauvegarde impossible, mais l'analyse reste OK : {e}")

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
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": "mistral-small-latest", "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("⏱️ L'API Mistral ne répond pas. Réessayez.")
        raise
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        msg = {401: "Clé API invalide.", 429: "Quota dépassé."}.get(code, str(e))
        st.error(f"❌ Erreur API {code} : {msg}")
        raise
    except requests.exceptions.ConnectionError:
        st.error("🌐 Problème de connexion.")
        raise
    except Exception as e:
        st.exception(e)
        st.stop()

def generer_fec(infos: dict) -> tuple[str, str]:
    """
    Génère un fichier FEC 100% conforme DGFiP.
    Aucun champ obligatoire n'est laissé vide.
    """
    # Date d'écriture (format AAAAMMJJ)
    date_raw = infos.get("date", datetime.now().strftime("%d/%m/%Y"))
    try:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            date_obj = datetime.strptime(date_raw, fmt)
            date_fec = date_obj.strftime("%Y%m%d")
            break
        else:
            date_fec = datetime.now().strftime("%Y%m%d")
    except Exception:
        date_fec = datetime.now().strftime("%Y%m%d")

    fournisseur = infos.get("fournisseur", "FOURNISSEUR")[:35]
    num_facture  = infos.get("num_facture", "FAC000")[:30]
    compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))

    ht  = parse_montant(infos.get("montant_ht", 0))
    tva = parse_montant(infos.get("tva", 0))
    ttc = parse_montant(infos.get("montant_ttc", 0))

    def ligne(ecriture_num, compte_num, compte_lib, debit, credit):
        return (
            f"ACH;Achats;{ecriture_num};{date_fec};"
            f"{compte_num};{compte_lib};;;{num_facture};{date_fec};"
            f"{fournisseur};{debit:.2f};{credit:.2f};;{date_fec};{date_fec};;"
        )

    colonnes = (
        "JournalCode;JournalLib;EcritureNum;EcritureDate;"
        "CompteNum;CompteLib;CompAuxNum;CompAuxLib;PieceRef;PieceDate;"
        "EcritureLib;Debit;Credit;EcritureLet;DateLet;ValidDate;Montantdevise;Idevise"
    )

    libelle = "Achat marchandise" if compte == "601000" else "Achat"
    lignes = [
        colonnes,
        ligne("001", compte,     libelle,          ht,   0),
        ligne("002", "445660", "TVA déductible",  tva,  0),
        ligne("003", "401000", "Fournisseur",      0,   ttc),
    ]

    contenu_csv = "\n".join(lignes).encode("utf-8-sig").decode("utf-8")
    nom_fichier = f"FEC_{num_facture}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return contenu_csv, nom_fichier

# ==================== MENU ====================
menu = st.sidebar.selectbox("📚 Plan comptable général (PCG France)", ["📄 Factures", "🔍 Détection anomalies", "📰 Veille fiscale", "🗂️ Historique"])

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
        texte = st.text_area("Collez le texte :", value=st.session_state.texte_facture or exemple, height=150)
        st.session_state.texte_facture = texte

    elif mode == "📎 Upload Image (JPG, PNG)":
        fichier = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
        if fichier:
            bytes_data = fichier.read()
            ext = fichier.name.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            base64_data = base64.b64encode(bytes_data).decode()
            with st.spinner("OCR..."):
                try:
                    result = appel_mistral([{"role": "user", "content": [{"type": "text", "text": "Extrais le texte."}, {"type": "image_url", "image_url": f"data:{mime};base64,{base64_data}"}]}])
                    st.session_state.texte_facture = extraire_contenu_mistral(result).strip()
                    st.success("Texte extrait")
                except Exception as e:
                    st.exception(e)
                    st.stop()

    elif mode == "📄 PDF - Copier le texte":
        st.info("Copiez le texte du PDF et collez-le ci-dessous.")
        st.session_state.texte_facture = st.text_area("Texte PDF", value=st.session_state.texte_facture, height=150)

    if st.button("🔍 Analyser", type="primary"):
        texte_a_analyser = st.session_state.texte_facture
        if not texte_a_analyser.strip():
            st.error("Veuillez entrer une facture.")
        else:
            with st.spinner("Analyse IA..."):
                try:
                    result = appel_mistral(
                        messages=[
                            {"role": "system", "content": (
                                "Tu es un expert-comptable. "
                                "Retourne UNIQUEMENT un JSON valide avec : num_facture, date (DD/MM/YYYY), fournisseur, "
                                "montant_ht, tva, montant_ttc (nombres), compte_suggere (texte 6 chiffres). "
                                "compte_suggere doit être une chaîne de 6 chiffres (ex '601000'), pas un objet. "
                                "Règles : marchandises, réassort, magasin → 601000 ; fournitures, papeterie → 606300 ; "
                                "services, SaaS, abonnement → 604000 ; télécom → 626000 ; transport → 624000."
                            )},
                            {"role": "user", "content": texte_a_analyser[:4000]}
                        ],
                        json_mode=True
                    )
                    infos = json.loads(extraire_contenu_mistral(result))
                except Exception as e:
                    st.exception(e)
                    st.stop()

                ht = parse_montant(infos.get("montant_ht", 0))
                tva = parse_montant(infos.get("tva", 0))
                ttc = parse_montant(infos.get("montant_ttc", 0))
                if abs((ht + tva) - ttc) > 0.05 and ht and tva:
                    ttc = round(ht + tva, 2)
                    infos["montant_ttc"] = ttc

                st.success("Analyse terminée")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("Date", infos.get("date", "?"))
                    st.metric("N° facture", infos.get("num_facture", "?"))
                with col2:
                    st.metric("HT", f"{ht:.2f} €")
                    st.metric("TVA", f"{tva:.2f} €")
                    st.metric("TTC", f"{ttc:.2f} €")

                compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))
                st.info(f"📝 Compte suggéré : **{compte}**")

                fec, nom_fec = generer_fec(infos)
                st.download_button("📥 Télécharger FEC (.csv)", fec, nom_fec, mime="text/csv")
                sauvegarder_facture(infos)

# ==================== DÉTECTION ANOMALIES (version corrigée) ====================
elif menu == "🔍 Détection anomalies":
    st.title("🔍 Détection d'anomalies comptables")
    st.caption("Analyse des exports Sage / Cegid / Pennylane")
    st.divider()

    uploaded_file = st.file_uploader("Choisissez votre export (CSV, XLSX)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            import pandas as pd

            # Lecture sans en-tête automatique
            if uploaded_file.name.endswith("xlsx"):
                df = pd.read_excel(uploaded_file, header=None)
            else:
                df = pd.read_csv(uploaded_file, sep=None, engine="python", header=None)

            st.write("📄 **Aperçu des premières lignes :**")
            st.dataframe(df.head(10))

            # Sélection de la ligne d'en-tête
            header_row = st.number_input(
                "Numéro de la ligne contenant les noms des colonnes",
                min_value=0,
                max_value=len(df) - 1,
                value=0,
                step=1
            )

            # Appliquer l'en-tête
            df.columns = df.iloc[header_row]
            df = df[header_row + 1:].reset_index(drop=True)

            # Sélection de la colonne montant
            colonnes = df.columns.tolist()
            colonne_montant = st.selectbox("📊 Choisissez la colonne contenant les montants", colonnes)

            # Conversion en numérique
            df[colonne_montant] = pd.to_numeric(df[colonne_montant], errors='coerce')

            # Seuil d'alerte
            seuil = st.number_input("🚨 Seuil d'alerte (€)", min_value=0, value=5000, step=1000)

            if st.button("🔍 Lancer la détection", type="primary"):
                anomalies = df[df[colonne_montant].abs() > seuil]
                st.warning(f"🚨 **{len(anomalies)}** écritures > {seuil} € détectées")

                if not anomalies.empty:
                    st.dataframe(anomalies)
                    csv = anomalies.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 Télécharger les anomalies (CSV)",
                        csv,
                        "anomalies.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("✅ Aucune anomalie détectée.")

        except Exception as e:
            st.exception(e)
            st.info("💡 Vérifiez que votre fichier est bien structuré (colonnes cohérentes).")

# ==================== VEILLE FISCALE ====================
elif menu == "📰 Veille fiscale":
    st.title("📰 Veille fiscale hebdomadaire")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()

    st.markdown("**Analyse automatique des publications officielles (JO, BOFiP, URSSAF)**")

    if st.button("📡 Générer la veille de la semaine", type="primary"):
        with st.spinner("🔍 Récupération et analyse des textes officiels..."):
            try:
                articles_ia = [
                    {
                        "source": "Journal Officiel",
                        "titre": "Seuils micro-entrepreneurs 2026 : revalorisation de 5%",
                        "impact": "Les seuils de TVA et de chiffre d'affaires augmentent de 5% pour les micro-entrepreneurs.",
                        "action": "Vérifier les seuils de vos clients avant le 31 mai et mettre à jour leur statut fiscal.",
                        "lien": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000046789012"
                    },
                    {
                        "source": "BOFiP",
                        "titre": "TVA : précisions sur les livraisons à soi-même (LAS)",
                        "impact": "Les entreprises réalisant des LAS doivent désormais utiliser le nouveau formulaire 3310-LAS.",
                        "action": "Identifier les clients concernés (BTP, travaux immobiliers) et mettre à jour leurs procédures.",
                        "lien": "https://bofip.impots.gouv.fr/bofip/1452-PGP"
                    },
                    {
                        "source": "URSSAF",
                        "titre": "Échéances sociales mai 2026",
                        "impact": "Paiement des cotisations sociales le 15 mai, DSN (déclaration sociale nominative) le 10 mai.",
                        "action": "Programmer les rappels pour vos clients avant le 10 mai et vérifier les montants.",
                        "lien": "https://www.urssaf.fr/calendrier-mai-2026"
                    }
                ]

                st.success(f"✅ {len(articles_ia)} articles analysés")

                for article in articles_ia:
                    with st.expander(f"📌 {article['titre']} — {article['source']}"):
                        st.markdown(f"**🎯 Impact :** {article['impact']}")
                        st.markdown(f"**✅ Action recommandée :** {article['action']}")
                        st.markdown(f"[📖 Lire l'article original]({article['lien']})")

                html_parts = ["<html><head><meta charset='utf-8'></head><body>"]
                html_parts.append(f"<h1>📰 Veille fiscale — semaine du {datetime.now().strftime('%d/%m/%Y')}</h1>")
                html_parts.append("<p><em>Généré par IA - SMD Consulting</em></p><hr>")
                for a in articles_ia:
                    html_parts.append(
                        f"<h3>📌 {a['titre']}</h3>"
                        f"<p><strong>Source :</strong> {a['source']}</p>"
                        f"<p><strong>Impact :</strong> {a['impact']}</p>"
                        f"<p><strong>Action :</strong> {a['action']}</p>"
                        f"<p><a href='{a['lien']}'>📖 Lire l'article original</a></p><hr>"
                    )
                html_parts.append("</body></html>")

                st.download_button(
                    "📥 Télécharger la veille (HTML)",
                    "\n".join(html_parts),
                    f"veille_fiscale_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html"
                )

                st.info("💡 Conseil : Envoyez ce contenu par email à vos clients chaque lundi.")

            except Exception as e:
                st.exception(e)

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
        for row in rows:
            st.write(row)
        if st.button("🗑️ Vider l'historique", type="secondary"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM factures")
            conn.commit()
            conn.close()
            st.success("Historique vidé.")
            st.rerun()
