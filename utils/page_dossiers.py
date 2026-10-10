# -*- coding: utf-8 -*-
"""
Page « Mes dossiers » : dossiers clients du cabinet et analyses sauvegardées
(retrouver, relire, retélécharger en Word, ranger dans un dossier, supprimer).
Les analyses sont conservées 30 jours (politique de confidentialité, art. 4) et partagées dans le cabinet.
"""
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from utils import database as D
from utils.security import sanitize_filename

SANS_DOSSIER = "Sans dossier"
TOUS = "Tous les dossiers"


def _date(iso) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone()
        return d.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(iso)[:16]


def _jours_restants(iso):
    if not iso:
        return None
    try:
        fin = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        import math
        return max(math.ceil((fin - datetime.now(timezone.utc)).total_seconds() / 86400), 0)
    except ValueError:
        return None


def _message():
    m = st.session_state.pop("dossiers_message", None)
    if m:
        (st.success if m[0] == "ok" else st.error)(m[1])


def _dire(ok, texte_ok, texte_ko):
    st.session_state["dossiers_message"] = ("ok", texte_ok) if ok else ("ko", texte_ko)


# ─── Actions (rappels exécutés avant le rechargement de la page) ─────────────

def _creer_dossier():
    nom = st.session_state.get("dos_nom", "").strip()
    if not nom:
        _dire(False, "", "Le nom du client est obligatoire.")
        return
    cid = D.creer_client(nom, st.session_state.get("dos_siret", "").strip(), st.session_state.get("dos_secteur", "").strip(),
                         st.session_state.get("dos_contact", "").strip(), st.session_state.get("dos_email", "").strip())
    _dire(bool(cid), f"Dossier « {nom} » créé.", "Création impossible : base de données indisponible.")
    if cid:
        for k in ("dos_nom", "dos_siret", "dos_secteur", "dos_contact", "dos_email"):
            st.session_state[k] = ""
        if isinstance(cid, int) and not isinstance(cid, bool):
            st.session_state["dossier_id"] = cid   # devient le dossier en cours


def _supprimer_dossier(cid, nom):
    ok = D.supprimer_client(cid)
    if ok and st.session_state.get("dossier_id") == cid:
        st.session_state["dossier_id"] = 0
    _dire(ok, f"Dossier « {nom} » supprimé. Ses analyses sont conservées, sans dossier.", "Suppression impossible.")


def _modifier_dossier(cid):
    g = lambda k: st.session_state.get(f"{k}_{cid}", "").strip()
    ok = D.modifier_client(cid, g("mod_nom"), g("mod_siret"), g("mod_secteur"), g("mod_contact"), g("mod_email"))
    _dire(ok, "Dossier mis à jour.", "Mise à jour impossible : le nom est obligatoire.")


def _choisir_dossier_en_cours(cid):
    st.session_state["dossier_id"] = cid


def _rattacher(aid):
    cible = st.session_state.get(f"ratt_{aid}")
    ok = D.rattacher_analyse(aid, cible)
    _dire(ok, "Analyse rangée." if cible is not None else "Analyse sortie de son dossier.", "Opération impossible.")


def _supprimer_analyse(aid):
    ok = D.supprimer_analyse(aid)
    if ok:
        st.session_state.pop("analyse_ouverte", None)
    _dire(ok, "Analyse supprimée.", "Suppression impossible.")


# ─── Page ────────────────────────────────────────────────────────────────────

def page_dossiers():
    st.title("🗂 Mes dossiers")
    if st.session_state.get("role") == "demo":
        st.info("En mode démonstration, rien n'est sauvegardé. Créez un compte gratuit pour retrouver vos analyses "
                "et les classer par dossier client.")
        return
    st.caption("Les analyses sauvegardées (bouton 💾 Sauvegarder des modules) sont conservées 30 jours, puis supprimées "
               "automatiquement. Elles sont partagées avec les membres de votre cabinet.")
    _message()

    clients = D.lister_clients()   # (id, nom, siret, secteur, contact, email, créé le)
    noms = {c[0]: c[1] for c in clients}
    analyses = D.analyses_du_cabinet()

    onglet_a, onglet_d = st.tabs([f"📄 Analyses sauvegardées ({len(analyses)})", f"📁 Dossiers clients ({len(clients)})"])
    with onglet_a:
        _onglet_analyses(analyses, noms)
    with onglet_d:
        _onglet_dossiers(clients, analyses)


def _onglet_analyses(analyses, noms):
    if not analyses:
        st.info("Aucune analyse sauvegardée pour l'instant. Dans un module, cliquez sur « 💾 Sauvegarder » : "
                "l'analyse apparaîtra ici, rangée dans le dossier du client choisi dans le menu de gauche.")
        return

    c1, c2, c3 = st.columns([2, 2, 3])
    choix_dossiers = [TOUS, SANS_DOSSIER] + sorted(noms.values(), key=str.lower)
    filtre_dossier = c1.selectbox("Dossier", choix_dossiers, key="filtre_dossier")
    types = sorted({a.get("type_analyse") or "Analyse" for a in analyses})
    filtre_type = c2.selectbox("Type d'analyse", ["Tous les types"] + types, key="filtre_type")
    recherche = c3.text_input("Rechercher dans les titres", key="filtre_texte", placeholder="ex. Martin, 2025…").strip().lower()

    lignes = []
    for a in analyses:
        dossier = noms.get(a.get("client_id"), SANS_DOSSIER) if a.get("client_id") else SANS_DOSSIER
        if filtre_dossier != TOUS and dossier != filtre_dossier:
            continue
        if filtre_type != "Tous les types" and (a.get("type_analyse") or "Analyse") != filtre_type:
            continue
        if recherche and recherche not in (a.get("titre") or "").lower():
            continue
        j = _jours_restants(a.get("expires_at"))
        lignes.append({"id": a["id"], "Date": _date(a.get("created_at")), "Type": a.get("type_analyse") or "Analyse",
                       "Titre": a.get("titre") or "", "Dossier": dossier, "Par": a.get("user_email") or "",
                       "Supprimée dans": "" if j is None else f"{j} j"})

    if not lignes:
        st.info("Aucune analyse ne correspond à ces filtres.")
        return
    df = pd.DataFrame(lignes)
    st.caption(f"{len(lignes)} analyse(s). Cliquez sur une ligne pour l'ouvrir.")
    sel = st.dataframe(df.drop(columns=["id"]), hide_index=True, width="stretch", on_select="rerun",
                       selection_mode="single-row", key="table_analyses")
    rangs = sel.selection.rows if sel and hasattr(sel, "selection") else []
    if rangs:
        st.session_state["analyse_ouverte"] = int(df.iloc[rangs[0]]["id"])
    aid = st.session_state.get("analyse_ouverte")
    if aid and aid in set(df["id"]):
        _detail_analyse(aid, noms)


def _detail_analyse(aid, noms):
    a = D.get_analyse(aid)   # (id, client_id, type, titre, contenu, créée, expire, exercice, auteur)
    if not a:
        st.warning("Cette analyse n'existe plus.")
        return
    _, client_id, type_a, titre, contenu, cree, expire, _, auteur = a
    st.divider()
    st.subheader(titre or type_a)
    j = _jours_restants(expire)
    st.caption(f"{type_a} · sauvegardée le {_date(cree)} par {auteur} · dossier : "
               f"{noms.get(client_id, SANS_DOSSIER) if client_id else SANS_DOSSIER}"
               + ("" if j is None else f" · supprimée automatiquement dans {j} jour(s)"))

    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        try:
            from utils.export_word import export_analyse_word
            from utils.ai import extraire_contenu_mistral
            buf = export_analyse_word(type_a or "Analyse", extraire_contenu_mistral(contenu))
            st.download_button("📄 Télécharger en Word", buf, f"{sanitize_filename(titre or type_a)}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               width="stretch", key=f"dl_{aid}")
        except Exception:
            st.warning("Export Word indisponible pour cette analyse.")
    with c2:
        options = [None] + list(noms.keys())
        st.selectbox("Ranger dans le dossier", options, index=options.index(client_id) if client_id in options else 0,
                     format_func=lambda i: SANS_DOSSIER if i is None else noms[i], key=f"ratt_{aid}",
                     on_change=_rattacher, args=(aid,))
    with c3:
        confirme = st.checkbox("Confirmer la suppression", key=f"conf_{aid}")
        st.button("🗑 Supprimer", key=f"sup_{aid}", disabled=not confirme, width="stretch",
                  on_click=_supprimer_analyse, args=(aid,))
    st.caption("Le fichier Word reprend le rapport sauvegardé ; les graphiques ne sont pas conservés.")
    with st.container(border=True):
        st.markdown(contenu)


def _onglet_dossiers(clients, analyses):
    with st.expander("➕ Nouveau dossier client", expanded=not clients):
        c1, c2 = st.columns(2)
        c1.text_input("Nom du client *", key="dos_nom", placeholder="ex. SARL Martin")
        c2.text_input("SIRET", key="dos_siret")
        c1.text_input("Secteur d'activité", key="dos_secteur")
        c2.text_input("Contact", key="dos_contact")
        c1.text_input("E-mail", key="dos_email")
        st.button("Créer le dossier", type="primary", on_click=_creer_dossier, key="btn_creer_dossier")

    if not clients:
        st.info("Aucun dossier client. Créez-en un, puis choisissez ce client dans le menu de gauche : "
                "vos sauvegardes y seront rangées.")
        return

    nb = {}
    for a in analyses:
        if a.get("client_id"):
            nb[a["client_id"]] = nb.get(a["client_id"], 0) + 1
    en_cours = st.session_state.get("dossier_id")
    for cid, nom, siret, secteur, contact, email, cree in clients:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 2])
            details = " · ".join(x for x in (f"SIRET {siret}" if siret else "", secteur, contact, email) if x)
            c1.markdown(f"**{nom}**" + ("  ·  ✅ client en cours" if cid == en_cours else "")
                        + (f"  \n{details}" if details else ""))
            c2.caption(f"{nb.get(cid, 0)} analyse(s)  \ncréé le {_date(cree)[:10]}")
            with c3:
                if cid != en_cours:
                    st.button("Travailler sur ce client", key=f"cur_{cid}", on_click=_choisir_dossier_en_cours,
                              args=(cid,), width="stretch")
                with st.popover("✏ Modifier", width="stretch"):
                    st.text_input("Nom du client *", value=nom, key=f"mod_nom_{cid}")
                    st.text_input("SIRET", value=siret or "", key=f"mod_siret_{cid}")
                    st.text_input("Secteur d'activité", value=secteur or "", key=f"mod_secteur_{cid}")
                    st.text_input("Contact", value=contact or "", key=f"mod_contact_{cid}")
                    st.text_input("E-mail", value=email or "", key=f"mod_email_{cid}")
                    st.button("Enregistrer", key=f"modb_{cid}", on_click=_modifier_dossier, args=(cid,), type="primary")
                with st.popover("🗑 Supprimer", width="stretch"):
                    st.write(f"Supprimer le dossier « {nom} » ? Ses {nb.get(cid, 0)} analyse(s) sont conservées, sans dossier.")
                    st.button("Confirmer la suppression", key=f"supd_{cid}", on_click=_supprimer_dossier, args=(cid, nom),
                              type="primary")
