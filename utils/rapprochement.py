# -*- coding: utf-8 -*-
"""Module Rapprochement Bancaire - SMD Global Consulting LLC"""
from utils.sig_pcg import nb_fr
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
from datetime import datetime, timedelta
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def normaliser_montant(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace(',', '.').str.replace(' ', '').str.replace('€', ''),
        errors='coerce'
    ).fillna(0)


def normaliser_date(serie):
    return pd.to_datetime(serie, errors='coerce', dayfirst=True)


def calculer_similarite_libelle(lib1, lib2):
    if pd.isna(lib1) or pd.isna(lib2):
        return 0
    lib1 = str(lib1).lower().strip()
    lib2 = str(lib2).lower().strip()
    if lib1 == lib2:
        return 1.0
    mots1 = set(lib1.split())
    mots2 = set(lib2.split())
    if not mots1 or not mots2:
        return 0
    intersection = mots1 & mots2
    union = mots1 | mots2
    return len(intersection) / len(union) if union else 0


def rapprocher_bancaire(df_releve, df_ecritures, tolerance_jours=3):
    """Effectue un rapprochement bancaire intelligent"""
    df_r = df_releve.copy()
    df_e = df_ecritures.copy()
    
    cols_releve = {col.lower(): col for col in df_r.columns}
    col_date_r = None
    col_lib_r = None
    col_montant_r = None
    col_debit_r = None
    col_credit_r = None
    
    for k in cols_releve:
        if 'date' in k:
            col_date_r = cols_releve[k]
        elif any(x in k for x in ['libelle', 'libellé', 'description', 'operation']):
            col_lib_r = cols_releve[k]
        elif 'montant' in k:
            col_montant_r = cols_releve[k]
        elif 'debit' in k or 'débit' in k:
            col_debit_r = cols_releve[k]
        elif 'credit' in k or 'crédit' in k:
            col_credit_r = cols_releve[k]
    
    cols_ecr = {col.lower(): col for col in df_e.columns}
    col_date_e = None
    col_lib_e = None
    col_debit_e = None
    col_credit_e = None
    col_montant_e = None
    
    for k in cols_ecr:
        if 'date' in k:
            col_date_e = cols_ecr[k]
        elif any(x in k for x in ['libelle', 'libellé', 'description', 'lib']):
            col_lib_e = cols_ecr[k]
        elif 'montant' in k:
            col_montant_e = cols_ecr[k]
        elif 'debit' in k or 'débit' in k:
            col_debit_e = cols_ecr[k]
        elif 'credit' in k or 'crédit' in k:
            col_credit_e = cols_ecr[k]
    
    if col_date_r:
        df_r['_date'] = normaliser_date(df_r[col_date_r])
    if col_lib_r:
        df_r['_libelle'] = df_r[col_lib_r].astype(str)
    
    if col_montant_r:
        df_r['_montant'] = normaliser_montant(df_r[col_montant_r])
    elif col_debit_r and col_credit_r:
        df_r['_debit'] = normaliser_montant(df_r[col_debit_r])
        df_r['_credit'] = normaliser_montant(df_r[col_credit_r])
        df_r['_montant'] = df_r['_credit'] - df_r['_debit']
    else:
        df_r['_montant'] = 0
    
    if col_date_e:
        df_e['_date'] = normaliser_date(df_e[col_date_e])
    if col_lib_e:
        df_e['_libelle'] = df_e[col_lib_e].astype(str)
    
    if col_debit_e:
        df_e['_debit'] = normaliser_montant(df_e[col_debit_e])
    else:
        df_e['_debit'] = 0
    
    if col_credit_e:
        df_e['_credit'] = normaliser_montant(df_e[col_credit_e])
    else:
        df_e['_credit'] = 0
    
    df_e['_montant'] = df_e['_debit'] - df_e['_credit']
    if col_montant_e and not (col_debit_e or col_credit_e):   # une seule colonne « Montant » signée
        df_e['_montant'] = normaliser_montant(df_e[col_montant_e])
    
    rapproches = []
    non_rapproches_releve = []
    df_e['_utilise'] = False
    
    for idx_r, row_r in df_r.iterrows():
        montant_r = row_r['_montant']
        date_r = row_r.get('_date')
        lib_r = row_r.get('_libelle', '')
        
        if abs(montant_r) < 0.01:
            continue
        
        meilleur_match = None
        meilleur_score = 0
        
        for idx_e, row_e in df_e[~df_e['_utilise']].iterrows():
            montant_e = row_e['_montant']
            
            if abs(abs(montant_r) - abs(montant_e)) > 0.01:
                continue
            
            score = 0.6
            
            if date_r is not None and pd.notna(date_r) and pd.notna(row_e.get('_date')):
                ecart_jours = abs((date_r - row_e['_date']).days)
                if ecart_jours <= tolerance_jours:
                    score += 0.3 * (1 - ecart_jours/tolerance_jours) if tolerance_jours > 0 else 0.3
            
            if lib_r and row_e.get('_libelle'):
                sim = calculer_similarite_libelle(lib_r, row_e['_libelle'])
                score += 0.1 * sim
            
            if score > meilleur_score:
                meilleur_score = score
                meilleur_match = idx_e
        
        if meilleur_match is not None and meilleur_score >= 0.6:
            df_e.at[meilleur_match, '_utilise'] = True
            rapproches.append({
                'Date relevé': row_r.get('_date'),
                'Libellé relevé': str(lib_r)[:50] if lib_r else '',
                'Montant': montant_r,
                'Date écriture': df_e.at[meilleur_match, '_date'],
                'Score': f"{nb_fr(meilleur_score*100, 0)} %"
            })
        else:
            non_rapproches_releve.append({
                'Date': row_r.get('_date'),
                'Libellé': str(lib_r)[:50] if lib_r else '',
                'Montant': montant_r
            })
    
    non_rapproches_ecritures = []
    for idx_e, row_e in df_e[~df_e['_utilise']].iterrows():
        montant_e = row_e['_montant']
        if abs(montant_e) < 0.01:
            continue
        non_rapproches_ecritures.append({
            'Date': row_e.get('_date'),
            'Libellé': str(row_e.get('_libelle', ''))[:50],
            'Montant': montant_e
        })
    
    return {
        'nb_total_releve': len(df_r),
        'nb_total_ecritures': len(df_e),
        'nb_rapproches': len(rapproches),
        'nb_non_rapproches_releve': len(non_rapproches_releve),
        'nb_non_rapproches_ecritures': len(non_rapproches_ecritures),
        'taux_rapprochement': (len(rapproches) / len(df_r) * 100) if len(df_r) > 0 else 0,
        'rapproches': pd.DataFrame(rapproches) if rapproches else pd.DataFrame(),
        'non_rapproches_releve': pd.DataFrame(non_rapproches_releve) if non_rapproches_releve else pd.DataFrame(),
        'non_rapproches_ecritures': pd.DataFrame(non_rapproches_ecritures) if non_rapproches_ecritures else pd.DataFrame()
    }


def _tableau_operations(df, titre, explication, maxi=200):
    """Liste des opérations (Date · Libellé · Montant) au format Markdown, avec total."""
    if df is None or getattr(df, "empty", True):
        return []
    lignes = ["---", "", f"## {titre}", "", f"*{explication}*", "",
              "| Date | Libellé | Montant (€) |", "|------|---------|------------:|"]
    for _, r in df.head(maxi).iterrows():
        d = r.get('Date')
        d = d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') and pd.notna(d) else (str(d) if pd.notna(d) else "")
        lib = str(r.get('Libellé', '')).replace("|", "/")
        lignes.append(f"| {d} | {lib} | {nb_fr(r.get('Montant', 0), 2)} |")
    lignes.append(f"| **Total ({nb_fr(len(df), 0)} opération{'s' if len(df) > 1 else ''})** |  | "
                  f"**{nb_fr(df['Montant'].sum(), 2)}** |")
    if len(df) > maxi:
        lignes.append(f"\n*Seules les {maxi} premières opérations sont listées.*")
    lignes.append("")
    return lignes


def visuels_rapprochement(resultats):
    """Indicateurs pour l'export Word (mêmes chiffres qu'à l'écran)."""
    taux = resultats['taux_rapprochement']
    verdict = "excellent" if taux >= 90 else "bon" if taux >= 70 else "moyen" if taux >= 50 else "faible"
    return [{"libelle": "Opérations du relevé", "valeur": nb_fr(resultats['nb_total_releve'])},
            {"libelle": "Écritures comptables", "valeur": nb_fr(resultats['nb_total_ecritures'])},
            {"libelle": "Rapprochées", "valeur": nb_fr(resultats['nb_rapproches'])},
            {"libelle": "Taux de rapprochement", "valeur": f"{nb_fr(taux, 1)} %", "detail": verdict,
             "ton": "bon" if taux >= 90 else "neutre" if taux >= 70 else "mauvais"},
            {"libelle": "Relevé non rapproché", "valeur": nb_fr(resultats['nb_non_rapproches_releve']),
             "ton": "mauvais" if resultats['nb_non_rapproches_releve'] else "bon",
             "detail": f"{nb_fr(resultats['non_rapproches_releve']['Montant'].sum(), 2)} €"
             if resultats['nb_non_rapproches_releve'] else "aucune"},
            {"libelle": "Écritures non rapprochées", "valeur": nb_fr(resultats['nb_non_rapproches_ecritures']),
             "ton": "mauvais" if resultats['nb_non_rapproches_ecritures'] else "bon",
             "detail": f"{nb_fr(resultats['non_rapproches_ecritures']['Montant'].sum(), 2)} €"
             if resultats['nb_non_rapproches_ecritures'] else "aucune"}], []


def generer_rapport_rapprochement(resultats, nom_compte="Compte bancaire"):
    """Génère un rapport professionnel"""
    rapport = []
    rapport.append(f"# RAPPORT DE RAPPROCHEMENT BANCAIRE")
    rapport.append(f"## {nom_compte}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## SYNTHÈSE")
    rapport.append("")
    rapport.append(f"- Opérations relevé : {nb_fr(resultats['nb_total_releve'], 0)}")
    rapport.append(f"- Écritures comptables : {nb_fr(resultats['nb_total_ecritures'], 0)}")
    rapport.append(f"- Rapprochées : {nb_fr(resultats['nb_rapproches'], 0)}")
    rapport.append(f"- Non rapprochées (relevé) : {nb_fr(resultats['nb_non_rapproches_releve'], 0)}")
    rapport.append(f"- Non rapprochées (écritures) : {nb_fr(resultats['nb_non_rapproches_ecritures'], 0)}")
    rapport.append(f"- Taux de rapprochement : {nb_fr(resultats['taux_rapprochement'], 1)} %")
    rapport.append("")
    
    if resultats['taux_rapprochement'] >= 90:
        rapport.append("**Excellent** : Rapprochement quasi-complet")
    elif resultats['taux_rapprochement'] >= 70:
        rapport.append("**Bon** : Rapprochement satisfaisant")
    else:
        rapport.append("**À vérifier** : investigations nécessaires")
    
    rapport.append("")
    for titre, cle, explication in (
            ("OPÉRATIONS BANCAIRES NON RAPPROCHÉES", 'non_rapproches_releve',
             "Opérations du relevé sans écriture comptable correspondante."),
            ("ÉCRITURES COMPTABLES NON RAPPROCHÉES", 'non_rapproches_ecritures',
             "Écritures du compte 512 sans opération correspondante sur le relevé.")):
        rapport += _tableau_operations(resultats.get(cle), titre, explication)
    rapport.append("---")
    rapport.append("*SMD Global Consulting LLC - Superviseur IA Comptable*")
    
    return "\n".join(rapport)



def page_rapprochement():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("🔄 Rapprochement Bancaire")
    st.markdown("**Matching intelligent** entre relevé bancaire et écritures comptables")
    st.caption("✨ Matching automatique par montant + date + libellé")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📥 Relevé Bancaire")
        releve = st.file_uploader(
            "Fichier relevé (CSV, XLSX)",
            type=TYPES_TABLEUR_CSV,
            key="releve",
            help="Colonnes attendues : Date, Libellé, Montant"
        )

    with col2:
        st.markdown("### 📚 Écritures Comptables")
        ecritures = st.file_uploader(
            "Fichier écritures (CSV, XLSX)",
            type=TYPES_TABLEUR_CSV,
            key="ecritures",
            help="Colonnes attendues : Date, Libellé, Débit, Crédit"
        )

    if releve and ecritures:
        from utils.rapprochement import rapprocher_bancaire, generer_rapport_rapprochement

        try:
            df_releve = pd.read_excel(releve) if est_tableur(releve.name) else pd.read_csv(releve, sep=None, engine='python')
            df_ecritures = pd.read_excel(ecritures) if est_tableur(ecritures.name) else pd.read_csv(ecritures, sep=None, engine='python')

            st.success(f"✅ Relevé : **{len(df_releve)} opérations** | Écritures : **{len(df_ecritures)} lignes**")

            with st.expander("👀 Aperçu des fichiers"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Relevé bancaire**")
                    st.dataframe(df_releve.head(5), width="stretch")
                with col2:
                    st.markdown("**Écritures comptables**")
                    st.dataframe(df_ecritures.head(5), width="stretch")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                nom_compte = st.text_input("🏦 Nom du compte", value="Compte bancaire principal")
            with col2:
                tolerance = st.slider("⏱ Tolérance jours", 0, 10, 3,
                                     help="Écart maximum entre date relevé et écriture")

            if st.button("🔄 Lancer le rapprochement", type="primary", width="stretch"):
                with st.spinner("Matching intelligent en cours..."):
                    resultats = rapprocher_bancaire(df_releve, df_ecritures, tolerance_jours=tolerance)

                    st.markdown("## 📊 Résultats du Rapprochement")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("✅ Rapprochés", resultats['nb_rapproches'])
                    with col2:
                        st.metric("❌ Non rapp. relevé", resultats['nb_non_rapproches_releve'])
                    with col3:
                        st.metric("❌ Non rapp. écritures", resultats['nb_non_rapproches_ecritures'])
                    with col4:
                        taux = resultats['taux_rapprochement']
                        st.metric("📈 Taux", f"{nb_fr(taux, 1)} %",
                                 delta="Excellent" if taux >= 90 else "Bon" if taux >= 70 else "À vérifier",
                                 delta_color="normal" if taux >= 70 else "inverse")

                    st.progress(min(int(taux), 100))

                    if taux >= 90:
                        st.success("✅ **Excellent rapprochement** - Quasi-complet")
                    elif taux >= 70:
                        st.info("ℹ **Bon rapprochement** - Satisfaisant")
                    elif taux >= 50:
                        st.warning("⚠ **Rapprochement moyen** - Investigations nécessaires")
                    else:
                        st.error("🚨 **Rapprochement faible** - Anomalies importantes")

                    st.divider()

                    if not resultats['rapproches'].empty:
                        with st.expander(f"✅ Opérations rapprochées ({resultats['nb_rapproches']})"):
                            st.dataframe(resultats['rapproches'], width="stretch", hide_index=True)

                    if not resultats['non_rapproches_releve'].empty:
                        with st.expander(f"❌ Relevé non rapproché ({resultats['nb_non_rapproches_releve']})", expanded=True):
                            st.warning("Opérations bancaires sans contrepartie comptable")
                            st.dataframe(resultats['non_rapproches_releve'], width="stretch", hide_index=True)

                    if not resultats['non_rapproches_ecritures'].empty:
                        with st.expander(f"❌ Écritures non rapprochées ({resultats['nb_non_rapproches_ecritures']})", expanded=True):
                            st.warning("Écritures sans contrepartie bancaire")
                            st.dataframe(resultats['non_rapproches_ecritures'], width="stretch", hide_index=True)

                    st.divider()

                    rapport = generer_rapport_rapprochement(resultats, nom_compte)

                    col1, col2 = st.columns(2)
                    with col1:
                        bouton_sauvegarde(type_analyse="Rapprochement Bancaire", resultat=rapport, libelle="💾 Sauvegarder")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_rapprochement(resultats)
                            generer_bouton_word(f"Rapprochement_{nom_compte}", rapport, indicateurs=ind_w,
                                                graphiques=graph_w, sans_sections=("SYNTHÈSE",))
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
    # -----------------------------------------------------------------------------
    # IMMOBILISATIONS - AMORTISSEMENTS & CESSIONS
    # -----------------------------------------------------------------------------

