# -*- coding: utf-8 -*-
"""
Module Compte de Résultat Professionnel - SMD Global Consulting LLC
Calcul des SIG (Soldes Intermédiaires de Gestion) selon PCG français
Pour Cabinets, DAF et Dirigeants
"""
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
from utils.sig_pcg import nb_fr, eur_fr, pct_fr
import numpy as np
from datetime import datetime
from utils.page_helpers import champ_exercice, champs_remplis
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


# Mapping des comptes PCG vers les rubriques du compte de resultat
RUBRIQUES_PCG = {
    # PRODUITS
    '70': 'Ventes de marchandises et services',
    '701': 'Ventes de produits finis',
    '706': 'Prestations de services',
    '707': 'Ventes de marchandises',
    '708': 'Produits des activités annexes',
    '71': 'Production stockée',
    '72': 'Production immobilisée',
    '74': 'Subventions d\'exploitation',
    '75': 'Autres produits de gestion courante',
    '76': 'Produits financiers',
    '77': 'Produits exceptionnels',
    '78': 'Reprises sur amortissements et provisions',
    '79': 'Transferts de charges',
    
    # CHARGES
    '60': 'Achats',
    '601': 'Achats stockés - Matières premières',
    '607': 'Achats de marchandises',
    '603': 'Variation des stocks',
    '61': 'Services extérieurs',
    '62': 'Autres services extérieurs',
    '63': 'Impôts et taxes',
    '64': 'Charges de personnel',
    '641': 'Salaires bruts',
    '645': 'Charges sociales',
    '65': 'Autres charges de gestion courante',
    '66': 'Charges financières',
    '67': 'Charges exceptionnelles',
    '68': 'Dotations aux amortissements et provisions',
    '69': 'Impôts sur les bénéfices'
}


def calculer_compte_resultat(df, type_entreprise='Mixte'):
    """
    Calcule le compte de résultat détaillé à partir d'une balance
    
    Args:
        df: DataFrame avec colonnes CompteNum, Debit, Credit
        type_entreprise: 'Commerciale', 'Industrielle', 'Services', 'Mixte'
    
    Returns:
        dict: Compte de résultat structuré avec SIG et ratios
    """
    # Normaliser les colonnes
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante'}
    
    # Conversion numerique
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(
            df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), 
            errors='coerce'
        ).fillna(0)
    else:
        df['_debit'] = 0
    
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(
            df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''),
            errors='coerce'
        ).fillna(0)
    else:
        df['_credit'] = 0
    
    # Conversion compte en string et extraction classe/sous-classe
    df['_compte'] = df['CompteNum'].astype(str).str.strip()
    df['_classe'] = df['_compte'].str[0]
    df['_sous_classe'] = df['_compte'].str[:2]
    df['_racine_3'] = df['_compte'].str[:3]
    
    resultat = {
        'type_entreprise': type_entreprise,
        'date_calcul': datetime.now().strftime('%d/%m/%Y'),
        'produits': {},
        'charges': {},
        'sig': {},
        'ratios': {},
        'analyse': []
    }
    
    # ===== PRODUITS (Classe 7) =====
    produits_70 = df[df['_sous_classe'] == '70']['_credit'].sum() - df[df['_sous_classe'] == '70']['_debit'].sum()
    produits_71 = df[df['_sous_classe'] == '71']['_credit'].sum() - df[df['_sous_classe'] == '71']['_debit'].sum()
    produits_72 = df[df['_sous_classe'] == '72']['_credit'].sum() - df[df['_sous_classe'] == '72']['_debit'].sum()
    produits_74 = df[df['_sous_classe'] == '74']['_credit'].sum() - df[df['_sous_classe'] == '74']['_debit'].sum()
    produits_75 = df[df['_sous_classe'] == '75']['_credit'].sum() - df[df['_sous_classe'] == '75']['_debit'].sum()
    produits_76 = df[df['_sous_classe'] == '76']['_credit'].sum() - df[df['_sous_classe'] == '76']['_debit'].sum()
    produits_77 = df[df['_sous_classe'] == '77']['_credit'].sum() - df[df['_sous_classe'] == '77']['_debit'].sum()
    produits_78 = df[df['_sous_classe'] == '78']['_credit'].sum() - df[df['_sous_classe'] == '78']['_debit'].sum()
    produits_79 = df[df['_sous_classe'] == '79']['_credit'].sum() - df[df['_sous_classe'] == '79']['_debit'].sum()
    
    # Detail ventes
    ventes_marchandises = df[df['_racine_3'] == '707']['_credit'].sum() - df[df['_racine_3'] == '707']['_debit'].sum()
    ventes_produits = df[df['_racine_3'] == '701']['_credit'].sum() - df[df['_racine_3'] == '701']['_debit'].sum()
    prestations = df[df['_racine_3'] == '706']['_credit'].sum() - df[df['_racine_3'] == '706']['_debit'].sum()
    
    resultat['produits'] = {
        'Ventes marchandises (707)': ventes_marchandises,
        'Ventes produits finis (701)': ventes_produits,
        'Prestations services (706)': prestations,
        'Autres ventes (70)': produits_70 - ventes_marchandises - ventes_produits - prestations,
        'Production stockée (71)': produits_71,
        'Production immobilisée (72)': produits_72,
        'Subventions (74)': produits_74,
        'Autres produits gestion (75)': produits_75,
        'Produits financiers (76)': produits_76,
        'Produits exceptionnels (77)': produits_77,
        'Reprises (78)': produits_78,
        'Transferts charges (79)': produits_79,
    }
    
    # Total chiffre d'affaires
    chiffre_affaires = produits_70
    production_exercice = produits_70 + produits_71 + produits_72
    
    # ===== CHARGES (Classe 6) =====
    achats_marchandises = df[df['_racine_3'] == '607']['_debit'].sum() - df[df['_racine_3'] == '607']['_credit'].sum()
    achats_mp = df[df['_racine_3'] == '601']['_debit'].sum() - df[df['_racine_3'] == '601']['_credit'].sum()
    var_stocks = df[df['_racine_3'] == '603']['_debit'].sum() - df[df['_racine_3'] == '603']['_credit'].sum()
    
    charges_60 = df[df['_sous_classe'] == '60']['_debit'].sum() - df[df['_sous_classe'] == '60']['_credit'].sum()
    charges_61 = df[df['_sous_classe'] == '61']['_debit'].sum() - df[df['_sous_classe'] == '61']['_credit'].sum()
    charges_62 = df[df['_sous_classe'] == '62']['_debit'].sum() - df[df['_sous_classe'] == '62']['_credit'].sum()
    charges_63 = df[df['_sous_classe'] == '63']['_debit'].sum() - df[df['_sous_classe'] == '63']['_credit'].sum()
    charges_64 = df[df['_sous_classe'] == '64']['_debit'].sum() - df[df['_sous_classe'] == '64']['_credit'].sum()
    charges_65 = df[df['_sous_classe'] == '65']['_debit'].sum() - df[df['_sous_classe'] == '65']['_credit'].sum()
    charges_66 = df[df['_sous_classe'] == '66']['_debit'].sum() - df[df['_sous_classe'] == '66']['_credit'].sum()
    charges_67 = df[df['_sous_classe'] == '67']['_debit'].sum() - df[df['_sous_classe'] == '67']['_credit'].sum()
    charges_68 = df[df['_sous_classe'] == '68']['_debit'].sum() - df[df['_sous_classe'] == '68']['_credit'].sum()
    charges_69 = df[df['_sous_classe'] == '69']['_debit'].sum() - df[df['_sous_classe'] == '69']['_credit'].sum()
    
    salaires = df[df['_racine_3'] == '641']['_debit'].sum() - df[df['_racine_3'] == '641']['_credit'].sum()
    charges_sociales = df[df['_racine_3'] == '645']['_debit'].sum() - df[df['_racine_3'] == '645']['_credit'].sum()
    
    resultat['charges'] = {
        'Achats marchandises (607)': achats_marchandises,
        'Achats matières premières (601)': achats_mp,
        'Variation stocks (603)': var_stocks,
        'Autres achats (60)': charges_60 - achats_marchandises - achats_mp - var_stocks,
        'Services extérieurs (61)': charges_61,
        'Autres services extérieurs (62)': charges_62,
        'Impôts et taxes (63)': charges_63,
        'Salaires bruts (641)': salaires,
        'Charges sociales (645)': charges_sociales,
        'Autres charges personnel (64)': charges_64 - salaires - charges_sociales,
        'Autres charges gestion (65)': charges_65,
        'Charges financières (66)': charges_66,
        'Charges exceptionnelles (67)': charges_67,
        'Dotations amortissements (68)': charges_68,
        'Impôts sur bénéfices (69)': charges_69,
    }
    
    # ===== CALCUL DES SIG (PCG, module commun utils/sig_pcg.py) =====
    from utils.sig_pcg import calculer_sig
    k = calculer_sig(df)
    chiffre_affaires = k['chiffre_affaires']
    resultat_net = k['resultat_net']
    ebe = k['ebe']

    sig = {"Chiffre d'affaires": chiffre_affaires}
    if k['ventes_marchandises'] or k['cout_achat_marchandises']:
        sig["Ventes de marchandises"] = k['ventes_marchandises']
        sig["Coût d'achat des marchandises vendues"] = k['cout_achat_marchandises']
        sig["Marge commerciale"] = k['marge_commerciale']
    sig.update({
        "Production de l'exercice": k['production_exercice'],
        "Consommations en provenance des tiers": k['consommations_tiers'],
        "Valeur ajoutée (VA)": k['valeur_ajoutee'],
        "Subventions d'exploitation": k['subventions'],
        "Impôts et taxes": k['impots_taxes'],
        "Charges de personnel": k['masse_salariale'],
        "Excédent brut d'exploitation (EBE)": ebe,
        "Résultat d'exploitation": k['resultat_exploitation'],
        "Résultat financier": k['resultat_financier'],
        "Résultat courant avant impôts": k['resultat_courant'],
        "Résultat exceptionnel": k['resultat_exceptionnel'],
        "Participation et impôts sur les bénéfices": k['participation_impots'],
        "Résultat net": resultat_net,
    })
    resultat['sig'] = sig
    resultat['ecart_controle'] = k['ecart_controle']

    # ===== RATIOS DE PERFORMANCE =====
    if chiffre_affaires > 0:
        resultat['ratios'] = {}
        if k['ventes_marchandises'] > 0:
            resultat['ratios']['Taux de marge commerciale (%)'] = k['taux_marge_commerciale']
        resultat['ratios'].update({
            'Taux de valeur ajoutée (%)': k['taux_va'],
            "Taux d'EBE (%)": k['taux_ebe'],
            "Taux de rentabilité d'exploitation (%)": k['resultat_exploitation'] / chiffre_affaires * 100,
            'Taux de rentabilité nette (%)': k['taux_rentabilite'],
            'Poids des charges de personnel (%)': k['poids_charges_personnel'],
            'Poids des consommations externes (%)': k['consommations_tiers'] / chiffre_affaires * 100,
        })

    if abs(k['ecart_controle']) >= 0.01:
        resultat['analyse'].append({
            'type': 'CRITIQUE',
            'message': f"Contrôle : écart de {eur_fr(k['ecart_controle'], 2)} entre le résultat par les SIG et classe 7 - classe 6. Vérifier le plan de comptes."
        })

    # ===== ANALYSE QUALITATIVE =====
    if resultat_net > 0:
        resultat['analyse'].append({
            'type': 'OK',
            'message': f'Résultat net bénéficiaire de {eur_fr(resultat_net, 2)}'
        })
    else:
        resultat['analyse'].append({
            'type': 'WARNING',
            'message': f'Résultat net déficitaire de {eur_fr(resultat_net, 2)}'
        })
    
    if ebe > 0:
        resultat['analyse'].append({
            'type': 'OK',
            'message': "EBE positif : capacité à générer de la trésorerie sur l'activité"
        })
    else:
        resultat['analyse'].append({
            'type': 'CRITIQUE',
            'message': 'EBE négatif : difficulté à couvrir les charges courantes'
        })
    
    if 'Taux de valeur ajoutée (%)' in resultat['ratios']:
        taux_va = resultat['ratios']['Taux de valeur ajoutée (%)']
        if taux_va > 30:
            resultat['analyse'].append({
                'type': 'OK',
                'message': f'Bon taux de valeur ajoutée ({pct_fr(taux_va)})'
            })
        elif taux_va < 15:
            resultat['analyse'].append({
                'type': 'WARNING',
                'message': f'Faible taux de valeur ajoutée ({pct_fr(taux_va)}) : revoir la chaîne de valeur'
            })
    
    return resultat


# Soldes intermédiaires (en gras dans le rapport), à distinguer de leurs composantes
SOLDES = ("Marge commerciale", "Production de l'exercice", "Valeur ajoutée", "Excédent brut",
          "Résultat")


def visuels_compte_resultat(resultat):
    """Indicateurs clés et graphique des soldes pour l'export Word (mêmes chiffres qu'à l'écran)."""
    from utils.word_visuels import barres_simples
    sig, r = resultat['sig'], resultat.get('ratios') or {}
    rn = sig.get('Résultat net', 0)
    ind = [{"libelle": "Chiffre d'affaires", "valeur": eur_fr(sig.get("Chiffre d'affaires", 0))},
           {"libelle": "Valeur ajoutée", "valeur": eur_fr(sig.get('Valeur ajoutée (VA)', 0))},
           {"libelle": "EBE", "valeur": eur_fr(sig.get("Excédent brut d'exploitation (EBE)", 0)),
            "ton": "mauvais" if sig.get("Excédent brut d'exploitation (EBE)", 0) < 0 else None,
            "detail": "négatif" if sig.get("Excédent brut d'exploitation (EBE)", 0) < 0 else ""},
           {"libelle": "Résultat net", "valeur": eur_fr(rn), "ton": "bon" if rn > 0 else "mauvais",
            "detail": "bénéfice" if rn > 0 else "perte" if rn < 0 else "nul"}]
    for lib, cle in (("Taux de valeur ajoutée", "Taux de valeur ajoutée (%)"), ("Taux d'EBE", "Taux d'EBE (%)"),
                     ("Rentabilité d'exploitation", "Taux de rentabilité d'exploitation (%)"),
                     ("Rentabilité nette", "Taux de rentabilité nette (%)")):
        if cle in r:
            ind.append({"libelle": lib, "valeur": pct_fr(r[cle])})
    principaux = [("Chiffre d'affaires", "Chiffre d'affaires"), ("Marge commerciale", "Marge commerciale"),
                  ("Valeur ajoutée (VA)", "Valeur ajoutée"), ("Excédent brut d'exploitation (EBE)", "EBE"),
                  ("Résultat d'exploitation", "Résultat d'exploitation"),
                  ("Résultat courant avant impôts", "Résultat courant avant impôts"), ("Résultat net", "Résultat net")]
    libs = [court for cle, court in principaux if cle in sig and (sig[cle] or cle == "Résultat net")]
    vals = [sig[cle] for cle, court in principaux if cle in sig and (sig[cle] or cle == "Résultat net")]
    graphiques = [barres_simples(libs, vals, "Du chiffre d'affaires au résultat net")] if libs else []
    return ind, graphiques


def generer_rapport_compte_resultat(resultat, nom_entreprise="Entreprise", exercice=""):
    """Génère un rapport professionnel du compte de résultat"""
    
    rapport = []
    rapport.append(f"# COMPTE DE RÉSULTAT - ANALYSE PROFESSIONNELLE")
    rapport.append(f"## {nom_entreprise} - Exercice {exercice}")
    rapport.append(f"*Date d'analyse : {resultat['date_calcul']}*")
    rapport.append(f"*Type d'entreprise : {resultat['type_entreprise']}*\n")
    rapport.append("---\n")
    
    # SOLDES INTERMEDIAIRES DE GESTION
    rapport.append("## 📊 SOLDES INTERMÉDIAIRES DE GESTION (SIG)\n")
    rapport.append("| Indicateur | Montant |")
    rapport.append("|------------|---------|")
    for nom, valeur in resultat['sig'].items():
        g = "**" if nom.startswith(SOLDES) else ""
        rapport.append(f"| {g}{nom}{g} | {g}{eur_fr(valeur, 2)}{g} |")
    rapport.append("")
    
    # RATIOS
    if resultat['ratios']:
        rapport.append("## 📈 RATIOS DE PERFORMANCE\n")
        rapport.append("| Ratio | Valeur |")
        rapport.append("|-------|--------|")
        for nom, valeur in resultat['ratios'].items():
            if '€' in nom:
                rapport.append(f"| {nom} | {nb_fr(valeur, 2)} |")
            else:
                rapport.append(f"| {nom} | {pct_fr(valeur)} |")
        rapport.append("")
    
    # PRODUITS ET CHARGES
    for titre, cle in (("💰 PRODUITS", "produits"), ("💸 CHARGES", "charges")):
        lignes = [(k, v) for k, v in resultat.get(cle, {}).items() if v != 0]
        if lignes:
            rapport.append(f"## {titre}\n")
            rapport.append("| Rubrique | Montant |")
            rapport.append("|----------|--------:|")
            rapport += [f"| {k} | {eur_fr(v, 2)} |" for k, v in lignes]
            rapport.append("")

    # ANALYSE
    if resultat['analyse']:
        rapport.append("## 💡 ANALYSE QUALITATIVE\n")
        for item in resultat['analyse']:
            symbol = '✅' if item['type'] == 'OK' else '⚠' if item['type'] == 'WARNING' else '🔴'
            rapport.append(f"- {symbol} {item['message']}")
        rapport.append("")
    
    rapport.append("---")
    rapport.append("*Rapport généré par SMD Global Consulting LLC - Superviseur IA Comptable*")
    
    return "\n".join(rapport)



def page_compte_resultat():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📈 Compte de Résultat")
    st.markdown("**Calcul automatique des SIG** (Soldes Intermédiaires de Gestion) selon PCG")
    st.caption("✨ Pour Cabinets, DAF et Dirigeants - Compatible toutes balances")

    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance ou FEC",
        type=TYPES_BALANCE,
        help="La balance doit contenir les comptes des classes 6 (charges) et 7 (produits)"
    )

    if uploaded_file:
        from utils.compte_resultat import calculer_compte_resultat, generer_rapport_compte_resultat
        from utils.intelligent_parser import parser_balance_intelligent, charger_balance_ou_fec

        try:
            with st.spinner("🤖 Analyse de la balance..."):
                df, _msg, info = charger_balance_ou_fec(uploaded_file)
                st.success(f"✅ {_msg}")
                if info and info.get('colonnes_manquantes'):
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Vérifiez l'en-tête du fichier.")

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            with col2:
                exercice = champ_exercice()
            with col3:
                type_entreprise = st.selectbox(
                    "🏭 Type d'entreprise",
                    ["Mixte", "Commerciale", "Industrielle", "Services"]
                )

            if st.button("📊 Générer le Compte de Résultat", type="primary", width="stretch") and \
                    champs_remplis(Exercice=exercice):
                with st.spinner("Calcul des SIG en cours..."):
                    resultat = calculer_compte_resultat(df, type_entreprise)

                    if 'erreur' in resultat:
                        st.error(f"❌ {resultat['erreur']}")
                    else:
                        st.markdown("## 📊 Soldes Intermédiaires de Gestion")
                        st.caption(f"{nom_entreprise} - Exercice {exercice}")

                        sig = resultat['sig']
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            _ca = sig.get("Chiffre d'affaires", 0)
                            st.metric("💰 CA", eur_fr(_ca))
                        with col2:
                            st.metric("⚙ VA", eur_fr(sig['Valeur ajoutée (VA)']))
                        with col3:
                            _ebe = sig.get("Excédent brut d'exploitation (EBE)", 0)
                            st.metric("📈 EBE", eur_fr(_ebe))
                        with col4:
                            rn = sig['Résultat net']
                            st.metric("🎯 Résultat Net", eur_fr(rn),
                                     delta="Bénéfice" if rn > 0 else "Déficit",
                                     delta_color="normal" if rn > 0 else "inverse")

                        st.divider()
                        st.markdown("### 📋 Détail des Soldes Intermédiaires")
                        df_sig = pd.DataFrame([
                            {'Indicateur': nom, 'Montant (€)': nb_fr(val, 2)} 
                            for nom, val in sig.items()
                        ])
                        st.dataframe(df_sig, width="stretch", hide_index=True)
                        try:
                            import plotly.graph_objects as go
                            noms, vals = list(sig.keys())[::-1], [float(v) for v in list(sig.values())[::-1]]
                            fig = go.Figure(go.Bar(
                                x=vals, y=noms, orientation="h",
                                marker_color=["#1F4E79" if v >= 0 else "#C0392B" for v in vals],
                                hovertemplate="%{y} : %{x:,.0f} €<extra></extra>"))
                            fig.update_layout(separators=", ", height=28 * len(noms) + 80,
                                              margin=dict(l=10, r=10, t=10, b=10), xaxis_title="€", xaxis_tickformat=",.0f")
                            st.plotly_chart(fig, width="stretch")
                        except Exception:
                            pass

                        st.divider()
                        if resultat['ratios']:
                            st.markdown("## 📈 Ratios de Performance")
                            ratios = resultat['ratios']
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if 'Taux de valeur ajoutée (%)' in ratios:
                                    st.metric("Taux de VA", pct_fr(ratios['Taux de valeur ajoutée (%)']))
                            with col2:
                                if "Taux d'EBE (%)" in ratios:
                                    st.metric("Taux d'EBE", pct_fr(ratios["Taux d'EBE (%)"]))
                            with col3:
                                if "Taux de rentabilité d'exploitation (%)" in ratios:
                                    st.metric("Rentab. exploitation", pct_fr(ratios["Taux de rentabilité d'exploitation (%)"]))
                            with col4:
                                if 'Taux de rentabilité nette (%)' in ratios:
                                    st.metric("Rentab. nette", pct_fr(ratios['Taux de rentabilité nette (%)']))

                        st.divider()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 💰 PRODUITS")
                            st.dataframe(pd.DataFrame([
                                {'Rubrique': k, 'Montant (€)': nb_fr(v, 2)} 
                                for k, v in resultat['produits'].items() if v != 0
                            ]), width="stretch", hide_index=True)
                        with col2:
                            st.markdown("### 💸 CHARGES")
                            st.dataframe(pd.DataFrame([
                                {'Rubrique': k, 'Montant (€)': nb_fr(v, 2)} 
                                for k, v in resultat['charges'].items() if v != 0
                            ]), width="stretch", hide_index=True)

                        st.divider()
                        if resultat['analyse']:
                            st.markdown("## 💡 Analyse Cabinet")
                            for item in resultat['analyse']:
                                if item['type'] == 'OK':
                                    st.success(f"✅ {item['message']}")
                                elif item['type'] == 'WARNING':
                                    st.warning(f"⚠ {item['message']}")
                                else:
                                    st.error(f"🔴 {item['message']}")

                        st.divider()
                        rapport = generer_rapport_compte_resultat(resultat, nom_entreprise, exercice)
                        col1, col2 = st.columns(2)
                        with col1:
                            bouton_sauvegarde(type_analyse="Compte de Résultat", resultat=rapport, libelle="💾 Sauvegarder")
                        with col2:
                            try:
                                ind_w, graph_w = visuels_compte_resultat(resultat)
                                generer_bouton_word(f"Compte_Resultat_{nom_entreprise}", rapport,
                                                    indicateurs=ind_w, graphiques=graph_w)
                            except Exception as e:
                                st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
    # -----------------------------------------------------------------------------
    # 7. BILAN COMPTABLE - VERSION PROFESSIONNELLE CABINET
    # -----------------------------------------------------------------------------

