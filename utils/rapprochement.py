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
    from utils.intelligent_parser import montants
    return montants(serie).fillna(0)


def _sans_accents(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def lire_operations(fichier):
    """Relevé bancaire ou écritures (CSV, TXT ou Excel) tel qu'exporté par la banque ou le logiciel :
    encodage UTF-8 ou Windows, séparateur quelconque, lignes d'en-tête de la banque (nom, n° de compte,
    solde…) ignorées : le tableau commence à la ligne qui contient « Date » et un montant.
    Retourne (DataFrame, solde_indique) ; solde_indique = solde lu dans l'en-tête de la banque, ou None."""
    import io, re
    from utils.formats import est_tableur
    nom = getattr(fichier, "name", "").lower()
    fichier.seek(0)
    contenu = fichier.read()
    if est_tableur(nom):
        brut = pd.read_excel(io.BytesIO(contenu), header=None, dtype=str)
    else:
        texte = None
        for enc in ("utf-8-sig", "cp1252"):
            try:
                texte = contenu.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        lignes = texte.splitlines()
        sep = max([";", "|", "\t", ","], key=lambda x: sum(l.count(x) for l in lignes[:30]))
        brut = pd.read_csv(io.StringIO(texte), sep=sep, header=None, dtype=str, engine="python",
                           on_bad_lines="skip", names=range(max(l.count(sep) for l in lignes[:200]) + 1))
    entete = None
    for i in range(min(len(brut), 40)):
        cellules = [_sans_accents(x) for x in brut.iloc[i].fillna("")]
        texte_l = " ".join(cellules)
        if any("date" in c for c in cellules) and re.search(r"montant|debit|credit|amount", texte_l):
            entete = i
            break
    solde = None
    zone = " ".join(" ".join(str(x) for x in brut.iloc[j].fillna("")) for j in range(entete or 0))
    # montant avec décimales (« 12 480,50 ») : la date « au 30/09/2026 » qui précède n'est pas prise
    m = re.search(r"(?i)solde\b.{0,40}?(-?\d{1,3}(?:[\s\u00a0\u202f.]\d{3})*[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)", zone)
    if m:
        from utils.intelligent_parser import montants
        v = montants(pd.Series([m.group(1)])).iloc[0]
        solde = None if pd.isna(v) else float(v)
    if entete is None:
        entete = 0
    noms = [str(x).strip() if str(x).strip() not in ("", "nan") else f"col_{k}" for k, x in enumerate(brut.iloc[entete])]
    df = brut.iloc[entete + 1:].copy()
    df.columns = noms
    df = df.dropna(how="all")
    df = df[[c for c in df.columns if not (c.startswith("col_") and df[c].isna().all())]]
    return df.reset_index(drop=True), solde


def ecritures_banque(df, compte=None):
    """FEC ou grand livre complet : seules les lignes du compte de banque (512 par défaut, ou le compte choisi)
    sont gardées. Fichier qui ne contient déjà que la banque : inchangé. Retourne (df, comptes_banque)."""
    col = next((c for c in df.columns if _sans_accents(c) in ("comptenum", "compte", "n compte", "numero de compte")), None)
    if col is None:
        return df, []
    cpt = df[col].astype(str).str.strip()
    banques = sorted(set(cpt[cpt.str.match(r"^51[2-7]")]))
    if not banques or cpt.str.match(r"^51").all():
        return df, banques
    choix = compte or ("512000" if "512000" in banques else banques[0])
    return df[cpt == choix].copy(), banques


def etat_rapprochement(resultats, solde_releve, solde_comptable):
    """État de rapprochement à la date d'arrêté.
    Côté banque : solde du relevé + encaissements comptabilisés non encore au relevé - décaissements comptabilisés
    non encore au relevé. Côté comptabilité : solde du 512 + crédits du relevé non comptabilisés - débits du
    relevé non comptabilisés. Les deux soldes rectifiés doivent être égaux."""
    nr_e = resultats.get('non_rapproches_ecritures')
    nr_r = resultats.get('non_rapproches_releve')
    m_e = nr_e['Montant'] if nr_e is not None and not nr_e.empty else pd.Series(dtype=float)
    m_r = nr_r['Montant'] if nr_r is not None and not nr_r.empty else pd.Series(dtype=float)
    enc_compta, dec_compta = float(m_e[m_e > 0].sum()), float(-m_e[m_e < 0].sum())
    cred_banque, deb_banque = float(m_r[m_r > 0].sum()), float(-m_r[m_r < 0].sum())
    banque_rect = solde_releve + enc_compta - dec_compta
    compta_rect = solde_comptable + cred_banque - deb_banque
    return {
        "Solde du relevé bancaire": solde_releve,
        "+ Encaissements comptabilisés, absents du relevé": enc_compta,
        "- Décaissements comptabilisés, absents du relevé (chèques émis non débités…)": dec_compta,
        "= Solde bancaire rectifié": banque_rect,
        "Solde comptable du compte de banque": solde_comptable,
        "+ Crédits du relevé non comptabilisés": cred_banque,
        "- Débits du relevé non comptabilisés (frais, prélèvements…)": deb_banque,
        "= Solde comptable rectifié": compta_rect,
        "Écart": round(banque_rect - compta_rect, 2),
    }


def normaliser_date(serie):
    t = serie.astype(str).str.strip()
    aaaammjj = pd.to_datetime(t.where(t.str.fullmatch(r"\d{8}")), format="%Y%m%d", errors="coerce")
    return aaaammjj.fillna(pd.to_datetime(t.where(~t.str.fullmatch(r"\d{8}")), errors='coerce', dayfirst=True))


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
            col_date_r = col_date_r or cols_releve[k]   # 1re date : date d'opération (pas date de valeur)
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
            col_date_e = col_date_e or (cols_ecr['ecrituredate'] if 'ecrituredate' in cols_ecr else cols_ecr[k])
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
    
    if 'ecriturelib' in cols_ecr:      # FEC : libellé de l'écriture, pas celui du journal ou du compte
        col_lib_e = cols_ecr['ecriturelib']
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

    # Sens : sur le relevé, un encaissement est au crédit ; dans le compte 512, au débit. Les deux sont donc
    # positifs dans _montant. Si le relevé suit la convention inverse (montant unique signé autrement),
    # on la détecte d'après le nombre de montants concordants dans chaque sens.
    mr = df_r['_montant'].round(2)
    me = set(df_e['_montant'].round(2))
    meme_sens = int(mr[mr != 0].isin(me).sum())
    sens_inverse = int((-mr[mr != 0]).isin(me).sum())
    sens = -1 if sens_inverse > meme_sens else 1
    
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
            
            if abs(sens * montant_r - montant_e) > 0.01:      # même montant ET même sens (encaissement / décaissement)
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


def affichable(df):
    """Copie pour l'écran : dates JJ/MM/AAAA, montants au format français (1 234,56)."""
    if df is None or df.empty:
        return df
    d = df.copy()
    for c in d.columns:
        if "Date" in c:
            d[c] = pd.to_datetime(d[c], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        elif c == "Montant":
            d[c] = d[c].map(lambda x: nb_fr(x, 2))
    return d


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


def generer_rapport_rapprochement(resultats, nom_compte="Compte bancaire", etat=None):
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
    if etat:
        rapport += ["## ÉTAT DE RAPPROCHEMENT", "", "| Poste | Montant (€) |", "|-------|------------:|"]
        for k, v in etat.items():
            gras = k.startswith("=") or k == "Écart"
            rapport.append(f"| {'**' + k + '**' if gras else k} | {'**' + nb_fr(v, 2) + '**' if gras else nb_fr(v, 2)} |")
        rapport.append("")
        rapport.append("Soldes rectifiés concordants : rapprochement justifié." if abs(etat["Écart"]) < 0.01
                       else f"**Écart non expliqué : {nb_fr(etat['Écart'], 2)} €.**")
        rapport.append("")
    for titre, cle, explication in (
            ("OPÉRATIONS BANCAIRES NON RAPPROCHÉES", 'non_rapproches_releve',
             "Opérations du relevé sans écriture comptable correspondante."),
            ("ÉCRITURES COMPTABLES NON RAPPROCHÉES", 'non_rapproches_ecritures',
             "Écritures du compte 512 sans opération correspondante sur le relevé.")):
        rapport += _tableau_operations(resultats.get(cle), titre, explication)
    rapport.append("---")
    rapport.append("*SMD Global Consulting LLC - KontrolIA*")
    
    return "\n".join(rapport)



def page_rapprochement():
    import streamlit as st
    from utils.permissions import compter_analyse
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("Rapprochement bancaire")
    st.markdown("**Matching intelligent** entre relevé bancaire et écritures comptables")
    st.caption("Matching automatique par montant + date + libellé")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Relevé bancaire")
        releve = st.file_uploader(
            "Fichier relevé (CSV, TXT, Excel)",
            type=TYPES_BALANCE,
            key="releve",
            help="Export de la banque (CSV ou Excel) : Date, Libellé et Montant, ou Débit / Crédit. "
                 "Les lignes d'en-tête de la banque sont ignorées."
        )

    with col2:
        st.markdown("### Écritures comptables")
        ecritures = st.file_uploader(
            "Fichier écritures : grand livre 512 ou FEC (CSV, TXT, Excel)",
            type=TYPES_BALANCE,
            key="ecritures",
            help="Grand livre du compte de banque ou FEC complet (seul le compte 512 est retenu) : "
                 "Date, Libellé, Débit, Crédit."
        )

    if releve and ecritures:
        from utils.rapprochement import rapprocher_bancaire, generer_rapport_rapprochement

        try:
            df_releve, solde_lu = lire_operations(releve)
            df_ecritures, _ = lire_operations(ecritures)
            df_ecritures, banques = ecritures_banque(df_ecritures)
            if len(banques) > 1:
                choix_banque = st.selectbox("Compte de banque à rapprocher", banques)
                df_ecritures, _ = ecritures_banque(lire_operations(ecritures)[0], choix_banque)
            elif banques:
                st.caption(f"Écritures du compte {banques[0]} retenues (les autres comptes du fichier sont ignorés).")

            st.success(f"Relevé : **{len(df_releve)} opérations** | Écritures : **{len(df_ecritures)} lignes**", icon=":material/check_circle:")

            with st.expander("Aperçu des fichiers"):
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
                nom_compte = st.text_input("Nom du compte", value="Compte bancaire principal")
            with col2:
                tolerance = st.slider("Tolérance (jours)", 0, 10, 3,
                                     help="Écart maximum entre date relevé et écriture")
            st.markdown("**État de rapprochement** (facultatif) : soldes à la date d'arrêté")
            col1, col2 = st.columns(2)
            with col1:
                solde_releve = st.number_input("Solde du relevé à la date d'arrêté (€)", value=solde_lu, step=0.01,
                                               format="%.2f", placeholder="ex. 12 480,50",
                                               help="Repris de l'en-tête du relevé quand la banque l'indique. "
                                                    "Créditeur (en votre faveur) = positif.")
            with col2:
                solde_compta = st.number_input("Solde comptable du compte de banque à la même date (€)", value=None,
                                               step=0.01, format="%.2f", placeholder="ex. 11 933,00",
                                               help="Solde du 512 dans votre balance ou grand livre. Débiteur = positif.")
            if solde_releve is None or solde_compta is None:
                st.caption("Sans ces deux soldes, le rapprochement des opérations est fait, mais l'état de "
                           "rapprochement (soldes rectifiés et écart) n'est pas établi, ni à l'écran ni dans le rapport Word.")

            if st.button("Lancer le rapprochement", type="primary", width="stretch"):
                if not compter_analyse("Rapprochement"):
                    st.stop()
                with st.spinner("Matching intelligent en cours..."):
                    resultats = rapprocher_bancaire(df_releve, df_ecritures, tolerance_jours=tolerance)

                    st.markdown("## Résultats du rapprochement")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Rapprochés", resultats['nb_rapproches'])
                    with col2:
                        st.metric("Non rapp. relevé", resultats['nb_non_rapproches_releve'])
                    with col3:
                        st.metric("Non rapp. écritures", resultats['nb_non_rapproches_ecritures'])
                    with col4:
                        taux = resultats['taux_rapprochement']
                        st.metric("Taux", f"{nb_fr(taux, 1)} %",
                                 delta="Excellent" if taux >= 90 else "Bon" if taux >= 70 else "À vérifier",
                                 delta_color="normal" if taux >= 70 else "inverse")

                    st.progress(min(int(taux), 100))

                    if taux >= 90:
                        st.success("**Excellent rapprochement** - Quasi-complet", icon=":material/check_circle:")
                    elif taux >= 70:
                        st.info("**Bon rapprochement** - Satisfaisant", icon=":material/info:")
                    elif taux >= 50:
                        st.warning("**Rapprochement moyen** - Investigations nécessaires", icon=":material/warning:")
                    else:
                        st.error("**Rapprochement faible** - Anomalies importantes", icon=":material/error:")

                    st.divider()

                    if not resultats['rapproches'].empty:
                        with st.expander(f"Opérations rapprochées ({resultats['nb_rapproches']})"):
                            st.dataframe(affichable(resultats['rapproches']), width="stretch", hide_index=True)

                    if not resultats['non_rapproches_releve'].empty:
                        with st.expander(f"Relevé non rapproché ({resultats['nb_non_rapproches_releve']})", expanded=True):
                            st.warning("Opérations bancaires sans contrepartie comptable")
                            st.dataframe(affichable(resultats['non_rapproches_releve']), width="stretch", hide_index=True)

                    if not resultats['non_rapproches_ecritures'].empty:
                        with st.expander(f"Écritures non rapprochées ({resultats['nb_non_rapproches_ecritures']})", expanded=True):
                            st.warning("Écritures sans contrepartie bancaire")
                            st.dataframe(affichable(resultats['non_rapproches_ecritures']), width="stretch", hide_index=True)

                    st.divider()

                    etat = None
                    if solde_releve is not None and solde_compta is not None:
                        etat = etat_rapprochement(resultats, solde_releve, solde_compta)
                        st.markdown("### État de rapprochement")
                        st.dataframe(pd.DataFrame({"Poste": list(etat), "Montant (€)": [nb_fr(v, 2) for v in etat.values()]}),
                                     width="stretch", hide_index=True)
                        if abs(etat["Écart"]) < 0.01:
                            st.success("Les soldes rectifiés concordent : rapprochement justifié.", icon=":material/check_circle:")
                        else:
                            st.error(f"Écart non expliqué de {nb_fr(etat['Écart'], 2)} € : opération manquante, "
                                     "erreur de montant ou soldes pris à des dates différentes.", icon=":material/error:")
                    else:
                        st.info("Indiquez les deux soldes pour obtenir l'état de rapprochement.", icon=":material/info:")

                    rapport = generer_rapport_rapprochement(resultats, nom_compte, etat)

                    col1, col2 = st.columns(2)
                    with col1:
                        bouton_sauvegarde(type_analyse="Rapprochement Bancaire", resultat=rapport, libelle="Sauvegarder")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_rapprochement(resultats)
                            generer_bouton_word(f"Rapprochement_{nom_compte}", rapport, indicateurs=ind_w,
                                                graphiques=graph_w, sans_sections=("SYNTHÈSE",))
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"Erreur : {str(e)}", icon=":material/error:")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
    # -----------------------------------------------------------------------------
    # IMMOBILISATIONS - AMORTISSEMENTS & CESSIONS
    # -----------------------------------------------------------------------------

