# -*- coding: utf-8 -*-
"""
utils/page_helpers.py - SMD Global Consulting LLC
Fonctions utilitaires partagées par toutes les pages (page_xxx).
Importées depuis les modules utils/ pour éviter les dépendances circulaires app.py.
"""
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import streamlit as st
import pandas as pd
import io

from utils.database import sauvegarder_analyse
from utils.ai import extraire_contenu_mistral
from utils.export_word import export_analyse_word
from utils.security import sanitize_filename
from utils.rendu_financier import afficher_rapport, afficher_synthese_score  # noqa: F401 — re-export


# =============================================================================
# DEMO
# =============================================================================

def is_demo() -> bool:
    return st.session_state.get("role") == "demo"


def banniere_demo():
    if is_demo():
        st.warning("👀 **Mode Démonstration** — Données fictives uniquement. Sauvegarde désactivée.")


# =============================================================================
# TRANSPARENCE IA (AI Act, art. 50)
# =============================================================================

MENTION_IA = ("Contenu généré par intelligence artificielle (Mistral AI). Il peut contenir des erreurs : "
              "à vérifier par un professionnel avant toute utilisation.")


def champ_exercice(label: str = "📅 Exercice", key: str = None, exemple: str = "2025") -> str:
    """Exercice à saisir : aucune valeur proposée par défaut."""
    return st.text_input(label, value="", placeholder=f"ex. {exemple}", key=key).strip()


def champs_remplis(**champs) -> bool:
    """Vrai si tous les champs sont remplis ; sinon affiche lesquels manquent.
    Ex. : champs_remplis(Exercice=exercice, **{"Date de clôture": date_cloture})"""
    manquants = [nom for nom, v in champs.items() if v is None or (isinstance(v, str) and not v.strip())]
    if manquants:
        st.warning("Renseignez d'abord : " + ", ".join(manquants) + ".")
        return False
    return True


def mention_ia():
    """Signale à l'utilisateur que le texte qui suit est produit par une IA."""
    st.caption("🤖 " + MENTION_IA)


def avec_mention_ia(texte) -> str:
    """Ajoute la mention IA à un texte exporté ou sauvegardé."""
    return f"{texte}\n\n---\n*{MENTION_IA}*"


def meta_ia(modele: str = "") -> dict:
    """Informations de marquage IA (AI Act, art. 50.2) pour un texte rédigé à l'instant par l'IA."""
    from datetime import datetime, timezone
    return {"mention": MENTION_IA, "modele": modele or "",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def afficher_contenu_ia(texte: str, cle: str, modele: str = "", masques: int = 0):
    """Affiche un texte rédigé par l'IA avec :
    - la mention visible (art. 50) ;
    - un marquage lisible par machine (art. 50.2) : bloc HTML portant la classe « st-key-contenu_ia_… »
      et un élément invisible data-ai-generated="true" avec le fournisseur, le modèle, la date
      et le type de source IPTC « trainedAlgorithmicMedia »."""
    from html import escape
    from utils.export_word import IPTC_IA
    m = meta_ia(modele)
    with st.container(key=f"contenu_ia_{cle}"):
        st.markdown(
            f'<span hidden data-ai-generated="true" data-ai-provider="Mistral AI" '
            f'data-ai-model="{escape(m["modele"] or "non précisé")}" data-ai-generation-date="{m["date"]}" '
            f'data-digital-source-type="{IPTC_IA}" data-ai-system="Superviseur IA Comptable"></span>',
            unsafe_allow_html=True)
        mention_ia()
        if masques:
            st.caption(f"🔒 {masques} identifiant(s) masqué(s) avant l'envoi à Mistral, remis en clair ici.")
        st.markdown(texte)


# =============================================================================
# SAUVEGARDE
# =============================================================================

def sauvegarder_si_autorise(type_analyse: str, resultat) -> bool:
    """Sauvegarde uniquement si pas en mode démo. Retourne True si sauvegardé."""
    if is_demo():
        st.info("💡 Sauvegarde désactivée en mode démonstration.")
        return False
    try:
        if sauvegarder_analyse(type_analyse=type_analyse, resultat=resultat):
            return True
        st.warning("⚠ Sauvegarde impossible : base de données indisponible. Réessayez plus tard.")
        return False
    except Exception as e:
        st.warning(f"⚠ Sauvegarde impossible : {e}")
        return False


def bouton_sauvegarde(type_analyse: str, resultat, libelle: str = "💾 Sauvegarder", key: str = None):
    """Bouton de sauvegarde qui fonctionne même placé sous un autre bouton (« Générer… »).
    La sauvegarde est faite dans le rappel (on_click), exécuté avant le rechargement de la page :
    un bouton classique imbriqué ne déclenche jamais son code, car le bouton parent redevient faux."""
    def _sauver():
        if is_demo():
            st.toast("💡 Sauvegarde désactivée en mode démonstration.")
        elif sauvegarder_si_autorise(type_analyse=type_analyse, resultat=resultat):
            st.toast(f"✅ {type_analyse} sauvegardé(e) pour 30 jours.")
    st.button(libelle, width="stretch", key=key or f"save_{type_analyse}", on_click=_sauver)


# =============================================================================
# EXPORT WORD
# =============================================================================

def generer_bouton_word(titre: str, contenu, ia=None):
    """Génère un bouton de téléchargement Word sécurisé.
    ia : meta_ia(...) si le texte est rédigé par l'IA (le fichier porte alors le marquage IA)."""
    try:
        texte_final = extraire_contenu_mistral(contenu)
        buf = export_analyse_word(titre, texte_final, ia=ia)
        st.download_button(
            f"📄 Télécharger {titre}",
            buf,
            f"{sanitize_filename(titre)}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
    except Exception:
        st.warning("⚠ Export Word temporairement indisponible. Copiez le contenu manuellement.")


# =============================================================================
# CHARGEMENT FICHIER
# =============================================================================

@st.cache_data(show_spinner=False)
def _charger_fichier_bytes(file_bytes: bytes, file_name: str, header: int = 0):
    buf = io.BytesIO(file_bytes)
    try:
        if est_tableur(file_name):
            return pd.read_excel(buf, header=header), None
        elif file_name.lower().endswith("txt"):
            # FEC (| ou tabulation) ou balance (;) : séparateur lu sur la ligne d'en-tête
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    entete = file_bytes.decode(enc).splitlines()[0] if file_bytes else ""
                    break
                except UnicodeDecodeError:
                    continue
            sep = max(["|", "\t", ";", ","], key=entete.count) if entete else "|"
            buf.seek(0)
            return pd.read_csv(buf, sep=sep, encoding=enc, header=header), None
        else:
            buf.seek(0)
            return pd.read_csv(buf, sep=None, engine="python", header=header), None
    except Exception as e:
        return None, str(e)


def charger_fichier(uploaded_file, header: int = 0):
    """Charge un fichier CSV ou XLSX en DataFrame (cache sur bytes)."""
    try:
        return _charger_fichier_bytes(uploaded_file.getvalue(), uploaded_file.name, header)
    except Exception as e:
        return None, str(e)


# =============================================================================
# APPEL MISTRAL SECURISE
# =============================================================================

def appel_mistral_securise(prompt: str, temperature: float = 0.3, label: str = "analyse"):
    from utils.ai import appel_mistral
    try:
        result = appel_mistral(prompt, temperature=temperature)
        if result["success"]:
            return result
        st.warning(f"⚠ L'IA est momentanément indisponible pour {label}. Réessayez dans quelques instants.")
        return {"success": False, "content": "", "error": result.get("error", "")}
    except Exception as e:
        st.warning(f"⚠ Connexion IA interrompue pour {label}.")
        return {"success": False, "content": "", "error": str(e)}
