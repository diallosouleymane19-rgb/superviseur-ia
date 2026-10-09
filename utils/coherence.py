# -*- coding: utf-8 -*-
"""Module Cohérence des Données - SMD Global Consulting LLC"""
from utils.sig_pcg import nb_fr
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)

# Colonnes du FEC renseignées seulement si elles servent (article A47 A-1 du LPF)
COLONNES_FEC_FACULTATIVES = ("CompAuxNum", "CompAuxLib", "EcritureLet", "DateLet", "Montantdevise", "Idevise")


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
            'message': 'Aucune donnée à analyser'
        }
        return resultat
    
    # Le score ne porte que sur les contrôles applicables au fichier (une balance n'a ni dates ni libellés d'écriture)
    points_total = 20 + 15   # complétude et doublons : toujours applicables
    points_obtenus = 0
    
    # 1. COMPLETUDE GLOBALE (20 points)
    # Colonnes facultatives du FEC (vides quand elles ne servent pas) : exclues de la complétude
    cols_utiles = [c for c in df.columns if c not in COLONNES_FEC_FACULTATIVES]
    vide = df[cols_utiles].astype(str).apply(lambda c: c.str.strip().isin(["", "nan", "None", "NaT"]))
    nb_cellules_total = len(df) * len(cols_utiles)
    nb_cellules_remplies = int((~vide & df[cols_utiles].notna()).sum().sum())
    completude = (nb_cellules_remplies / nb_cellules_total * 100) if nb_cellules_total > 0 else 0
    
    if completude >= 95:
        resultat['verifications']['Complétude des données'] = {
            'status': 'OK',
            'message': f'{nb_fr(completude, 1)} % des cellules sont remplies'
        }
        points_obtenus += 20
    elif completude >= 80:
        resultat['verifications']['Complétude des données'] = {
            'status': 'WARNING',
            'message': f'{nb_fr(completude, 1)} % remplies - quelques données manquantes'
        }
        points_obtenus += 12
    else:
        resultat['verifications']['Complétude des données'] = {
            'status': 'KO',
            'message': f'{nb_fr(completude, 1)} % seulement - beaucoup de données manquantes'
        }
        points_obtenus += 5
        resultat['recommandations'].append("Compléter les données manquantes")
    
    # 2. UNICITE / DOUBLONS (15 points)
    nb_doublons = df.duplicated().sum()
    if nb_doublons == 0:
        resultat['verifications']['Unicité des lignes'] = {
            'status': 'OK',
            'message': 'Aucun doublon détecté'
        }
        points_obtenus += 15
    elif nb_doublons < len(df) * 0.01:
        resultat['verifications']['Unicité des lignes'] = {
            'status': 'WARNING',
            'message': f'{nb_doublons} doublons détectés (< 1%)'
        }
        points_obtenus += 10
    else:
        resultat['verifications']['Unicité des lignes'] = {
            'status': 'KO',
            'message': f'{nb_doublons} doublons détectés'
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
        points_total += 25
        total_debit = df['_debit'].sum()
        total_credit = df['_credit'].sum()
        ecart = abs(total_debit - total_credit)
        
        if ecart < 0.01:
            resultat['verifications']['Équilibre Débit/Crédit'] = {
                'status': 'OK',
                'message': f'Balance équilibrée ({nb_fr(total_debit, 2)} €)'
            }
            points_obtenus += 25
        elif ecart < total_debit * 0.001:
            resultat['verifications']['Équilibre Débit/Crédit'] = {
                'status': 'WARNING',
                'message': f'Léger écart de {nb_fr(ecart, 2)} €'
            }
            points_obtenus += 15
        else:
            resultat['verifications']['Équilibre Débit/Crédit'] = {
                'status': 'KO',
                'message': f'Déséquilibre de {nb_fr(ecart, 2)} €'
            }
            points_obtenus += 5
            resultat['recommandations'].append("Vérifier l'intégrité des écritures")
    
    # 5. COHERENCE DES COMPTES (15 points)
    if 'CompteNum' in df.columns:
        points_total += 15
        compte_str = df['CompteNum'].astype(str).str.strip()
        comptes_valides = compte_str.str.match(r'^\d{2,8}$').sum()
        taux_valide = (comptes_valides / len(df) * 100) if len(df) > 0 else 0
        
        if taux_valide >= 95:
            resultat['verifications']['Format des comptes'] = {
                'status': 'OK',
                'message': f'{nb_fr(taux_valide, 1)} % des comptes au format valide'
            }
            points_obtenus += 15
        elif taux_valide >= 80:
            resultat['verifications']['Format des comptes'] = {
                'status': 'WARNING',
                'message': f'{nb_fr(taux_valide, 1)} % au format valide'
            }
            points_obtenus += 10
        else:
            resultat['verifications']['Format des comptes'] = {
                'status': 'KO',
                'message': f'{nb_fr(taux_valide, 1)} % seulement au format valide'
            }
            points_obtenus += 3
            resultat['recommandations'].append("Vérifier le format des numéros de compte")
    
    # 6. COHERENCE DATES (15 points)
    if 'EcritureDate' in df.columns:
        points_total += 15
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce')
            dates_valides = dates.notna().sum()
            taux_dates = (dates_valides / len(df) * 100) if len(df) > 0 else 0
            
            if taux_dates >= 95:
                resultat['verifications']['Format des dates'] = {
                    'status': 'OK',
                    'message': f'{nb_fr(taux_dates, 1)} % des dates valides'
                }
                points_obtenus += 15
            else:
                resultat['verifications']['Format des dates'] = {
                    'status': 'WARNING',
                    'message': f'{nb_fr(taux_dates, 1)} % des dates valides'
                }
                points_obtenus += 8
                resultat['recommandations'].append("Vérifier le format des dates (AAAAMMJJ)")
        except:
            pass
    
    # 7. LIBELLES (10 points)
    if 'EcritureLib' in df.columns:
        points_total += 10
        libelles_remplis = df['EcritureLib'].notna().sum()
        taux_libelles = (libelles_remplis / len(df) * 100) if len(df) > 0 else 0
        
        if taux_libelles >= 95:
            resultat['verifications']['Libellés renseignés'] = {
                'status': 'OK',
                'message': f'{nb_fr(taux_libelles, 1)} % des écritures ont un libellé'
            }
            points_obtenus += 10
        else:
            resultat['verifications']['Libellés renseignés'] = {
                'status': 'WARNING',
                'message': f'{nb_fr(taux_libelles, 1)} % renseignés'
            }
            points_obtenus += 5
            resultat['recommandations'].append("Renseigner les libellés manquants (obligatoire PCG)")
    
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
        resultat['niveau'] = 'A améliorer'
    else:
        resultat['niveau'] = 'Critique'
    
    if not resultat['recommandations']:
        if resultat['score_qualite'] >= 90:
            resultat['recommandations'].append("Données de qualité excellente - poursuivre les bonnes pratiques")
        else:
            resultat['recommandations'].append("Maintenir la rigueur sur la saisie comptable")
    
    return resultat


def visuels_coherence(resultat):
    """Indicateurs pour l'export Word (mêmes chiffres qu'à l'écran)."""
    score, k = resultat['score_qualite'], resultat.get('kpis', {})
    return [{"libelle": "Score qualité", "valeur": f"{nb_fr(score, 1)} %", "detail": resultat.get('niveau', ''),
             "ton": "bon" if score >= 90 else "neutre" if score >= 75 else "mauvais"},
            {"libelle": "Complétude", "valeur": f"{nb_fr(k.get('completude', 0), 1)} %", "detail": ""},
            {"libelle": "Doublons", "valeur": nb_fr(k.get('doublons', 0)),
             "ton": "mauvais" if k.get('doublons', 0) else "bon", "detail": "à examiner" if k.get('doublons', 0) else "aucun"},
            {"libelle": "Lignes / colonnes", "valeur": f"{nb_fr(k.get('nb_lignes', 0))} / {k.get('nb_colonnes', 0)}",
             "detail": ""}], []


def generer_rapport_coherence(resultat, nom_entreprise="Entreprise"):
    """Génère un rapport professionnel de cohérence des données."""
    rapport = []
    rapport.append("# RAPPORT DE COHÉRENCE DES DONNÉES")
    rapport.append(f"## {nom_entreprise}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## SCORE DE QUALITÉ")
    rapport.append("")
    rapport.append(f"**{resultat.get('niveau', 'N/A')} : {nb_fr(resultat['score_qualite'], 1)} %**")
    rapport.append("")
    rapport.append(f"- Lignes : {nb_fr(resultat['kpis'].get('nb_lignes', 0), 0)}")
    rapport.append(f"- Colonnes : {resultat['kpis'].get('nb_colonnes', 0)}")
    rapport.append(f"- Complétude : {nb_fr(resultat['kpis'].get('completude', 0), 1)} %")
    rapport.append(f"- Doublons : {resultat['kpis'].get('doublons', 0)}")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## VÉRIFICATIONS EFFECTUÉES")
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
    rapport.append("*SMD Global Consulting LLC - Superviseur IA Comptable*")
    
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
    st.markdown("**Contrôle qualité** des données comptables")
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
        type=TYPES_BALANCE
    )

    if uploaded_file:
        from utils.coherence import verifier_coherence, generer_rapport_coherence
        from utils.intelligent_parser import parser_balance_intelligent, charger_balance_ou_fec

        try:
            with st.spinner("🤖 Analyse..."):
                df, _msg, info = charger_balance_ou_fec(uploaded_file)
                st.success(f"✅ {_msg}")
                if info and info.get('colonnes_manquantes'):
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Vérifiez l'en-tête du fichier.")

            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), width="stretch")

            st.divider()

            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")

            if st.button("🔍 Vérifier la cohérence", type="primary", width="stretch"):
                with st.spinner("Vérifications en cours..."):
                    resultat = verifier_coherence(df)

                    st.markdown("## 🎯 Score de Qualité")

                    score = resultat['score_qualite']
                    niveau = resultat.get('niveau', 'N/A')

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score >= 90:
                            st.success(f"### {niveau} : {nb_fr(score, 1)} % ✅")
                        elif score >= 75:
                            st.info(f"### {niveau} : {nb_fr(score, 1)} % ℹ")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {nb_fr(score, 1)} % ⚠")
                        else:
                            st.error(f"### {niveau} : {nb_fr(score, 1)} % ❌")

                        st.progress(int(score))

                    st.divider()

                    kpis = resultat.get('kpis', {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📝 Lignes", f"{nb_fr(kpis.get('nb_lignes', 0), 0)}")
                    with col2:
                        st.metric("📊 Colonnes", kpis.get('nb_colonnes', 0))
                    with col3:
                        st.metric("✅ Complétude", f"{nb_fr(kpis.get('completude', 0), 1)} %")
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
                        bouton_sauvegarde(type_analyse="Cohérence", resultat=rapport, libelle="💾 Sauvegarder")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_coherence(resultat)
                            generer_bouton_word(f"Coherence_{nom_entreprise}", rapport, indicateurs=ind_w,
                                                graphiques=graph_w, sans_sections=("SCORE DE QUALITÉ",))
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")

    # -----------------------------------------------------------------------------
    # 12. VEILLE FISCALE
    # -----------------------------------------------------------------------------

