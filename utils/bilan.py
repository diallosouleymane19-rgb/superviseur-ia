# -*- coding: utf-8 -*-
"""Module Bilan Comptable - SMD Global Consulting LLC"""
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
import numpy as np
from datetime import datetime
from utils.sig_pcg import nb_fr, eur_fr, pct_fr
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


# Libellés des postes (partagés avec le module Comparatif N/N-1)
AI_INCORP, AI_CORP, AI_FIN, TOTAL_AI = ("Immobilisations incorporelles", "Immobilisations corporelles",
                                        "Immobilisations financières", "TOTAL ACTIF IMMOBILISÉ")
STOCKS, CLIENTS, AUTRES_CREANCES, CCA, TOTAL_AC = ("Stocks et en-cours", "Créances clients", "Autres créances",
                                                   "Charges constatées d'avance",
                                                   "TOTAL ACTIF CIRCULANT (hors trésorerie)")
VMP, DISPO, TOTAL_TRESO, TOTAL_ACTIF = ("Valeurs mobilières de placement", "Disponibilités",
                                        "TOTAL TRÉSORERIE", "TOTAL ACTIF")
CAPITAL, RAN, RESULTAT, RESULTAT_ATTENTE, SUBV, PROV_REG, TOTAL_CP = (
    "Capital et réserves", "Report à nouveau", "Résultat de l'exercice",
    "Résultat en instance d'affectation (12)", "Subventions d'investissement", "Provisions réglementées",
    "TOTAL CAPITAUX PROPRES")
PROV_RC, EMPRUNTS, CONCOURS, AVANCES, FOURN, FISC_SOC, AUTRES_DETTES, PCA, TOTAL_DETTES, TOTAL_PASSIF = (
    "Provisions pour risques et charges", "Emprunts et dettes financières", "Concours bancaires courants",
    "Avances et acomptes reçus", "Dettes fournisseurs", "Dettes fiscales et sociales", "Autres dettes",
    "Produits constatés d'avance", "TOTAL DETTES", "TOTAL PASSIF")
R_FRNG, R_BFR, R_TN = ("Fonds de roulement net global (FRNG)", "Besoin en fonds de roulement (BFR)",
                       "Trésorerie nette (TN)")
R_AUTONOMIE, R_ENDETTEMENT, R_LIQ_GEN, R_LIQ_RED = ("Autonomie financière (%)",
                                                   "Endettement (dettes financières / capitaux propres)",
                                                   "Liquidité générale", "Liquidité réduite")


def _classer(cpt: str, s: float):
    """Poste du bilan d'un compte selon le PCG (ANC 2014-03) et le sens de son solde.
    s = débit - crédit. Retourne (côté, poste, montant, nature) ; nature = 'brut' ou 'amort' (actif)."""
    c2, c3 = cpt[:2], cpt[:3]
    if cpt[0] in "678" or not cpt[0].isdigit():
        return None
    # --- Classe 2 : immobilisations, amortissements (28), dépréciations (29)
    if c2 == "28" or c2 == "29":
        poste = AI_INCORP if c3 in ("280", "290") else AI_FIN if c3 in ("296", "297") else AI_CORP
        return ("actif", poste, -s, "amort")
    if c2 == "20":
        return ("actif", AI_INCORP, s, "brut")
    if c2 in ("21", "22", "23", "24", "25"):
        return ("actif", AI_CORP, s, "brut")
    if c2 in ("26", "27"):
        return ("actif", AI_FIN, s, "brut")
    # --- Classe 3 : stocks, dépréciations (39)
    if c2 == "39":
        return ("actif", STOCKS, -s, "amort")
    if cpt[0] == "3":
        return ("actif", STOCKS, s, "brut")
    # --- Classe 4 : tiers, classés selon le sens du solde
    if c3 == "491":
        return ("actif", CLIENTS, -s, "amort")
    if c2 == "49":
        return ("actif", AUTRES_CREANCES, -s, "amort")
    if c3 == "486":
        return ("actif", CCA, s, "brut") if s >= 0 else ("passif", AUTRES_DETTES, -s, None)
    if c3 == "487":
        return ("passif", PCA, -s, None) if s <= 0 else ("actif", AUTRES_CREANCES, s, "brut")
    if c2 == "41":
        return ("actif", CLIENTS, s, "brut") if s >= 0 else ("passif", AVANCES, -s, None)
    if c2 == "40":
        return ("passif", FOURN, -s, None) if s <= 0 else ("actif", AUTRES_CREANCES, s, "brut")
    if c2 in ("42", "43", "44"):
        return ("passif", FISC_SOC, -s, None) if s <= 0 else ("actif", AUTRES_CREANCES, s, "brut")
    if cpt[0] == "4":
        return ("passif", AUTRES_DETTES, -s, None) if s <= 0 else ("actif", AUTRES_CREANCES, s, "brut")
    # --- Classe 5 : trésorerie ; soldes créditeurs de banque = concours bancaires
    if c2 == "59":
        return ("actif", VMP, -s, "amort")
    if c2 == "50":
        return ("actif", VMP, s, "brut")
    if c3 == "519":
        return ("passif", CONCOURS, -s, None)
    if cpt[0] == "5":
        return ("actif", DISPO, s, "brut") if s >= 0 else ("passif", CONCOURS, -s, None)
    # --- Classe 1 : capitaux propres, provisions, dettes financières
    poste = {"10": CAPITAL, "11": RAN, "12": RESULTAT_ATTENTE, "13": SUBV, "14": PROV_REG,
             "15": PROV_RC, "16": EMPRUNTS, "17": EMPRUNTS}.get(c2)
    if poste:
        return ("passif", poste, -s, None)
    if cpt[0] == "1":   # 18 comptes de liaison
        return ("passif", AUTRES_DETTES, -s, None) if s <= 0 else ("actif", AUTRES_CREANCES, s, "brut")
    return None


def calculer_bilan(df, date_cloture=None):
    """Bilan PCG à partir d'une balance ou d'un FEC (colonnes CompteNum, Debit, Credit).
    Chaque compte est classé selon son préfixe et le sens de son solde (ex. 401 débiteur -> autres créances,
    512 créditeur -> concours bancaires). Contrôle : total actif = total passif et FRNG - BFR = TN."""
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante'}
    from utils.sig_pcg import _preparer
    d = _preparer(df)
    d = d[d["_cpt"].str.match(r"^\d")]
    total_debit, total_credit = round(float(d["_d"].sum()), 2), round(float(d["_c"].sum()), 2)
    soldes = (d.groupby("_cpt")["_d"].sum() - d.groupby("_cpt")["_c"].sum()).round(2)

    brut = {k: 0.0 for k in (AI_INCORP, AI_CORP, AI_FIN, STOCKS, CLIENTS, AUTRES_CREANCES, CCA, VMP, DISPO)}
    amort = dict.fromkeys(brut, 0.0)
    passif_v = {k: 0.0 for k in (CAPITAL, RAN, RESULTAT, RESULTAT_ATTENTE, SUBV, PROV_REG, PROV_RC, EMPRUNTS,
                                 CONCOURS, AVANCES, FOURN, FISC_SOC, AUTRES_DETTES, PCA)}
    for cpt, s in soldes.items():
        r = _classer(cpt, float(s))
        if not r:
            continue
        cote, poste, montant, nature = r
        if cote == "actif":
            (amort if nature == "amort" else brut)[poste] += montant
        else:
            passif_v[poste] += montant

    # Résultat : classes 6 et 7 (balance avant clôture) ; le compte 12 reste un poste à part
    resultat = float(-soldes[[c for c in soldes.index if c[0] in "67"]].sum())
    passif_v[RESULTAT] = resultat
    if not any(c[0] in "67" for c in soldes.index):          # balance après clôture : le résultat est en 12
        passif_v[RESULTAT], passif_v[RESULTAT_ATTENTE] = passif_v[RESULTAT_ATTENTE], 0.0

    net = {k: brut[k] - amort[k] for k in brut}
    ai = net[AI_INCORP] + net[AI_CORP] + net[AI_FIN]
    acx = net[STOCKS] + net[CLIENTS] + net[AUTRES_CREANCES] + net[CCA]
    treso = net[VMP] + net[DISPO]
    total_actif = ai + acx + treso
    actif = {AI_INCORP: net[AI_INCORP], AI_CORP: net[AI_CORP], AI_FIN: net[AI_FIN], TOTAL_AI: ai,
             STOCKS: net[STOCKS], CLIENTS: net[CLIENTS], AUTRES_CREANCES: net[AUTRES_CREANCES], CCA: net[CCA],
             TOTAL_AC: acx, VMP: net[VMP], DISPO: net[DISPO], TOTAL_TRESO: treso, TOTAL_ACTIF: total_actif}
    actif_detail = [(k, brut[k], amort[k], net[k]) for k in brut]

    cp = sum(passif_v[k] for k in (CAPITAL, RAN, RESULTAT, RESULTAT_ATTENTE, SUBV, PROV_REG))
    dettes_ct = sum(passif_v[k] for k in (CONCOURS, AVANCES, FOURN, FISC_SOC, AUTRES_DETTES, PCA))
    dettes_expl = dettes_ct - passif_v[CONCOURS]
    total_dettes = passif_v[EMPRUNTS] + dettes_ct
    total_passif = cp + passif_v[PROV_RC] + total_dettes
    passif = {k: passif_v[k] for k in (CAPITAL, RAN, RESULTAT, RESULTAT_ATTENTE, SUBV, PROV_REG)}
    passif[TOTAL_CP] = cp
    passif[PROV_RC] = passif_v[PROV_RC]
    for k in (EMPRUNTS, CONCOURS, AVANCES, FOURN, FISC_SOC, AUTRES_DETTES, PCA):
        passif[k] = passif_v[k]
    passif[TOTAL_DETTES] = total_dettes
    passif[TOTAL_PASSIF] = total_passif

    dettes_fin = passif_v[EMPRUNTS] + passif_v[CONCOURS]
    bilan = {
        'date_cloture': date_cloture or datetime.now().strftime('%d/%m/%Y'),
        'actif': actif, 'actif_detail': actif_detail, 'passif': passif, 'ratios': {}, 'analyse': [],
        'totaux': {'total_actif': total_actif, 'total_passif': total_passif,
                   'ecart': round(abs(total_actif - total_passif), 2), 'capitaux_propres': cp,
                   'dettes_financieres': dettes_fin, 'tresorerie': treso, 'resultat_exercice': passif[RESULTAT],
                   'total_debit': total_debit, 'total_credit': total_credit,
                   'ecart_balance': round(abs(total_debit - total_credit), 2)},
    }

    frng = cp + passif_v[PROV_RC] + passif_v[EMPRUNTS] - ai
    bfr = acx - dettes_expl
    tn = treso - passif_v[CONCOURS]
    bilan['ratios'] = {
        R_FRNG: frng, R_BFR: bfr, R_TN: tn,
        R_AUTONOMIE: (cp / total_passif * 100) if total_passif else None,
        R_ENDETTEMENT: (dettes_fin / cp) if cp > 0 else None,
        R_LIQ_GEN: ((acx + treso) / dettes_ct) if dettes_ct else None,
        R_LIQ_RED: ((acx - net[STOCKS] + treso) / dettes_ct) if dettes_ct else None,
    }

    A = bilan['analyse']
    ecart = bilan['totaux']['ecart']
    if abs(total_debit - total_credit) >= 1:
        # Balance fausse : ratios et diagnostic n'ont pas de sens, seul le constat est donné
        A.append({'type': 'CRITIQUE', 'message':
                  f"Balance non équilibrée : total des débits {eur_fr(total_debit, 2)}, total des crédits "
                  f"{eur_fr(total_credit, 2)}, écart {eur_fr(abs(total_debit - total_credit), 2)}. "
                  "Il manque des comptes ou des écritures : le bilan et les ratios ne sont pas fiables."})
        bilan['balance_desequilibree'] = True
        return bilan
    A.append({'type': 'OK', 'message': 'Balance et bilan équilibrés'} if ecart < 1 else
             {'type': 'CRITIQUE', 'message': f"Bilan déséquilibré de {eur_fr(ecart, 2)} alors que la balance est équilibrée : à signaler"})
    if abs(frng - bfr - tn) >= 1 and ecart < 1:
        A.append({'type': 'CRITIQUE', 'message': "Incohérence FRNG - BFR ≠ TN : à signaler"})
    if cp <= 0:
        A.append({'type': 'CRITIQUE', 'message': f"Capitaux propres négatifs ou nuls ({eur_fr(cp)})"})
    aut = bilan['ratios'][R_AUTONOMIE]
    if aut is not None:
        A.append({'type': 'OK' if aut >= 20 else 'WARNING',
                  'message': f"Autonomie financière de {pct_fr(aut)}" + ("" if aut >= 20 else " : inférieure au seuil de 20 %")})
    A.append({'type': 'OK' if frng >= 0 else 'WARNING',
              'message': f"FRNG {'positif' if frng >= 0 else 'négatif'} ({eur_fr(frng)}) : "
                         + ("les immobilisations sont financées par des ressources stables" if frng >= 0
                            else "des immobilisations sont financées par des dettes à court terme")})
    A.append({'type': 'OK' if tn >= 0 else 'WARNING',
              'message': f"Trésorerie nette {'positive' if tn >= 0 else 'négative'} ({eur_fr(tn)})"
                         + ("" if tn >= 0 else " : recours aux concours bancaires")})
    lg = bilan['ratios'][R_LIQ_GEN]
    if lg is not None and lg < 1:
        A.append({'type': 'WARNING', 'message': f"Liquidité générale de {nb_fr(lg, 2)} : l'actif à court terme ne couvre pas les dettes à court terme"})
    end = bilan['ratios'][R_ENDETTEMENT]
    if end is not None and end > 1:
        A.append({'type': 'WARNING', 'message': f"Endettement de {nb_fr(end, 2)} : dettes financières supérieures aux capitaux propres"})
    if passif_v[RESULTAT_ATTENTE]:
        A.append({'type': 'WARNING', 'message': "Compte 12 présent avec des comptes de gestion : résultat antérieur non affecté ?"})
    return bilan


def _fmt_ratio(nom, val):
    if val is None:
        return "n/d"
    if nom == R_AUTONOMIE:
        return pct_fr(val)
    if nom in (R_ENDETTEMENT, R_LIQ_GEN, R_LIQ_RED):
        return nb_fr(val, 2)
    return eur_fr(val)


def generer_rapport_bilan(bilan, nom_entreprise="Entreprise", exercice=""):
    """Rapport du bilan (format français)."""
    L = [f"# BILAN COMPTABLE - {nom_entreprise}", f"## Exercice {exercice}",
         f"*Date de clôture : {bilan['date_cloture']}*", "", "## ACTIF", "",
         "| Poste | Brut | Amort. / dépr. | Net |", "|---|---:|---:|---:|"]
    for poste, b, a, n in bilan.get('actif_detail', []):
        if b or a:
            L.append(f"| {poste} | {nb_fr(b, 2)} | {nb_fr(a, 2)} | {nb_fr(n, 2)} |")
    L.append(f"| **{TOTAL_ACTIF}** | | | **{nb_fr(bilan['actif'][TOTAL_ACTIF], 2)}** |")
    L += ["", "## PASSIF", "", "| Poste | Montant |", "|---|---:|"]
    for poste, v in bilan['passif'].items():
        if v or poste.startswith("TOTAL"):
            L.append(f"| {'**' + poste + '**' if poste.startswith('TOTAL') else poste} | {nb_fr(v, 2)} |")
    if not bilan.get('balance_desequilibree'):
        L += ["", "## ÉQUILIBRE FINANCIER ET RATIOS", ""]
        for nom, val in bilan['ratios'].items():
            L.append(f"- {nom} : {_fmt_ratio(nom, val)}")
    L += ["", "## ANALYSE", ""]
    L += [f"- [{i['type']}] {i['message']}" for i in bilan['analyse']]
    L += ["", "*Emprunts (16-17) considérés à plus d'un an : la balance ne donne pas l'échéance.*",
          "", "---", "*SMD Global Consulting LLC - Superviseur IA Comptable*"]
    return "\n".join(L)


def generer_bilan(df, date_cloture):
    """Wrapper pour compatibilité"""
    return calculer_bilan(df, date_cloture)



def page_bilan():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📊 Bilan Comptable")
    st.markdown("**Vision patrimoniale** avec ratios financiers selon PCG")
    st.caption("✨ Pour Cabinets, DAF et Dirigeants - FDR, BFR, Trésorerie nette")

    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance ou FEC",
        type=TYPES_BALANCE
    )

    if uploaded_file:
        from utils.intelligent_parser import parser_balance_intelligent, charger_balance_ou_fec

        try:
            with st.spinner("🤖 Analyse..."):
                df, _msg, info = charger_balance_ou_fec(uploaded_file)
                st.success(f"✅ {_msg}")
                if info and info.get('colonnes_manquantes'):
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Vérifiez l'en-tête du fichier.")

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                nom_entreprise = st.text_input("🏢 Entreprise", value="Entreprise")
            with col2:
                exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))
            with col3:
                date_cloture = st.date_input("📆 Date de clôture")

            if st.button("📊 Générer le Bilan", type="primary", width="stretch"):
                with st.spinner("Calcul en cours..."):
                    bilan = calculer_bilan(df, date_cloture.strftime('%d/%m/%Y'))

                    if 'erreur' in bilan:
                        st.error(f"❌ {bilan['erreur']}")
                    else:
                        st.markdown(f"## 💼 Bilan au {date_cloture.strftime('%d/%m/%Y')}")
                        st.caption(f"{nom_entreprise} - Exercice {exercice}")

                        totaux = bilan['totaux']
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("📦 Total actif", eur_fr(totaux['total_actif']))
                        col2.metric("💼 Total passif", eur_fr(totaux['total_passif']))
                        col3.metric("🏦 Capitaux propres", eur_fr(totaux['capitaux_propres']))
                        ecart = totaux['ecart']
                        col4.metric("⚖ Écart", eur_fr(ecart, 2))
                        desequilibre = bilan.get('balance_desequilibree')
                        if desequilibre:
                            st.error(f"⛔ {bilan['analyse'][0]['message']}")
                        elif ecart < 1:
                            st.success("✅ Bilan équilibré")
                        else:
                            st.warning(f"⚠ Bilan déséquilibré de {eur_fr(ecart, 2)}")

                        st.divider()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 📦 ACTIF")
                            lignes = [{'Poste': k, 'Brut (€)': nb_fr(b_, 2), 'Amort./dépr. (€)': nb_fr(a_, 2),
                                       'Net (€)': nb_fr(n_, 2)} for k, b_, a_, n_ in bilan['actif_detail'] if b_ or a_]
                            lignes.append({'Poste': TOTAL_ACTIF, 'Brut (€)': '', 'Amort./dépr. (€)': '',
                                           'Net (€)': nb_fr(bilan['actif'][TOTAL_ACTIF], 2)})
                            st.dataframe(pd.DataFrame(lignes), width="stretch", hide_index=True)
                        with col2:
                            st.markdown("### 💼 PASSIF")
                            st.dataframe(pd.DataFrame([
                                {'Poste': k, 'Montant (€)': nb_fr(v, 2)}
                                for k, v in bilan['passif'].items() if v or k.startswith("TOTAL")
                            ]), width="stretch", hide_index=True)

                        st.divider()
                        ratios = bilan['ratios']
                        if desequilibre:
                            st.info("Ratios et diagnostic masqués tant que la balance n'est pas équilibrée. "
                                    "Corrigez la balance (comptes manquants, à-nouveaux, écritures) puis déposez-la à nouveau.")
                        if not desequilibre:
                            st.markdown("## 📈 Équilibre financier")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("FRNG", eur_fr(ratios[R_FRNG]), help="Capitaux propres + provisions + emprunts - actif immobilisé net")
                            c2.metric("BFR", eur_fr(ratios[R_BFR]), help="Actif circulant hors trésorerie - dettes d'exploitation et diverses")
                            c3.metric("Trésorerie nette", eur_fr(ratios[R_TN]), help="Disponibilités + VMP - concours bancaires = FRNG - BFR")
                            st.markdown("## 📊 Ratios")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Autonomie financière", _fmt_ratio(R_AUTONOMIE, ratios[R_AUTONOMIE]), help="Capitaux propres / total passif. Seuil d'alerte : 20 %")
                            c2.metric("Endettement", _fmt_ratio(R_ENDETTEMENT, ratios[R_ENDETTEMENT]), help="Dettes financières (emprunts + concours bancaires) / capitaux propres. Alerte au-delà de 1")
                            c3.metric("Liquidité générale", _fmt_ratio(R_LIQ_GEN, ratios[R_LIQ_GEN]), help="Actif circulant (trésorerie comprise) / dettes à court terme. Alerte en dessous de 1")
                            c4.metric("Liquidité réduite", _fmt_ratio(R_LIQ_RED, ratios[R_LIQ_RED]), help="Actif circulant hors stocks / dettes à court terme")
                            st.caption("Emprunts (16-17) considérés à plus d'un an : la balance ne donne pas l'échéance.")

                            st.divider()
                            st.markdown("## 💡 Analyse")
                            for item in bilan['analyse']:
                                if item['type'] == 'OK':
                                    st.success(f"✅ {item['message']}")
                                elif item['type'] == 'WARNING':
                                    st.warning(f"⚠ {item['message']}")
                                else:
                                    st.error(f"🔴 {item['message']}")

                        st.divider()
                        rapport = generer_rapport_bilan(bilan, nom_entreprise, exercice)
                        col1, col2 = st.columns(2)
                        with col1:
                            bouton_sauvegarde(type_analyse="Bilan", resultat=rapport, libelle="💾 Sauvegarder")
                        with col2:
                            try:
                                generer_bouton_word(f"Bilan_{nom_entreprise}", rapport)
                            except Exception as e:
                                st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
    # -----------------------------------------------------------------------------
    # 8. RAPPROCHEMENT BANCAIRE - VERSION PROFESSIONNELLE
    # -----------------------------------------------------------------------------

