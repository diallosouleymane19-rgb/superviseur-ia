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

TRANCHES_ANCIENNETE = ((90, "✅ Saine"), (180, "🟠 À surveiller"), (365, "🟡 Douteuse"),
                       (None, "🔴 Très ancienne – perte (654) à confirmer"))


def calculer_provision_creances(df_clients, taux_91_180=25, taux_181_365=50, taux_plus_365=100):
    """Dépréciation des créances clients (PCG : compte 491, dotation 6817), calculée sur le montant HT.
    df_clients : colonnes Client, Montant TTC, TVA (%), Ancienneté (jours).
    Le taux par ancienneté est indicatif : il se justifie créance par créance. Au-delà de 365 jours, la créance est
    signalée ; la perte définitive (654) ne se constate que si l'irrécouvrabilité est certaine."""
    resultats = []
    total_provision = 0.0
    for _, row in df_clients.iterrows():
        ttc = float(str(row.get('Montant TTC', row.get('Montant', 0)) or 0).replace(',', '.').replace(' ', ''))
        tva = float(row.get('TVA (%)', 0) or 0)
        ht = ttc / (1 + tva / 100)
        anciennete = int(row.get('Ancienneté', 0) or 0)
        if anciennete <= 90:
            taux, statut = 0, TRANCHES_ANCIENNETE[0][1]
        elif anciennete <= 180:
            taux, statut = taux_91_180, TRANCHES_ANCIENNETE[1][1]
        elif anciennete <= 365:
            taux, statut = taux_181_365, TRANCHES_ANCIENNETE[2][1]
        else:
            taux, statut = taux_plus_365, TRANCHES_ANCIENNETE[3][1]
        provision = ht * taux / 100
        total_provision += provision
        resultats.append({
            'Client': str(row.get('Client', '') or 'Non renseigné'),
            'Créance TTC (€)': round(ttc, 2),
            'Base HT (€)': round(ht, 2),
            'Ancienneté (jours)': anciennete,
            'Statut': statut,
            'Taux (%)': taux,
            'Dépréciation (€)': round(provision, 2),
        })
    return pd.DataFrame(resultats), round(total_provision, 2)


NATURES_PROVISION = {"Exploitation": "6815", "Financière": "6865", "Exceptionnelle": "6875"}
PROBABILITES = ("Probable", "Possible, mais non probable", "Éloignée")


def calculer_provision_risque(libelle, estimation, probabilite, compte="151", nature="Exploitation"):
    """Provision pour risques et charges selon le PCG (art. 321-1 et s.) : si la sortie de ressources est probable,
    provision = meilleure estimation ; sinon, aucune provision (passif éventuel : mention en annexe s'il est possible)."""
    compte_dotation = NATURES_PROVISION.get(nature, "6815")
    provision = float(estimation) if probabilite == "Probable" else 0.0
    if provision:
        ecriture = pd.DataFrame([
            {'Compte': compte_dotation, 'Libellé': f'Dotation aux provisions — {libelle}', 'Débit': round(provision, 2), 'Crédit': 0},
            {'Compte': compte, 'Libellé': f'Provision — {libelle}', 'Débit': 0, 'Crédit': round(provision, 2)}])
        conclusion = "Sortie de ressources probable : provision de la meilleure estimation."
    else:
        ecriture = pd.DataFrame(columns=['Compte', 'Libellé', 'Débit', 'Crédit'])
        conclusion = ("Sortie de ressources possible mais non probable : pas de provision ; passif éventuel à mentionner "
                      "en annexe." if probabilite == PROBABILITES[1] else
                      "Sortie de ressources éloignée : ni provision ni mention en annexe.")
    return {'libelle': libelle, 'estimation': float(estimation), 'probabilite': probabilite,
            'provision': round(provision, 2), 'compte': compte, 'compte_dotation': compte_dotation,
            'conclusion': conclusion, 'ecriture': ecriture}


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
            st.markdown("#### 📉 Dépréciation des créances clients")
            st.caption("Compte 491, dotation 6817 — calculée sur le montant hors taxes (la TVA n'est pas une perte tant que "
                       "la créance n'est pas définitivement irrécouvrable).")

            st.markdown("**Taux de dépréciation indicatifs selon l'ancienneté** — à ajuster créance par créance selon "
                        "la situation réelle du client.")
            col1, col2, col3 = st.columns(3)
            with col1:
                taux_91_180 = st.slider("91 à 180 jours (%)", 0, 100, 25)
            with col2:
                taux_181_365 = st.slider("181 à 365 jours (%)", 0, 100, 50)
            with col3:
                taux_plus_365 = st.slider("Plus de 365 jours (%)", 0, 100, 100)

            st.markdown("#### 📋 Saisie des créances clients")
            nb_clients = st.number_input("Nombre de clients à analyser", min_value=1, max_value=20, value=3)

            clients_data = []
            for i in range(int(nb_clients)):
                st.markdown(f"**Client {i+1}**")
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                with col1:
                    nom = st.text_input("Nom", key=f"client_nom_{i}", placeholder="SARL X")
                with col2:
                    montant = st.number_input("Créance TTC (€)", min_value=0.0, key=f"client_montant_{i}", value=None,
                                              placeholder="ex. 1 200")
                with col3:
                    tva = st.selectbox("TVA", [20.0, 10.0, 5.5, 2.1, 0.0], key=f"client_tva_{i}",
                                       format_func=lambda t: f"{nb_fr(t, 1 if t % 1 else 0)} %")
                with col4:
                    anciennete = st.number_input("Ancienneté (jours)", min_value=0, key=f"client_anc_{i}", value=None,
                                                 placeholder="ex. 120")
                clients_data.append({'Client': nom, 'Montant TTC': montant, 'TVA (%)': tva, 'Ancienneté': anciennete})
            manquants_cr = [f"{c} (client {i + 1})" for i, d in enumerate(clients_data)
                            for c, v in (("Créance TTC", d['Montant TTC']), ("Ancienneté", d['Ancienneté'])) if v is None]

            if st.button("⚠ Calculer les dépréciations", type="primary", width="stretch", key="btn_prov_creances") and \
                    champs_remplis(**{m: None for m in manquants_cr}):
                df_resultats, total = calculer_provision_creances(pd.DataFrame(clients_data), taux_91_180, taux_181_365,
                                                                  taux_plus_365)
                st.markdown("## 📊 Résultats")
                st.dataframe(df_resultats, width="stretch", hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Total des dépréciations", f"{nb_fr(total, 2)} €")
                with col2:
                    st.metric("⚠ Créances dépréciées", len(df_resultats[df_resultats['Taux (%)'] > 0]))
                anciennes = df_resultats[df_resultats['Ancienneté (jours)'] > 365]
                if len(anciennes):
                    st.warning(f"{len(anciennes)} créance(s) de plus de 365 jours. La perte définitive (Débit 654 et 44571 "
                               "/ Crédit 411) ne se constate que si l'irrécouvrabilité est certaine (liquidation judiciaire "
                               "clôturée, jugement, accord de remise) ; la dépréciation est alors reprise (Débit 491 / Crédit 7817).")

                st.divider()
                st.markdown("### 📚 Écriture comptable")
                st.info(f"""
    **Dotation aux dépréciations :**
    - Débit **6817** (Dotations aux dépréciations des actifs circulants) : {nb_fr(total, 2)} €
    - Crédit **491** (Dépréciations des comptes clients) : {nb_fr(total, 2)} €
                """)

                bouton_sauvegarde(type_analyse="Dépréciation des créances", libelle="💾 Sauvegarder", key="save_prov_creances",
                                  resultat="\n".join(["# DÉPRÉCIATION DES CRÉANCES CLIENTS",
                                                      "*Calculée sur le montant HT ; taux indicatifs selon l'ancienneté.*", "",
                                                      tableau_markdown(df_resultats), "",
                                                      f"**Total des dépréciations** : {nb_fr(total, 2)} €", "",
                                                      f"- Débit 6817 (Dotations aux dépréciations des actifs circulants) : {nb_fr(total, 2)} €",
                                                      f"- Crédit 491 (Dépréciations des comptes clients) : {nb_fr(total, 2)} €"]
                                                     + ([f"", f"*{len(anciennes)} créance(s) de plus de 365 jours : perte "
                                                         "(654) à constater seulement si l'irrécouvrabilité est certaine.*"]
                                                        if len(anciennes) else [])))
        with sous_onglet2:
            st.markdown("#### 🛡 Provisions pour risques et charges")
            st.caption("Comptes 15x — PCG : une provision est constituée si une sortie de ressources est probable à la "
                       "clôture ; son montant est la meilleure estimation de cette sortie.")

            col1, col2 = st.columns(2)
            with col1:
                libelle_risque = st.text_input("📝 Nature du risque", placeholder="Ex: Litige fournisseur")
                montant_risque = st.number_input("💰 Meilleure estimation de la sortie de ressources (€)", min_value=0.0,
                                                 value=None, placeholder="ex. 5 000")
                probabilite = st.radio("📊 La sortie de ressources est-elle probable ?", PROBABILITES, index=None,
                                       horizontal=False)
            with col2:
                compte_prov = st.selectbox("📚 Compte de provision", [
                    "1511 — Provisions pour litiges",
                    "1512 — Provisions pour garanties données aux clients",
                    "1514 — Provisions pour amendes et pénalités",
                    "1518 — Autres provisions pour risques",
                    "153 — Provisions pour pensions et obligations similaires",
                    "154 — Provisions pour restructurations",
                    "155 — Provisions pour impôts",
                    "158 — Autres provisions pour charges"
                ])
                nature = st.selectbox("🏷 Nature de la charge", list(NATURES_PROVISION),
                                      format_func=lambda n: f"{n} ({NATURES_PROVISION[n]})")

            if st.button("🛡 Calculer la provision", type="primary", width="stretch", key="btn_prov_risque") and \
                    champs_remplis(**{"Nature du risque": libelle_risque, "Meilleure estimation": montant_risque,
                                      "Probabilité de la sortie de ressources": probabilite}):
                compte = compte_prov.split(" — ")[0]
                result = calculer_provision_risque(libelle_risque, montant_risque, probabilite, compte, nature)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Meilleure estimation", f"{nb_fr(montant_risque, 2)} €")
                with col2:
                    st.metric("⚠ Provision à constituer", f"{nb_fr(result['provision'], 2)} €")
                (st.success if result['provision'] else st.info)(result['conclusion'])
                if result['provision']:
                    st.markdown("### 📚 Écriture comptable")
                    st.dataframe(result['ecriture'], width="stretch", hide_index=True)

                rapport_risque = [f"# PROVISION POUR RISQUES ET CHARGES – {libelle_risque}", "",
                                  f"- **Meilleure estimation** : {nb_fr(montant_risque, 2)} €",
                                  f"- **Sortie de ressources** : {probabilite.lower()}",
                                  f"- **Provision à constituer** : {nb_fr(result['provision'], 2)} €", "",
                                  result['conclusion']]
                if result['provision']:
                    rapport_risque += ["", "## Écriture comptable", "", tableau_markdown(result['ecriture'])]
                bouton_sauvegarde(type_analyse="Provision pour risques", resultat="\n".join(rapport_risque),
                                  libelle="💾 Sauvegarder", key="save_prov_risque")

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

