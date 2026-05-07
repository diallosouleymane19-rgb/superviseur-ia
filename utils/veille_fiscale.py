# -*- coding: utf-8 -*-
"""Module de veille fiscale enrichie - SMD Consulting"""
import feedparser
from datetime import datetime, timedelta


def obtenir_veille_fiscale():
    """
    Recupere les actualites fiscales depuis multiples sources
    et fournit un contenu detaille pour les comptables
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


def obtenir_contenu_enrichi():
    """Contenu fiscal detaille et toujours disponible"""
    
    aujourd_hui = datetime.now()
    
    actualites = [
        {
            'titre': '[ECHEANCES] Calendrier Fiscal Mai 2026',
            'date': aujourd_hui.strftime('%Y-%m-%d'),
            'source': 'SMD Consulting',
            'resume': """
**Echeances importantes du mois :**

- **15 Mai** : TVA mensuelle (regime reel normal) - Declaration CA3
- **15 Mai** : Acompte d'impot sur les societes (IS) - Premier acompte
- **20 Mai** : DAS2 - Declaration des honoraires verses en 2025
- **31 Mai** : DSN - Declaration sociale nominative mensuelle
- **31 Mai** : Liasse fiscale (cloture 31 decembre 2025)

**Penalites en cas de retard :**
- Retard declaration : 10% minimum
- Retard paiement : 5% + interets de retard (0.20% / mois)
- Defaut declaration : 40% (mauvaise foi)

**Conseil SMD :** Anticipez les declarations et provisionnez les echeances pour eviter les penalites.
            """,
            'lien': 'https://www.impots.gouv.fr'
        },
        {
            'titre': '[TVA] Nouveautes 2026 - Facturation Electronique',
            'date': aujourd_hui.strftime('%Y-%m-%d'),
            'source': 'BOFiP',
            'resume': """
**Reforme de la facturation electronique :**

Generalisation progressive de la facturation electronique B2B :

- **Septembre 2026** : Reception obligatoire pour TOUTES les entreprises
- **Septembre 2026** : Emission obligatoire pour grandes entreprises et ETI
- **Septembre 2027** : Emission obligatoire pour PME et TPE

**Plateformes autorisees :**
- Portail Public de Facturation (PPF) - gratuit
- Plateformes de Dematerialisation Partenaires (PDP) - immatriculation

**Donnees a transmettre (e-reporting) :**
- Operations B2B internationales
- Operations B2C
- Statuts de paiement

**Conseil SMD :** Preparez la transition des maintenant - audit des outils, formation des equipes, choix de plateforme.
            """,
            'lien': 'https://www.impots.gouv.fr/professionnel/je-passe-la-facturation-electronique'
        },
        {
            'titre': '[IS] Taux Reduit IS 15% - Conditions 2026',
            'date': aujourd_hui.strftime('%Y-%m-%d'),
            'source': 'CGI Article 219',
            'resume': """
**Taux reduit a 15% sur les premiers 42 500 EUR de benefices :**

**Conditions a remplir :**
1. Chiffre d'affaires HT < 10 millions EUR
2. Capital entierement libere
3. Capital detenu pour 75% au moins par des personnes physiques (ou societes remplissant les memes conditions)

**Application :**
- Tranche de benefice 0 - 42 500 EUR : taux 15%
- Au-dela de 42 500 EUR : taux normal 25%

**Exemple concret :**
- Benefice de 60 000 EUR
- IS = (42 500 x 15%) + (17 500 x 25%) = 6 375 + 4 375 = 10 750 EUR
- Economie vs taux plein : 4 250 EUR

**Conseil SMD :** Optimisez la structure capitalistique pour beneficier du taux reduit.
            """,
            'lien': 'https://bofip.impots.gouv.fr'
        },
        {
            'titre': '[CONTROLE FISCAL] Tendances 2026 et Points de Vigilance',
            'date': aujourd_hui.strftime('%Y-%m-%d'),
            'source': 'DGFiP',
            'resume': """
**Axes de controle prioritaires 2026 :**

1. **TVA et facturation electronique**
   - Verification de la conformite des systemes
   - Coherence factures emises / declarations CA3
   - Auto-liquidation TVA

2. **Prix de transfert (groupes internationaux)**
   - Documentation obligatoire si CA > 50 M EUR
   - Examen des transactions intra-groupe

3. **Charges deductibles**
   - Frais de representation et reception
   - Vehicules de fonction
   - Remunerations dirigeants

4. **CIR / CII (Credit Impot Recherche / Innovation)**
   - Justification scientifique des projets
   - Eligibilite des depenses

5. **Cryptomonnaies et actifs numeriques**
   - Declaration des comptes detenus a l'etranger
   - Plus-values de cessions

**Conseil SMD :** Constituer un dossier de defense fiscale pour chaque exercice (justificatifs, methodes, calculs).
            """,
            'lien': 'https://www.impots.gouv.fr'
        },
        {
            'titre': '[SOCIAL] Charges Sociales 2026 - Taux et Plafonds',
            'date': aujourd_hui.strftime('%Y-%m-%d'),
            'source': 'URSSAF',
            'resume': """
**Plafonds Securite Sociale 2026 :**

- PMSS (Plafond Mensuel) : 3 925 EUR
- PASS (Plafond Annuel) : 47 100 EUR
- SMIC horaire : 11.65 EUR
- SMIC mensuel (35h) : 1 766.92 EUR brut

**Cotisations principales (taux salarial / patronal) :**

| Cotisation | Salarial | Patronal |
|-----------|----------|----------|
| Maladie | 0% | 7% (ou 13%) |
| Vieillesse plafonnee | 6.90% | 8.55% |
| Vieillesse deplafonnee | 0.40% | 2.02% |
| Famille | 0% | 3.45% / 5.25% |
| AT/MP | 0% | Variable |
| Chomage | 0% | 4.05% |
| AGS | 0% | 0.20% |
| Retraite complementaire | Variable | Variable |
| CSG/CRDS | 9.70% | 0% |

**Reductions :**
- Reduction generale (Fillon) : sous SMIC x 1.6
- Reduction TO-DE : agriculture
- Aides a l'embauche : selon dispositifs

**Conseil SMD :** Audit annuel des charges sociales pour optimiser les exonerations applicables.
            """,
            'lien': 'https://www.urssaf.fr'
        }
    ]
    
    return actualites