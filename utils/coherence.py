# -*- coding: utf-8 -*-
"""Module Coherence des Donnees - SMD Consulting"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)

def verifier_coherence(df):
    resultat = {
        'score_qualite': 0,
        'champs_valides': 0,
        'lignes_completes': 0,
        'verifications': {},
        'recommandations': [],
        'kpis': {}
    }
    
    if df is None or len(df) == 0:
        resultat['verifications']['Donnees'] = {
            'status': 'KO',
            'message': 'Aucune donnee a analyser'
        }
        return resultat
    
    points_total = 100
    points_obtenus = 0
    
    # 1. COMPLETUDE GLOBALE (20 points)
    nb_cellules_total = len(df) * len(df.columns)
    nb_cellules_remplies = df.notna().sum().sum()
    completude = (nb_cellules_remplies / nb_cellules_total * 100) if nb_cellules_total > 0 else 0
    
    if completude >= 95:
        resultat['verifications']['Completude des donnees'] = {
            'status': 'OK',
            'message': f'{completude:.1f}% des cellules sont remplies'
        }
        points_obtenus += 20
    elif completude >= 80:
        resultat['verifications']['Completude des donnees'] = {
            'status': 'WARNING',
            'message': f'{completude:.1f}% remplies - quelques donnees manquantes'
        }
        points_obtenus += 12
    else:
        resultat['verifications']['Completude des donnees'] = {
            'status': 'KO',
            'message': f'{completude:.1f}% seulement - beaucoup de donnees manquantes'
        }
        points_obtenus += 5
        resultat['recommandations'].append("Completer les donnees manquantes")
    
    # 2. UNICITE / DOUBLONS (15 points)
    nb_doublons = df.duplicated().sum()
    if nb_doublons == 0:
        resultat['verifications']['Unicite des lignes'] = {
            'status': 'OK',
            'message': 'Aucun doublon detecte'
        }
        points_obtenus += 15
    elif nb_doublons < len(df) * 0.01:
        resultat['verifications']['Unicite des lignes'] = {
            'status': 'WARNING',
            'message': f'{nb_doublons} doublons detectes (< 1%)'
        }
        points_obtenus += 10
    else:
        resultat['verifications']['Unicite des lignes'] = {
            'status': 'KO',
            'message': f'{nb_doublons} doublons detectes'
        }
        points_obtenus += 3
        resultat['recommandations'].append("Supprimer les doublons identiques")
    
    # 3. CONVERSION NUMERIQUE
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    # 4. EQUILIBRE COMPTABLE (25 points)
    if '_debit' in df.columns and '_credit' in df.columns:
        total_debit = df['_debit'].sum()
        total_credit = df['_credit'].sum()
        ecart = abs(total_debit - total_credit)
        
        if ecart < 0.01:
            resultat['verifications']['Equilibre Debit/Credit'] = {
                'status': 'OK',
                'message': f'Balance equilibree ({total_debit:,.2f} EUR)'
            }
            points_obtenus += 25
        elif ecart < total_debit * 0.001:
            resultat['verifications']['Equilibre Debit/Credit'] = {
                'status': 'WARNING',
                'message': f'Leger ecart de {ecart:.2f} EUR'
            }
            points_obtenus += 15
        else:
            resultat['verifications']['Equilibre Debit/Credit'] = {
                'status': 'KO',
                'message': f'Desequilibre de {ecart:,.2f} EUR'
            }
            points_obtenus += 5
            resultat['recommandations'].append("Verifier l'integrite des ecritures")
    
    # 5. COHERENCE DES COMPTES (15 points)
    if 'CompteNum' in df.columns:
        compte_str = df['CompteNum'].astype(str).str.strip()
        comptes_valides = compte_str.str.match(r'^\d{2,8}$').sum()
        taux_valide = (comptes_valides / len(df) * 100) if len(df) > 0 else 0
        
        if taux_valide >= 95:
            resultat['verifications']['Format des comptes'] = {
                'status': 'OK',
                'message': f'{taux_valide:.1f}% des comptes au format valide'
            }
            points_obtenus += 15
        elif taux_valide >= 80:
            resultat['verifications']['Format des comptes'] = {
                'status': 'WARNING',
                'message': f'{taux_valide:.1f}% au format valide'
            }
            points_obtenus += 10
        else:
            resultat['verifications']['Format des comptes'] = {
                'status': 'KO',
                'message': f'{taux_valide:.1f}% seulement au format valide'
            }
            points_obtenus += 3
            resultat['recommandations'].append("Verifier le format des numeros de compte")
    
    # 6. COHERENCE DATES (15 points)
    if 'EcritureDate' in df.columns:
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce')
            dates_valides = dates.notna().sum()
            taux_dates = (dates_valides / len(df) * 100) if len(df) > 0 else 0
            
            if taux_dates >= 95:
                resultat['verifications']['Format des dates'] = {
                    'status': 'OK',
                    'message': f'{taux_dates:.1f}% des dates valides'
                }
                points_obtenus += 15
            else:
                resultat['verifications']['Format des dates'] = {
                    'status': 'WARNING',
                    'message': f'{taux_dates:.1f}% des dates valides'
                }
                points_obtenus += 8
                resultat['recommandations'].append("Verifier le format des dates (AAAAMMJJ)")
        except:
            pass
    
    # 7. LIBELLES (10 points)
    if 'EcritureLib' in df.columns:
        libelles_remplis = df['EcritureLib'].notna().sum()
        taux_libelles = (libelles_remplis / len(df) * 100) if len(df) > 0 else 0
        
        if taux_libelles >= 95:
            resultat['verifications']['Libelles renseignes'] = {
                'status': 'OK',
                'message': f'{taux_libelles:.1f}% des ecritures ont un libelle'
            }
            points_obtenus += 10
        else:
            resultat['verifications']['Libelles renseignes'] = {
                'status': 'WARNING',
                'message': f'{taux_libelles:.1f}% renseignes'
            }
            points_obtenus += 5
            resultat['recommandations'].append("Renseigner les libelles manquants (obligatoire PCG)")
    
    # ===== KPIs =====
    resultat['score_qualite'] = round((points_obtenus / points_total) * 100, 1)
    resultat['champs_valides'] = len(df.columns)
    resultat['lignes_completes'] = int(df.dropna().shape[0])
    
    resultat['kpis'] = {
        'completude': completude,
        'doublons': int(nb_doublons),
        'nb_lignes': len(df),
        'nb_colonnes': len(df.columns)
    }
    
    # ===== NIVEAU =====
    if resultat['score_qualite'] >= 90:
        resultat['niveau'] = 'Excellent'
    elif resultat['score_qualite'] >= 75:
        resultat['niveau'] = 'Bon'
    elif resultat['score_qualite'] >= 50:
        resultat['niveau'] = 'A ameliorer'
    else:
        resultat['niveau'] = 'Critique'
    
    if not resultat['recommandations']:
        if resultat['score_qualite'] >= 90:
            resultat['recommandations'].append("Donnees de qualite excellente - poursuivre les bonnes pratiques")
        else:
            resultat['recommandations'].append("Maintenir la rigueur sur la saisie comptable")
    
    return resultat


def generer_rapport_coherence(resultat, nom_entreprise="Entreprise"):
    """Genere un rapport professionnel de coherence des donnees."""
    rapport = []
    rapport.append("# RAPPORT DE COHERENCE DES DONNEES")
    rapport.append(f"## {nom_entreprise}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## SCORE DE QUALITE")
    rapport.append("")
    rapport.append(f"**{resultat.get('niveau', 'N/A')} : {resultat['score_qualite']}%**")
    rapport.append("")
    rapport.append(f"- Lignes : {resultat['kpis'].get('nb_lignes', 0):,}")
    rapport.append(f"- Colonnes : {resultat['kpis'].get('nb_colonnes', 0)}")
    rapport.append(f"- Completude : {resultat['kpis'].get('completude', 0):.1f}%")
    rapport.append(f"- Doublons : {resultat['kpis'].get('doublons', 0)}")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## VERIFICATIONS EFFECTUEES")
    rapport.append("")
    
    for nom, ctrl in resultat['verifications'].items():
        symbol = '[OK]' if ctrl['status'] == 'OK' else '[!]' if ctrl['status'] == 'WARNING' else '[X]'
        rapport.append(f"- {symbol} **{nom}** : {ctrl['message']}")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if resultat['recommandations']:
        rapport.append("## RECOMMANDATIONS")
        rapport.append("")
        for reco in resultat['recommandations']:
            rapport.append(f"- {reco}")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)




def page_coherence():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("✅ Cohérence des Données")
    st.markdown("**Audit qualité** des données comptables")
    st.caption("✨ 7 contrôles automatiques + Score qualité")

    with st.expander("ℹ Quels contrôles ?"):
        st.markdown("""
        1. **Complétude des données** (20 pts)
        2. **Unicité / Doublons** (15 pts)
        3. **Équilibre Débit/Crédit** (25 pts)
        4. **Format des comptes** (15 pts)
        5. **Format des dates** (15 pts)
        6. **Libellés renseignés** (10 pts)

        **Total : 100 points**
        """)

    uploaded_file = st.file_uploader(
        "📎 Données comptables",
        type=["csv", "xlsx", "txt"]
    )

    if uploaded_file:
        from utils.coherence import verifier_coherence, generer_rapport_coherence
        from utils.intelligent_parser import parser_balance_intelligent

        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    try:
                        df, info = parser_balance_intelligent(uploaded_file)
                        st.success(f"✅ Format : **{info['format_detecte']}** | **{len(df):,} lignes**")
                    except:
                        if uploaded_file.name.endswith('xlsx'):
                            df = pd.read_excel(uploaded_file)
                        else:
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')
                        st.success(f"✅ Fichier chargé : **{len(df):,} lignes**")
                else:
                    df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                    st.success(f"✅ FEC : **{len(df):,} lignes**")

            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), use_container_width=True)

            st.divider()

            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")

            if st.button("🔍 Vérifier la cohérence", type="primary", use_container_width=True):
                with st.spinner("Vérifications en cours..."):
                    resultat = verifier_coherence(df)

                    st.markdown("## 🎯 Score de Qualité")

                    score = resultat['score_qualite']
                    niveau = resultat.get('niveau', 'N/A')

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score >= 90:
                            st.success(f"### {niveau} : {score}% ✅")
                        elif score >= 75:
                            st.info(f"### {niveau} : {score}% ℹ")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {score}% ⚠")
                        else:
                            st.error(f"### {niveau} : {score}% ❌")

                        st.progress(int(score))

                    st.divider()

                    kpis = resultat.get('kpis', {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📝 Lignes", f"{kpis.get('nb_lignes', 0):,}")
                    with col2:
                        st.metric("📊 Colonnes", kpis.get('nb_colonnes', 0))
                    with col3:
                        st.metric("✅ Complétude", f"{kpis.get('completude', 0):.1f}%")
                    with col4:
                        st.metric("⚠ Doublons", kpis.get('doublons', 0),
                                 delta_color="inverse" if kpis.get('doublons', 0) > 0 else "normal")

                    st.divider()

                    st.markdown("## 🔍 Vérifications Effectuées")

                    for nom, ctrl in resultat['verifications'].items():
                        if ctrl['status'] == 'OK':
                            st.success(f"✅ **{nom}** : {ctrl['message']}")
                        elif ctrl['status'] == 'WARNING':
                            st.warning(f"⚠ **{nom}** : {ctrl['message']}")
                        else:
                            st.error(f"❌ **{nom}** : {ctrl['message']}")

                    st.divider()

                    if resultat['recommandations']:
                        st.markdown("## 💡 Recommandations")
                        for reco in resultat['recommandations']:
                            st.info(f"💼 {reco}")

                    st.divider()

                    rapport = generer_rapport_coherence(resultat, nom_entreprise)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Cohérence", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Coherence_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")

    # -----------------------------------------------------------------------------
    # 12. VEILLE FISCALE
    # -----------------------------------------------------------------------------

