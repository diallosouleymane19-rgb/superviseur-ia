# -*- coding: utf-8 -*-
"""utils/page_accueil.py - Page d'accueil (charte finance pro clair)."""
import os
from datetime import datetime
from html import escape

import streamlit as st

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]

# Boutons d'accès rapide : libellé d'action -> page du menu
ACCES_RAPIDE = [
    ("Analyser une facture", "🧾 Analyse et comptabilisation de factures"),
    ("Contrôler une balance", "📊 Contrôle de balance"),
    ("Contrôler un FEC", "📂 Traitement FEC"),
    ("Compte de résultat", "📈 Compte de Résultat"),
    ("Bilan comptable", "📊 Bilan Comptable"),
    ("Rapport client", "📋 Rapport Client"),
]


def _date_fr(d):
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} {d.year}"


def _prochaine_echeance(maintenant):
    """Prochaine échéance IS/CFE à partir du calendrier fiscal vérifié."""
    from utils.veille_fiscale import calendrier_fiscal
    debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    for annee in (maintenant.year, maintenant.year + 1):
        for e in calendrier_fiscal(annee):
            if e["date"] >= debut:
                return e, (e["date"] - debut).days
    return None, None


def _kpis(user_email, plan):
    """Compteurs Supabase. Retourne des '—' si la base n'est pas joignable."""
    res = {"users": "—", "analyses": "—", "quota": "—", "last": "—", "sb_ok": False}
    try:
        from utils.db_supabase import get_supabase, supabase_disponible
        from utils.auth_rbac import get_quota_used, get_quota_limit, get_user, PLANS
        if not supabase_disponible():
            return res
        res["sb_ok"] = True
        sb = get_supabase()
        mois = datetime.now().strftime("%Y-%m")
        res["users"] = sb.table("users").select("id", count="exact").eq("is_active", True).execute().count or 0
        res["analyses"] = sb.table("analyses").select("id", count="exact").gte("created_at", mois + "-01").execute().count or 0
        u = get_user(user_email) if user_email else None
        used = get_quota_used(user_email) if user_email else 0
        limit = get_quota_limit(u) if u else PLANS.get(plan, {}).get("quota", 10)
        res["quota"] = f"{used} / {limit if limit != -1 else 'illimité'}"
        last = (u or {}).get("last_login", "")
        try:
            res["last"] = datetime.fromisoformat(last[:10]).strftime("%d/%m/%Y") if last else "Aujourd'hui"
        except ValueError:
            res["last"] = last[:10]
    except Exception:
        pass
    return res


def _mistral_configure():
    try:
        if st.secrets.get("MISTRAL_API_KEY"):
            return True
    except Exception:
        pass
    return bool(os.getenv("MISTRAL_API_KEY"))


MAIL_DEMO = ("mailto:contact@smdconsulting.pro?subject=Demande%20de%20d%C3%A9mo%20personnalis%C3%A9e"
             "&body=Bonjour%2C%0A%0AJe%20souhaite%20une%20d%C3%A9mo%20personnalis%C3%A9e%20du%20Superviseur%20IA%20Comptable.%0A%0A"
             "Cabinet%20%2F%20entreprise%20%3A%0AT%C3%A9l%C3%A9phone%20%3A%0ADisponibilit%C3%A9s%20%3A%0A")


def _vers_inscription():
    """Quitte la démonstration et ouvre l'onglet « Créer un compte » (plan gratuit)."""
    for k in ["authenticated", "user_email", "role", "nom", "plan", "cabinet", "pays_user", "login_time", "nav_page"]:
        st.session_state.pop(k, None)
    st.session_state["ouvrir_inscription"] = True


def _appel_action():
    """Boutons d'action pour les visiteurs en démonstration."""
    st.markdown("<div class='smd-cta'>Vous découvrez l'outil ? Testez-le sur votre propre dossier "
                "ou demandez une présentation adaptée à votre cabinet.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("Tester gratuitement sur un dossier", type="primary", width="stretch",
              on_click=_vers_inscription, key="cta_tester",
              help="Compte gratuit : 10 analyses par mois sur vos propres fichiers.")
    c2.link_button("Demander une démo personnalisée", MAIL_DEMO, width="stretch",
                   help="Ouvre un e-mail à contact@smdconsulting.pro")


def page_accueil(aller_a):
    """aller_a : callback qui change la page du menu (défini dans app.py)."""
    maintenant = datetime.now()
    email = st.session_state.get("user_email", "")
    nom = (st.session_state.get("nom") or st.session_state.get("user_nom")
           or (email.split("@")[0] if "@" in email else "Utilisateur"))
    plan = st.session_state.get("plan", "free")
    role = st.session_state.get("role", "client")

    if role == "demo":
        st.info("Mode démonstration : données fictives, sauvegarde désactivée.")

    st.markdown(
        f"<div class='smd-entete'><div><h1>Bienvenue à {escape(nom)}</h1>"
        f"<p>Superviseur IA Comptable, référentiel PCG France</p></div>"
        f"<div class='smd-date'>{_date_fr(maintenant)}</div></div>",
        unsafe_allow_html=True,
    )
    if role == "demo":
        _appel_action()

    ech, jours = _prochaine_echeance(maintenant)
    if ech:
        delai = "aujourd'hui" if jours == 0 else ("demain" if jours == 1 else f"dans {jours} jours")
        st.markdown(
            "<div class='smd-echeance' role='status'>"
            "<div class='lib'>Prochaine échéance fiscale</div>"
            f"<div class='date'>{ech['date'].strftime('%d/%m/%Y')}</div>"
            f"<div class='quoi'>{escape(ech['obligation'])}</div>"
            f"<div class='delai'>{delai}</div></div>",
            unsafe_allow_html=True,
        )

    k = _kpis(email, plan)
    st.markdown(
        "<div class='smd-ligne'>"
        f"<div><div class='lib'>Utilisateurs actifs</div><div class='val'>{escape(str(k['users']))}</div></div>"
        f"<div><div class='lib'>Analyses ce mois</div><div class='val'>{escape(str(k['analyses']))}</div></div>"
        f"<div><div class='lib'>Quota utilisé</div><div class='val'>{escape(str(k['quota']))}</div></div>"
        f"<div><div class='lib'>Dernière connexion</div><div class='val'>{escape(str(k['last']))}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Accès rapide")
    for ligne in (ACCES_RAPIDE[:3], ACCES_RAPIDE[3:]):
        cols = st.columns(3)
        for col, (libelle, cible) in zip(cols, ligne):
            col.button(libelle, width="stretch", on_click=aller_a, args=(cible,),
                       key=f"rapide_{cible}")

    st.subheader("Modules disponibles")
    groupes = [
        ("Analyse et contrôle", ["Factures (OCR)", "Contrôle de balance", "Loi de Benford", "Alertes", "Cohérence des données"]),
        ("États financiers", ["Bilan", "Compte de résultat et SIG", "TFT trésorerie", "Plan de financement", "Comparatif N/N-1"]),
        ("Gestion et clôture", ["Immobilisations", "Inventaire et clôture", "Rapprochement bancaire"]),
        ("Reporting et fiscal", ["FEC DGFiP", "TVA CA3/CA12", "Rapport client", "Veille fiscale"]),
    ]
    cols = st.columns(4)
    for col, (titre, items) in zip(cols, groupes):
        col.markdown(
            f"<div class='smd-modules'><h4>{titre}</h4><ul>"
            + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>",
            unsafe_allow_html=True,
        )

    sb = "<span class='smd-pastille ok'></span>Base de données connectée" if k["sb_ok"] \
        else "<span class='smd-pastille ko'></span>Base de données non joignable"
    ia = "<span class='smd-pastille ok'></span>Clé Mistral AI configurée" if _mistral_configure() \
        else "<span class='smd-pastille ko'></span>Clé Mistral AI absente"
    st.markdown(
        f"<div class='smd-statut'><span>{sb}</span><span>{ia}</span>"
        f"<span>Plan {escape(plan.capitalize())}</span><span>Rôle {escape(role.capitalize())}</span></div>",
        unsafe_allow_html=True,
    )
    st.caption("SMD Global Consulting LLC © 2026. PCG France, ANC 2014-03, RGPD. contact@smdconsulting.pro")
