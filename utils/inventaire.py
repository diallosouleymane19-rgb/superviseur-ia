# -*- coding: utf-8 -*-
"""
Module Travaux d'Inventaire - SMD Global Consulting LLC
Provisions, Régularisations, Stocks, Check-list clôture
"""
from utils.sig_pcg import nb_fr
import pandas as pd
from datetime import datetime
from utils.page_helpers import champ_exercice, champs_remplis
from utils.page_helpers import tableau_markdown
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


# =============================================================================
# PROVISIONS
# =============================================================================

def calculer_provision_creances(df_clients, taux_douteux=50, taux_irrecouvrables=100):
    """
    Calcule les provisions pour créances douteuses
    df_clients : DataFrame avec colonnes Client, Montant, Ancienneté (jours)
    """
    resultats = []
    total_provision = 0

    for _, row in df_clients.iterrows():
        montant = float(str(row.get('Montant', 0)).replace(',', '.').replace(' ', ''))
        anciennete = int(row.get('Ancienneté', 0))
        client = str(row.get('Client', 'Inconnu'))

        if anciennete > 365:
            taux = taux_irrecouvrables
            statut = "🔴 Irrécouvrable"
            compte = "654"
        elif anciennete > 180:
            taux = taux_douteux
            statut = "🟡 Douteux"
            compte = "491"
        elif anciennete > 90:
            taux = taux_douteux / 2
            statut = "🟠 À surveiller"
            compte = "491"
        else:
            taux = 0
            statut = "✅ Sain"
            compte = "-"

        provision = montant * taux / 100
        total_provision += provision

        resultats.append({
            'Client': client,
            'Montant (€)': round(montant, 2),
            'Ancienneté (jours)': anciennete,
            'Statut': statut,
            'Taux (%)': taux,
            'Provision (€)': round(provision, 2),
            'Compte': compte
        })

    return pd.DataFrame(resultats), round(total_provision, 2)


def calculer_provision_risque(libelle, montant, probabilite, compte="15"):
    """Calcule une provision pour risque et charge"""
    provision = montant * probabilite / 100
    
    ecriture = pd.DataFrame([
        {'Compte': '6815', 'Libellé': f'Dotation aux provisions — {libelle}', 'Débit': round(provision, 2), 'Crédit': 0},
        {'Compte': compte, 'Libellé': f'Provision — {libelle}', 'Débit': 0, 'Crédit': round(provision, 2)}
    ])
    
    return {
        'libelle': libelle,
        'montant_risque': montant,
        'probabilite': probabilite,
        'provision': round(provision, 2),
        'ecriture': ecriture
    }


# =============================================================================
# RÉGULARISATIONS
# =============================================================================

def calculer_regularisations(charges_produits):
    """
    Calcule les régularisations de fin d'exercice
    charges_produits : liste de dicts avec type, libellé, montant_total, 
                       date_debut, date_fin, date_cloture
    """
    resultats = []

    for item in charges_produits:
        type_reg = item.get('type')
        libelle = item.get('libelle', '')
        montant = float(item.get('montant_total', 0))
        date_debut = item.get('date_debut')
        date_fin = item.get('date_fin')
        date_cloture = item.get('date_cloture')

        # Prorata en jours, bornes incluses : du 01/07 au 30/06 = 365 jours ; part de l'exercice = du début à la clôture incluse
        duree_totale = (date_fin - date_debut).days + 1
        avant = min(max((date_cloture - date_debut).days + 1, 0), duree_totale)
        if duree_totale > 0:
            montant_exercice = montant * avant / duree_totale
        else:
            montant_exercice = montant
        montant_suivant = montant - montant_exercice

        # CCA / PCA : on retire la part de l'exercice suivant ; CAP / PAR : on rattache la part de l'exercice
        comptes = {
            "CCA": ("486", "Charges constatées d'avance", montant_suivant, "Débit 486 / Crédit 6xx"),
            "PCA": ("487", "Produits constatés d'avance", montant_suivant, "Débit 7xx / Crédit 487"),
            "CAP": ("408", "Charges à payer", montant_exercice, "Débit 6xx / Crédit 408 (ou 428, 438…)"),
            "PAR": ("418", "Produits à recevoir", montant_exercice, "Débit 418 / Crédit 7xx"),
        }
        compte_regularisation, libelle_compte, montant_regularise, ecriture = comptes.get(type_reg, comptes["PAR"])

        resultats.append({
            'Type': type_reg,
            'Libellé': libelle,
            'Montant total (€)': round(montant, 2),
            'Part exercice (€)': round(montant_exercice, 2),
            'Montant régularisé (€)': round(montant_regularise, 2),
            'Compte': compte_regularisation,
            'Libellé compte': libelle_compte,
            'Écriture': ecriture,
        })

    return pd.DataFrame(resultats)


# =============================================================================
# STOCKS
# =============================================================================

def calculer_variation_stock(stock_debut, stock_fin, type_stock="marchandises"):
    """Calcule la variation de stock et les écritures"""
    variation = stock_fin - stock_debut

    comptes = {
        "marchandises": {"stock": "37", "variation": "6037", "libelle": "Marchandises"},
        "matieres_premieres": {"stock": "31", "variation": "6031", "libelle": "Matières premières"},
        "produits_finis": {"stock": "35", "variation": "7135", "libelle": "Produits finis"},
        "en_cours": {"stock": "33", "variation": "7133", "libelle": "En-cours"}
    }

    info = comptes.get(type_stock, comptes["marchandises"])

    if variation > 0:
        ecriture = pd.DataFrame([
            {'Compte': info['stock'], 'Libellé': f"Stock {info['libelle']}", 'Débit': round(variation, 2), 'Crédit': 0},
            {'Compte': info['variation'], 'Libellé': f"Variation stock {info['libelle']}", 'Débit': 0, 'Crédit': round(variation, 2)}
        ])
        sens = "📈 Augmentation"
    elif variation < 0:
        ecriture = pd.DataFrame([
            {'Compte': info['variation'], 'Libellé': f"Variation stock {info['libelle']}", 'Débit': round(abs(variation), 2), 'Crédit': 0},
            {'Compte': info['stock'], 'Libellé': f"Stock {info['libelle']}", 'Débit': 0, 'Crédit': round(abs(variation), 2)}
        ])
        sens = "📉 Diminution"
    else:
        ecriture = pd.DataFrame(columns=['Compte', 'Libellé', 'Débit', 'Crédit'])
        sens = "➡ Stable"

    return {
        'stock_debut': stock_debut,
        'stock_fin': stock_fin,
        'variation': round(variation, 2),
        'sens': sens,
        'ecriture': ecriture
    }


# =============================================================================
# CHECK-LIST CLÔTURE
# =============================================================================

def generer_checklist_cloture(exercice):
    """Génère la check-list complète de clôture d'exercice"""
    checklist = [
        # Rapprochements
        {"Catégorie": "🏦 Rapprochements", "Tâche": "Rapprochement bancaire tous comptes", "Priorité": "🔴 Critique", "Délai": "J-30"},
        {"Catégorie": "🏦 Rapprochements", "Tâche": "Lettrage comptes clients (41x)", "Priorité": "🔴 Critique", "Délai": "J-30"},
        {"Catégorie": "🏦 Rapprochements", "Tâche": "Lettrage comptes fournisseurs (40x)", "Priorité": "🔴 Critique", "Délai": "J-30"},
        
        # Immobilisations
        {"Catégorie": "📦 Immobilisations", "Tâche": "Calcul dotations amortissements", "Priorité": "🔴 Critique", "Délai": "J-20"},
        {"Catégorie": "📦 Immobilisations", "Tâche": "Inventaire physique des biens", "Priorité": "🟡 Important", "Délai": "J-20"},
        {"Catégorie": "📦 Immobilisations", "Tâche": "Enregistrement cessions/sorties", "Priorité": "🟡 Important", "Délai": "J-20"},
        
        # Stocks
        {"Catégorie": "📦 Stocks", "Tâche": "Inventaire physique des stocks", "Priorité": "🔴 Critique", "Délai": "J-15"},
        {"Catégorie": "📦 Stocks", "Tâche": "Valorisation des stocks", "Priorité": "🔴 Critique", "Délai": "J-15"},
        {"Catégorie": "📦 Stocks", "Tâche": "Dépréciation stocks obsolètes", "Priorité": "🟡 Important", "Délai": "J-15"},
        
        # Provisions
        {"Catégorie": "⚠ Provisions", "Tâche": "Provisions créances douteuses (491)", "Priorité": "🔴 Critique", "Délai": "J-10"},
        {"Catégorie": "⚠ Provisions", "Tâche": "Provisions risques et charges (15x)", "Priorité": "🟡 Important", "Délai": "J-10"},
        {"Catégorie": "⚠ Provisions", "Tâche": "Provisions pour congés payés (428)", "Priorité": "🟡 Important", "Délai": "J-10"},
        
        # Régularisations
        {"Catégorie": "🔄 Régularisations", "Tâche": "Charges constatées d'avance (486)", "Priorité": "🔴 Critique", "Délai": "J-5"},
        {"Catégorie": "🔄 Régularisations", "Tâche": "Produits constatés d'avance (487)", "Priorité": "🔴 Critique", "Délai": "J-5"},
        {"Catégorie": "🔄 Régularisations", "Tâche": "Charges à payer (408/428/438)", "Priorité": "🔴 Critique", "Délai": "J-5"},
        {"Catégorie": "🔄 Régularisations", "Tâche": "Produits à recevoir (418)", "Priorité": "🟡 Important", "Délai": "J-5"},
        
        # Fiscal
        {"Catégorie": "🏛 Fiscal", "Tâche": "Calcul IS / acomptes", "Priorité": "🔴 Critique", "Délai": "J-3"},
        {"Catégorie": "🏛 Fiscal", "Tâche": "Déclaration TVA dernière période", "Priorité": "🔴 Critique", "Délai": "J-3"},
        {"Catégorie": "🏛 Fiscal", "Tâche": "Vérification liasse fiscale", "Priorité": "🔴 Critique", "Délai": "J-1"},
        
        # Clôture
        {"Catégorie": "✅ Clôture", "Tâche": "Vérification équilibre balance", "Priorité": "🔴 Critique", "Délai": "J-1"},
        {"Catégorie": "✅ Clôture", "Tâche": "Édition balance définitive", "Priorité": "🔴 Critique", "Délai": "J"},
        {"Catégorie": "✅ Clôture", "Tâche": "Génération FEC", "Priorité": "🔴 Critique", "Délai": "J"},
    ]

    return pd.DataFrame(checklist)


def generer_rapport_inventaire(resultats, exercice):
    """Génère un rapport de travaux d'inventaire"""
    rapport = [f"# TRAVAUX D'INVENTAIRE — Exercice {exercice}"]
    rapport.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*\n---\n")

    for section, contenu in resultats.items():
        rapport.append(f"\n## {section}\n")
        rapport.append(contenu)

    rapport.append("\n---")
    rapport.append("*SMD Global Consulting LLC - Superviseur IA Comptable*")
    return "\n".join(rapport)



def _dates_dans_l_ordre(elements_inverses) -> bool:
    """Vrai si aucun élément n'a une date de fin antérieure à sa date de début ; sinon affiche lesquels."""
    import streamlit as st
    if elements_inverses:
        st.error("La date de fin précède la date de début : élément(s) " + ", ".join(map(str, elements_inverses)) + ".")
        return False
    return True


def page_inventaire():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📋 Travaux d'Inventaire & Clôture")
    st.markdown("**Provisions, Régularisations, Stocks, Check-list clôture**")
    st.caption("✨ Opérations de fin d'exercice — Qualité grand cabinet")

    from utils.inventaire import (
        calculer_provision_creances,
        calculer_provision_risque,
        calculer_regularisations,
        calculer_variation_stock,
        generer_checklist_cloture,
        generer_rapport_inventaire
    )

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "⚠ Provisions",
        "🔄 Régularisations",
        "📦 Stocks",
        "✅ Check-list Clôture"
    ])

    # ── ONGLET 1 : PROVISIONS ──
    with onglet1:
        st.markdown("### ⚠ Provisions")

        sous_onglet1, sous_onglet2 = st.tabs([
            "Créances douteuses",
            "Risques & Charges"
        ])

        with sous_onglet1:
            st.markdown("#### 📉 Provisions pour créances douteuses")
            st.caption("Compte 491 — Article L123-20 du Code de Commerce")

            col1, col2 = st.columns(2)
            with col1:
                taux_douteux = st.slider("Taux créances douteuses (%)", 0, 100, 50)
            with col2:
                taux_irrecouvrables = st.slider("Taux créances irrécouvrables (%)", 0, 100, 100)

            st.markdown("#### 📋 Saisie des créances clients")

            nb_clients = st.number_input("Nombre de clients à analyser", min_value=1, max_value=20, value=3)

            clients_data = []
            for i in range(int(nb_clients)):
                st.markdown(f"**Client {i+1}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    nom = st.text_input(f"Nom", key=f"client_nom_{i}", placeholder="SARL X")
                with col2:
                    montant = st.number_input("Montant HT (€)", min_value=0.0, key=f"client_montant_{i}", value=None,
                                              placeholder="ex. 1 000")
                with col3:
                    anciennete = st.number_input("Ancienneté (jours)", min_value=0, key=f"client_anc_{i}", value=None,
                                                 placeholder="ex. 120")
                clients_data.append({'Client': nom, 'Montant': montant, 'Ancienneté': anciennete})
            manquants_cr = [f"{c} (client {i + 1})" for i, d in enumerate(clients_data)
                            for c, v in (("Montant", d['Montant']), ("Ancienneté", d['Ancienneté'])) if v is None]

            if st.button("⚠ Calculer les provisions", type="primary", width="stretch", key="btn_prov_creances") and \
                    champs_remplis(**{m: None for m in manquants_cr}):
                df_clients = pd.DataFrame(clients_data)
                df_resultats, total = calculer_provision_creances(df_clients, taux_douteux, taux_irrecouvrables)

                st.markdown("## 📊 Résultats")
                st.dataframe(df_resultats, width="stretch", hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Total provisions", f"{nb_fr(total, 2)} €")
                with col2:
                    nb_douteux = len(df_resultats[df_resultats['Taux (%)'] > 0])
                    st.metric("⚠ Créances à risque", nb_douteux)

                st.divider()
                st.markdown("### 📚 Écriture comptable")
                st.info(f"""
    **Dotation aux provisions :**
    - Débit **6817** (Dotation provisions créances) : {nb_fr(total, 2)} €
    - Crédit **491** (Provision créances douteuses) : {nb_fr(total, 2)} €
                """)

                bouton_sauvegarde(type_analyse="Provisions créances", libelle="💾 Sauvegarder", key="save_prov_creances",
                                  resultat="\n".join(["# PROVISIONS POUR CRÉANCES DOUTEUSES", "", tableau_markdown(df_resultats), "",
                                                      f"**Total à provisionner** : {nb_fr(total, 2)} €", "",
                                                      f"- Débit 6817 (Dotation aux provisions pour créances) : {nb_fr(total, 2)} €",
                                                      f"- Crédit 491 (Provision pour créances douteuses) : {nb_fr(total, 2)} €"]))
        with sous_onglet2:
            st.markdown("#### 🛡 Provisions pour risques et charges")
            st.caption("Compte 15x — Risques identifiés fin d'exercice")

            col1, col2, col3 = st.columns(3)
            with col1:
                libelle_risque = st.text_input("📝 Nature du risque", placeholder="Ex: Litige fournisseur")
            with col2:
                montant_risque = st.number_input("💰 Montant estimé (€)", min_value=0.0, value=None, placeholder="ex. 5 000")
            with col3:
                probabilite = st.slider("📊 Probabilité (%)", 0, 100, 70)

            compte_prov = st.selectbox("📚 Compte de provision", [
                "151 — Provisions pour risques",
                "152 — Provisions pour impôts",
                "153 — Provisions pour pensions",
                "155 — Provisions pour garanties",
                "158 — Autres provisions pour charges"
            ])

            if st.button("🛡 Calculer la provision", type="primary", width="stretch", key="btn_prov_risque") and \
                    champs_remplis(**{"Nature du risque": libelle_risque, "Montant estimé": montant_risque}):
                compte = compte_prov.split(" — ")[0]
                result = calculer_provision_risque(libelle_risque, montant_risque, probabilite, compte)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 Montant risque", f"{nb_fr(montant_risque, 2)} €")
                with col2:
                    st.metric("📊 Probabilité", f"{nb_fr(probabilite, 0)} %")
                with col3:
                    st.metric("⚠ Provision", f"{nb_fr(result['provision'], 2)} €")

                st.divider()
                st.markdown("### 📚 Écriture comptable")
                st.dataframe(result['ecriture'], width="stretch", hide_index=True)

    # ── ONGLET 2 : RÉGULARISATIONS ──
    with onglet2:
        st.markdown("### 🔄 Régularisations de fin d'exercice")
        st.caption("CCA, PCA, Charges à payer, Produits à recevoir")

        with st.expander("ℹ Comprendre les régularisations"):
            st.markdown("""
    | Type | Compte | Description |
    |---|---|---|
    | **CCA** | 486 | Charges payées mais concernant l'exercice suivant |
    | **PCA** | 487 | Produits encaissés mais concernant l'exercice suivant |
    | **CAP** | 408/428 | Charges dues mais pas encore facturées |
    | **PAR** | 418 | Produits à facturer non encore encaissés |
            """)

        date_cloture = st.date_input("📅 Date de clôture de l'exercice", value=None, format="DD/MM/YYYY")

        nb_elements = st.number_input("Nombre d'éléments à régulariser", min_value=1, max_value=10, value=2)

        elements, manquants_reg, dates_inversees = [], [], []
        for i in range(int(nb_elements)):
            st.markdown(f"**Élément {i+1}**")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                type_reg = st.selectbox("Type", ["CCA", "PCA", "CAP", "PAR"], key=f"type_{i}")
            with col2:
                lib = st.text_input("Libellé", key=f"lib_{i}", placeholder="Ex: Assurance")
            with col3:
                montant = st.number_input("Montant (€)", min_value=0.0, key=f"mont_{i}", value=None, placeholder="ex. 1 200")
            with col4:
                date_debut = st.date_input("Début", key=f"deb_{i}", value=None, format="DD/MM/YYYY")
            with col5:
                date_fin = st.date_input("Fin", key=f"fin_{i}", value=None, format="DD/MM/YYYY")

            manquants_reg += [f"{nom} (élément {i + 1})" for nom, v in
                              (("Montant", montant), ("Début", date_debut), ("Fin", date_fin)) if v is None]
            if date_debut and date_fin and date_fin < date_debut:
                dates_inversees.append(i + 1)
            if montant is not None and date_debut and date_fin:
                elements.append({
                    'type': type_reg,
                    'libelle': lib,
                    'montant_total': montant,
                    'date_debut': datetime.combine(date_debut, datetime.min.time()),
                    'date_fin': datetime.combine(date_fin, datetime.min.time()),
                    'date_cloture': datetime.combine(date_cloture, datetime.min.time()) if date_cloture else None
                })

        if st.button("🔄 Calculer les régularisations", type="primary", width="stretch") and \
                champs_remplis(**{"Date de clôture de l'exercice": date_cloture},
                               **{m: None for m in manquants_reg}) and \
                _dates_dans_l_ordre(dates_inversees):
            df_reg = calculer_regularisations(elements)

            st.markdown("## 📊 Résultats des régularisations")
            st.dataframe(df_reg, width="stretch", hide_index=True)

            total_reg = df_reg['Montant régularisé (€)'].sum()
            st.metric("💰 Total à régulariser", f"{nb_fr(total_reg, 2)} €")

            bouton_sauvegarde(type_analyse="Régularisations", libelle="💾 Sauvegarder", key="save_reg",
                              resultat="\n".join([f"# RÉGULARISATIONS DE FIN D'EXERCICE",
                                                  f"## Clôture au {date_cloture.strftime('%d/%m/%Y')}", "",
                                                  tableau_markdown(df_reg), "",
                                                  f"**Total à régulariser** : {nb_fr(total_reg, 2)} €"]))
    # ── ONGLET 3 : STOCKS ──
    with onglet3:
        st.markdown("### 📦 Ajustement des stocks")
        st.caption("Variation de stock — Écritures comptables automatiques")

        col1, col2, col3 = st.columns(3)
        with col1:
            type_stock = st.selectbox("📦 Type de stock", [
                "marchandises",
                "matieres_premieres",
                "produits_finis",
                "en_cours"
            ])
        with col2:
            stock_debut = st.number_input("📊 Stock début exercice (€)", min_value=0.0, value=None, placeholder="ex. 50 000")
        with col3:
            stock_fin = st.number_input("📊 Stock fin exercice (€)", min_value=0.0, value=None, placeholder="ex. 45 000")

        if st.button("📦 Calculer la variation", type="primary", width="stretch") and \
                champs_remplis(**{"Stock début exercice": stock_debut, "Stock fin exercice": stock_fin}):
            result = calculer_variation_stock(stock_debut, stock_fin, type_stock)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Stock début", f"{nb_fr(stock_debut, 2)} €")
            with col2:
                st.metric("📊 Stock fin", f"{nb_fr(stock_fin, 2)} €")
            with col3:
                delta_color = "normal" if result['variation'] > 0 else "inverse"
                st.metric(
                    "🔄 Variation",
                    f"{nb_fr(abs(result['variation']), 2)} €",
                    delta=result['sens'],
                    delta_color=delta_color
                )

            st.divider()
            st.markdown("### 📚 Écriture comptable")
            st.dataframe(result['ecriture'], width="stretch", hide_index=True)

            bouton_sauvegarde(type_analyse="Variation stock", libelle="💾 Sauvegarder", key="save_stock",
                              resultat="\n".join([f"# VARIATION DE STOCK – {type_stock.replace('_', ' ')}", "",
                                                  f"- **Variation** : {nb_fr(result['variation'], 2)} € ({result['sens']})", "",
                                                  "## Écriture comptable", "", tableau_markdown(result['ecriture'])]))
    # ── ONGLET 4 : CHECK-LIST CLÔTURE ──
    with onglet4:
        st.markdown("### ✅ Check-list de clôture d'exercice")
        st.caption("Toutes les opérations à effectuer avant clôture")

        exercice = champ_exercice(key="exercice_checklist")

        if st.button("✅ Générer la check-list", type="primary", width="stretch") and champs_remplis(Exercice=exercice):
            df_checklist = generer_checklist_cloture(exercice)

            # Résumé
            nb_critique = len(df_checklist[df_checklist['Priorité'] == "🔴 Critique"])
            nb_important = len(df_checklist[df_checklist['Priorité'] == "🟡 Important"])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📋 Total tâches", len(df_checklist))
            with col2:
                st.metric("🔴 Critiques", nb_critique)
            with col3:
                st.metric("🟡 Importantes", nb_important)

            st.divider()

            # Affichage par catégorie
            for categorie in df_checklist['Catégorie'].unique():
                st.markdown(f"#### {categorie}")
                df_cat = df_checklist[df_checklist['Catégorie'] == categorie][['Tâche', 'Priorité', 'Délai']]
                st.dataframe(df_cat, width="stretch", hide_index=True)

            st.divider()

            sans_icone = lambda t: str(t).split(" ", 1)[-1] if str(t)[:1] in "🔴🟡🔵🟢" else str(t)
            rapport = [f"# CHECK-LIST DE CLÔTURE {exercice}",
                       "*Délais exprimés en jours avant la date de clôture (J = jour de clôture). "
                       "Cochez la colonne « Fait » au fur et à mesure.*", ""]
            for categorie in df_checklist['Catégorie'].unique():
                rapport += ["", f"## {categorie}", "", "| Tâche | Priorité | Délai | Fait |", "|---|---|:---:|:---:|"]
                for _, l in df_checklist[df_checklist['Catégorie'] == categorie].iterrows():
                    rapport.append(f"| {l['Tâche']} | {sans_icone(l['Priorité'])} | {l['Délai']} | ☐ |")
            rapport = "\n".join(rapport)

            col1, col2 = st.columns(2)
            with col1:
                bouton_sauvegarde(type_analyse="Check-list clôture", resultat=rapport, libelle="💾 Sauvegarder", key="save_checklist")
            with col2:
                try:
                    ind_w = [{"libelle": "Tâches", "valeur": str(len(df_checklist))},
                             {"libelle": "Critiques", "valeur": str(nb_critique), "ton": "mauvais", "detail": "à faire en priorité"},
                             {"libelle": "Importantes", "valeur": str(nb_important), "detail": ""}]
                    generer_bouton_word(f"Checklist_Cloture_{exercice}", rapport, indicateurs=ind_w)
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # -----------------------------------------------------------------------------
    # 9a. PLAN DE FINANCEMENT
    # -----------------------------------------------------------------------------

