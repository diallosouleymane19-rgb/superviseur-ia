# -*- coding: utf-8 -*-
"""
utils/permissions.py — SMD Consulting
Helpers Streamlit pour le contrôle d'accès basé sur les rôles (RBAC).
Compatible PCG France & SYSCOHADA.
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
                <span style='font-size:1.2em'>⛔</span>
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
                <span style='font-size:1.2em'>⚠</span>
                <strong style='color:#92400e'> Quota mensuel atteint</strong><br>
                <span style='color:#666;font-size:0.9em'>
                    Votre plan <b>{plan_label}</b> inclut <b>{limit} analyses/mois</b>.<br>
                    Passez au plan supérieur pour continuer à analyser.
                </span>
            </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.link_button("🚀 Mettre à niveau", "https://smd-consulting.com/upgrade")
        return False
    return True


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

    st.sidebar.markdown(f"""
        <div style='background:{color}12;border:1px solid {color}40;
                    padding:8px 12px;border-radius:6px;margin:4px 0 8px'>
            <div style='color:{color};font-weight:700;font-size:0.82em;
                        letter-spacing:.3px'>
                {role_label}
            </div>
            <div style='display:flex;align-items:center;gap:6px;margin-top:2px'>
                <span style='background:{plan_color};color:#fff;
                             font-size:0.68em;font-weight:600;
                             padding:1px 6px;border-radius:10px'>
                    {plan_label}
                </span>
                {f'<span style="color:#888;font-size:0.75em">{nom}</span>' if nom else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)


# ─── Sidebar : barre de quota ─────────────────────────────────────────────────

def afficher_quota_sidebar() -> None:
    """Affiche la barre de progression du quota mensuel dans la sidebar."""
    user_email = st.session_state.get("user_email", "")
    role       = st.session_state.get("role", "client")

    if role == "admin":
        st.sidebar.caption("♾ Quota illimité (Admin)")
        return

    user = get_user(user_email) if user_email else None
    if not user:
        return

    limit = get_quota_limit(user)
    if limit == -1:
        st.sidebar.caption("♾ Quota illimité (Enterprise)")
        return

    used = get_quota_used(user_email)
    pct  = min(100, int(used / limit * 100)) if limit > 0 else 0
    remaining = max(0, limit - used)

    if pct < 60:
        bar_color = "#22c55e"
        icon = "🟢"
    elif pct < 85:
        bar_color = "#f59e0b"
        icon = "🟡"
    else:
        bar_color = "#ef4444"
        icon = "🔴"

    st.sidebar.markdown(f"""
        <div style='font-size:0.78em;color:#555;margin:4px 0 2px'>
            {icon} Analyses ce mois :
            <b style='color:{bar_color}'>{used} / {limit}</b>
            <span style='color:#aaa'> ({remaining} restantes)</span>
        </div>
        <div style='background:#e5e7eb;border-radius:4px;height:5px;margin-bottom:2px'>
            <div style='background:{bar_color};width:{pct}%;
                        height:5px;border-radius:4px;
                        transition:width .3s'></div>
        </div>
    """, unsafe_allow_html=True)

    if pct >= 90:
        st.sidebar.warning("⚠ Quota presque épuisé — pensez à upgrader.")


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

    st.subheader("👥 Gestion des utilisateurs")

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
    st.dataframe(df_display, use_container_width=True)

    st.divider()
    st.subheader("📋 Audit logs (50 derniers)")
    logs = get_audit_logs(limit=50)
    if logs:
        df_logs