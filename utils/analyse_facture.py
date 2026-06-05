# -*- coding: utf-8 -*-
"""Module Analyse de Facture Pro - SMD Global Consulting LLC"""
import re
from datetime import datetime
from utils.ai import appel_mistral
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


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
    
    rapport.append("*Rapport genere par SMD Global Consulting LLC - Superviseur IA Comptable*")
    
    return "\n".join(rapport)



def page_analyse_facture():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("🧾 Analyse de Facture")
    st.markdown("**OCR + IA** : Extraction structurée + Conformité + Comptabilisation")
    st.caption("✨ Pour Cabinets et Saisie comptable automatisée")

    # Initialisation état
    if 'fact_ocr' not in st.session_state:
        st.session_state.fact_ocr = None
    if 'fact_donnees' not in st.session_state:
        st.session_state.fact_donnees = None
    if 'fact_controles' not in st.session_state:
        st.session_state.fact_controles = None
    if 'fact_ecritures' not in st.session_state:
        st.session_state.fact_ecritures = None
    if 'fact_nom_fichier' not in st.session_state:
        st.session_state.fact_nom_fichier = None

    col1, col2 = st.columns([5, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "📎 Déposer une facture (PDF, PNG, JPG)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="facture_uploader"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄", help="Réinitialiser"):
            st.session_state.fact_ocr = None
            st.session_state.fact_donnees = None
            st.session_state.fact_controles = None
            st.session_state.fact_ecritures = None
            st.session_state.fact_nom_fichier = None
            st.rerun()

    if uploaded_file:
        # ✅ CORRECTION CACHE : Réinitialiser si nouveau fichier uploadé
        if st.session_state.get('fact_nom_fichier') != uploaded_file.name:
            st.session_state.fact_ocr = None
            st.session_state.fact_donnees = None
            st.session_state.fact_controles = None
            st.session_state.fact_ecritures = None
            st.session_state['fact_nom_fichier'] = uploaded_file.name

        # Étape 1 : OCR
        if st.session_state.fact_ocr is None:
            with st.spinner("🔍 Extraction OCR en cours..."):
                try:
                    texte, erreur = ocr_image_mistral(uploaded_file)
                    if erreur:
                        st.error(erreur)
                    elif texte:
                        st.session_state.fact_ocr = texte
                        # Pas de st.rerun() — Streamlit rerun automatiquement apres spinner
                    else:
                        st.error("❌ Impossible d'extraire le texte")
                except Exception as e:
                    st.error(f"❌ Erreur OCR : {e}")

        if st.session_state.fact_ocr:
            st.success("✅ Texte extrait avec succès !")

            with st.expander("📄 Texte brut extrait"):
                st.code(st.session_state.fact_ocr, language="text")

            st.divider()

            # Étape 2 : Analyse IA structurée
            if st.session_state.fact_donnees is None:
                if st.button("🤖 Analyser avec IA (extraction structurée)", type="primary", use_container_width=True):
                    with st.spinner("🤖 Analyse structurée en cours..."):
                        try:
                            from utils.analyse_facture import extraire_donnees_facture, verifier_conformite_facture, suggerer_comptabilisation

                            result = extraire_donnees_facture(st.session_state.fact_ocr)

                            if result.get('success'):
                                st.session_state.fact_donnees   = result['data']
                                st.session_state.fact_controles = verifier_conformite_facture(result['data'])
                                st.session_state.fact_ecritures = suggerer_comptabilisation(result['data'])
                                # Pas de st.rerun() — le bloc suivant lit session_state directement
                            else:
                                st.error(f"❌ Erreur analyse : {result.get('error')}")
                                if result.get('raw'):
                                    with st.expander("Réponse brute"):
                                        st.code(result['raw'])
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")
                            import traceback
                            with st.expander("Détails"):
                                st.code(traceback.format_exc())

            # Affichage des résultats
            if st.session_state.fact_donnees:
                donnees = st.session_state.fact_donnees

                st.markdown("## 📋 Données Extraites")

                # Informations générales
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🏢 Fournisseur")
                    fournisseur = donnees.get('fournisseur', {})
                    st.write(f"**Nom** : {fournisseur.get('nom', 'N/A')}")
                    st.write(f"**SIRET** : {fournisseur.get('siret', 'N/A')}")
                    st.write(f"**TVA Intra** : {fournisseur.get('tva_intra', 'N/A')}")
                    st.write(f"**Adresse** : {fournisseur.get('adresse', 'N/A')}")

                with col2:
                    st.markdown("### 👤 Client")
                    client = donnees.get('client', {})
                    st.write(f"**Nom** : {client.get('nom', 'N/A')}")
                    st.write(f"**Adresse** : {client.get('adresse', 'N/A')}")

                st.divider()

                # Facture
                st.markdown("### 📄 Facture")
                facture = donnees.get('facture', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("N°", facture.get('numero', 'N/A'))
                with col2:
                    st.metric("Date", facture.get('date', 'N/A'))
                with col3:
                    st.metric("Échéance", facture.get('echeance', 'N/A'))
                with col4:
                    st.metric("Paiement", facture.get('mode_paiement', 'N/A'))

                st.divider()

                # Montants
                st.markdown("### 💰 Montants")
                montants = donnees.get('montants', {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total HT", f"{float(montants.get('total_ht', 0)):,.2f} €")
                with col2:
                    st.metric(f"TVA ({montants.get('taux_tva', 20)}%)", f"{float(montants.get('total_tva', 0)):,.2f} €")
                with col3:
                    st.metric("Total TTC", f"{float(montants.get('total_ttc', 0)):,.2f} €")

                st.divider()

                # Conformité
                if st.session_state.fact_controles:
                    st.markdown("### ✅ Conformité Légale")
                    st.caption("*Article 242 nonies A du CGI*")

                    for ctrl in st.session_state.fact_controles:
                        if ctrl['statut'] == 'OK':
                            st.success(f"✅ {ctrl['mention']}")
                        elif ctrl['statut'] == 'WARNING':
                            st.warning(f"⚠ {ctrl['mention']}")
                        else:
                            st.error(f"❌ {ctrl['mention']}")

                st.divider()

                # Comptabilisation
                if st.session_state.fact_ecritures:
                    st.markdown("### 📚 Comptabilisation Suggérée")

                    import pandas as pd
                    df_ecritures = pd.DataFrame(st.session_state.fact_ecritures)
                    df_ecritures['debit'] = df_ecritures['debit'].apply(lambda x: f"{x:,.2f} €" if x > 0 else "")
                    df_ecritures['credit'] = df_ecritures['credit'].apply(lambda x: f"{x:,.2f} €" if x > 0 else "")
                    df_ecritures.columns = ['Compte', 'Libellé', 'Débit', 'Crédit']

                    st.dataframe(df_ecritures, use_container_width=True, hide_index=True)

                st.divider()

                # Export
                from utils.analyse_facture import generer_rapport_facture
                rapport = generer_rapport_facture(donnees, st.session_state.fact_controles, st.session_state.fact_ecritures)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True):
                        sauvegarder_si_autorise(type_analyse="Analyse Facture", resultat=rapport)
                        st.success("✅ Sauvegardé !")
                with col2:
                    try:
                        nom_fact = donnees.get('facture', {}).get('numero', 'inconnu')
                        generer_bouton_word(f"Facture_{nom_fact}", rapport)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # -----------------------------------------------------------------------------
    # 3. AUDIT BALANCE - VERSION UNIVERSELLE
    # -----------------------------------------------------------------------------

