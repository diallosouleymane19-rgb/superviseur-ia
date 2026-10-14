# -*- coding: utf-8 -*-
"""
utils/permissions.py — SMD Global Consulting LLC
Helpers Streamlit pour le contrôle d'accès basé sur les rôles (RBAC).
Superviseur IA PCG France.
"""

import streamlit as st
from utils.auth_rbac import (
    has_permission, ROLES, PLANS,
    get_quota_limit, get_quota_used,
    get_user, incrementer_quota, log_action,
)


# ─── Vérification de permission ───────────────────────────────────────────────

def check_permission(permission: str) -> bool:
    """Retourne True si l'utilisateur connecté a la permission."""
    role = st.session_state.get("role", "client")
    return has_permission(role, permission)


def require_permission(permission: str, message: str = None) -> None:
    """
    Bloque l'accès si l'utilisateur n'a pas la permission.
    Affiche un message et arrête l'exécution Streamlit.
    """
    if not check_permission(permission):
        st.markdown("""
            <div style='background:#fef2f2;border-left:4px solid #dc2626;
                        padding:14px 18px;border-radius:6px;margin:16px 0'>
                <span style='font-size:1.2em'></span>
                <strong style='color:#dc2626'> Accès restreint</strong><br>
                <span style='color:#666;font-size:0.9em'>
                    Votre rôle actuel ne permet pas d'accéder à cette fonctionnalité.<br>
                    Contactez votre administrateur SMD pour une montée en niveau.
                </span>
            </div>
        """, unsafe_allow_html=True)
        if message:
            st.info(message)
        st.stop()


def check_quota(action_type: str = "analyse", details: str = "") -> bool:
    """
    Vérifie et incrémente le quota.
    Retourne False (et affiche un warning) si quota dépassé.
    """
    user_email = st.session_state.get("user_email", "")
    role = st.session_state.get("role", "client")

    # Admin et démo ne sont pas limités
    if role in ("admin", "demo"):
        return True

    ok = incrementer_quota(user_email, action_type, details)
    if not ok:
        user = get_user(user_email) if user_email else None
        limit = get_quota_limit(user) if user else 0
        plan  = user.get("plan", "free") if user else "free"
        plan_label = PLANS.get(plan, {}).get("label", plan)
        st.markdown(f"""
            <div style='background:#fffbeb;border-left:4px solid #f59e0b;
                        padding:14px 18px;border-radius:6px;margin:16px 0'>
                <span style='font-size:1.2em'></span>
                <strong style='color:#92400e'> Quota mensuel atteint</strong><br>
                <span style='color:#666;font-size:0.9em'>
                    Votre plan <b>{plan_label}</b> inclut <b>{limit} analyses/mois</b>.<br>
                    Passez au plan supérieur pour continuer à analyser.
                </span>
            </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.button("Mettre à niveau", key="btn_upgrade_quota",
                      on_click=lambda: st.session_state.update(nav_page="💳 Tarifs & Abonnement"))
        return False
    return True


def compter_analyse(module: str, *empreinte) -> bool:
    """Décompte 1 analyse du quota pour un calcul lancé.
    Avec une empreinte (fichiers déposés, paramètres), le même calcul n'est compté qu'une fois
    par session : les réaffichages de Streamlit ne consomment rien.
    Retourne False (avertissement affiché) si le quota est atteint."""
    if empreinte:
        import hashlib
        h = hashlib.sha256()
        for p in empreinte:
            h.update(p if isinstance(p, (bytes, bytearray)) else str(p).encode("utf-8"))
        cle = f"{module}:{h.hexdigest()}"
        vus = st.session_state.setdefault("_analyses_comptees", set())
        if cle in vus:
            return True
        ok = check_quota(module)
        if ok:
            vus.add(cle)
        return ok
    return check_quota(module)


# ─── Sidebar : badge rôle ─────────────────────────────────────────────────────

def afficher_badge_role() -> None:
    """Affiche le badge rôle + plan dans la sidebar."""
    role  = st.session_state.get("role", "client")
    plan  = st.session_state.get("plan", "free")
    nom   = st.session_state.get("nom", "")

    role_info = ROLES.get(role, {"label": role.capitalize(), "color": "#6b7280"})
    plan_info = PLANS.get(plan, {"label": plan.capitalize(), "color": "#6b7280"})

    color      = role_info["color"]
    role_label = role_info["label"]
    plan_label = plan_info["label"]
    plan_color = plan_info["color"]

    import html as _html
    st.sidebar.markdown(
        f"<div class='smd-role'><div class='smd-role-lib'>{_html.escape(role_label)}</div>"
        f"<div class='smd-role-plan'><span class='smd-plan'>{_html.escape(plan_label)}</span>"
        + (f"<span class='smd-role-nom'>{_html.escape(nom)}</span>" if nom else "") + "</div></div>",
        unsafe_allow_html=True)


# ─── Sidebar : barre de quota ─────────────────────────────────────────────────

def afficher_quota_sidebar() -> None:
    """Affiche la barre de progression du quota mensuel dans la sidebar."""
    user_email = st.session_state.get("user_email", "")
    role       = st.session_state.get("role", "client")

    if role == "admin":
        st.sidebar.markdown("<div class='smd-quota'>Analyses illimitées (administrateur)</div>", unsafe_allow_html=True)
        return

    user = get_user(user_email) if user_email else None
    if not user:
        return

    limit = get_quota_limit(user)
    if limit == -1:
        st.sidebar.markdown("<div class='smd-quota'>Analyses illimitées (Entreprise)</div>", unsafe_allow_html=True)
        return

    used = get_quota_used(user_email)
    pct  = min(100, int(used / limit * 100)) if limit > 0 else 0
    remaining = max(0, limit - used)

    niveau = "ok" if pct < 60 else ("moyen" if pct < 85 else "haut")
    st.sidebar.markdown(
        f"<div class='smd-quota'>Analyses du cabinet ce mois : <b>{used} / {limit}</b> "
        f"({remaining} restantes)</div>"
        f"<div class='smd-jauge'><div class='smd-jauge-{niveau}' style='width:{pct}%'></div></div>",
        unsafe_allow_html=True)

    if pct >= 90:
        st.sidebar.warning("Quota presque épuisé : voyez l'offre supérieure dans Abonnement.")


# ─── Audit log automatique ────────────────────────────────────────────────────

def log_user_action(action: str, resource: str = "", details: str = "", app: str = "") -> None:
    """Raccourci pour logger une action depuis n'importe quel module."""
    user_email = st.session_state.get("user_email", "anonymous")
    log_action(user_email, action, resource, details, app)


# ─── Page admin : gestion utilisateurs ───────────────────────────────────────

def page_admin_users(app_name: str = "") -> None:
    """
    Page d'administration des utilisateurs.
    À appeler uniquement si role == 'admin'.
    """
    require_permission("*")  # admin seulement
    from utils.auth_rbac import lister_users, get_audit_logs
    import pandas as pd

    st.subheader("Gestion des utilisateurs")

    users = lister_users()
    if not users:
        st.info("Aucun utilisateur enregistré dans la base RBAC.")
        return

    df = pd.DataFrame(users)
    cols_display = ["email", "nom", "cabinet", "pays", "role", "plan",
                    "quota_used_month", "last_login", "created_at"]
    cols_display = [c for c in cols_display if c in df.columns]
    df_display = df[cols_display].copy()

    # Renommage pour affichage
    rename = {
        "email": "Email", "nom": "Nom", "cabinet": "Cabinet",
        "pays": "Pays", "role": "Rôle", "plan": "Plan",
        "quota_used_month": "Quota/mois", "last_login": "Dernière connexion",
        "created_at": "Créé le"
    }
    df_display = df_display.rename(columns=rename)
    st.dataframe(df_display, width="stretch")

    st.divider()
    st.subheader("Journal des actions (50 dernières)")
    logs = get_audit_logs(limit=50)
    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(df_logs, width="stretch", hide_index=True)
    else:
        st.info("Aucune action enregistrée pour le moment.")
