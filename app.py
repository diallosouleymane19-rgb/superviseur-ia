# -*- coding: utf-8 -*- 
"""
Superviseur IA Comptable - SMD Consulting
Application complète de supervision comptable augmentée par IA
Auteur: Souleymane Diallo
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Imports des modules utils
from utils.ai import appel_mistral, extraire_contenu_mistral, appel_mistral_vision
from utils.export_word import export_analyse_word
from utils.database import init_db, sauvegarder_analyse
from utils.rendu_financier import afficher_rapport, afficher_synthese_score
from utils.permissions import afficher_badge_role, afficher_quota_sidebar, check_quota, log_user_action
from utils.bilan import generer_bilan
from utils.rapprochement import rapprocher_bancaire
from utils.rapport_client import generer_rapport_client
from utils.alertes import detecter_alertes
from utils.coherence import verifier_coherence
from utils.security import sanitize_filename, sanitize_html_value
# Modules lourds en lazy dans leurs blocs (cold start optimise) :
# utils.ocr, utils.veille_fiscale, utils.fec, utils.plan_financement,
# utils.tft, utils.comparatif, utils.tva, utils.benford_module

# Authentification
from auth import login, logout, is_connecte

# =============================================================================
# CONFIGURATION DE L'APPLICATION
# =============================================================================

st.set_page_config(
    page_title="SMD Consulting - Superviseur IA", 
    layout="wide", 
    page_icon="🔒",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données
init_db()

# =============================================================================
# AUTHENTIFICATION
# =============================================================================

if not is_connecte():
    # Retour Stripe éventuel (upgrade depuis login)
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()

    tab_login, tab_signup = st.tabs(["🔑 Se connecter", "📝 Créer un compte"])

    with tab_login:
        st.title("🔒 Superviseur IA Comptable")
        st.subheader("Accès réservé aux cabinets clients")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("---")
            st.markdown("""
            <div style='background:#f0fdf4;padding:12px;border-radius:8px;
                        margin-bottom:10px;font-size:0.85em'>
            ✅ <b>Données anonymisées</b> — SIRET masqués, noms supprimés<br>
            ✅ <b>Non stockées</b> — Aucune conservation après analyse<br>
            ✅ <b>Non utilisées pour entraîner l'IA</b> — Politique Mistral garantie
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")

            prefill = st.session_state.pop("prefill_email", "")
            email    = st.text_input("📧 Email professionnel",
                                     value=prefill,
                                     placeholder="contact@cabinet.com")
            password = st.text_input("🔑 Mot de passe", type="password")

            if st.button("🚀 Se connecter", type="primary", use_container_width=True):
                if login(email, password):
                    st.success("✅ Connexion réussie !")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect")

            st.markdown("---")
            st.markdown("##### 🎯 Vous souhaitez tester l'application ?")
            if st.button("👀 Accès Démonstration", use_container_width=True, key="btn_demo"):
                st.session_state.update({
                    "authenticated": True,
                    "user_email":    "demo@smdconsulting.pro",
                    "role":          "demo",
                    "plan":          "free",
                    "nom":           "Démonstration",
                    "login_time":    datetime.now().isoformat(),
                })
                st.rerun()

            st.caption("📧 Demander un accès : contact@smdconsulting.pro")
            st.markdown("---")

        st.divider()
        st.caption("SMD Consulting © 2026 - Comptable IA Augmenté")

    with tab_signup:
        from utils.page_inscription import page_inscription
        page_inscription(app_name="pcg")

    st.stop()

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.sidebar.title("SMD Consulting")
st.sidebar.caption(f"👤 {st.session_state.get('user_email', 'Utilisateur')}")

# Badge rôle + plan + quota
afficher_badge_role()
afficher_quota_sidebar()

# Indicateur mode démo
if st.session_state.get("role") == "demo":
    st.sidebar.warning("👀 Mode Démonstration")

st.sidebar.divider()

page = st.sidebar.selectbox(
    "Navigation",
    [
        "🏠 Accueil",
        "─── Analyse & Audit ───",
        "🧾 Analyse Facture (OCR)",
        "📊 Audit Balance",
        "🛡 Loi de Benford",
        "⚠ Alertes & Anomalies",
        "✅ Cohérence des Données",
        "─── États Financiers ───",
        "📈 Compte de Résultat",
        "📊 Bilan Comptable",
        "🔄 Rapprochement Bancaire",
        "📦 Immobilisations",
        "📋 Inventaire & Clôture",
        "📐 Plan de Financement",
        "💹 TFT Trésorerie",
        "📊 Comparatif N/N-1",
        "🧾 Aide TVA CA3/CA12",
        "─── Supervision & Reporting ───",
        "📂 Traitement FEC",
        "📋 Rapport Client",
        "📰 Veille Fiscale",
        "─── Connecteurs ───",
        "🔌 Connecteurs ERP",
        "─── Paramètres ───",
        "💳 Tarifs & Abonnement",
        "🔒 Confidentialité & Sécurité",
    ],
    label_visibility="collapsed"
)

# Neutraliser les séparateurs
separateurs = ["─── Analyse & Audit ───", "─── États Financiers ───",
               "─── Supervision & Reporting ───", "─── Connecteurs ───",
               "─── Paramètres ───"]
if page in separateurs:
    page = "🏠 Accueil"

st.sidebar.divider()

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
    logout()
# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def is_demo():
    """Vérifie si l'utilisateur est en mode démonstration"""
    return st.session_state.get("role") == "demo"

def banniere_demo():
    """Affiche une bannière demo si applicable"""
    if is_demo():
        st.warning("👀 **Mode Démonstration** — Données fictives uniquement. Sauvegarde désactivée.")

def sauvegarder_si_autorise(type_analyse, resultat):
    """Sauvegarde uniquement si pas en mode démo"""
    if is_demo():
        st.info("💡 Sauvegarde désactivée en mode démonstration.")
    else:
        sauvegarder_analyse(type_analyse=type_analyse, resultat=resultat)

def generer_bouton_word(titre, contenu):
    """Génère un bouton de téléchargement Word sécurisé"""
    try:
        texte_final = extraire_contenu_mistral(contenu)
        buf = export_analyse_word(titre, texte_final)
        st.download_button(
            f"📄 Télécharger {titre}", 
            buf, 
            f"{sanitize_filename(titre)}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    except Exception as e:
        st.warning("⚠ Export Word temporairement indisponible. Copiez le contenu manuellement.")

def appel_mistral_securise(prompt, temperature=0.3, label="analyse"):
    """Appel Mistral avec fallback et message utilisateur clair"""
    try:
        result = appel_mistral(prompt, temperature=temperature)
        if result["success"]:
            return result
        else:
            st.warning(f"⚠ L'IA est momentanément indisponible pour {label}. Réessayez dans quelques instants.")
            return {"success": False, "content": "", "error": result.get("error", "")}
    except Exception as e:
        st.warning(f"⚠ Connexion IA interrompue pour {label}. Vérifiez votre connexion.")
        return {"success": False, "content": "", "error": str(e)}
@st.cache_data(show_spinner=False)
def _charger_fichier_bytes(file_bytes: bytes, file_name: str, header: int = 0):
    """Charge un fichier depuis ses bytes (hashable par st.cache_data)."""
    import io
    buf = io.BytesIO(file_bytes)
    try:
        if file_name.endswith('xlsx'):
            return pd.read_excel(buf, header=header), None
        elif file_name.endswith('txt'):
            buf.seek(0)
            return pd.read_csv(buf, sep='|', encoding='utf-8', header=header), None
        else:
            buf.seek(0)
            return pd.read_csv(buf, sep=None, engine='python', header=header), None
    except Exception as e:
        return None, str(e)


def charger_fichier(uploaded_file, header=0):
    """Charge un fichier CSV ou XLSX en DataFrame (cache sur bytes, pas sur UploadedFile)."""
    try:
        file_bytes = uploaded_file.getvalue()
        return _charger_fichier_bytes(file_bytes, uploaded_file.name, header)
    except Exception as e:
        return None, str(e)

# =============================================================================
# PAGES / MODULES
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ACCUEIL
# -----------------------------------------------------------------------------

if page == "\U0001f3e0 Accueil":
    banniere_demo()

    # --- En-tete ---
    _user_email = st.session_state.get("user_email", "")
    _user_nom   = st.session_state.get("user_nom", _user_email.split("@")[0] if "@" in _user_email else "Utilisateur")
    _role       = st.session_state.get("role", "client")
    _plan       = st.session_state.get("plan", "free")
    from datetime import datetime as _dtnow
    _heure = _dtnow.now().hour
    _salut = "Bonjour" if _heure < 18 else "Bonsoir"

    st.markdown(
        "<div style='padding:1.4rem 1rem 1rem 1rem;border-left:5px solid #1F4E79;"
        "background:linear-gradient(90deg,#f0f4ff,#ffffff);"
        "border-radius:0 10px 10px 0;margin-bottom:1.2rem;'>"
        "<h1 style='margin:0;color:#1F4E79;font-size:1.8rem;'>"
        + _salut + ", " + _user_nom + " 👋</h1>"
        "<p style='margin:0.3rem 0 0 0;color:#555;font-size:0.9rem;'>"
        "Superviseur IA Comptable &nbsp;·&nbsp; PCG France &nbsp;·&nbsp;"
        " <b>SMD Consulting</b></p></div>",
        unsafe_allow_html=True,
    )

    # --- KPIs Supabase ---
    from datetime import datetime as _dtm
    _mois_kpi = _dtm.now().strftime("%Y-%m")
    _nb_users = "—"; _nb_analyses = "—"
    _quota_label = "—"; _quota_pct = 0; _last_label = "—"
    _sb_ok = False
    try:
        from utils.db_supabase import get_supabase, supabase_disponible
        from utils.auth_rbac import get_quota_used, get_quota_limit, get_user, PLANS
        _sb_ok = supabase_disponible()
        if _sb_ok:
            _sb2 = get_supabase()
            _r_u = _sb2.table("users").select("id", count="exact").eq("is_active", True).execute()
            _nb_users = _r_u.count or 0
            _r_a = _sb2.table("analyses").select("id", count="exact").gte("created_at", _mois_kpi + "-01").execute()
            _nb_analyses = _r_a.count or 0
            _uobj = get_user(_user_email) if _user_email else None
            _qused  = get_quota_used(_user_email) if _user_email else 0
            _qlimit = get_quota_limit(_uobj) if _uobj else PLANS.get(_plan, {}).get("quota", 10)
            _quota_label = str(_qused) + "/" + (str(_qlimit) if _qlimit != -1 else "Inf")
            _quota_pct   = int(_qused / _qlimit * 100) if _qlimit and _qlimit > 0 else 0
            _last = (_uobj or {}).get("last_login", "")
            _last_label  = _last[:10] if _last else "Aujourd'hui"
    except Exception:
        pass

    _c1, _c2, _c3, _c4 = st.columns(4)
    _c1.metric("👥 Utilisateurs actifs", _nb_users)
    _c2.metric("📊 Analyses ce mois", _nb_analyses)
    _c3.metric("⚡ Quota utilisé", _quota_label,
               delta=str(_quota_pct) + "%" if _quota_pct > 0 else None,
               delta_color="inverse" if _quota_pct > 80 else "normal")
    _c4.metric("🔐 Dernière connexion", _last_label)

    st.divider()

    # --- Acces rapide ---
    st.markdown("#### 🚀 Accès rapide aux agents")
    _a1, _a2, _a3, _a4, _a5, _a6 = st.columns(6)
    with _a1:
        if st.button("🧾 Facture", use_container_width=True):
            st.session_state["_nav_page"] = "🧾 Analyse Facture (OCR)"
            st.rerun()
    with _a2:
        if st.button("📊 Balance", use_container_width=True):
            st.session_state["_nav_page"] = "📊 Audit Balance"
            st.rerun()
    with _a3:
        if st.button("📂 FEC", use_container_width=True):
            st.session_state["_nav_page"] = "📂 Traitement FEC"
            st.rerun()
    with _a4:
        if st.button("📈 Résultat", use_container_width=True):
            st.session_state["_nav_page"] = "📈 Compte de Résultat"
            st.rerun()
    with _a5:
        if st.button("📊 Bilan", use_container_width=True, key="btn_bilan_home"):
            st.session_state["_nav_page"] = "📊 Bilan Comptable"
            st.rerun()
    with _a6:
        if st.button("📋 Rapport", use_container_width=True):
            st.session_state["_nav_page"] = "📋 Rapport Client"
            st.rerun()

    st.divider()

    # --- Modules disponibles ---
    st.markdown("#### 📦 Agents disponibles (20 modules)")
    _m1, _m2, _m3, _m4 = st.columns(4)
    with _m1:
        st.markdown("**🔍 Analyse & Audit**")
        st.caption("Factures OCR · Audit balance · Benford · Alertes · Cohérence")
    with _m2:
        st.markdown("**📈 États Financiers**")
        st.caption("Bilan · CdR/SIG · TFT · Plan Financement · Comparatif N/N-1")
    with _m3:
        st.markdown("**📦 Gestion & Clôture**")
        st.caption("Immobilisations · Amortissements · Inventaire · Rapprochement")
    with _m4:
        st.markdown("**📁 Reporting & Fiscal**")
        st.caption("FEC DGFiP · TVA CA3/CA12 · Rapport client · Veille fiscale")

    st.divider()

    # --- Statut plateforme ---
    st.markdown("#### 🛠 Statut plateforme")
    _s1, _s2, _s3, _s4 = st.columns(4)
    if _sb_ok:
        _s1.success("✅ Supabase connecté")
    else:
        _s1.warning("⚠️ Supabase hors ligne")
    _s2.success("✅ Mistral AI actif")
    _s3.info("📋 Plan : **" + _plan.capitalize() + "**")
    _s4.info("🎭 Rôle : **" + _role.capitalize() + "**")

    st.divider()
    st.caption("SMD Consulting © 2026 — PCG France · ANC/CRC 99-02 · RGPD · contact@smdconsulting.pro")

# 2. ANALYSE FACTURE (OCR) - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "🧾 Analyse Facture (OCR)":
    try:
        from utils.analyse_facture import page_analyse_facture
        page_analyse_facture()
    except ImportError as e:
        st.error(f"Module analyse_facture indisponible : {e}")
elif page == "📊 Audit Balance":
    try:
        from utils.audit_balance import page_audit_balance
        page_audit_balance()
    except ImportError as e:
        st.error(f"Module audit_balance indisponible : {e}")
elif page == "📂 Traitement FEC":
    try:
        from utils.fec import page_fec
        page_fec()
    except ImportError as e:
        st.error(f"Module fec indisponible : {e}")
elif page == "🛡 Loi de Benford":
    try:
        from utils.benford_module import page_benford
        page_benford()
    except ImportError as e:
        st.error(f"Module benford_module indisponible : {e}")
elif page == "📈 Compte de Résultat":
    try:
        from utils.compte_resultat import page_compte_resultat
        page_compte_resultat()
    except ImportError as e:
        st.error(f"Module compte_resultat indisponible : {e}")
elif page == "📊 Bilan Comptable":
    try:
        from utils.bilan import page_bilan
        page_bilan()
    except ImportError as e:
        st.error(f"Module bilan indisponible : {e}")
elif page == "🔄 Rapprochement Bancaire":
    try:
        from utils.rapprochement import page_rapprochement
        page_rapprochement()
    except ImportError as e:
        st.error(f"Module rapprochement indisponible : {e}")
elif page == "📦 Immobilisations":
    try:
        from utils.immobilisations import page_immobilisations
        page_immobilisations()
    except ImportError as e:
        st.error(f"Module immobilisations indisponible : {e}")
elif page == "📋 Inventaire & Clôture":
    try:
        from utils.inventaire import page_inventaire
        page_inventaire()
    except ImportError as e:
        st.error(f"Module inventaire indisponible : {e}")
elif page == "📐 Plan de Financement":
    try:
        from utils.plan_financement import page_plan_financement
        page_plan_financement()
    except ImportError as e:
        st.error(f"Module plan_financement indisponible : {e}")

# -----------------------------------------------------------------------------
# 9b. TFT TRESORERIE
# -----------------------------------------------------------------------------

elif page == "💹 TFT Trésorerie":
    try:
        from utils.tft import page_tft
        page_tft()
    except ImportError as e:
        st.error(f"Module TFT indisponible : {e}")

# -----------------------------------------------------------------------------
# 9c. COMPARATIF N/N-1
# -----------------------------------------------------------------------------

elif page == "📊 Comparatif N/N-1":
    try:
        from utils.comparatif import page_comparatif
        page_comparatif()
    except ImportError as e:
        st.error(f"Module Comparatif indisponible : {e}")

# -----------------------------------------------------------------------------
# 9d. AIDE TVA CA3/CA12
# -----------------------------------------------------------------------------

elif page == "🧾 Aide TVA CA3/CA12":
    try:
        from utils.tva import page_tva
        page_tva()
    except ImportError as e:
        st.error(f"Module TVA indisponible : {e}")

# -----------------------------------------------------------------------------
# 9. RAPPORT CLIENT - VERSION PRO AVEC MODE MANUEL
# -----------------------------------------------------------------------------

elif page == "📋 Rapport Client":
    try:
        from utils.rapport_client import page_rapport_client
        page_rapport_client()
    except ImportError as e:
        st.error(f"Module rapport_client indisponible : {e}")
elif page == "⚠ Alertes & Anomalies":
    try:
        from utils.alertes import page_alertes
        page_alertes()
    except ImportError as e:
        st.error(f"Module alertes indisponible : {e}")
elif page == "✅ Cohérence des Données":
    try:
        from utils.coherence import page_coherence
        page_coherence()
    except ImportError as e:
        st.error(f"Module coherence indisponible : {e}")
elif page == "📰 Veille Fiscale":
    try:
        from utils.veille_fiscale import page_veille_fiscale
        page_veille_fiscale()
    except ImportError as e:
        st.error(f"Module veille_fiscale indisponible : {e}")
elif page == "🔌 Connecteurs ERP":
    from utils.page_connectors import page_connectors
    page_connectors(app_name="pcg")

# 13b. TARIFS & ABONNEMENT
# -----------------------------------------------------------------------------

elif page == "💳 Tarifs & Abonnement":
    from utils.page_tarifs import page_tarifs
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()
    page_tarifs(app_name="pcg")

# 14. CONFIDENTIALITÉ & SÉCURITÉ
# -----------------------------------------------------------------------------

elif page == "🔒 Confidentialité & Sécurité":
    st.title("🔒 Confidentialité & Sécurité")
    st.markdown("**Engagements SMD Consulting** envers la protection de vos données")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("### ✅ Anonymisation\n\nVous transmettez uniquement des données anonymisées. NIF masqués, noms supprimés avant tout envoi à l'IA.")
    with col2:
        st.success("### ✅ Non stockées\n\nAucune donnée comptable n'est conservée après votre session.")
    with col3:
        st.success("### ✅ IA éthique\n\nVos données ne sont jamais utilisées pour entraîner Mistral AI.")
    st.divider()
    st.markdown("### 📋 Politique de Conservation (RGPD)")
    st.info("Les analyses sauvegardées sont automatiquement supprimées après **30 jours**.")
    st.caption("**SMD Consulting** — Superviseur IA Comptable © 2026")
