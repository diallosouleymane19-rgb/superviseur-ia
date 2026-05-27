# -*- coding: utf-8 -*-
"""
utils/rendu_financier.py — Moteur de rendu financier structuré
SMD Consulting — Superviseur IA PCG France
Transforme les sorties narratives Mistral en KPIs + tableaux + alertes visuelles.
"""
import re
import streamlit as st
import pandas as pd
from typing import Optional


# ─── COULEURS SÉMANTIQUES ────────────────────────────────────────────────────
_COULEUR_OK      = "#2e7d32"   # vert
_COULEUR_WARN    = "#e65100"   # orange
_COULEUR_KO      = "#c62828"   # rouge
_COULEUR_INFO    = "#1a3a5c"   # bleu SMD
_BG_OK           = "#f1f8e9"
_BG_WARN         = "#fff3e0"
_BG_KO           = "#ffebee"
_BG_INFO         = "#e8f0fa"


# ─── HELPERS INTERNES ────────────────────────────────────────────────────────

def _couleur_signe(texte: str):
    t = texte.lower()
    if any(x in t for x in ["✅", "ok", "positif", "bon", "équilibr", "conforme", "excellent"]):
        return _COULEUR_OK, _BG_OK
    if any(x in t for x in ["⚠️", "attention", "modéré", "surveiller", "risque moyen"]):
        return _COULEUR_WARN, _BG_WARN
    if any(x in t for x in ["❌", "🚨", "critique", "négatif", "anomalie", "impayé", "alerte"]):
        return _COULEUR_KO, _BG_KO
    return _COULEUR_INFO, _BG_INFO


def _extraire_tables_markdown(texte: str):
    """Extrait les tableaux Markdown du texte et retourne (avant, table_df, après) pour chaque table."""
    # Regex pour capturer un tableau Markdown
    pattern = r'(\|[^\n]+\|\n\|[-| :]+\|\n(?:\|[^\n]+\|\n?)+)'
    blocs = re.split(pattern, texte)
    resultats = []
    for bloc in blocs:
        if bloc.strip().startswith('|') and '---' in bloc:
            try:
                lignes = [l.strip() for l in bloc.strip().split('\n') if l.strip()]
                headers = [h.strip() for h in lignes[0].split('|') if h.strip()]
                rows = []
                for ligne in lignes[2:]:
                    row = [c.strip() for c in ligne.split('|') if c.strip() != '']
                    if len(row) == len(headers):
                        rows.append(row)
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                    resultats.append(('table', df))
                    continue
            except Exception:
                pass
        if bloc.strip():
            resultats.append(('text', bloc))
    return resultats


def _extraire_kpis_inline(texte: str) -> list:
    """Détecte les patterns KPI : 'Label : Valeur' avec unités monétaires ou %."""
    kpis = []
    patterns = [
        r'\*\*([^*:]+?)\*\*\s*[:：]\s*([0-9][0-9 ,.]+\s*(?:€|EUR|FCFA|%|K€|M€|k€)?)',
        r'[-•]\s*\*\*([^*:]+?)\*\*\s*[:：]\s*([0-9][0-9 ,.]+\s*(?:€|EUR|FCFA|%|K€|M€|k€)?)',
        r'[-•]\s*([A-ZÀ-Ÿa-zà-ÿ][^:*\n]{3,30}?)\s*[:：]\s*([0-9][0-9 ,.]+\s*(?:€|EUR|FCFA|%|K€|M€|k€)?)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, texte):
            label = m.group(1).strip().rstrip(':').strip()
            valeur = m.group(2).strip()
            if len(label) > 3 and label not in [k[0] for k in kpis]:
                kpis.append((label, valeur))
    return kpis[:8]  # max 8 KPIs


def _extraire_alertes(texte: str) -> list:
    """Extrait les lignes contenant des indicateurs d'alerte."""
    alertes = []
    for ligne in texte.split('\n'):
        l = ligne.strip().lstrip('- •*').strip()
        if not l:
            continue
        if any(x in ligne for x in ['❌', '🚨', '⚠️', '✅', '[CRITIQUE]', '[FAIBLE]', '[MOYEN]',
                                     'CRITIQUE', 'ANOMALIE', 'ALERTE', 'ATTENTION']):
            alertes.append(l)
    return alertes


def _extraire_sections(texte: str) -> list:
    """Découpe le texte en sections par headers Markdown (## ou ###)."""
    sections = re.split(r'(#{2,4}\s+[^\n]+)', texte)
    resultats = []
    titre_courant = None
    for bloc in sections:
        if re.match(r'#{2,4}\s+', bloc):
            titre_courant = re.sub(r'^#{2,4}\s+', '', bloc).strip()
        else:
            contenu = bloc.strip()
            if contenu:
                resultats.append((titre_courant, contenu))
    return resultats


def _afficher_kpis(kpis: list):
    """Affiche les KPIs en colonnes avec st.metric."""
    if not kpis:
        return
    nb = min(len(kpis), 4)
    cols = st.columns(nb)
    for i, (label, valeur) in enumerate(kpis[:nb]):
        cols[i].metric(label=label, value=valeur)
    if len(kpis) > 4:
        nb2 = min(len(kpis) - 4, 4)
        cols2 = st.columns(nb2)
        for i, (label, valeur) in enumerate(kpis[4:4+nb2]):
            cols2[i].metric(label=label, value=valeur)


def _afficher_alerte(texte: str):
    """Affiche une ligne d'alerte dans le bon container Streamlit."""
    t = texte.lower()
    if any(x in texte for x in ['❌', '🚨', '[CRITIQUE]', 'CRITIQUE']):
        st.error(texte)
    elif any(x in texte for x in ['⚠️', '[MOYEN]', 'ATTENTION', 'ALERTE']):
        st.warning(texte)
    elif any(x in texte for x in ['✅', '[FAIBLE]']):
        st.success(texte)
    else:
        st.info(texte)


def _afficher_tableau(df: pd.DataFrame):
    """Affiche un DataFrame avec style professionnel."""
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


def _afficher_bloc_texte(titre: Optional[str], contenu: str):
    """Affiche un bloc de texte avec titre optionnel, en filtrant les KPIs déjà rendus."""
    # Supprimer les lignes KPI déjà extraites (patterns numériques)
    lignes_filtrees = []
    for ligne in contenu.split('\n'):
        l = ligne.strip()
        # Garder seulement les lignes substantielles non-KPI
        if l and not re.match(r'^[-•*]\s*\*\*[^*]+\*\*\s*[:：]\s*[0-9]', l):
            lignes_filtrees.append(ligne)
    texte_propre = '\n'.join(lignes_filtrees).strip()
    if not texte_propre:
        return
    if titre:
        st.markdown(f"**{titre}**")
    st.markdown(texte_propre)


# ─── FONCTION PRINCIPALE ─────────────────────────────────────────────────────

def afficher_rapport(
    texte: str,
    titre: str = "",
    afficher_kpis_auto: bool = True,
    afficher_alertes_auto: bool = True,
    afficher_tables_auto: bool = True,
    compact: bool = False
):
    """
    Rendu structuré d'un rapport IA narratif.
    Remplace st.markdown(rapport) dans app.py.

    Args:
        texte: Texte brut renvoyé par Mistral
        titre: Titre optionnel affiché en header
        afficher_kpis_auto: Extraire et afficher les KPIs en cards
        afficher_alertes_auto: Extraire et colorier les alertes
        afficher_tables_auto: Rendre les tableaux Markdown en DataFrames
        compact: Mode compact (expander pour la partie narrative)
    """
    if not texte or not texte.strip():
        st.info("Aucune analyse disponible.")
        return

    if titre:
        st.markdown(f"### {titre}")

    # 1. KPIs inline ─────────────────────────────────────────────────────────
    if afficher_kpis_auto:
        kpis = _extraire_kpis_inline(texte)
        if kpis:
            _afficher_kpis(kpis)
            st.divider()

    # 2. Alertes groupées ────────────────────────────────────────────────────
    if afficher_alertes_auto:
        alertes = _extraire_alertes(texte)
        if alertes:
            for alerte in alertes:
                _afficher_alerte(alerte)
            st.divider()

    # 3. Tables + texte ──────────────────────────────────────────────────────
    blocs = _extraire_tables_markdown(texte)
    tables_trouvees = any(t == 'table' for t, _ in blocs)

    if afficher_tables_auto and tables_trouvees:
        for type_bloc, contenu in blocs:
            if type_bloc == 'table':
                _afficher_tableau(contenu)
            else:
                # Texte restant affiché en expander si compact
                if compact:
                    with st.expander("📄 Détail narratif"):
                        _afficher_bloc_texte(None, contenu)
                else:
                    _afficher_bloc_texte(None, contenu)
    else:
        # Pas de tables : rendu section par section
        sections = _extraire_sections(texte)
        if len(sections) > 1:
            for titre_sec, contenu_sec in sections:
                if titre_sec:
                    st.markdown(f"**{titre_sec}**")
                _afficher_bloc_texte(None, contenu_sec)
        else:
            # Texte simple sans sections
            if compact:
                with st.expander("📄 Voir l'analyse complète"):
                    st.markdown(texte)
            else:
                st.markdown(texte)


# ─── RENDU SPÉCIALISÉ : SYNTHÈSE AVEC SCORE ──────────────────────────────────

def afficher_synthese_score(
    score: float,
    niveau: str,
    kpis: dict,
    controles: dict,
    anomalies: list,
    recommandations: list,
    devise: str = "€"
):
    """
    Rendu premium pour les modules d'audit avec score de qualité.
    Utilisé par Audit Balance, FEC, Benford.
    """
    # Score visuel ─────────────────────────────────────────────────────────
    col_score, col_info = st.columns([1, 3])
    with col_score:
        couleur = _COULEUR_OK if score >= 80 else _COULEUR_WARN if score >= 55 else _COULEUR_KO
        bg = _BG_OK if score >= 80 else _BG_WARN if score >= 55 else _BG_KO
        st.markdown(
            f"""<div style='background:{bg};border:2px solid {couleur};border-radius:12px;
            padding:20px;text-align:center;'>
            <div style='font-size:2.8em;font-weight:bold;color:{couleur}'>{score:.0f}%</div>
            <div style='font-size:1em;color:{couleur};font-weight:600'>{niveau}</div>
            </div>""",
            unsafe_allow_html=True
        )
    with col_info:
        nb_ok   = sum(1 for c in controles.values() if c.get('statut') == 'OK')
        nb_ko   = sum(1 for c in controles.values() if c.get('statut') == 'KO')
        nb_warn = sum(1 for c in controles.values() if c.get('statut') == 'WARNING')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Contrôles OK",    f"✅ {nb_ok}")
        c2.metric("Avertissements",  f"⚠️ {nb_warn}")
        c3.metric("Contrôles KO",    f"❌ {nb_ko}")
        c4.metric("Anomalies",       f"🔍 {len(anomalies)}")

    st.divider()

    # KPIs financiers ──────────────────────────────────────────────────────
    if kpis:
        st.markdown("#### 💰 Indicateurs Financiers")
        kpi_keys = {
            'total_debit':       ("Total Débit",     devise),
            'total_credit':      ("Total Crédit",    devise),
            'resultat_estime':   ("Résultat estimé", devise),
            'marge_pct':         ("Marge nette",     "%"),
            'nb_comptes':        ("Comptes actifs",  ""),
            'charges_totales':   ("Charges totales", devise),
            'produits_totaux':   ("Produits totaux", devise),
        }
        affichables = [(lab, f"{kpis[k]:,.0f} {u}".strip() if u != "%" else f"{kpis[k]:.1f}%")
                       for k, (lab, u) in kpi_keys.items() if k in kpis]
        if affichables:
            cols = st.columns(min(len(affichables), 4))
            for i, (lab, val) in enumerate(affichables[:4]):
                cols[i].metric(lab, val)
            if len(affichables) > 4:
                cols2 = st.columns(min(len(affichables) - 4, 4))
                for i, (lab, val) in enumerate(affichables[4:]):
                    cols2[i].metric(lab, val)

        # Répartition par classe ───────────────────────────────────────────
        if 'repartition_classes' in kpis and kpis['repartition_classes']:
            st.divider()
            st.markdown("#### 📚 Répartition par Classe Comptable")
            rep = kpis['repartition_classes']
            df_rep = pd.DataFrame(
                [(k, v) for k, v in rep.items()],
                columns=["Classe", "Nb écritures"]
            ).sort_values("Nb écritures", ascending=False)
            cols_rep = st.columns([2, 3])
            with cols_rep[0]:
                st.dataframe(df_rep, use_container_width=True, hide_index=True)
            with cols_rep[1]:
                st.bar_chart(df_rep.set_index("Classe"))

    st.divider()

    # Contrôles ────────────────────────────────────────────────────────────
    st.markdown("#### 🔍 Détail des Contrôles")
    rows_ctrl = []
    for nom_ctrl, ctrl in controles.items():
        s = ctrl.get('statut', '')
        icone = "✅" if s == 'OK' else "⚠️" if s == 'WARNING' else "❌"
        rows_ctrl.append({
            "Contrôle": nom_ctrl,
            "Statut": f"{icone} {s}",
            "Détail": ctrl.get('message', '')
        })
    if rows_ctrl:
        st.dataframe(pd.DataFrame(rows_ctrl), use_container_width=True, hide_index=True)

    st.divider()

    # Anomalies ────────────────────────────────────────────────────────────
    if anomalies:
        st.markdown("#### ⚠️ Anomalies Détectées")
        rows_anom = []
        for a in anomalies:
            g = a.get('gravite', 'INFO')
            icone = "🚨" if g == 'CRITIQUE' else "⚠️" if g == 'MOYENNE' else "ℹ️"
            rows_anom.append({
                "Gravité": f"{icone} {g}",
                "Type": a.get('type', ''),
                "Description": a.get('description', '')
            })
        df_anom = pd.DataFrame(rows_anom)
        st.dataframe(df_anom, use_container_width=True, hide_index=True)
        st.divider()

    # Recommandations ──────────────────────────────────────────────────────
    if recommandations:
        st.markdown("#### 💡 Recommandations")
        for i, reco in enumerate(recommandations, 1):
            st.markdown(
                f"""<div style='background:{_BG_INFO};border-left:4px solid {_COULEUR_INFO};
                padding:10px 14px;border-radius:0 6px 6px 0;margin:6px 0;
                font-size:0.92em;color:#1a3a5c'>
                <b>{i}.</b> {reco}</div>""",
                unsafe_allow_html=True
            )


# ─── RENDU SPÉCIALISÉ : TABLEAU FINANCIER ────────────────────────────────────

def afficher_tableau_financier(
    df: pd.DataFrame,
    titre: str = "",
    lignes_totaux: list = None,
    devise: str = "€"
):
    """
    Affiche un DataFrame financier avec mise en forme : totaux en gras, couleurs.
    """
    if titre:
        st.markdown(f"#### {titre}")

    if df is None or df.empty:
        st.info("Aucune donnée disponible.")
        return

    lignes_totaux = lignes_totaux or []

    def style_row(row):
        idx = row.name
        if idx in lignes_totaux or (isinstance(idx, str) and any(
            t.lower() in str(idx).lower() for t in ['total', 'résultat', 'solde', 'net']
        )):
            return ['background-color: #D6E4F0; font-weight: bold'] * len(row)
        return [''] * len(row)

    styled = df.style.apply(style_row, axis=1)

    # Formatage numérique des colonnes numériques
    for col in df.select_dtypes(include='number').columns:
        styled = styled.format({col: f"{{:,.0f}} {devise}".strip()})

    st.dataframe(styled, use_container_width=True)
