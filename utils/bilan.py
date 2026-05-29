# -*- coding: utf-8 -*-
"""Module Bilan Comptable - SMD Consulting"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def calculer_bilan(df, date_cloture=None):
    """Calcule le bilan comptable a partir d'une balance"""
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante'}
    
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_debit'] = 0
    
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_credit'] = 0
    
    df['_solde'] = df['_debit'] - df['_credit']
    df['_compte'] = df['CompteNum'].astype(str).str.strip()
    df['_classe'] = df['_compte'].str[0]
    df['_sous_classe'] = df['_compte'].str[:2]
    
    bilan = {
        'date_cloture': date_cloture or datetime.now().strftime('%d/%m/%Y'),
        'actif': {},
        'passif': {},
        'totaux': {},
        'ratios': {},
        'analyse': []
    }
    
    # ACTIF - Immobilisations
    immo_20 = df[df['_sous_classe'] == '20']['_solde'].sum()
    immo_21 = df[df['_sous_classe'] == '21']['_solde'].sum()
    immo_22 = df[df['_sous_classe'] == '22']['_solde'].sum()
    immo_23 = df[df['_sous_classe'] == '23']['_solde'].sum()
    immo_26 = df[df['_sous_classe'] == '26']['_solde'].sum()
    immo_27 = df[df['_sous_classe'] == '27']['_solde'].sum()
    amort_28 = df[df['_sous_classe'] == '28']['_solde'].sum()
    
    bilan['actif']['Immo incorporelles (20)'] = immo_20
    bilan['actif']['Terrains (21)'] = immo_21
    bilan['actif']['Constructions (22-23)'] = immo_22 + immo_23
    bilan['actif']['Immo financieres (26-27)'] = immo_26 + immo_27
    bilan['actif']['Amortissements (28)'] = amort_28
    
    immobilisations = immo_20 + immo_21 + immo_22 + immo_23 + immo_26 + immo_27 + amort_28
    bilan['actif']['TOTAL IMMOBILISATIONS'] = immobilisations
    
    # Actif circulant
    stocks = df[df['_classe'] == '3']['_solde'].sum()
    clients = df[df['_sous_classe'] == '41']['_solde'].sum()
    autres_creances = df[df['_classe'] == '4']['_solde'].sum() - clients
    banque = df[df['_sous_classe'] == '51']['_solde'].sum()
    caisse = df[df['_sous_classe'] == '53']['_solde'].sum()
    
    bilan['actif']['Stocks (3)'] = stocks
    bilan['actif']['Clients (41)'] = max(clients, 0)
    bilan['actif']['Autres creances'] = max(autres_creances, 0)
    bilan['actif']['Banque (51)'] = max(banque, 0)
    bilan['actif']['Caisse (53)'] = max(caisse, 0)
    
    actif_circulant = stocks + max(clients, 0) + max(autres_creances, 0)
    tresorerie = max(banque, 0) + max(caisse, 0)
    
    bilan['actif']['TOTAL ACTIF CIRCULANT'] = actif_circulant
    bilan['actif']['TOTAL TRESORERIE'] = tresorerie
    
    total_actif = immobilisations + actif_circulant + tresorerie
    bilan['actif']['TOTAL ACTIF'] = total_actif
    
    # PASSIF
    # PCG : 10x = Capital + primes + réserves (106x) ; 11x = Report à nouveau ; 12x = Résultat
    capital = -df[df['_sous_classe'] == '10']['_solde'].sum()
    report = -df[df['_sous_classe'] == '11']['_solde'].sum()   # 11x = Report à nouveau (110/119)
    # Note: le résultat est calculé ci-dessous à partir des classes 6 et 7
    # Note: 12x = Résultat de l'exercice (non doublonné car calculé séparément)
    # Note: 13x = Subventions d'investissement (exclu des capitaux propres usuels)

    produits = df[df['_classe'] == '7']['_credit'].sum() - df[df['_classe'] == '7']['_debit'].sum()
    charges = df[df['_classe'] == '6']['_debit'].sum() - df[df['_classe'] == '6']['_credit'].sum()
    resultat = produits - charges

    bilan['passif']['Capital et reserves (10)'] = capital
    bilan['passif']['Report a nouveau (11)'] = report
    bilan['passif']['Resultat exercice'] = resultat

    capitaux_propres = capital + report + resultat
    bilan['passif']['TOTAL CAPITAUX PROPRES'] = capitaux_propres
    
    dettes_fin = -df[df['_sous_classe'] == '16']['_solde'].sum()
    dettes_four = -df[df['_sous_classe'] == '40']['_solde'].sum()
    dettes_perso = -df[df['_sous_classe'] == '42']['_solde'].sum()
    dettes_soc = -df[df['_sous_classe'] == '43']['_solde'].sum()
    dettes_fisc = -df[df['_sous_classe'] == '44']['_solde'].sum()
    
    bilan['passif']['Dettes financieres (16)'] = max(dettes_fin, 0)
    bilan['passif']['Dettes fournisseurs (40)'] = max(dettes_four, 0)
    bilan['passif']['Dettes personnel (42)'] = max(dettes_perso, 0)
    bilan['passif']['Dettes sociales (43)'] = max(dettes_soc, 0)
    bilan['passif']['Dettes fiscales (44)'] = max(dettes_fisc, 0)
    
    total_dettes = max(dettes_fin, 0) + max(dettes_four, 0) + max(dettes_perso, 0) + max(dettes_soc, 0) + max(dettes_fisc, 0)
    bilan['passif']['TOTAL DETTES'] = total_dettes
    
    total_passif = capitaux_propres + total_dettes
    bilan['passif']['TOTAL PASSIF'] = total_passif
    
    # Totaux
    bilan['totaux'] = {
        'total_actif': total_actif,
        'total_passif': total_passif,
        'ecart': abs(total_actif - total_passif),
        'capitaux_propres': capitaux_propres,
        'dettes_financieres': dettes_fin,
        'tresorerie': tresorerie,
        'resultat_exercice': resultat
    }
    
    # Ratios
    if total_actif > 0:
        autonomie = (capitaux_propres / total_actif) * 100
        endettement = (total_dettes / capitaux_propres * 100) if capitaux_propres > 0 else 0
        fdr = (capitaux_propres + dettes_fin) - immobilisations
        bfr = (stocks + max(clients, 0)) - (max(dettes_four, 0) + max(dettes_perso, 0) + max(dettes_soc, 0) + max(dettes_fisc, 0))
        tn = fdr - bfr
        liquidite = ((actif_circulant + tresorerie) / total_dettes * 100) if total_dettes > 0 else 0
        
        bilan['ratios'] = {
            'Autonomie financiere (%)': autonomie,
            'Endettement (%)': endettement,
            'Fonds de roulement FDR': fdr,
            'Besoin FDR BFR': bfr,
            'Tresorerie nette': tn,
            'Liquidite generale (%)': liquidite
        }
        
        # Analyse
        if bilan['totaux']['ecart'] < 1:
            bilan['analyse'].append({'type': 'OK', 'message': 'Bilan equilibre'})
        else:
            bilan['analyse'].append({'type': 'CRITIQUE', 'message': f"Bilan desequilibre : {bilan['totaux']['ecart']:.2f} EUR"})
        
        if autonomie > 30:
            bilan['analyse'].append({'type': 'OK', 'message': f'Bonne autonomie ({autonomie:.1f}%)'})
        elif autonomie < 20:
            bilan['analyse'].append({'type': 'WARNING', 'message': f'Faible autonomie ({autonomie:.1f}%)'})
        
        if tn > 0:
            bilan['analyse'].append({'type': 'OK', 'message': f'Tresorerie nette positive ({tn:,.2f} EUR)'})
        else:
            bilan['analyse'].append({'type': 'WARNING', 'message': f'Tresorerie nette negative ({tn:,.2f} EUR)'})
    
    return bilan


def generer_rapport_bilan(bilan, nom_entreprise="Entreprise", exercice=""):
    """Genere un rapport professionnel du bilan"""
    rapport = []
    rapport.append(f"# BILAN COMPTABLE - {nom_entreprise}")
    rapport.append(f"## Exercice {exercice}")
    rapport.append(f"*Date cloture : {bilan['date_cloture']}*\n---\n")
    
    rapport.append("## ACTIF\n")
    for poste, val in bilan['actif'].items():
        if val != 0:
            rapport.append(f"- {poste} : {val:,.2f} EUR")
    
    rapport.append("\n## PASSIF\n")
    for poste, val in bilan['passif'].items():
        if val != 0:
            rapport.append(f"- {poste} : {val:,.2f} EUR")
    
    if bilan['ratios']:
        rapport.append("\n## RATIOS FINANCIERS\n")
        for nom, val in bilan['ratios'].items():
            rapport.append(f"- {nom} : {val:,.2f}")
    
    if bilan['analyse']:
        rapport.append("\n## ANALYSE\n")
        for item in bilan['analyse']:
            rapport.append(f"- [{item['type']}] {item['message']}")
    
    rapport.append("\n---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)


def generer_bilan(df, date_cloture):
    """Wrapper pour compatibilite"""
    return calculer_bilan(df, date_cloture)

def page_bilan():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
st.title("📊 Bilan Comptable")
st.markdown("**Vision patrimoniale** avec ratios financiers selon PCG")
st.caption("✨ Pour Cabinets, DAF et Dirigeants - FDR, BFR, Trésorerie nette")

uploaded_file = st.file_uploader(
    "📎 Déposer votre balance ou FEC",
    type=["csv", "xlsx", "txt"]
)

if uploaded_file:
    from utils.bilan import calculer_bilan, generer_rapport_bilan
    from utils.intelligent_parser import parser_balance_intelligent

    try:
        with st.spinner("🤖 Analyse..."):
            if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                df, info = parser_balance_intelligent(uploaded_file)
                st.success(f"✅ Format : **{info['format_detecte']}** | **{len(df):,} comptes**")
            else:
                df, erreur = charger_fichier(uploaded_file)
                if erreur:
                    st.error(f"❌ Erreur : {erreur}")
                    st.stop()
                st.success(f"✅ FEC chargé : **{len(df):,} lignes**")

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            nom_entreprise = st.text_input("🏢 Entreprise", value="Entreprise")
        with col2:
            exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))
        with col3:
            date_cloture = st.date_input("📆 Date de clôture")

        if st.button("📊 Générer le Bilan", type="primary", use_container_width=True):
            with st.spinner("Calcul en cours..."):
                bilan = calculer_bilan(df, str(date_cloture))

                if 'erreur' in bilan:
                    st.error(f"❌ {bilan['erreur']}")
                else:
                    st.markdown(f"## 💼 Bilan au {date_cloture}")
                    st.caption(f"{nom_entreprise} - Exercice {exercice}")

                    totaux = bilan['totaux']
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📦 Actif", f"{totaux['total_actif']:,.0f} €")
                    with col2:
                        st.metric("💼 Passif", f"{totaux['total_passif']:,.0f} €")
                    with col3:
                        st.metric("🏦 Capitaux", f"{totaux['capitaux_propres']:,.0f} €")
                    with col4:
                        ecart = totaux['ecart']
                        st.metric("⚖ Écart", f"{ecart:,.2f} €")

                    if ecart < 1:
                        st.success("✅ Bilan équilibré")
                    else:
                        st.warning(f"⚠ Bilan déséquilibré de {ecart:,.2f} €")

                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### 📦 ACTIF")
                        st.dataframe(pd.DataFrame([
                            {'Poste': k, 'Montant (€)': f"{v:,.2f}"} 
                            for k, v in bilan['actif'].items() if v != 0
                        ]), use_container_width=True, hide_index=True)
                    with col2:
                        st.markdown("### 💼 PASSIF")
                        st.dataframe(pd.DataFrame([
                            {'Poste': k, 'Montant (€)': f"{v:,.2f}"} 
                            for k, v in bilan['passif'].items() if v != 0
                        ]), use_container_width=True, hide_index=True)

                    st.divider()
                    if bilan['ratios']:
                        st.markdown("## 📈 Ratios Financiers")
                        ratios = bilan['ratios']
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Autonomie", f"{ratios['Autonomie financiere (%)']:.1f}%")
                        with col2:
                            st.metric("FDR", f"{ratios['Fonds de roulement FDR']:,.0f} €")
                        with col3:
                            st.metric("Trésorerie nette", f"{ratios['Tresorerie nette']:,.0f} €")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Endettement", f"{ratios['Endettement (%)']:.1f}%")
                        with col2:
                            st.metric("BFR", f"{ratios['Besoin FDR BFR']:,.0f} €")
                        with col3:
                            st.metric("Liquidité", f"{ratios['Liquidite generale (%)']:.1f}%")

                    st.divider()
                    if bilan['analyse']:
                        st.markdown("## 💡 Analyse Cabinet")
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
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Bilan", resultat=rapport)
                            st.success("✅ Sauvegardé !")
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

