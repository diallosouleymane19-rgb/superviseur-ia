# -*- coding: utf-8 -*-
"""
Module Analyse et comptabilisation de factures - SMD Global Consulting LLC
Fonctionne SANS API : lecture locale (PDF texte, TXT, CSV), règles PCG (utils/compta_facture.py).
Scans et photos : OCR Tesseract gratuit et local (aucune API, aucun abonnement).
"""
import re
from datetime import datetime

from utils.compta_facture import (
    PCG, lire_document, analyser, imputer, export_fec,
)
from utils.sig_pcg import eur_fr, nb_fr

OPTIONS_TVA = {
    "exigibilite": "Selon l'exigibilité : prestations de services en 445800 jusqu'au paiement (sauf option pour les débits)",
    "directe": "Directement en 445660 dès la facture",
}


def _comptes_possibles(sens):
    classes = ("2", "6") if sens == "achat" else ("7",)
    autres = ["471000"]
    return [c for c in PCG if c.startswith(classes)] + autres


def _ocr_images(pieces):
    """Images restées sans texte (Tesseract absent) : écartées avec un message. Aucun appel API."""
    out, infos = [], []
    for p in pieces:
        if "image" in p:
            infos.append(f"{p['source']} : non analysée (OCR indisponible). Déposez le PDF d'origine.")
        else:
            out.append(p)
    return out, infos


def _recalculer(r, choix, tva_services, ma_societe):
    """Recalcule l'écriture selon les choix de l'utilisateur :
    choix = {"sens", "mode" ("lignes" ou "unique"), "compte" (mode unique), "lignes" (un compte par ligne)}."""
    if choix["sens"] != r["sens"]:
        r.update(sens=choix["sens"], justif_sens="Choisi par l'utilisateur")
    if choix.get("mode") == "unique":
        return imputer(r, ma_societe, tva_services, compte=choix.get("compte"), ventiler_lignes=False)
    return imputer(r, ma_societe, tva_services, comptes_lignes=choix.get("lignes"))


def _en_attente(r):
    return any(l["compte"] == "471000" for l in r["ecriture"]["lignes"])


def _rapport(resultats):
    L = ["# Analyse et comptabilisation de factures",
         f"*Édité le {datetime.now().strftime('%d/%m/%Y %H:%M')}*", ""]
    for r in resultats:
        d = r["donnees"]
        L.append(f"## {d.get('type', 'pièce').capitalize()} {d.get('numero') or ''} : "
                 f"{d.get('fournisseur') if r['sens'] == 'achat' else d.get('client')}")
        L.append(f"- Date : {d['date'].strftime('%d/%m/%Y') if d.get('date') else 'non lue'}")
        L.append(f"- Sens : {r['sens']} | Compte : {r['compte']} {r['libelle_compte']} ({r['regle']})")
        for g in r.get("ventilation") or []:
            L.append(f"  - {g['compte']} {PCG.get(g['compte'], '')} : {nb_fr(g['ht'], 2)} € HT ({g['libelles']})")
        if r.get("doublon_de"):
            L.append(f"- Doublon de {r['doublon_de']} : non comptabilisé")
        L.append("")
        L.append("| Compte | Auxiliaire | Libellé | Débit | Crédit |")
        L.append("|---|---|---|---|---|")
        for l in r["ecriture"]["lignes"]:
            L.append(f"| {l['compte']} | {l['aux']} | {l['libelle']} | {nb_fr(l['debit'], 2)} | {nb_fr(l['credit'], 2)} |")
        L.append("")
        for st_, m in r["controles"]:
            if st_ != "OK":
                L.append(f"- [{st_}] {m}")
        L.append("")
    L.append("*Superviseur IA Comptable - SMD Global Consulting LLC*")
    return "\n".join(L)


def page_analyse_facture():
    import streamlit as st
    import pandas as pd
    from utils.page_helpers import banniere_demo, generer_bouton_word, sauvegarder_si_autorise

    st.title("🧾 Analyse et comptabilisation de factures")
    st.markdown("Détection, contrôle et comptabilisation selon le PCG, **sans API** : "
                "factures électroniques (Factur-X, UBL, CII), PDF issus d'un logiciel, fichiers texte et listes CSV.")
    st.caption("PDF scannés et photos : lecture par OCR Tesseract, gratuit et local (aucune API). Vérifiez toujours les montants lus.")
    banniere_demo()

    with st.expander("⚙️ Paramètres", expanded=False):
        ma_societe = st.text_input(
            "Votre société (nom ou SIREN)", value=st.session_state.get("cabinet", "") or "",
            help="Sert à distinguer vos ventes (vous êtes l'émetteur) de vos achats.")
        tva_services = st.radio("TVA déductible sur les prestations de services",
                                list(OPTIONS_TVA), format_func=OPTIONS_TVA.get, key="cf_tva")
        st.caption("Exigibilité de la TVA sur les services : à l'encaissement (art. 269 du CGI), "
                   "donc déductible au paiement, sauf option du fournisseur pour les débits.")

    fichiers = st.file_uploader("📎 Déposer une ou plusieurs factures",
                                type=["pdf", "xml", "txt", "csv", "png", "jpg", "jpeg"],
                                accept_multiple_files=True, key="cf_upload")
    if not fichiers:
        st.info("Déposez vos factures : facture électronique (Factur-X, XML UBL ou CII), PDF (y compris scanné), "
                "photo JPG/PNG, fichier texte ou liste CSV "
                "(colonnes Numéro, Date, Fournisseur, Montant HT, TVA, Montant TTC).")
        return

    pieces, infos = [], []
    for f in fichiers:
        p, i = lire_document(f.getvalue(), f.name)
        pieces += p
        infos += i
    pieces, i2 = _ocr_images(pieces)
    for msg in [m for m in infos if "OCR Tesseract non installé" not in m] + i2:
        (st.info if re.search(r"lue? par OCR|données exactes|montants exacts", msg) else st.warning)(msg)
    if not pieces:
        st.error("Aucune facture lisible dans les fichiers déposés.")
        return

    resultats = analyser(pieces, ma_societe=ma_societe, tva_services=tva_services)
    resultats = [r for r in resultats if r["donnees"].get("type") or r["donnees"].get("ttc")]

    choix = st.session_state.setdefault("cf_choix", {})
    for r in resultats:
        cle = f"{r['donnees']['source']}|{r['donnees'].get('numero')}"
        if cle in choix:
            _recalculer(r, choix[cle], tva_services, ma_societe)

    retenus = [r for r in resultats if not r.get("doublon_de")]
    a_verifier = [r for r in retenus if r["confiance"] == "basse" or r["donnees"].get("ocr") or _en_attente(r)
                  or any(s == "KO" and not m.startswith(("SIREN", "N° de TVA")) for s, m in r["controles"])]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pièces détectées", len(resultats))
    c2.metric("À comptabiliser", len(retenus))
    c3.metric("À vérifier", len(a_verifier))
    c4.metric("Doublons écartés", len(resultats) - len(retenus))

    st.subheader("Pièces")
    st.caption("✅ comptabilisée et conforme · 🟠 comptabilisée, point d'attention (mentions ou TVA) · "
               "⚠️ imputation ou montants à vérifier · ⛔ doublon écarté")
    for i, r in enumerate(resultats):
        d = r["donnees"]
        tiers = d.get("fournisseur") if r["sens"] == "achat" else d.get("client")
        non_conforme = any(s_ in ("KO", "ALERTE") for s_, _ in r["controles"])
        icone = "⛔" if r.get("doublon_de") else "⚠️" if r in a_verifier else "🟠" if non_conforme else "✅"
        titre = (f"{icone} {(d.get('type') or 'pièce').capitalize()} {d.get('numero') or 's/n'} · "
                 f"{tiers or 'tiers inconnu'} · {eur_fr(d.get('ttc') or 0, 2)} TTC")
        with st.expander(titre, expanded=(r in a_verifier and not r.get("doublon_de"))):
            if r.get("doublon_de"):
                st.error(f"Doublon de {r['doublon_de']} : exclu de l'export.")
            a, b, c = st.columns(3)
            a.markdown(f"**Date**  \n{d['date'].strftime('%d/%m/%Y') if d.get('date') else 'non lue'}")
            b.markdown(f"**HT / TVA / TTC**  \n{eur_fr(d.get('ht') or 0, 2)} / {eur_fr(d.get('tva') or 0, 2)} / "
                       f"{eur_fr(d.get('ttc') or 0, 2)}"
                       + (f"  \n*soit {nb_fr((d.get('montants_devise') or {}).get('ttc') or 0, 2)} {d['devise']} TTC*"
                          if d.get("devise", "EUR") != "EUR" else ""))
            c.markdown(f"**Source**  \n{d['source']}")
            if d.get("objet"):
                st.caption(f"Désignation : {d['objet']}")

            cle = f"{d['source']}|{d.get('numero')}"
            fmt = lambda c: f"{c} · {PCG.get(c, '')}"
            arts = r.get("lignes_articles") or []
            s1, s2 = st.columns([1, 3])
            sens = s1.selectbox("Sens", ["achat", "vente"], index=["achat", "vente"].index(r["sens"]),
                                key=f"cf_sens_{i}", help=r["justif_sens"])
            if sens != r["sens"]:
                # Changement de sens : les comptes proposés sont recalculés, les anciens choix sont oubliés
                choix[cle] = {"sens": sens, "mode": "lignes"}
                for k in [k for k in st.session_state if k.startswith((f"cf_cpt_{i}", f"cf_l_{i}_", f"cf_v_{i}"))]:
                    st.session_state.pop(k, None)
                st.rerun()
            options = _comptes_possibles(sens)
            par_ligne = False
            if arts:
                par_ligne = s2.toggle("Imputer ligne par ligne", value=bool(r.get("ventilation")) or
                                      choix.get(cle, {}).get("mode") == "lignes", key=f"cf_v_{i}",
                                      help="Les montants des lignes redonnent le total HT : chaque ligne peut "
                                           "avoir son propre compte.")
                if par_ligne != (choix.get(cle, {}).get("mode", "lignes" if r.get("ventilation") else "unique") == "lignes"):
                    choix[cle] = {"sens": sens, "mode": "lignes" if par_ligne else "unique"}
                    st.rerun()
            if par_ligne:
                actuels = [l["compte"] for l in arts]
                nouveaux = []
                for j, l in enumerate(arts):
                    opts = options if l["compte"] in options else [l["compte"]] + options
                    c1_, c2_ = st.columns([3, 2])
                    nouveaux.append(c1_.selectbox(
                        f"{l['libelle'][:70]} · {nb_fr(l['ht'], 2)} € HT", opts, index=opts.index(l["compte"]),
                        format_func=fmt, key=f"cf_l_{i}_{j}"))
                    c2_.caption(f"{l['regle']} · confiance {l['confiance']}")
                if nouveaux != actuels:
                    choix[cle] = {"sens": sens, "mode": "lignes", "lignes": nouveaux}
                    st.rerun()
            else:
                if r["compte"] not in options:
                    options = [r["compte"]] + options
                compte = (s2 if not arts else st).selectbox(
                    "Compte de charge / produit", options, index=options.index(r["compte"]),
                    format_func=fmt, key=f"cf_cpt_{i}")
                if compte != r["compte"]:
                    choix[cle] = {"sens": sens, "mode": "unique", "compte": compte}
                    st.rerun()
            st.caption(f"Proposition : {r['regle']} · confiance {r['confiance']}")

            lignes = pd.DataFrame([{
                "Journal": r["ecriture"]["journal"], "Compte": l["compte"],
                "Intitulé": PCG.get(l["compte"], ""), "Auxiliaire": l["aux"], "Libellé": l["libelle"],
                "Débit": nb_fr(l["debit"], 2) if l["debit"] else "",
                "Crédit": nb_fr(l["credit"], 2) if l["credit"] else ""} for l in r["ecriture"]["lignes"]])
            st.dataframe(lignes, hide_index=True, width="stretch")

            for st_, m in r["controles"]:
                if st_ == "KO":
                    st.error(m)
                elif st_ == "ALERTE":
                    st.warning(m)
            oks = [m for s_, m in r["controles"] if s_ == "OK"]
            if oks:
                st.caption("Conforme : " + " · ".join(oks))

    st.subheader("Journal à importer")
    lignes_j = []
    for r in retenus:
        d = r["donnees"]
        for l in r["ecriture"]["lignes"]:
            lignes_j.append({"Date": d["date"].strftime("%d/%m/%Y") if d.get("date") else "",
                             "Journal": r["ecriture"]["journal"], "Pièce": d.get("numero") or "",
                             "Compte": l["compte"], "Auxiliaire": l["aux"], "Libellé": l["libelle"],
                             "Débit": l["debit"], "Crédit": l["credit"]})
    if lignes_j:
        dfj = pd.DataFrame(lignes_j)
        td, tc = round(dfj["Débit"].sum(), 2), round(dfj["Crédit"].sum(), 2)
        aff = dfj.copy()
        aff["Débit"] = aff["Débit"].map(lambda x: nb_fr(x, 2) if x else "")
        aff["Crédit"] = aff["Crédit"].map(lambda x: nb_fr(x, 2) if x else "")
        st.dataframe(aff, hide_index=True, width="stretch")
        (st.success if td == tc else st.error)(
            f"Total débit {eur_fr(td, 2)} · total crédit {eur_fr(tc, 2)}"
            + (" · journal équilibré" if td == tc else " · journal déséquilibré"))
        if any(_en_attente(r) for r in retenus):
            st.warning("Des pièces sont en compte d'attente 471000 : choisissez leur compte avant import.")

        e1, e2, e3 = st.columns(3)
        e1.download_button("Télécharger les écritures (format FEC)", export_fec(retenus).encode("utf-8"),
                           file_name=f"ecritures_factures_{datetime.now():%Y%m%d}.txt", mime="text/plain",
                           width="stretch")
        rapport = _rapport(resultats)
        with e2:
            generer_bouton_word("Analyse_factures", rapport)
        if e3.button("Sauvegarder l'analyse", width="stretch"):
            sauvegarder_si_autorise(type_analyse="Comptabilisation factures", resultat=rapport)
