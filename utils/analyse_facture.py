# -*- coding: utf-8 -*-
"""
Module Analyse et comptabilisation de factures - SMD Global Consulting LLC
Fonctionne SANS API : lecture locale (PDF texte, TXT, CSV), règles PCG (utils/compta_facture.py).
Scans et photos : OCR Tesseract gratuit et local (aucune API, aucun abonnement).
"""
from datetime import datetime

from utils.compta_facture import (
    PCG, lire_document, analyser, proposer_compte,
    generer_ecriture, controler, nature_compte, export_fec,
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


def _recalculer(r, sens, compte, tva_services, ma_societe):
    """Recalcule l'écriture après un changement de sens ou de compte par l'utilisateur."""
    d = r["donnees"]
    if sens != r["sens"]:
        compte_prop, nature, confiance, regle = proposer_compte(d, sens, ma_societe)
        r.update(sens=sens, justif_sens="Choisi par l'utilisateur", confiance=confiance, regle=regle)
        if compte == r["compte"]:
            compte = compte_prop
    if compte != r["compte"]:
        r.update(regle="Compte choisi par l'utilisateur", confiance="haute")
    r["compte"], r["libelle_compte"] = compte, PCG.get(compte, "")
    r["nature"] = nature_compte(compte)
    r["ecriture"] = generer_ecriture(d, sens, compte, r["nature"], tva_services)
    r["controles"] = [c for c in controler(d, r["ecriture"])] + \
        [c for c in r["controles"] if c[1].startswith("Doublon")]
    return r


def _rapport(resultats):
    L = ["# Analyse et comptabilisation de factures",
         f"*Édité le {datetime.now().strftime('%d/%m/%Y %H:%M')}*", ""]
    for r in resultats:
        d = r["donnees"]
        L.append(f"## {d.get('type', 'pièce').capitalize()} {d.get('numero') or ''} : "
                 f"{d.get('fournisseur') if r['sens'] == 'achat' else d.get('client')}")
        L.append(f"- Date : {d['date'].strftime('%d/%m/%Y') if d.get('date') else 'non lue'}")
        L.append(f"- Sens : {r['sens']} | Compte : {r['compte']} {r['libelle_compte']} ({r['regle']})")
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
                "PDF issus d'un logiciel, fichiers texte et listes CSV.")
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
                                type=["pdf", "txt", "csv", "png", "jpg", "jpeg"],
                                accept_multiple_files=True, key="cf_upload")
    if not fichiers:
        st.info("Déposez vos factures : PDF (y compris scanné), photo JPG/PNG, fichier texte ou liste CSV "
                "(colonnes Numéro, Date, Fournisseur, Montant HT, TVA, Montant TTC).")
        return

    pieces, infos = [], []
    for f in fichiers:
        p, i = lire_document(f.getvalue(), f.name)
        pieces += p
        infos += i
    pieces, i2 = _ocr_images(pieces)
    for msg in [m for m in infos if "OCR Tesseract non installé" not in m] + i2:
        (st.info if "lu par OCR" in msg or "lue par OCR" in msg else st.warning)(msg)
    if not pieces:
        st.error("Aucune facture lisible dans les fichiers déposés.")
        return

    resultats = analyser(pieces, ma_societe=ma_societe, tva_services=tva_services)
    resultats = [r for r in resultats if r["donnees"].get("type") or r["donnees"].get("ttc")]

    choix = st.session_state.setdefault("cf_choix", {})
    for r in resultats:
        cle = f"{r['donnees']['source']}|{r['donnees'].get('numero')}"
        if cle in choix:
            sens, compte = choix[cle]
            _recalculer(r, sens, compte, tva_services, ma_societe)

    retenus = [r for r in resultats if not r.get("doublon_de")]
    a_verifier = [r for r in retenus if r["confiance"] == "basse" or r["donnees"].get("ocr") or r["compte"] == "471000"
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
            s1, s2 = st.columns([1, 3])
            sens = s1.selectbox("Sens", ["achat", "vente"], index=["achat", "vente"].index(r["sens"]),
                                key=f"cf_sens_{i}", help=r["justif_sens"])
            options = _comptes_possibles(sens)
            if r["compte"] not in options:
                options = [r["compte"]] + options
            compte = s2.selectbox("Compte de charge / produit", options, index=options.index(r["compte"]),
                                  format_func=lambda c: f"{c} · {PCG.get(c, '')}", key=f"cf_cpt_{i}")
            if sens != r["sens"]:
                # Changement de sens : le compte proposé est recalculé, l'ancien choix de compte est oublié
                choix[cle] = (sens, r["compte"])
                st.session_state.pop(f"cf_cpt_{i}", None)
                st.rerun()
            if compte != r["compte"]:
                choix[cle] = (sens, compte)
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
        if any(r["compte"] == "471000" for r in retenus):
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
