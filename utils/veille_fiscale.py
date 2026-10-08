# -*- coding: utf-8 -*-
"""Module de veille fiscale enrichie - SMD Global Consulting LLC"""
import feedparser
from datetime import datetime, timedelta


def obtenir_veille_fiscale():
    """
    Récupère les actualités fiscales depuis multiples sources
    et fournit un contenu détaillé pour les comptables
    """
    actualites = []
    
    # Tentative de recuperation des flux RSS
    flux_rss = [
        ("https://www.economie.gouv.fr/rss/actualites.xml", "Bercy"),
        ("https://bofip.impots.gouv.fr/rss/bofip.xml", "BOFiP"),
    ]
    
    for url, source in flux_rss:
        try:
            feed = feedparser.parse(url)
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                for entry in feed.entries[:3]:
                    try:
                        article = {
                            'titre': str(entry.get('title', 'Sans titre')),
                            'resume': str(entry.get('summary', entry.get('description', ''))),
                            'lien': str(entry.get('link', '')),
                            'date': str(entry.get('published', 'Recent')),
                            'source': source
                        }
                        actualites.append(article)
                    except:
                        continue
        except:
            continue
    
    # Toujours ajouter du contenu enrichi pour les comptables
    contenu_enrichi = obtenir_contenu_enrichi()
    actualites.extend(contenu_enrichi)
    
    return actualites


# Date de la derniere verification des chiffres ci-dessous sur sources officielles
DATE_MAJ_DONNEES = "octobre 2026"

# Jours feries fixes (France metropolitaine). Les feries mobiles (Paques,
# Ascension, Pentecote) ne sont pas geres : verifier le calendrier officiel.
_FERIES_FIXES = {(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)}


def _jour_ouvre(d):
    """Décale une date au prochain jour ouvre (week-end et fériés fixes)."""
    from datetime import timedelta
    while d.weekday() >= 5 or (d.month, d.day) in _FERIES_FIXES:
        d += timedelta(days=1)
    return d


def _deuxieme_jour_ouvre_apres_1er_mai(annee):
    """Date légale de dépôt de la liasse IS (exercice clos le 31/12)."""
    from datetime import timedelta
    d = datetime(annee, 5, 1)
    compte = 0
    while compte < 2:
        d += timedelta(days=1)
        if d.weekday() < 5 and (d.month, d.day) not in _FERIES_FIXES:
            compte += 1
    return d


def calendrier_fiscal(annee):
    """
    Principales échéances fiscales des sociétés à l'IS pour l'année donnée.
    Retourne une liste de dicts : date (datetime), obligation, concerne.
    """
    from datetime import timedelta
    liasse = _deuxieme_jour_ouvre_apres_1er_mai(annee)
    j = lambda m, d: _jour_ouvre(datetime(annee, m, d))
    return [
        {"date": j(3, 15), "obligation": "Acompte IS n°1", "concerne": "Sociétés IS"},
        {"date": liasse, "obligation": f"Liasse fiscale IS, CA12, CVAE (1330) - exercice clos 31/12/{annee-1}", "concerne": "Sociétés IS"},
        {"date": j(5, 15), "obligation": f"Solde IS - exercice clos 31/12/{annee-1}", "concerne": "Sociétés IS"},
        {"date": liasse + timedelta(days=15), "obligation": "Liasse fiscale teledeclaree (délai supplémentaire 15 jours)", "concerne": "Sociétés IS"},
        {"date": j(6, 15), "obligation": "Acompte IS n°2 + acompte CFE (si CFE N-1 >= 3 000 EUR)", "concerne": "Sociétés IS"},
        {"date": j(9, 15), "obligation": "Acompte IS n°3", "concerne": "Sociétés IS"},
        {"date": j(12, 15), "obligation": "Acompte IS n°4 + solde CFE", "concerne": "Sociétés IS"},
    ]


def obtenir_contenu_enrichi():
    """Contenu fiscal détaillé et toujours disponible (vérifié : voir DATE_MAJ_DONNEES)"""

    aujourd_hui = datetime.now()
    date_str = aujourd_hui.strftime('%Y-%m-%d')

    # Echeances des 90 prochains jours, calculees (plus de mois fige)
    a_venir = [e for e in calendrier_fiscal(aujourd_hui.year) + calendrier_fiscal(aujourd_hui.year + 1)
               if 0 <= (e["date"] - aujourd_hui).days <= 90]
    lignes = "\n".join(f"- **{e['date'].strftime('%d/%m/%Y')}** : {e['obligation']}" for e in a_venir) \
        or "- Aucune échéance IS/CFE dans les 90 prochains jours."

    actualites = [
        {
            'titre': '[ÉCHÉANCES] Prochaines échéances (90 jours)',
            'date': date_str,
            'source': 'SMD Global Consulting LLC',
            'resume': f"""
**Échéances à venir :**

{lignes}

**Échéances mensuelles :**
- TVA CA3 (réel normal) : entre le 15 et le 24 de chaque mois selon l'entreprise
- DSN : le 5 du mois suivant (50 salariés et plus, paie dans le mois), le 15 pour les autres

**Pénalités en cas de retard :**
- Intérêt de retard : 0,20 % par mois
- Majoration de 10 % pour dépôt tardif (sauf régularisation)
- Majoration de 40 % en cas de manquement délibéré

**Conseil SMD :** Anticipez les déclarations et provisionnez les échéances pour éviter les pénalités.
            """,
            'lien': 'https://www.impots.gouv.fr'
        },
        {
            'titre': '[TVA] Facturation électronique - en vigueur depuis le 1er septembre 2026',
            'date': date_str,
            'source': 'DGFiP',
            'resume': """
**Calendrier de la réforme :**

- **1er septembre 2026** : réception obligatoire pour TOUTES les entreprises assujetties à la TVA
- **1er septembre 2026** : émission et e-reporting obligatoires pour les grandes entreprises et ETI
- **1er septembre 2027** : émission et e-reporting obligatoires pour les PME, TPE et micro-entreprises

**Plateformes :**
- Les factures circulent uniquement via des **Plateformes Agréées (PA)**, privées, immatriculées par l'administration (ex-PDP)
- Le **Portail Public de Facturation (PPF)** ne transmet plus de factures : il gère l'annuaire national et concentre les données pour l'administration
- La plateforme publique gratuite initialement prévue a été abandonnée

**Données à transmettre (e-reporting) :**
- Opérations B2B internationales
- Opérations B2C
- Statuts de paiement

**Conseil SMD :** Vérifiez que vos clients ont choisi une PA pour la réception ; préparez les PME à l'émission de 2027.
            """,
            'lien': 'https://www.impots.gouv.fr/professionnel/je-passe-la-facturation-electronique'
        },
        {
            'titre': '[IS] Taux Réduit IS 15% - Conditions 2026',
            'date': date_str,
            'source': 'CGI Article 219',
            'resume': """
**Taux réduit à 15 % sur les premiers 42 500 EUR de bénéfices** (non modifié par la loi de finances 2026) :

**Conditions à remplir :**
1. Chiffre d'affaires HT < 10 millions EUR
2. Capital entièrement libéré
3. Capital détenu pour 75 % au moins par des personnes physiques (ou sociétés remplissant les mêmes conditions)

**Application :**
- Tranche de bénéfice 0 - 42 500 EUR : taux 15 %
- Au-delà de 42 500 EUR : taux normal 25 %

**Exemple concret :**
- Bénéfice de 60 000 EUR
- IS = (42 500 x 15 %) + (17 500 x 25 %) = 6 375 + 4 375 = 10 750 EUR
- Économie vs taux plein : 4 250 EUR

**Conseil SMD :** Optimisez la structure capitalistique pour bénéficier du taux réduit.
            """,
            'lien': 'https://bofip.impots.gouv.fr'
        },
        {
            'titre': '[CONTRÔLE FISCAL] Points de vigilance (avis SMD)',
            'date': date_str,
            'source': 'SMD Global Consulting LLC',
            'resume': """
**Points de vigilance recommandes :**

1. **TVA et facturation électronique**
   - Conformité des flux via Plateforme Agréée
   - Cohérence factures émises / déclarations CA3
   - Auto-liquidation TVA

2. **Prix de transfert (groupes internationaux)**
   - Documentation des transactions intra-groupe

3. **Charges déductibles**
   - Frais de représentation et réception
   - Véhicules de fonction
   - Rémunérations dirigeants

4. **CIR / CII (Crédit Impôt Recherche / Innovation)**
   - Justification scientifique des projets
   - Éligibilité des dépenses

5. **Cryptomonnaies et actifs numériques**
   - Déclaration des comptes détenus à l'étranger
   - Plus-values de cessions

**Conseil SMD :** Constituer un dossier de défense fiscale pour chaque exercice (justificatifs, méthodes, calculs).
            """,
            'lien': 'https://www.impots.gouv.fr'
        },
        {
            'titre': '[SOCIAL] Charges Sociales 2026 - Taux et Plafonds',
            'date': date_str,
            'source': 'URSSAF / CLEISS',
            'resume': """
**Plafonds et SMIC 2026 :**

- PMSS (Plafond Mensuel) : 4 005 EUR
- PASS (Plafond Annuel) : 48 060 EUR
- SMIC horaire brut : 12,31 EUR (depuis le 1er juin 2026 ; 12,02 EUR du 1er janvier au 31 mai)
- SMIC mensuel brut (35h) : 1 867,02 EUR (depuis le 1er juin 2026)

**Cotisations principales au 1er janvier 2026 (taux salarial / patronal) :**

| Cotisation | Salarial | Patronal |
|-----------|----------|----------|
| Maladie | 0 % | 13 % (ou 7 %) |
| Vieillesse plafonnée | 6,90 % | 8,55 % |
| Vieillesse déplafonnée | 0,40 % | 2,11 % |
| Famille | 0 % | 5,25 % (ou 3,45 %) |
| AT/MP | 0 % | Variable |
| Chômage | 0 % | 4,00 % |
| AGS | 0 % | 0,25 % |
| Retraite complémentaire | Variable | Variable |
| CSG / CRDS | 9,20 % + 0,50 % (sur 98,25 % du brut) | 0 % |

**Réductions :**
- Réduction générale dégressive unique (RGDU) depuis le 1er janvier 2026 : jusqu'à 3 SMIC (remplace la réduction Fillon)
- Aides à l'embauche : selon dispositifs

**Conseil SMD :** revue annuelle des charges sociales pour optimiser les exonérations applicables.
            """,
            'lien': 'https://www.urssaf.fr'
        }
    ]

    return actualites



def page_veille_fiscale():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
    bouton_sauvegarde,
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📰 Veille Fiscale")
    st.markdown("**Actualités fiscales officielles** — France")
    st.caption("✨ Sources : DGFiP, BOFiP, Légifrance")

    onglet1, onglet2 = st.tabs([
        "🇫🇷 Fiscalité France",
        "❓ Question Fiscale IA"
    ])

    with onglet1:
        st.markdown("### 📡 Sources Officielles Françaises")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**DGFiP**\nDirection Générale des Finances Publiques")
            st.markdown("[🔗 impots.gouv.fr](https://www.impots.gouv.fr)")
        with col2:
            st.info("**BOFiP**\nBulletin Officiel des Finances Publiques")
            st.markdown("[🔗 bofip.impots.gouv.fr](https://bofip.impots.gouv.fr)")
        with col3:
            st.info("**Légifrance**\nTextes législatifs et réglementaires")
            st.markdown("[🔗 legifrance.gouv.fr](https://www.legifrance.gouv.fr)")

        st.divider()

        # La liste et les analyses IA sont gardées en mémoire de session : un clic sur « Analyser avec IA »
        # recharge la page, et sans cela la liste disparaissait avant que l'analyse ne s'affiche.
        if st.button("🔄 Actualiser la veille France", type="primary", width="stretch"):
            with st.spinner("Récupération des actualités fiscales françaises..."):
                try:
                    st.session_state["veille_fr"] = obtenir_veille_fiscale() or []
                    st.session_state["veille_fr_ia"] = {}
                except Exception as e:
                    st.session_state.pop("veille_fr", None)
                    st.error(f"❌ Erreur de récupération : {str(e)}")

        actualites = st.session_state.get("veille_fr")
        if actualites is not None:
            analyses_ia = st.session_state.setdefault("veille_fr_ia", {})
            if len(actualites) > 0:
                st.success(f"✅ {len(actualites)} actualité(s) récupérée(s)")
                for idx, article in enumerate(actualites):
                    if not isinstance(article, dict):
                        continue
                    titre = article.get('titre', 'Sans titre')
                    date = article.get('date', 'Date inconnue')
                    resume = article.get('resume', '')
                    lien = article.get('lien', '')
                    source = article.get('source', 'Source officielle')

                    with st.expander(f"📄 {titre}", expanded=idx in analyses_ia):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.caption(f"🗓 {date} | 📡 {source}")
                        with col2:
                            if lien:
                                st.markdown(f"[🔗 Article complet]({lien})")
                        if resume:
                            st.markdown(resume)

                        if st.button("🤖 Analyser avec IA", key=f"ia_{idx}"):
                            with st.spinner("Analyse IA..."):
                                prompt = f"""En tant qu'expert fiscal français, analyse cette actualité :

    Titre : {titre}
    Résumé : {resume}

    Fournis :
    1. Impact pour les TPE/PME françaises
    2. Actions à entreprendre
    3. Délais à respecter
    4. Références légales (CGI, BOFiP)"""
                                analyses_ia[idx] = appel_mistral_securise(prompt, temperature=0.2, label="analyse fiscale")
                        result = analyses_ia.get(idx)
                        if result and result.get("success"):
                            st.markdown("#### 🤖 Analyse IA")
                            from utils.page_helpers import afficher_contenu_ia
                            afficher_contenu_ia(result["content"], f"veille_{idx}", result.get("model", ""),
                                                result.get("masques", 0))
                        elif result:
                            st.error(f"❌ {result.get('error') or 'Analyse IA indisponible.'}")

                bouton_sauvegarde(type_analyse="Veille Fiscale France", resultat=str(actualites),
                                  libelle="💾 Sauvegarder la veille")
            else:
                st.info("ℹ Aucune actualité récente. Consultez directement les sources officielles.")

    with onglet2:
        st.markdown("### 🤖 Posez votre question fiscale à l'IA")
        st.caption("Fiscalité française — CGI, BOFiP, LPF")

        question = st.text_area(
            "📝 Votre question",
            placeholder="Ex: Quel est le taux de TVA applicable aux prestations de services ?",
            height=120
        )

        if st.button("🤖 Obtenir une réponse IA", type="primary", width="stretch") and question:
            with st.spinner("Analyse fiscale en cours..."):
                prompt = f"""En tant qu'expert en fiscalité française (CGI, BOFiP, LPF), réponds à cette question professionnelle :

    {question}

    Structure ta réponse ainsi :
    1. **Réponse directe et précise**
    2. **Références légales** (articles CGI, BOFiP)
    3. **Exemple chiffré** si pertinent
    4. **Points d'attention** et risques à éviter
    5. **Recommandation cabinet**"""

                result = appel_mistral_securise(prompt, temperature=0.2, label="question fiscale")

                if result["success"]:
                    st.markdown("### 🤖 Réponse IA")
                    from utils.page_helpers import afficher_contenu_ia, avec_mention_ia, meta_ia
                    afficher_contenu_ia(result["content"], "question_fiscale", result.get("model", ""),
                                        result.get("masques", 0))

                    col1, col2 = st.columns(2)
                    with col1:
                        bouton_sauvegarde(type_analyse="Question Fiscale IA", resultat=avec_mention_ia(result["content"]), libelle="💾 Sauvegarder")
                    with col2:
                        try:
                            generer_bouton_word("Reponse_Fiscale", avec_mention_ia(result["content"]),
                                               ia=meta_ia(result.get("model", "")))
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                    st.caption("⚠ Réponse à titre informatif. Consultez un expert pour validation.")


    # -----------------------------------------------------------------------------
    # 13. CONNECTEURS ERP
    # -----------------------------------------------------------------------------

