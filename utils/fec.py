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


def normaliser_debit_credit(df):
    """Le FEC peut présenter les montants en Debit / Credit ou en Montant + Sens (D/C ou +1/-1)
    (article A.47 A-1 du LPF). Retourne une copie avec des colonnes Debit et Credit."""
    if df is None or ("Debit" in df.columns and "Credit" in df.columns) \
            or not {"Montant", "Sens"} <= set(df.columns):
        return df
    d = df.copy()
    sens = d["Sens"].astype(str).str.strip().str.upper()
    debit = sens.isin(["D", "+1", "1"])
    d["Debit"] = d["Montant"].where(debit, "0")
    d["Credit"] = d["Montant"].where(~debit, "0")
    d.attrs["format_montant_sens"] = True
    return d


def _num(serie):
    from utils.intelligent_parser import montants
    return montants(serie).fillna(0)


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
                    return normaliser_debit_credit(df), sep, enc
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


# Champs à renseigner sur chaque ligne (les autres peuvent être vides : auxiliaire, lettrage, devise)
CHAMPS_OBLIGATOIRES = ['JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate', 'CompteNum', 'CompteLib',
                       'PieceRef', 'PieceDate', 'EcritureLib', 'ValidDate']


def _vide(serie):
    return serie.isna() | serie.astype(str).str.strip().isin(["", "nan", "None"])


def _dates(serie):
    return pd.to_datetime(serie.astype(str).str.strip(), format='%Y%m%d', errors='coerce')


def controle_nom_fichier(nom):
    """Nom réglementaire : SirenFECAAAAMMJJ (SIREN, « FEC », date de clôture), extension .txt ou .xml.
    Retourne (valide, message, date_cloture ou None)."""
    import re
    from utils.compta_facture import siren_valide
    base = str(nom or "").rsplit("/", 1)[-1]
    m = re.fullmatch(r"(\d{9})FEC(\d{8})\.(txt|xml)", base, re.I)
    if not m:
        return False, f"« {base} » ne suit pas la forme SirenFECAAAAMMJJ.txt (ex. 123456789FEC20251231.txt)", None
    cloture = pd.to_datetime(m.group(2), format="%Y%m%d", errors="coerce")
    if pd.isna(cloture):
        return False, f"Date de clôture {m.group(2)} invalide dans le nom du fichier", None
    if not siren_valide(m.group(1)):
        return False, f"SIREN {m.group(1)} du nom de fichier invalide (clé de contrôle)", cloture
    return True, f"Nom conforme (SIREN {m.group(1)}, clôture {cloture.strftime('%d/%m/%Y')})", cloture


def valider_fec(df, sep=None, nom_fichier=None):
    """
    Contrôles de conformité du FEC (article A.47 A-1 du LPF), sur le modèle du test de l'administration :
    structure, séparateur et nom du fichier, champs obligatoires, dates, équilibre global et par écriture,
    cohérence de chaque écriture, montants, lettrage.
    Returns: dict des contrôles (valide, message) + '_meta' (score, niveau).
    """
    resultats = {}
    pts = {"points": 0, "max": 0}
    format_sens = {"Montant", "Sens"} <= set(df.columns)
    df = normaliser_debit_credit(df)

    def ctrl(nom, poids, valide, message):
        pts["max"] += poids
        pts["points"] += poids if valide else 0
        resultats[nom] = {"valide": bool(valide), "message": message}

    # 1. Structure : 18 colonnes (Montant + Sens peuvent remplacer Debit + Credit)
    presentes = set(df.columns) | ({"Debit", "Credit"} if format_sens else set())
    manquantes = [c for c in COLONNES_FEC_OBLIGATOIRES if c not in presentes]
    ctrl('Structure (18 colonnes)', 15, not manquantes,
         "Toutes les colonnes obligatoires sont présentes" if not manquantes
         else f"Colonnes manquantes : {', '.join(manquantes)}")

    # 2. Séparateur et nom du fichier
    if sep is not None:
        ok_sep = sep in ("|", "\t")
        ctrl('Séparateur', 5, ok_sep, "Barre verticale ou tabulation : conforme" if ok_sep
             else f"Séparateur « {sep} » non admis : seuls la tabulation et la barre verticale | le sont")
    cloture = None
    if nom_fichier:
        ok_nom, msg_nom, cloture = controle_nom_fichier(nom_fichier)
        ctrl('Nom du fichier', 5, ok_nom, msg_nom)

    # 3. Champs obligatoires renseignés sur chaque ligne
    vides = {c: int(_vide(df[c]).sum()) for c in CHAMPS_OBLIGATOIRES if c in df.columns}
    vides = {c: n for c, n in vides.items() if n}
    ctrl('Champs obligatoires renseignés', 15, not vides,
         "Journal, n° et date d'écriture, compte, pièce, libellé et date de validation renseignés partout"
         if not vides else "Champs vides : " + ", ".join(f"{c} ({nb_fr(n, 0)} ligne{'s' if n > 1 else ''})"
                                                          for c, n in vides.items()))

    # 4. Dates au format AAAAMMJJ (écriture, pièce, validation) et dans l'exercice
    pb = []
    for c in ('EcritureDate', 'PieceDate', 'ValidDate'):
        if c in df.columns:
            remplies = ~_vide(df[c])
            invalides = int((_dates(df[c]).isna() & remplies).sum())
            if invalides:
                pb.append(f"{c} : {nb_fr(invalides, 0)} date(s) hors format AAAAMMJJ")
    if cloture is not None and 'EcritureDate' in df.columns:
        apres = int((_dates(df['EcritureDate']) > cloture).sum())
        if apres:
            pb.append(f"{nb_fr(apres, 0)} écriture(s) datée(s) après la clôture du {cloture.strftime('%d/%m/%Y')}")
    if 'EcritureDate' in df.columns:
        ctrl('Dates (format AAAAMMJJ)', 10, not pb, "Dates d'écriture, de pièce et de validation conformes"
             if not pb else " ; ".join(pb))

    # 5. Équilibre global et par écriture (JournalCode + EcritureNum)
    if 'Debit' in df.columns and 'Credit' in df.columns:
        d_num, c_num = _num(df['Debit']), _num(df['Credit'])
        total_debit, total_credit = d_num.sum(), c_num.sum()
        ecart = abs(total_debit - total_credit)
        cles = [c for c in ('JournalCode', 'EcritureNum') if c in df.columns]
        desequilibrees = 0
        if 'EcritureNum' in cles:
            soldes = (d_num - c_num).groupby([df[c].astype(str) for c in cles]).sum().round(2)
            desequilibrees = int((soldes.abs() >= 0.01).sum())
        msg = []
        if ecart >= 0.01:
            msg.append(f"Écart total de {_eur(ecart)}")
        if desequilibrees:
            msg.append(f"{desequilibrees} écriture(s) non équilibrée(s) (débit ≠ crédit par numéro d'écriture)")
        ctrl('Équilibre Débit/Crédit', 25, not msg,
             f"Équilibre parfait : {_eur(total_debit)}" + (", chaque écriture est équilibrée" if 'EcritureNum' in cles else "")
             if not msg else " ; ".join(msg))

        # 6. Montants : positifs, et une seule colonne remplie par ligne
        negatifs = int(((d_num < 0) | (c_num < 0)).sum())
        double = int(((d_num != 0) & (c_num != 0)).sum())
        nuls = int(((d_num == 0) & (c_num == 0)).sum())
        pb = ([f"{nb_fr(negatifs, 0)} montant(s) négatif(s)"] if negatifs else []) + \
             ([f"{nb_fr(double, 0)} ligne(s) avec débit ET crédit"] if double else []) + \
             ([f"{nb_fr(nuls, 0)} ligne(s) à zéro"] if nuls else [])
        ctrl('Montants', 10, not pb, "Montants positifs, un seul sens par ligne" if not pb else " ; ".join(pb))

    # 7. Cohérence de chaque écriture : une seule date et un seul journal par numéro d'écriture
    if {'EcritureNum', 'EcritureDate'} <= set(df.columns):
        cle = df['JournalCode'].astype(str) + "|" + df['EcritureNum'].astype(str) if 'JournalCode' in df.columns \
            else df['EcritureNum'].astype(str)
        multi_dates = int((df.groupby(cle)['EcritureDate'].nunique() > 1).sum())
        ctrl('Cohérence des écritures', 10, not multi_dates,
             "Chaque écriture a une date unique" if not multi_dates
             else f"{nb_fr(multi_dates, 0)} écriture(s) avec plusieurs dates pour le même numéro")

    # 8. Lettrage : une date de lettrage pour chaque code de lettrage
    if {'EcritureLet', 'DateLet'} <= set(df.columns):
        sans_date = int((~_vide(df['EcritureLet']) & _vide(df['DateLet'])).sum())
        ctrl('Lettrage', 5, not sans_date, "Codes de lettrage accompagnés de leur date" if not sans_date
             else f"{nb_fr(sans_date, 0)} ligne(s) lettrée(s) sans date de lettrage")

    score_conformite = (pts["points"] / pts["max"] * 100) if pts["max"] > 0 else 0
    eq = resultats.get('Équilibre Débit/Crédit', {}).get('valide', True)
    niveau = ('Excellent' if score_conformite >= 90 else 'Bon' if score_conformite >= 75
              else 'À améliorer' if score_conformite >= 50 else 'Non conforme')
    if not eq or manquantes:
        niveau = 'Non conforme'    # FEC déséquilibré ou incomplet : rejeté par l'administration
    resultats['_meta'] = {'score_conformite': round(score_conformite, 1), 'points': pts["points"],
                          'points_max': pts["max"], 'niveau': niveau}
    return resultats


def rapport_controle_fec(score, niveau, resultats, analyse, anomalies):
    """Rapport complet du contrôle FEC (Markdown) : score, contrôles DGFiP, analyse, anomalies."""
    lignes_analyse = str(analyse).split("\n")
    date = next((l for l in lignes_analyse if l.startswith("*Date d'analyse")), "")
    corps = [l for l in lignes_analyse if l != date and not l.startswith("## RAPPORT D'ANALYSE FEC")]
    r = ["# RAPPORT DE CONTRÔLE FEC",
         f"## Score de conformité DGFiP : {nb_fr(score, 1)} % ({niveau})",
         date, "",
         "## Détail des contrôles DGFiP", ""]
    r += [f"- {'✅' if v_['valide'] else '❌'} **{k}** : {v_.get('message', '')}" for k, v_ in resultats.items()]
    r += ["", "## Analyse du fichier", ""]
    r += corps
    r += ["", "## Anomalies détectées", ""]
    r += ([f"- {a['type']} ({a['gravite']}) : {a['description']}" for a in anomalies] or ["Aucune anomalie majeure"])
    r += ["", "---", "*Rapport généré par SMD Global Consulting LLC - KontrolIA*"]
    return "\n".join(r)


def visuels_fec(df, score, niveau, anomalies):
    """Indicateurs et graphiques pour l'export Word du contrôle FEC (mêmes chiffres qu'à l'écran)."""
    import pandas as pd
    from utils.word_visuels import barres_simples
    ton = "bon" if score >= 90 else "neutre" if score >= 75 else "mauvais"
    compte = lambda g: len([a for a in anomalies if a['gravite'] == g])
    ind = [{"libelle": "Conformité DGFiP", "valeur": f"{nb_fr(score, 1)} %", "detail": niveau, "ton": ton},
           {"libelle": "Lignes", "valeur": nb_fr(len(df))}]
    for col, lib in (('EcritureNum', "Écritures"), ('CompteNum', "Comptes"), ('JournalCode', "Journaux")):
        if col in df.columns:
            ind.append({"libelle": lib, "valeur": nb_fr(df[col].nunique())})
    ind += [{"libelle": "Anomalies élevées", "valeur": str(compte('Élevée')), "ton": "mauvais" if compte('Élevée') else "bon",
             "detail": "à corriger" if compte('Élevée') else "aucune"},
            {"libelle": "Anomalies moyennes", "valeur": str(compte('Moyenne')),
             "ton": "mauvais" if compte('Moyenne') else "bon", "detail": ""},
            {"libelle": "Anomalies faibles", "valeur": str(compte('Faible')), "detail": ""}]
    graphiques = []
    if 'JournalCode' in df.columns:
        par_j = df['JournalCode'].astype(str).value_counts()
        graphiques.append(barres_simples(list(par_j.index), [int(v) for v in par_j.values],
                                         "Nombre de lignes par journal", unite="Nombre de lignes"))
    if {'EcritureDate', 'Debit'} <= set(df.columns):
        dates = pd.to_datetime(df['EcritureDate'].astype(str).str[:8], format="%Y%m%d", errors="coerce")
        debit = pd.to_numeric(df['Debit'].astype(str).str.replace(" ", "").str.replace(",", "."), errors="coerce")
        par_mois = debit.groupby(dates.dt.to_period("M")).sum()
        if len(par_mois) >= 2:
            mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
            libs = [f"{mois[p.month - 1]} {str(p.year)[2:]}" for p in par_mois.index]
            graphiques.append(barres_simples(libs, [float(v) for v in par_mois.values],
                                             "Montants débités par mois"))
    return ind, graphiques


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
    rapport.append(f"- **Nombre de lignes** : {nb_fr(len(df), 0)}")
    rapport.append(f"- **Nombre de colonnes** : {len(df.columns)}")
    
    if 'EcritureNum' in df.columns:
        nb_pieces = df['EcritureNum'].nunique()
        rapport.append(f"- **Nombre d'écritures** (numéros d'écriture) : {nb_fr(nb_pieces, 0)}")
    
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
            rapport.append(f"- **Montant moyen par ligne** : {_eur(volume_total / len(df))}")
        except Exception as e:
            rapport.append(f"*Erreur calcul : {e}*")
    
    # 3. ANALYSE PAR JOURNAL
    if 'JournalCode' in df.columns:
        rapport.append("\n### 3. RÉPARTITION PAR JOURNAL")
        repartition = df['JournalCode'].value_counts().head(10)
        for journal, count in repartition.items():
            pct = (count / len(df)) * 100
            rapport.append(f"- **{journal}** : {nb_fr(count, 0)} lignes ({nb_fr(pct, 1)} %)")
    
    # 4. ANALYSE PERIODE
    if 'EcritureDate' in df.columns:
        rapport.append("\n### 4. PÉRIODE COMPTABLE")
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce').dropna()
            if len(dates) > 0:
                rapport.append(f"- **Date début** : {dates.min().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Date fin** : {dates.max().strftime('%d/%m/%Y')}")
                rapport.append(f"- **Durée** : {(dates.max() - dates.min()).days + 1} jours")
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
                'description': f"{sans_libelle} ligne{'s' if sans_libelle > 1 else ''} sans libellé"
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
                    'description': f"{ecritures_nulles} ligne{'s' if ecritures_nulles > 1 else ''} avec débit et crédit à zéro"
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
            'description': f"{duplicates} ligne{'s' if duplicates > 1 else ''} en double exact (même journal, numéro, compte, libellé et montant)"
        })
    
    return anomalies



def page_fec():
    import streamlit as st
    from utils.permissions import compter_analyse
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("Fichier des écritures comptables (FEC)")
    st.markdown("**Validation et analyse approfondie** des Fichiers des Écritures Comptables (Article L.47 A du LPF)")

    uploaded_file = st.file_uploader(
        "Déposer votre fichier FEC", 
        type=["txt", "csv"],
        help="Format pipe (|) ou tabulation, encodage UTF-8 ou ISO-8859-1"
    )

    if uploaded_file:
        from utils.fec import lire_fec, valider_fec, analyser_fec, detecter_anomalies_fec, colonnes_trouvees

        with st.spinner("Lecture du FEC..."):
            df, sep, enc = lire_fec(uploaded_file)

        if df is None:
            n = colonnes_trouvees(uploaded_file)
            st.error(f"Ce fichier n'est pas un FEC : {n} colonne{'s' if n > 1 else ''} trouvée{'s' if n > 1 else ''}, "
                     "18 attendues (JournalCode, EcritureDate, CompteNum…), séparées par | ou une tabulation.", icon=":material/error:")
            st.info("Pour une facture, utilisez la page **Analyse et comptabilisation de factures**, "
                    "puis exportez les écritures au format FEC.")
        else:
            st.success(f"FEC chargé : **{nb_fr(len(df), 0)} lignes** | Séparateur : `{sep}` | Encodage : `{enc}`", icon=":material/check_circle:")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Lignes", f"{nb_fr(len(df), 0)}")
            with col2:
                if 'EcritureNum' in df.columns:
                    st.metric("Écritures", f"{nb_fr(df['EcritureNum'].nunique(), 0)}")
            with col3:
                if 'CompteNum' in df.columns:
                    st.metric("Comptes", f"{df['CompteNum'].nunique()}")
            with col4:
                if 'JournalCode' in df.columns:
                    st.metric("Journaux", f"{df['JournalCode'].nunique()}")

            with st.expander("Aperçu des données (20 premières lignes)"):
                st.dataframe(df.head(20), width="stretch")

            st.divider()

            if st.button("Lancer la validation DGFiP complète", type="primary", width="stretch"):
                if not compter_analyse("FEC"):
                    st.stop()
                with st.spinner("Validation en cours selon Article A.47 A-1 du LPF..."):
                    resultats = valider_fec(df, sep=sep, nom_fichier=uploaded_file.name)

                    meta = resultats.pop('_meta', {})
                    score = meta.get('score_conformite', 0)
                    niveau = meta.get('niveau', 'Inconnu')

                    st.markdown("## Score de conformité DGFiP")

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if niveau == 'Non conforme':
                            st.error(f"### {niveau} : {nb_fr(score, 1)} %")
                        elif score >= 90:
                            st.success(f"### {niveau} : {nb_fr(score, 1)} %")
                        elif score >= 75:
                            st.info(f"### {niveau} : {nb_fr(score, 1)} %")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {nb_fr(score, 1)} %")
                        else:
                            st.error(f"### {niveau} : {nb_fr(score, 1)} %")

                        st.progress(min(int(score), 100))
                        st.caption(f"Points obtenus : {meta.get('points', 0)} / {meta.get('points_max', 100)}")

                    st.divider()

                    st.markdown("## Détail des contrôles")

                    for verif, status in resultats.items():
                        if status["valide"]:
                            st.success(f"**{verif}** : {status.get('message', 'Conforme')}", icon=":material/check_circle:")
                        else:
                            st.error(f"**{verif}** : {status.get('message', '')}", icon=":material/error:")

                    st.divider()

                    st.markdown("## Analyse approfondie")
                    analyse = analyser_fec(df)
                    afficher_rapport(analyse, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True)

                    st.divider()

                    st.markdown("## Détection d'anomalies")
                    anomalies = detecter_anomalies_fec(df)

                    if anomalies:
                        col1, col2, col3 = st.columns(3)
                        nb_elevees = len([a for a in anomalies if a['gravite'] == 'Élevée'])
                        nb_moyennes = len([a for a in anomalies if a['gravite'] == 'Moyenne'])
                        nb_faibles = len([a for a in anomalies if a['gravite'] == 'Faible'])

                        with col1:
                            st.metric("Élevées", nb_elevees)
                        with col2:
                            st.metric("Moyennes", nb_moyennes)
                        with col3:
                            st.metric("Faibles", nb_faibles)

                        for anomalie in anomalies:
                            if anomalie['gravite'] == 'Élevée':
                                st.error(f"**{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}", icon=":material/error:")
                            elif anomalie['gravite'] == 'Moyenne':
                                st.warning(f"**{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}", icon=":material/warning:")
                            else:
                                st.info(f"**{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}", icon=":material/info:")
                    else:
                        st.success("Aucune anomalie majeure détectée", icon=":material/check_circle:")

                    st.divider()

                    rapport_complet = rapport_controle_fec(score, niveau, resultats, analyse, anomalies)
                    col1, col2 = st.columns(2)
                    with col1:
                        bouton_sauvegarde(type_analyse="Contrôle FEC", resultat=rapport_complet, libelle="Sauvegarder le rapport")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_fec(df, score, niveau, anomalies)
                            generer_bouton_word("Rapport_Controle_FEC", rapport_complet,
                                                indicateurs=ind_w, graphiques=graph_w)
                        except Exception as e:
                            st.error(f"Erreur export : {e}")


    # -----------------------------------------------------------------------------
    # 5. LOI DE BENFORD - VERSION PROFESSIONNELLE
    # -----------------------------------------------------------------------------

