# -*- coding: utf-8 -*-
"""
Module Traitement FEC Professionnel - SMD Global Consulting LLC
Conforme aux exigences DGFiP (Article L.47 A du LPF)
"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


# Colonnes obligatoires du FEC (Article A.47 A-1 du LPF)
COLONNES_FEC_OBLIGATOIRES = [
    'JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate',
    'CompteNum', 'CompteLib', 'CompAuxNum', 'CompAuxLib',
    'PieceRef', 'PieceDate', 'EcritureLib', 'Debit', 'Credit',
    'EcritureLet', 'DateLet', 'ValidDate', 'Montantdevise', 'Idevise'
]


def lire_fec(fichier):
    """
    Lit un fichier FEC en testant differents separateurs et encodages
    """
    separateurs = ['|', '\t', ';']
    encodages = ['utf-8', 'iso-8859-1', 'cp1252']
    
    for sep in separateurs:
        for enc in encodages:
            try:
                fichier.seek(0)
                df = pd.read_csv(fichier, sep=sep, encoding=enc, dtype=str)
                if len(df.columns) >= 15:
                    return df, sep, enc
            except Exception:
                continue

    return None, None, None


def valider_fec(df):
    """
    Validation complete du FEC selon normes DGFiP
    
    Returns:
        dict: Resultats detailles de validation avec score de conformite
    """
    resultats = {}
    points = 0
    points_max = 0
    
    # 1. VERIFICATION STRUCTURE (18 colonnes obligatoires)
    points_max += 20
    colonnes_presentes = set(df.columns)
    colonnes_attendues = set(COLONNES_FEC_OBLIGATOIRES)
    colonnes_manquantes = colonnes_attendues - colonnes_presentes
    
    if not colonnes_manquantes:
        resultats['Structure (18 colonnes)'] = {
            "valide": True,
            "message": "Toutes les colonnes obligatoires sont presentes"
        }
        points += 20
    else:
        resultats['Structure (18 colonnes)'] = {
            "valide": False,
            "message": f"Colonnes manquantes : {', '.join(colonnes_manquantes)}"
        }
    
    # 2. VERIFICATION COMPLETUDE DES DONNEES
    points_max += 15
    if 'EcritureDate' in df.columns:
        nb_dates_manquantes = df['EcritureDate'].isna().sum()
        if nb_dates_manquantes == 0:
            resultats['Dates ecritures'] = {
                "valide": True,
                "message": "100% des ecritures sont datees"
            }
            points += 15
        else:
            resultats['Dates ecritures'] = {
                "valide": False,
                "message": f"{nb_dates_manquantes} ecritures sans date"
            }
    
    # 3. VERIFICATION FORMAT DATES (AAAAMMJJ)
    points_max += 10
    if 'EcritureDate' in df.columns:
        try:
            echantillon = df['EcritureDate'].head(100)
            dates_test = pd.to_datetime(echantillon, format='%Y%m%d', errors='coerce')
            taux_valide = (dates_test.notna().sum() / len(echantillon)) * 100 if len(echantillon) > 0 else 0
        
            if taux_valide >= 95:
                resultats['Format dates (AAAAMMJJ)'] = {
                    "valide": True,
                    "message": f"Format conforme ({taux_valide:.0f}% valide)"
                }
                points += 10
            else:
                resultats['Format dates (AAAAMMJJ)'] = {
                    "valide": False,
                    "message": f"Format non conforme ({taux_valide:.0f}% valide)"
                }
        except Exception:
            resultats['Format dates (AAAAMMJJ)'] = {
                "valide": False,
                "message": "Format de date non valide"
            }
    
    # 4. VERIFICATION EQUILIBRE DEBIT/CREDIT
    points_max += 25
    if 'Debit' in df.columns and 'Credit' in df.columns:
        try:
            df_calc = df.copy()
            df_calc['Debit_num'] = pd.to_numeric(df_calc['Debit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_calc['Credit_num'] = pd.to_numeric(df_calc['Credit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            total_debit = df_calc['Debit_num'].sum()
            total_credit = df_calc['Credit_num'].sum()
            ecart = abs(total_debit - total_credit)
            
            if ecart < 0.01:
                resultats['Equilibre Debit/Credit'] = {
                    "valide": True,
                    "message": f"Equilibre parfait : {total_debit:,.2f} EUR"
                }
                points += 25
            else:
                resultats['Equilibre Debit/Credit'] = {
                    "valide": False,
                    "message": f"Ecart de {ecart:,.2f} EUR detecte"
                }
        except Exception as e:
            resultats['Equilibre Debit/Credit'] = {
                "valide": False,
                "message": f"Impossible de calculer : {e}"
            }
    
    # 5. VERIFICATION NUMEROS DE COMPTES
    points_max += 15
    if 'CompteNum' in df.columns:
        comptes_uniques = df['CompteNum'].nunique()
        comptes_vides = df['CompteNum'].isna().sum()
        if comptes_vides == 0:
            resultats['Numeros de comptes'] = {
                "valide": True,
                "message": f"{comptes_uniques} comptes utilises - 100% renseignes"
            }
            points += 15
        else:
            resultats['Numeros de comptes'] = {
                "valide": False,
                "message": f"{comptes_vides} ecritures sans compte"
            }
    
    # 6. VERIFICATION JOURNAUX
    points_max += 15
    if 'JournalCode' in df.columns:
        journaux = df['JournalCode'].nunique()
        if journaux > 0:
            resultats['Journaux comptables'] = {
                "valide": True,
                "message": f"{journaux} journaux distincts identifies"
            }
            points += 15
        else:
            resultats['Journaux comptables'] = {
                "valide": False,
                "message": "Aucun journal identifie"
            }
    
    # SCORE DE CONFORMITE
    score_conformite = (points / points_max * 100) if points_max > 0 else 0
    
    resultats['_meta'] = {
        'score_conformite': round(score_conformite, 1),
        'points': points,
        'points_max': points_max,
        'niveau': 'Excellent' if score_conformite >= 90 else 'Bon' if score_conformite >= 75 else 'A ameliorer' if score_conformite >= 50 else 'Non conforme'
    }
    
    return resultats


def analyser_fec(df):
    """
    Analyse approfondie du FEC - Rendu cabinet professionnel
    """
    rapport = []
    
    # En-tete du rapport
    rapport.append("## RAPPORT D'ANALYSE FEC")
    rapport.append(f"*Date d'analyse : {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")
    
    # 1. STATISTIQUES GENERALES
    rapport.append("### 1. STATISTIQUES GENERALES")
    rapport.append(f"- **Nombre total d'ecritures** : {len(df):,}")
    rapport.append(f"- **Nombre de colonnes** : {len(df.columns)}")
    
    if 'EcritureNum' in df.columns:
        nb_pieces = df['EcritureNum'].nunique()
        rapport.append(f"- **Nombre de pieces comptables** : {nb_pieces:,}")
    
    if 'CompteNum' in df.columns:
        nb_comptes = df['CompteNum'].nunique()
        rapport.append(f"- **Nombre de comptes utilises** : {nb_comptes}")
    
    if 'JournalCode' in df.columns:
        nb_journaux = df['JournalCode'].nunique()
        rapport.append(f"- **Nombre de journaux** : {nb_journaux}")
    
    # 2. ANALYSE FINANCIERE
    rapport.append("\n### 2. ANALYSE FINANCIERE")
    if 'Debit' in df.columns and 'Credit' in df.columns:
        try:
            df_calc = df.copy()
            df_calc['Debit_num'] = pd.to_numeric(df_calc['Debit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_calc['Credit_num'] = pd.to_numeric(df_calc['Credit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            total_debit = df_calc['Debit_num'].sum()
            total_credit = df_calc['Credit_num'].sum()
            volume_total = total_debit + total_credit
            
            rapport.append(f"- **Total Debit** : {total_debit:,.2f} EUR")
            rapport.append(f"- **Total Credit** : {total_credit:,.2f} EUR")
            rapport.append(f"- **Volume total** : {volume_total:,.2f} EUR")
            rapport.append(f"- **Ecart D/C** : {abs(total_debit - total_credit):,.2f} EUR")
            rapport.append(f"- **Montant moyen ecriture** : {volume_total / len(df):,.2f} EUR")
        except Exception as e:
            rapport.append(f"*Erreur calcul : {e}*")
    
    # 3. ANALYSE PAR JOURNAL
    if 'JournalCode' in df.columns:
        rapport.append("\n### 3. REPARTITION PAR JOURNAL")
        repartition = df['JournalCode'].value_counts().head(10)
        for journal, count in repartition.items():
            pct = (count / len(df)) * 100
            rapport.append(f"- **{journal}** : {count:,} ecritures ({pct:.1f}%)")
    
    # 4. ANALYSE PERIODE
    if 'EcritureDate' in df.columns:
        rapport.append("\n### 4. PERIODE COMPTABLE")
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce').dropna()
            if len(dates) > 0:
                rapport.append(f"- **Date debut** : {dates.min().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Date fin** : {dates.max().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Duree** : {(dates.max() - dates.min()).days} jours")
        except Exception:
            rapport.append("*Format de dates non standard*")
    
    # 5. CONCLUSION
    rapport.append("\n### 5. SYNTHESE")
    rapport.append("Le FEC analyse contient les donnees comptables de l'exercice.")
    rapport.append("Les controles automatiques portent sur la conformite formelle (article A.47 A-1 du LPF).")
    rapport.append("\n**Recommandation** : Croiser cette analyse avec les modules Audit Balance et Loi de Benford pour une expertise complete.")
    
    return "\n".join(rapport)


def detecter_anomalies_fec(df):
    """
    Detection d'anomalies dans le FEC - Approche audit
    """
    anomalies = []
    
    # Ecritures sans libelle
    if 'EcritureLib' in df.columns:
        sans_libelle = df['EcritureLib'].isna().sum()
        if sans_libelle > 0:
            anomalies.append({
                'type': 'Libelle manquant',
                'gravite': 'Moyenne',
                'count': int(sans_libelle),
                'description': f"{sans_libelle} ecritures sans libelle"
            })
    
    # Montants nuls Debit ET Credit
    if 'Debit' in df.columns and 'Credit' in df.columns:
        try:
            df_calc = df.copy()
            df_calc['Debit_num'] = pd.to_numeric(df_calc['Debit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_calc['Credit_num'] = pd.to_numeric(df_calc['Credit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            ecritures_nulles = ((df_calc['Debit_num'] == 0) & (df_calc['Credit_num'] == 0)).sum()
            
            if ecritures_nulles > 0:
                anomalies.append({
                    'type': 'Ecritures montants nuls',
                    'gravite': 'Faible',
                    'count': int(ecritures_nulles),
                    'description': f"{ecritures_nulles} ecritures avec Debit=0 et Credit=0"
                })
        except:
            pass
    
    # Doublons exacts
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        anomalies.append({
            'type': 'Doublons exacts',
            'gravite': 'Elevee',
            'count': int(duplicates),
            'description': f"{duplicates} lignes en doublons exacts detectees"
        })
    
    return anomalies



def page_fec():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📂 Traitement FEC - Audit Conformité DGFiP")
    st.markdown("**Validation et analyse approfondie** des Fichiers des Écritures Comptables (Article L.47 A du LPF)")

    uploaded_file = st.file_uploader(
        "📎 Déposer votre fichier FEC", 
        type=["txt", "csv"],
        help="Format pipe (|) ou tabulation, encodage UTF-8 ou ISO-8859-1"
    )

    if uploaded_file:
        from utils.fec import lire_fec, valider_fec, analyser_fec, detecter_anomalies_fec

        with st.spinner("📖 Lecture du FEC..."):
            df, sep, enc = lire_fec(uploaded_file)

        if df is None:
            st.error("❌ Impossible de lire le FEC. Vérifiez le format (séparateur pipe | ou tabulation).")
        else:
            st.success(f"✅ FEC chargé : **{len(df):,} écritures** | Séparateur : `{sep}` | Encodage : `{enc}`")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📝 Écritures", f"{len(df):,}")
            with col2:
                if 'EcritureNum' in df.columns:
                    st.metric("📄 Pièces", f"{df['EcritureNum'].nunique():,}")
            with col3:
                if 'CompteNum' in df.columns:
                    st.metric("🔢 Comptes", f"{df['CompteNum'].nunique()}")
            with col4:
                if 'JournalCode' in df.columns:
                    st.metric("📚 Journaux", f"{df['JournalCode'].nunique()}")

            with st.expander("👀 Aperçu des données (20 premières lignes)"):
                st.dataframe(df.head(20), use_container_width=True)

            st.divider()

            if st.button("🛡 Lancer la validation DGFiP complète", type="primary", use_container_width=True):
                with st.spinner("Validation en cours selon Article A.47 A-1 du LPF..."):
                    resultats = valider_fec(df)

                    meta = resultats.pop('_meta', {})
                    score = meta.get('score_conformite', 0)
                    niveau = meta.get('niveau', 'Inconnu')

                    st.markdown("## 🎯 Score de Conformité DGFiP")

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

                        st.progress(min(int(score), 100))
                        st.caption(f"Points obtenus : {meta.get('points', 0)} / {meta.get('points_max', 100)}")

                    st.divider()

                    st.markdown("## 📋 Détail des Contrôles")

                    for verif, status in resultats.items():
                        if status["valide"]:
                            st.success(f"✅ **{verif}** : {status.get('message', 'Conforme')}")
                        else:
                            st.error(f"❌ **{verif}** : {status.get('message', '')}")

                    st.divider()

                    st.markdown("## 🔍 Analyse Approfondie")
                    analyse = analyser_fec(df)
                    afficher_rapport(analyse, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True)

                    st.divider()

                    st.markdown("## ⚠ Détection d'Anomalies")
                    anomalies = detecter_anomalies_fec(df)

                    if anomalies:
                        col1, col2, col3 = st.columns(3)
                        nb_elevees = len([a for a in anomalies if a['gravite'] == 'Elevee'])
                        nb_moyennes = len([a for a in anomalies if a['gravite'] == 'Moyenne'])
                        nb_faibles = len([a for a in anomalies if a['gravite'] == 'Faible'])

                        with col1:
                            st.metric("🔴 Élevées", nb_elevees)
                        with col2:
                            st.metric("🟡 Moyennes", nb_moyennes)
                        with col3:
                            st.metric("🔵 Faibles", nb_faibles)

                        for anomalie in anomalies:
                            if anomalie['gravite'] == 'Elevee':
                                st.error(f"🔴 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                            elif anomalie['gravite'] == 'Moyenne':
                                st.warning(f"🟡 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                            else:
                                st.info(f"🔵 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                    else:
                        st.success("✅ Aucune anomalie majeure détectée")

                    st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder le rapport", use_container_width=True):
                            sauvegarder_si_autorise(
                                type_analyse="Audit FEC", 
                                resultat=f"Score: {score}% - {analyse}"
                            )
                            st.success("✅ Rapport sauvegardé !")

                    with col2:
                        rapport_complet = f"""# RAPPORT D'AUDIT FEC

    ## Score de Conformité DGFiP : {score}% ({niveau})

    {analyse}

    ## Anomalies Détectées
    {chr(10).join([f"- {a['type']} ({a['gravite']}) : {a['description']}" for a in anomalies]) if anomalies else "Aucune anomalie majeure"}

    ---
    *Rapport généré par SMD Global Consulting LLC - Superviseur IA Comptable*
    """
                        try:
                            generer_bouton_word("Rapport_Audit_FEC", rapport_complet)
                        except Exception as e:
                            st.error(f"Erreur export : {e}")


    # -----------------------------------------------------------------------------
    # 5. LOI DE BENFORD - VERSION PROFESSIONNELLE CABINET D'AUDIT
    # -----------------------------------------------------------------------------

