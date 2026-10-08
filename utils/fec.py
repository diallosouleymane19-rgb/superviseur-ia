# -*- coding: utf-8 -*-
"""
Module Traitement FEC Professionnel - SMD Global Consulting LLC
Conforme aux exigences DGFiP (Article L.47 A du LPF)
"""
from utils.sig_pcg import nb_fr
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def _eur(x):
    """Montant au format français : 198 970,40 €"""
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " €"


# Colonnes obligatoires du FEC (Article A.47 A-1 du LPF)
COLONNES_FEC_OBLIGATOIRES = [
    'JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate',
    'CompteNum', 'CompteLib', 'CompAuxNum', 'CompAuxLib',
    'PieceRef', 'PieceDate', 'EcritureLib', 'Debit', 'Credit',
    'EcritureLet', 'DateLet', 'ValidDate', 'Montantdevise', 'Idevise'
]


def lire_fec(fichier):
    """
    Lit un fichier FEC en testant différents séparateurs et encodages
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


def colonnes_trouvees(fichier):
    """Nombre de colonnes de la première ligne (meilleur séparateur parmi | tabulation ;)."""
    try:
        fichier.seek(0)
        brut = fichier.read()
        texte = brut.decode("utf-8", errors="replace") if isinstance(brut, bytes) else str(brut)
        entete = next((l for l in texte.splitlines() if l.strip()), "")
        return max(entete.count(sep) for sep in ("|", "\t", ";")) + 1 if entete else 0
    except Exception:
        return 0


def valider_fec(df):
    """
    Validation complète du FEC selon normes DGFiP
    
    Returns:
        dict: Résultats détaillés de validation avec score de conformité
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
            "message": "Toutes les colonnes obligatoires sont présentes"
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
            resultats['Dates écritures'] = {
                "valide": True,
                "message": "100% des écritures sont datées"
            }
            points += 15
        else:
            resultats['Dates écritures'] = {
                "valide": False,
                "message": f"{nb_dates_manquantes} écritures sans date"
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
                    "message": f"Format conforme ({nb_fr(taux_valide, 0)} % valide)"
                }
                points += 10
            else:
                resultats['Format dates (AAAAMMJJ)'] = {
                    "valide": False,
                    "message": f"Format non conforme ({nb_fr(taux_valide, 0)} % valide)"
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
                resultats['Équilibre Débit/Crédit'] = {
                    "valide": True,
                    "message": f"Équilibre parfait : {_eur(total_debit)}"
                }
                points += 25
            else:
                resultats['Équilibre Débit/Crédit'] = {
                    "valide": False,
                    "message": f"Écart de {_eur(ecart)} détecté"
                }
        except Exception as e:
            resultats['Équilibre Débit/Crédit'] = {
                "valide": False,
                "message": f"Impossible de calculer : {e}"
            }
    
    # 5. VERIFICATION NUMEROS DE COMPTES
    points_max += 15
    if 'CompteNum' in df.columns:
        comptes_uniques = df['CompteNum'].nunique()
        comptes_vides = df['CompteNum'].isna().sum()
        if comptes_vides == 0:
            resultats['Numéros de comptes'] = {
                "valide": True,
                "message": f"{comptes_uniques} comptes utilisés, 100 % renseignés"
            }
            points += 15
        else:
            resultats['Numéros de comptes'] = {
                "valide": False,
                "message": f"{comptes_vides} écritures sans compte"
            }
    
    # 6. VERIFICATION JOURNAUX
    points_max += 15
    if 'JournalCode' in df.columns:
        journaux = df['JournalCode'].nunique()
        if journaux > 0:
            resultats['Journaux comptables'] = {
                "valide": True,
                "message": f"{journaux} journaux distincts identifiés"
            }
            points += 15
        else:
            resultats['Journaux comptables'] = {
                "valide": False,
                "message": "Aucun journal identifié"
            }
    
    # SCORE DE CONFORMITE
    score_conformite = (points / points_max * 100) if points_max > 0 else 0
    
    resultats['_meta'] = {
        'score_conformite': round(score_conformite, 1),
        'points': points,
        'points_max': points_max,
        'niveau': 'Excellent' if score_conformite >= 90 else 'Bon' if score_conformite >= 75 else 'À améliorer' if score_conformite >= 50 else 'Non conforme'
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
    rapport.append("### 1. STATISTIQUES GÉNÉRALES")
    rapport.append(f"- **Nombre total d'écritures** : {nb_fr(len(df), 0)}")
    rapport.append(f"- **Nombre de colonnes** : {len(df.columns)}")
    
    if 'EcritureNum' in df.columns:
        nb_pieces = df['EcritureNum'].nunique()
        rapport.append(f"- **Nombre de pièces comptables** : {nb_fr(nb_pieces, 0)}")
    
    if 'CompteNum' in df.columns:
        nb_comptes = df['CompteNum'].nunique()
        rapport.append(f"- **Nombre de comptes utilisés** : {nb_comptes}")
    
    if 'JournalCode' in df.columns:
        nb_journaux = df['JournalCode'].nunique()
        rapport.append(f"- **Nombre de journaux** : {nb_journaux}")
    
    # 2. ANALYSE FINANCIERE
    rapport.append("\n### 2. ANALYSE FINANCIÈRE")
    if 'Debit' in df.columns and 'Credit' in df.columns:
        try:
            df_calc = df.copy()
            df_calc['Debit_num'] = pd.to_numeric(df_calc['Debit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_calc['Credit_num'] = pd.to_numeric(df_calc['Credit'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            total_debit = df_calc['Debit_num'].sum()
            total_credit = df_calc['Credit_num'].sum()
            volume_total = total_debit + total_credit
            
            rapport.append(f"- **Total Débit** : {_eur(total_debit)}")
            rapport.append(f"- **Total Crédit** : {_eur(total_credit)}")
            rapport.append(f"- **Volume total** : {_eur(volume_total)}")
            rapport.append(f"- **Écart D/C** : {_eur(abs(total_debit - total_credit))}")
            rapport.append(f"- **Montant moyen écriture** : {_eur(volume_total / len(df))}")
        except Exception as e:
            rapport.append(f"*Erreur calcul : {e}*")
    
    # 3. ANALYSE PAR JOURNAL
    if 'JournalCode' in df.columns:
        rapport.append("\n### 3. RÉPARTITION PAR JOURNAL")
        repartition = df['JournalCode'].value_counts().head(10)
        for journal, count in repartition.items():
            pct = (count / len(df)) * 100
            rapport.append(f"- **{journal}** : {nb_fr(count, 0)} écritures ({nb_fr(pct, 1)} %)")
    
    # 4. ANALYSE PERIODE
    if 'EcritureDate' in df.columns:
        rapport.append("\n### 4. PÉRIODE COMPTABLE")
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce').dropna()
            if len(dates) > 0:
                rapport.append(f"- **Date début** : {dates.min().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Date fin** : {dates.max().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Durée** : {(dates.max() - dates.min()).days} jours")
        except Exception:
            rapport.append("*Format de dates non standard*")
    
    # 5. CONCLUSION
    rapport.append("\n### 5. SYNTHÈSE")
    rapport.append("Le FEC analysé contient les données comptables de l'exercice.")
    rapport.append("Les contrôles automatiques portent sur la conformité formelle (article A.47 A-1 du LPF).")
    rapport.append("\n**Recommandation** : Croiser cette analyse avec les modules Contrôle de balance et Loi de Benford pour une expertise complète.")
    
    return "\n".join(rapport)


def detecter_anomalies_fec(df):
    """
    Détection d'anomalies dans le FEC
    """
    anomalies = []
    
    # Ecritures sans libelle
    if 'EcritureLib' in df.columns:
        sans_libelle = df['EcritureLib'].isna().sum()
        if sans_libelle > 0:
            anomalies.append({
                'type': 'Libellé manquant',
                'gravite': 'Moyenne',
                'count': int(sans_libelle),
                'description': f"{sans_libelle} écritures sans libellé"
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
                    'type': 'Écritures montants nuls',
                    'gravite': 'Faible',
                    'count': int(ecritures_nulles),
                    'description': f"{ecritures_nulles} écritures avec Débit=0 et Crédit=0"
                })
        except:
            pass
    
    # Doublons exacts
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        anomalies.append({
            'type': 'Doublons exacts',
            'gravite': 'Élevée',
            'count': int(duplicates),
            'description': f"{duplicates} lignes en doublons exacts détectées"
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
    st.title("📂 Traitement FEC – Contrôle de conformité DGFiP")
    st.markdown("**Validation et analyse approfondie** des Fichiers des Écritures Comptables (Article L.47 A du LPF)")

    uploaded_file = st.file_uploader(
        "📎 Déposer votre fichier FEC", 
        type=["txt", "csv"],
        help="Format pipe (|) ou tabulation, encodage UTF-8 ou ISO-8859-1"
    )

    if uploaded_file:
        from utils.fec import lire_fec, valider_fec, analyser_fec, detecter_anomalies_fec, colonnes_trouvees

        with st.spinner("📖 Lecture du FEC..."):
            df, sep, enc = lire_fec(uploaded_file)

        if df is None:
            n = colonnes_trouvees(uploaded_file)
            st.error(f"❌ Ce fichier n'est pas un FEC : {n} colonne{'s' if n > 1 else ''} trouvée{'s' if n > 1 else ''}, "
                     "18 attendues (JournalCode, EcritureDate, CompteNum…), séparées par | ou une tabulation.")
            st.info("Pour une facture, utilisez la page **Analyse et comptabilisation de factures**, "
                    "puis exportez les écritures au format FEC.")
        else:
            st.success(f"✅ FEC chargé : **{nb_fr(len(df), 0)} écritures** | Séparateur : `{sep}` | Encodage : `{enc}`")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📝 Écritures", f"{nb_fr(len(df), 0)}")
            with col2:
                if 'EcritureNum' in df.columns:
                    st.metric("📄 Pièces", f"{nb_fr(df['EcritureNum'].nunique(), 0)}")
            with col3:
                if 'CompteNum' in df.columns:
                    st.metric("🔢 Comptes", f"{df['CompteNum'].nunique()}")
            with col4:
                if 'JournalCode' in df.columns:
                    st.metric("📚 Journaux", f"{df['JournalCode'].nunique()}")

            with st.expander("👀 Aperçu des données (20 premières lignes)"):
                st.dataframe(df.head(20), width="stretch")

            st.divider()

            if st.button("🛡 Lancer la validation DGFiP complète", type="primary", width="stretch"):
                with st.spinner("Validation en cours selon Article A.47 A-1 du LPF..."):
                    resultats = valider_fec(df)

                    meta = resultats.pop('_meta', {})
                    score = meta.get('score_conformite', 0)
                    niveau = meta.get('niveau', 'Inconnu')

                    st.markdown("## 🎯 Score de Conformité DGFiP")

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
                        nb_elevees = len([a for a in anomalies if a['gravite'] == 'Élevée'])
                        nb_moyennes = len([a for a in anomalies if a['gravite'] == 'Moyenne'])
                        nb_faibles = len([a for a in anomalies if a['gravite'] == 'Faible'])

                        with col1:
                            st.metric("🔴 Élevées", nb_elevees)
                        with col2:
                            st.metric("🟡 Moyennes", nb_moyennes)
                        with col3:
                            st.metric("🔵 Faibles", nb_faibles)

                        for anomalie in anomalies:
                            if anomalie['gravite'] == 'Élevée':
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
                        bouton_sauvegarde(type_analyse="Contrôle FEC", resultat=f"Score : {nb_fr(score, 1)} % – {analyse}", libelle="💾 Sauvegarder le rapport")
                    with col2:
                        rapport_complet = f"""# RAPPORT DE CONTRÔLE FEC

    ## Score de Conformité DGFiP : {nb_fr(score, 1)} % ({niveau})

    {analyse}

    ## Anomalies Détectées
    {chr(10).join([f"- {a['type']} ({a['gravite']}) : {a['description']}" for a in anomalies]) if anomalies else "Aucune anomalie majeure"}

    ---
    *Rapport généré par SMD Global Consulting LLC - Superviseur IA Comptable*
    """
                        try:
                            generer_bouton_word("Rapport_Controle_FEC", rapport_complet)
                        except Exception as e:
                            st.error(f"Erreur export : {e}")


    # -----------------------------------------------------------------------------
    # 5. LOI DE BENFORD - VERSION PROFESSIONNELLE
    # -----------------------------------------------------------------------------

