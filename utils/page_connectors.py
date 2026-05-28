# -*- coding: utf-8 -*-
"""
utils/page_connectors.py - SMD Consulting
Page de gestion des connecteurs ERP.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# --- Registre des connecteurs disponibles ---
CONNECTEURS = {
    "sage": {
        "nom": "Sage Business Cloud", "icone": "🟩", "couleur": "#00b050",
        "description": "Sage 50cloud, Sage 100, Sage Business Cloud Comptabilite",
        "auth_type": "oauth_token",
        "champs": [
            {"key": "access_token", "label": "Access Token OAuth2", "type": "password"},
        ],
        "docs": "https://developer.sage.com/accounting/reference/",
        "classe": "SageConnector",
        "module": "utils.connectors.sage_connector",
    },
    "cegid": {
        "nom": "Cegid", "icone": "🔵", "couleur": "#003f8a",
        "description": "Cegid Expert, Cegid Loop, Cegid XRP Flex",
        "auth_type": "oauth_client",
        "champs": [
            {"key": "client_id",     "label": "Client ID",         "type": "text"},
            {"key": "client_secret", "label": "Client Secret",     "type": "password"},
            {"key": "tenant_id",     "label": "Tenant ID (Azure)", "type": "text"},
            {"key": "subscription_key", "label": "Subscription Key Ocp-Apim", "type": "password"},
        ],
        "docs": "https://developer.cegid.com/",
        "classe": "CegidConnector",
        "module": "utils.connectors.cegid_connector",
    },
    "odoo": {
        "nom": "Odoo", "icone": "🟣", "couleur": "#714b67",
        "description": "Odoo 14 a 17, On-premise & Cloud",
        "auth_type": "credentials",
        "champs": [
            {"key": "url",      "label": "URL Odoo (ex: https://mon-erp.odoo.com)", "type": "text"},
            {"key": "db",       "label": "Nom de la base de donnees",               "type": "text"},
            {"key": "username", "label": "Email / Login",                           "type": "text"},
            {"key": "password", "label": "Mot de passe",                            "type": "password"},
        ],
        "docs": "https://www.odoo.com/documentation/17.0/developer/reference/external_api.html",
        "classe": "OdooConnector",
        "module": "utils.connectors.odoo_connector",
    },
    "quickbooks": {
        "nom": "QuickBooks Online", "icone": "🟢", "couleur": "#2ca01c",
        "description": "QuickBooks Online (US, UK, FR) — OAuth2",
        "auth_type": "oauth_token",
        "champs": [
            {"key": "access_token", "label": "Access Token OAuth2",        "type": "password"},
            {"key": "realm_id",     "label": "Realm ID (Company ID)",      "type": "text"},
            {"key": "sandbox",      "label": "Mode Sandbox (test)",        "type": "checkbox"},
        ],
        "docs": "https://developer.intuit.com/app/developer/qbo/docs",
        "classe": "QuickBooksConnector",
        "module": "utils.connectors.quickbooks_connector",
    },
    "pennylane": {
        "nom": "Pennylane", "icone": "🟡", "couleur": "#f5a623",
        "description": "Pennylane — logiciel comptable francais",
        "auth_type": "api_key",
        "champs": [
            {"key": "api_key", "label": "Cle API Pennylane", "type": "password"},
        ],
        "docs": "https://pennylane.readme.io/reference",
        "classe": "PennylaneConnector",
        "module": "utils.connectors.pennylane_connector",
    },
}


def _get_connector(erp_key, credentials):
    """Instancie le connecteur correspondant."""
    cfg = CONNECTEURS[erp_key]
    import importlib
    mod   = importlib.import_module(cfg["module"])
    klass = getattr(mod, cfg["classe"])
    return klass(credentials)


def _session_key(erp_key):
    return "connector_" + erp_key


def _creds_key(erp_key):
    return "connector_creds_" + erp_key


def page_connectors(app_name="pcg"):
    st.title("Connecteurs ERP")
    st.markdown(
        "Connectez votre logiciel comptable pour importer automatiquement "
        "la balance, les ecritures (FEC), le grand livre et les factures."
    )

    # --- Statut des connexions actives ---
    actifs = [k for k in CONNECTEURS if st.session_state.get(_session_key(k))]
    if actifs:
        st.success(
            str(len(actifs)) + " connecteur(s) actif(s) : "
            + ", ".join(CONNECTEURS[k]["nom"] for k in actifs)
        )
    st.markdown("---")

    # --- Onglets par ERP ---
    noms_onglets = [
        CONNECTEURS[k]["icone"] + " " + CONNECTEURS[k]["nom"]
        for k in CONNECTEURS
    ]
    tabs = st.tabs(noms_onglets)

    for tab, erp_key in zip(tabs, CONNECTEURS):
        cfg    = CONNECTEURS[erp_key]
        with tab:
            _render_connecteur_tab(erp_key, cfg, app_name)


def _render_connecteur_tab(erp_key, cfg, app_name):
    """Affiche l'onglet d'un connecteur : connexion + import."""
    couleur  = cfg["couleur"]
    est_conn = st.session_state.get(_session_key(erp_key), False)

    # Statut
    if est_conn:
        info = st.session_state.get(_session_key(erp_key) + "_info", "")
        st.markdown(
            "<div style='background:#f0fdf4;border-left:4px solid #16a34a;"
            "padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:12px'>"
            "<b style='color:#16a34a'>Connecte</b> — " + str(info) + "</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='background:#f8fafc;border-left:4px solid " + couleur + ";"
            "padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:12px'>"
            + cfg["description"] + " &nbsp;|&nbsp; "
            "<a href='" + cfg["docs"] + "' target='_blank'>Documentation API</a></div>",
            unsafe_allow_html=True
        )

    # Formulaire de connexion
    with st.expander("Parametres de connexion", expanded=not est_conn):
        creds = {}
        for champ in cfg["champs"]:
            if champ["type"] == "password":
                val = st.text_input(
                    champ["label"],
                    key=erp_key + "_" + champ["key"],
                    type="password",
                    value=st.session_state.get(_creds_key(erp_key), {}).get(champ["key"], "")
                )
            elif champ["type"] == "checkbox":
                val = st.checkbox(
                    champ["label"],
                    key=erp_key + "_" + champ["key"],
                    value=st.session_state.get(_creds_key(erp_key), {}).get(champ["key"], False)
                )
            else:
                val = st.text_input(
                    champ["label"],
                    key=erp_key + "_" + champ["key"],
                    value=st.session_state.get(_creds_key(erp_key), {}).get(champ["key"], "")
                )
            creds[champ["key"]] = val

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Tester la connexion", key="test_" + erp_key,
                         use_container_width=True, type="primary"):
                with st.spinner("Connexion en cours..."):
                    try:
                        conn   = _get_connector(erp_key, creds)
                        result = conn.tester_connexion()
                        if result.get("ok"):
                            st.session_state[_session_key(erp_key)]          = True
                            st.session_state[_session_key(erp_key) + "_info"] = result.get("info", "")
                            st.session_state[_creds_key(erp_key)]             = creds
                            st.success("Connexion reussie — " + result.get("info", ""))
                            st.rerun()
                        else:
                            st.error("Echec : " + result.get("error", "Erreur inconnue"))
                    except Exception as e:
                        st.error("Erreur : " + str(e))
        with col2:
            if est_conn and st.button("Deconnecter", key="disc_" + erp_key,
                                      use_container_width=True):
                st.session_state[_session_key(erp_key)] = False
                st.rerun()

    # Zone d'import (si connecte)
    if est_conn:
        st.markdown("#### Importer des donnees")
        exercice = st.number_input(
            "Exercice", min_value=2018, max_value=datetime.now().year,
            value=datetime.now().year - 1,
            key="ex_" + erp_key
        )
        type_import = st.selectbox(
            "Type de donnees",
            ["Balance generale", "Ecritures (FEC)", "Grand livre", "Factures fournisseurs", "Factures clients"],
            key="type_" + erp_key
        )

        if st.button("Importer", key="imp_" + erp_key,
                     use_container_width=True, type="primary"):
            with st.spinner("Import en cours depuis " + cfg["nom"] + "..."):
                try:
                    creds_saved = st.session_state.get(_creds_key(erp_key), {})
                    conn = _get_connector(erp_key, creds_saved)
                    conn.tester_connexion()

                    def _store_df(key, data, source):
                        """Stocke un DataFrame en session state avec garde 1MB."""
                        if data is None or data.empty:
                            return
                        size_mb = data.memory_usage(deep=True).sum() / 1_048_576
                        if size_mb > 1.0:
                            # Tronquer a 5000 lignes pour eviter le crash Streamlit Cloud
                            data = data.head(5000)
                            st.warning(
                                "Fichier volumineux (" + str(round(size_mb, 1)) + " MB) — "
                                "affichage limite aux 5 000 premieres lignes."
                            )
                        st.session_state[key]           = data
                        st.session_state["erp_source"]  = source

                    df = pd.DataFrame()
                    if type_import == "Balance generale":
                        df = conn.get_balance(int(exercice))
                        _store_df("erp_balance", df, cfg["nom"])
                    elif type_import == "Ecritures (FEC)":
                        df = conn.get_ecritures(int(exercice))
                        _store_df("erp_fec", df, cfg["nom"])
                    elif type_import == "Grand livre":
                        df = conn.get_grand_livre(int(exercice))
                        _store_df("erp_grand_livre", df, cfg["nom"])
                    elif "fournisseur" in type_import.lower():
                        df = conn.get_factures("fournisseur", int(exercice))
                        _store_df("erp_factures_fournisseur", df, cfg["nom"])
                    elif "clients" in type_import.lower():
                        df = conn.get_factures("client", int(exercice))
                        _store_df("erp_factures_client", df, cfg["nom"])

                    if df is not None and not df.empty:
                        st.success(
                            str(len(df)) + " lignes importees depuis "
                            + cfg["nom"] + " — exercice " + str(exercice)
                        )
                        st.dataframe(df.head(20), use_container_width=True)
                        st.caption("Apercu 20 premieres lignes. Donnees disponibles dans tous les modules d'analyse.")
                    else:
                        st.warning("Aucune donnee retournee. Verifiez les credentials et l'exercice.")

                except Exception as e:
                    st.error("Erreur import : " + str(e))

        # Donnees deja importees
        _afficher_donnees_importees(erp_key, cfg)


def _afficher_donnees_importees(erp_key, cfg):
    """Affiche un recap des donnees deja importees en session."""
    disponibles = []
    if st.session_state.get("erp_balance") is not None:
        df = st.session_state["erp_balance"]
        if not df.empty:
            disponibles.append("Balance (" + str(len(df)) + " comptes)")
    if st.session_state.get("erp_fec") is not None:
        df = st.session_state["erp_fec"]
        if not df.empty:
            disponibles.append("FEC (" + str(len(df)) + " ecritures)")
    if st.session_state.get("erp_grand_livre") is not None:
        df = st.session_state["erp_grand_livre"]
        if not df.empty:
            disponibles.append("Grand livre (" + str(len(df)) + " lignes)")
    if st.session_state.get("erp_factures_fournisseur") is not None:
        df = st.session_state["erp_factures_fournisseur"]
        if not df.empty:
            disponibles.append("Factures fournisseurs (" + str(len(df)) + ")")
    if st.session_state.get("erp_factures_client") is not None:
        df = st.session_state["erp_factures_client"]
        if not df.empty:
            disponibles.append("Factures clients (" + str(len(df)) + ")")

    if not disponibles:
        return

    source = st.session_state.get("erp_source", "ERP")
    st.success(
        "Donnees importees depuis **" + source + "** : "
        + ", ".join(disponibles)
        + ". Disponibles dans tous les modules d'analyse."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Effacer les donnees importees", key="clear_erp_" + erp_key):
            for k in ["erp_balance", "erp_fec", "erp_grand_livre",
                      "erp_factures_fournisseur", "erp_factures_client", "erp_source"]:
                st.session_state.pop(k, None)
            st.rerun()
