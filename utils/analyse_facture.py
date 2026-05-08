# -*- coding: utf-8 -*-
"""Module Analyse de Facture Pro - SMD Consulting"""
import re
from datetime import datetime
from utils.ai import appel_mistral


def extraire_donnees_facture(texte):
    """
    Extrait les donnees structurees d'une facture
    
    Returns:
        dict: Donnees structurees
    """
    prompt = f"""Tu es un expert-comptable. Analyse cette facture et extrait les informations suivantes au format JSON strict.

Facture :
{texte}

Reponds UNIQUEMENT avec un JSON valide (pas de markdown, pas de commentaires) :
{{
  "fournisseur": {{
    "nom": "nom du fournisseur",
    "siret": "siret si present sinon vide",
    "adresse": "adresse",
    "tva_intra": "numero TVA intra si present"
  }},
  "client": {{
    "nom": "nom du client",
    "adresse": "adresse client"
  }},
  "facture": {{
    "numero": "numero de facture",
    "date": "date de facture format JJ/MM/AAAA",
    "echeance": "date echeance",
    "mode_paiement": "mode de paiement"
  }},
  "montants": {{
    "total_ht": 0.00,
    "total_tva": 0.00,
    "total_ttc": 0.00,
    "taux_tva": 20.0
  }},
  "lignes": [
    {{
      "description": "description article/service",
      "quantite": 1,
      "prix_unitaire": 0.00,
      "total_ht": 0.00
    }}
  ],
  "mentions_obligatoires": {{
    "siret_fournisseur": true,
    "tva_intra_fournisseur": true,
    "numero_facture": true,
    "date_facture": true,
    "mention_tva": true
  }},
  "type_charge_suggere": "compte 60x ou 61x ou 62x suggere selon nature"
}}"""
    
    result = appel_mistral(prompt, temperature=0.1)
    
    if result.get('success'):
        try:
            import json
            content = result['content']
            # Nettoyer si markdown
            if '```' in content:
                content = re.sub(r'```(?:json)?\n?', '', content)
                content = content.replace('```', '').strip()
            
            data = json.loads(content)
            return {'success': True, 'data': data}
        except Exception as e:
            return {'success': False, 'error': f'Parsing JSON: {e}', 'raw': result.get('content')}
    else:
        return {'success': False, 'error': result.get('error', 'Erreur API')}


def verifier_conformite_facture(donnees):
    """Verifie la conformite legale de la facture"""
    controles = []
    
    if not donnees:
        return controles
    
    fournisseur = donnees.get('fournisseur', {})
    facture = donnees.get('facture', {})
    montants = donnees.get('montants', {})
    
    # Mentions obligatoires (Article 242 nonies A du CGI)
    if fournisseur.get('siret'):
        controles.append({'statut': 'OK', 'mention': 'SIRET fournisseur present'})
    else:
        controles.append({'statut': 'KO', 'mention': 'SIRET fournisseur manquant'})
    
    if fournisseur.get('tva_intra'):
        controles.append({'statut': 'OK', 'mention': 'TVA intra fournisseur'})
    else:
        controles.append({'statut': 'WARNING', 'mention': 'TVA intra non verifiee'})
    
    if facture.get('numero'):
        controles.append({'statut': 'OK', 'mention': 'Numero de facture'})
    else:
        controles.append({'statut': 'KO', 'mention': 'Numero de facture manquant'})
    
    if facture.get('date'):
        controles.append({'statut': 'OK', 'mention': 'Date de facture'})
    else:
        controles.append({'statut': 'KO', 'mention': 'Date de facture manquante'})
    
    # Calculs
    if montants.get('total_ht') and montants.get('total_tva') and montants.get('total_ttc'):
        ht = float(montants['total_ht'])
        tva = float(montants['total_tva'])
        ttc = float(montants['total_ttc'])
        
        if abs((ht + tva) - ttc) < 0.02:
            controles.append({'statut': 'OK', 'mention': 'Coherence HT + TVA = TTC'})
        else:
            controles.append({'statut': 'KO', 'mention': f'Incoherence HT+TVA != TTC (ecart {abs((ht+tva)-ttc):.2f} EUR)'})
    
    return controles


def suggerer_comptabilisation(donnees):
    """Suggere une ecriture comptable"""
    if not donnees:
        return None
    
    montants = donnees.get('montants', {})
    type_charge = donnees.get('type_charge_suggere', '60')
    
    ht = float(montants.get('total_ht', 0))
    tva = float(montants.get('total_tva', 0))
    ttc = float(montants.get('total_ttc', 0))
    
    # Extraire le compte de charge suggere
    match = re.search(r'\d{2,7}', str(type_charge))
    compte_charge = match.group(0) if match else '606'
    
    # Construire l'ecriture
    ecritures = [
        {
            'compte': compte_charge,
            'libelle': f"Achats - {donnees.get('fournisseur', {}).get('nom', '')}",
            'debit': ht,
            'credit': 0
        },
        {
            'compte': '44566',
            'libelle': 'TVA deductible',
            'debit': tva,
            'credit': 0
        },
        {
            'compte': '401',
            'libelle': f"Fournisseur - {donnees.get('fournisseur', {}).get('nom', '')}",
            'debit': 0,
            'credit': ttc
        }
    ]
    
    return ecritures


def generer_rapport_facture(donnees, controles, ecritures):
    """Genere un rapport professionnel"""
    rapport = []
    rapport.append("# RAPPORT D'ANALYSE DE FACTURE")
    rapport.append(f"*Date analyse : {datetime.now().strftime('%d/%m/%Y %H:%M')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if donnees:
        rapport.append("## INFORMATIONS GENERALES")
        rapport.append("")
        
        fournisseur = donnees.get('fournisseur', {})
        client = donnees.get('client', {})
        facture = donnees.get('facture', {})
        montants = donnees.get('montants', {})
        
        rapport.append(f"### Fournisseur")
        rapport.append(f"- **Nom** : {fournisseur.get('nom', 'N/A')}")
        rapport.append(f"- **SIRET** : {fournisseur.get('siret', 'N/A')}")
        rapport.append(f"- **TVA Intra** : {fournisseur.get('tva_intra', 'N/A')}")
        rapport.append(f"- **Adresse** : {fournisseur.get('adresse', 'N/A')}")
        rapport.append("")
        
        rapport.append(f"### Client")
        rapport.append(f"- **Nom** : {client.get('nom', 'N/A')}")
        rapport.append(f"- **Adresse** : {client.get('adresse', 'N/A')}")
        rapport.append("")
        
        rapport.append(f"### Facture")
        rapport.append(f"- **Numero** : {facture.get('numero', 'N/A')}")
        rapport.append(f"- **Date** : {facture.get('date', 'N/A')}")
        rapport.append(f"- **Echeance** : {facture.get('echeance', 'N/A')}")
        rapport.append(f"- **Mode paiement** : {facture.get('mode_paiement', 'N/A')}")
        rapport.append("")
        
        rapport.append(f"### Montants")
        rapport.append(f"- **Total HT** : {montants.get('total_ht', 0):,.2f} EUR")
        rapport.append(f"- **TVA ({montants.get('taux_tva', 20)}%)** : {montants.get('total_tva', 0):,.2f} EUR")
        rapport.append(f"- **Total TTC** : {montants.get('total_ttc', 0):,.2f} EUR")
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    # Conformite
    if controles:
        rapport.append("## CONFORMITE LEGALE")
        rapport.append("*(Article 242 nonies A du CGI)*")
        rapport.append("")
        for ctrl in controles:
            symbol = '[OK]' if ctrl['statut'] == 'OK' else '[!]' if ctrl['statut'] == 'WARNING' else '[X]'
            rapport.append(f"- {symbol} {ctrl['mention']}")
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    # Comptabilisation
    if ecritures:
        rapport.append("## COMPTABILISATION SUGGEREE")
        rapport.append("")
        rapport.append("| Compte | Libelle | Debit | Credit |")
        rapport.append("|--------|---------|-------|--------|")
        for ecr in ecritures:
            rapport.append(f"| {ecr['compte']} | {ecr['libelle']} | {ecr['debit']:,.2f} | {ecr['credit']:,.2f} |")
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    rapport.append("*Rapport genere par SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)