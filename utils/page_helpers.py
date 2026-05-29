# -*- coding: utf-8 -*-
"""
utils/page_helpers.py - SMD Consulting
Fonctions utilitaires partagées par toutes les pages (page_xxx).
Importées depuis les modules utils/ pour éviter les dépendances circulaires app.py.
"""
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
# SAUVEGARDE
# =============================================================================

def sauvegarder_si_autorise(type_analyse: str, resultat) -> bool:
    """Sauvegarde uniquement si pas en mode démo. Retourne True si sauvegardé."""
    if is_demo():
        st.info("💡 Sauvegarde désactivée en mode démonstration.")
        return False
    try:
        sauvegarder_analyse(type_analyse=type_analyse, resultat=resultat)
        return True
    except Exception as e:
        st.warning(f"⚠ Sauvegarde impossible : {e}")
        return False


# =============================================================================
# EXPORT WORD
# =============================================================================

def generer_bouton_word(titre: str, contenu):
    """Génère un bouton de téléchargement Word sécurisé."""
    try:
        texte_final = extraire_contenu_mistral(contenu)
        buf = export_analyse_word(titre, texte_final)
        st.download_button(
            f"📄 Télécharger {titre}",
            buf,
            f"{sanitize_filename(titre)}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
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
        if file_name.endswith("xlsx"):
            return pd.read_excel(buf, header=header), None
        elif file_name.endswith("txt"):
            buf.seek(0)
            return pd.read_csv(buf, sep="|", encoding="utf-8", header=header), None
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
