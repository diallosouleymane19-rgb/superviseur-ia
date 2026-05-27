# -*- coding: utf-8 -*-
"""
Module Travaux d'Inventaire - SMD Consulting
Provisions, Régularisations, Stocks, Check-list clôture
"""
import pandas as pd
from datetime import datetime


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
        {'Compte': compte, 'Libellé': f'Provision — {libelle}', 'Débit': round(provision, 2), 'Crédit': 0},
        {'Compte': '6815', 'Libellé': f'Dotation provision — {libelle}', 'Débit': 0, 'Crédit': round(provision, 2)}
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
    charges_produits : liste de dicts avec type, libelle, montant_total, 
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

        # Calcul prorata
        duree_totale = (date_fin - date_debut).days
        duree_avant_cloture = (date_cloture - date_debut).days
        duree_apres_cloture = (date_fin - date_cloture).days

        if duree_totale > 0:
            montant_exercice = montant * duree_avant_cloture / duree_totale
            montant_regularise = montant * duree_apres_cloture / duree_totale
        else:
            montant_exercice = montant
            montant_regularise = 0

        if type_reg == "CCA":
            compte_regularisation = "486"
            libelle_compte = "Charges constatées d'avance"
            compte_contrepartie = "6xx"
        elif type_reg == "PCA":
            compte_regularisation = "487"
            libelle_compte = "Produits constatés d'avance"
            compte_contrepartie = "7xx"
        elif type_reg == "CAP":
            compte_regularisation = "408"
            libelle_compte = "Charges à payer"
            compte_contrepartie = "6xx"
        else:  # PAR
            compte_regularisation = "418"
            libelle_compte = "Produits à recevoir"
            compte_contrepartie = "7xx"

        resultats.append({
            'Type': type_reg,
            'Libellé': libelle,
            'Montant total (€)': round(montant, 2),
            'Part exercice (€)': round(montant_exercice, 2),
            'Montant régularisé (€)': round(montant_regularise, 2),
            'Compte': compte_regularisation,
            'Libellé compte': libelle_compte
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
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    return "\n".join(rapport)