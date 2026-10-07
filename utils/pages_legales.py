# -*- coding: utf-8 -*-
"""
Pages légales - SMD Global Consulting LLC
CGU et politique de confidentialité, accessibles sans connexion :
    ?doc=cgu   et   ?doc=confidentialite
Texte = projet du 07/10/2026 (document « CGU et politique de confidentialité »),
en attente de relecture juridique : les mentions entre crochets restent à valider.
"""
import streamlit as st

VERSION = "Projet du 07/10/2026, en cours de validation juridique"

CGU_MD = """
### Article 1 — Objet et acceptation

Les présentes conditions générales d'utilisation (« CGU ») régissent l'accès et l'utilisation du service en ligne « Superviseur IA Comptable » (le « Service »). Elles sont acceptées lors de la création du compte, par la case à cocher prévue à cet effet. Le Service est réservé aux professionnels agissant dans le cadre de leur activité ; il n'est pas destiné aux consommateurs.

### Article 2 — Éditeur

Le Service est édité par SMD Global Consulting LLC, société à responsabilité limitée de droit de l'État du Wyoming (États-Unis), identifiée auprès de l'administration fiscale américaine (IRS) sous le numéro EIN 30-1497639. Adresse de correspondance en France : 38 rue Christophe Colomb, Appt. 1878, 41000 Blois. Contact : contact@smdconsulting.pro. Directeur de la publication : Souleymane Diallo, gérant.

Hébergement de l'application : Streamlit Community Cloud (Snowflake Inc., États-Unis). Hébergement de la base de données : Supabase, région Union européenne (Irlande).

### Article 3 — Définitions

- **Utilisateur** : professionnel titulaire d'un compte.
- **Données de l'Utilisateur** : fichiers, balances, FEC, factures et informations que l'Utilisateur dépose ou saisit dans le Service, y compris celles de ses propres clients.
- **Analyse** : traitement décompté du quota mensuel de l'abonnement.
- **Fonction IA** : fonction dont le texte est rédigé par un modèle d'intelligence artificielle (Mistral AI).

### Article 4 — Description du Service

Le Service est un outil d'aide à l'analyse et à la supervision comptable selon le Plan comptable général français et le SYSCOHADA. Il comprend notamment : l'audit de balance, l'analyse de FEC, la loi de Benford, le bilan, le compte de résultat et les soldes intermédiaires de gestion, le tableau de flux de trésorerie, le plan de financement, l'aide à la TVA, la veille fiscale, ainsi que l'analyse et la comptabilisation de factures.

La comptabilisation des factures est calculée par des règles, sans intelligence artificielle. Les Fonctions IA sont signalées comme telles dans le Service. Un mode démonstration, sans sauvegarde, permet de découvrir le Service avec des données fictives.

### Article 5 — Compte

L'Utilisateur fournit des informations exactes lors de son inscription et les tient à jour. Il garde son mot de passe confidentiel et reste responsable de l'utilisation de son compte. Il informe sans délai l'Éditeur de toute utilisation non autorisée.

### Article 6 — Abonnements, prix et paiement

| Plan | Analyses par mois | Prix mensuel | Prix annuel |
| --- | --- | --- | --- |
| Gratuit | 10 | 0 € | 0 € |
| Starter | 50 | 29 € | 279 € |
| Pro | 200 | 79 € | 759 € |
| Entreprise | Illimité | 199 € | 1 909 € |

Les prix s'entendent hors taxes. Le Service étant fourni à des professionnels par une société établie hors de l'Union européenne, la TVA éventuellement due est autoliquidée par le client établi dans l'Union européenne [MÉCANISME À FAIRE VALIDER PAR UN CONSEIL FISCAL]. Le paiement est traité par Stripe ; l'Éditeur n'a jamais accès aux numéros de carte. L'abonnement se renouvelle automatiquement à chaque échéance. L'Utilisateur peut le résilier à tout moment depuis le portail Stripe ; la résiliation prend effet à la fin de la période en cours, sans remboursement de la période entamée. Le quota non utilisé n'est pas reporté au mois suivant. L'Éditeur peut modifier ses prix pour les périodes suivantes, en prévenant l'Utilisateur au moins 30 jours à l'avance.

### Article 7 — Obligations de l'Utilisateur

L'Utilisateur s'engage à :

- utiliser le Service conformément à la loi et à sa déontologie professionnelle ;
- ne déposer que des données qu'il est autorisé à traiter, et ne pas y inclure de données personnelles inutiles à l'analyse ;
- ne pas tenter de porter atteinte à la sécurité ou au fonctionnement du Service ;
- ne pas revendre ni mettre le Service à disposition de tiers sans accord écrit de l'Éditeur.

### Article 8 — Nature des résultats

Le Service est un outil d'aide à la décision. Il ne remplace ni l'expertise d'un expert-comptable, ni un conseil juridique ou fiscal. Les écritures, contrôles, ratios et analyses produits sont des propositions que l'Utilisateur doit vérifier avant toute utilisation, notamment avant import en comptabilité ou déclaration. Les textes rédigés par une Fonction IA peuvent contenir des erreurs. Les données lues par reconnaissance de caractères (OCR) sur des documents scannés ou photographiés doivent être comparées à l'original.

### Article 9 — Données des clients de l'Utilisateur

Pour les données personnelles contenues dans les Données de l'Utilisateur, l'Utilisateur est responsable de traitement et l'Éditeur agit comme sous-traitant au sens de l'article 28 du RGPD. Les conditions de cette sous-traitance figurent dans l'accord de sous-traitance annexé [ANNEXE À RÉDIGER]. Les fichiers déposés sont lus en mémoire et ne sont pas enregistrés ; seules les analyses que l'Utilisateur choisit de sauvegarder sont conservées, 30 jours au plus.

### Article 10 — Propriété intellectuelle

Le Service, son code, ses textes et ses règles d'analyse restent la propriété de l'Éditeur. L'Utilisateur dispose d'un droit d'utilisation personnel, non exclusif et non cessible, pour la durée de son abonnement. Les Données de l'Utilisateur et les résultats produits à partir d'elles restent sa propriété.

### Article 11 — Disponibilité

L'Éditeur s'efforce de rendre le Service accessible en continu, dans le cadre d'une obligation de moyens. Le Service peut être interrompu pour maintenance ou en cas d'indisponibilité de ses prestataires (hébergement, base de données, intelligence artificielle, paiement). Aucun niveau de disponibilité n'est garanti.

### Article 12 — Responsabilité

L'Éditeur n'est responsable que des dommages directs prouvés résultant d'une faute de sa part. Il n'est pas responsable des dommages indirects, notamment perte de chiffre d'affaires, de clientèle ou de données, ni des décisions prises par l'Utilisateur sur la base des résultats du Service. Sa responsabilité totale est limitée au montant le plus élevé entre les sommes payées par l'Utilisateur au cours des 12 derniers mois et 500 € [MONTANT MINIMUM À VALIDER AVEC L'AVOCAT ET L'ASSUREUR]. Cette limite ne s'applique pas en cas de faute lourde ou intentionnelle de l'Éditeur.

### Article 13 — Suspension et résiliation

L'Éditeur peut suspendre ou fermer un compte en cas de manquement grave aux présentes CGU, après mise en demeure restée sans effet pendant 15 jours, sauf urgence liée à la sécurité. L'Utilisateur peut demander la suppression de son compte à tout moment à contact@smdconsulting.pro.

### Article 14 — Modification des CGU

L'Éditeur peut modifier les CGU. L'Utilisateur est informé au moins 30 jours avant l'entrée en vigueur d'une modification importante ; s'il la refuse, il peut résilier son abonnement avant cette date.

### Article 15 — Droit applicable et litiges

Les CGU sont soumises au droit français. En cas de litige, les parties recherchent d'abord une solution amiable. À défaut, les tribunaux compétents du ressort de Blois sont seuls compétents.
"""

CONFIDENTIALITE_MD = """
### Article 1 — Responsable de traitement

SMD Global Consulting LLC (coordonnées à l'article 2 des CGU) est responsable du traitement des données de compte, de facturation et d'utilisation des Utilisateurs. Pour les données personnelles contenues dans les fichiers que l'Utilisateur dépose (par exemple celles de ses clients), l'Utilisateur est responsable de traitement et SMD Global Consulting LLC agit comme sous-traitant (CGU, article 9).

### Article 2 — Données collectées

| Catégorie | Données | Source |
| --- | --- | --- |
| Compte | E-mail, nom, prénom, cabinet, pays, plan, mot de passe chiffré (bcrypt), date de dernière connexion | Formulaire d'inscription |
| Facturation | Identifiants client et abonnement Stripe ; les numéros de carte sont traités par Stripe seul | Stripe |
| Utilisation | Nombre d'analyses du mois, type d'analyse, journal des actions (sauvegarde, suppression) | Service |
| Contenus | Fichiers déposés, lus en mémoire et non enregistrés ; analyses que l'Utilisateur choisit de sauvegarder | Utilisateur |

Le Service ne dépose aucun cookie publicitaire ni de mesure d'audience. Seuls les cookies techniques nécessaires au fonctionnement de la session sont utilisés.

### Article 3 — Finalités et bases légales

| Finalité | Base légale (RGPD art. 6) |
| --- | --- |
| Créer et gérer le compte, fournir le Service, décompter les quotas | Exécution du contrat |
| Facturer et encaisser les abonnements | Exécution du contrat |
| Conserver les pièces comptables et factures | Obligation légale (Code de commerce, art. L123-22) |
| Sécuriser le Service et tracer les actions sensibles | Intérêt légitime |

Aucune décision produisant des effets juridiques n'est prise de façon entièrement automatisée (RGPD art. 22) : les résultats du Service sont des propositions que l'Utilisateur valide.

### Article 4 — Durées de conservation

| Données | Durée |
| --- | --- |
| Fichiers déposés | Non conservés : lus en mémoire le temps de l'analyse |
| Analyses sauvegardées | 30 jours, puis suppression automatique |
| Compte | Durée de la relation, puis 3 ans après la dernière connexion |
| Journal des actions et décompte des quotas | 12 mois |
| Factures et données de facturation | 10 ans (obligation légale) |

### Article 5 — Destinataires et sous-traitants

Les données ne sont ni vendues ni louées. Elles sont accessibles à l'Éditeur et aux prestataires suivants, dans la limite de leur mission :

| Prestataire | Rôle | Localisation des données |
| --- | --- | --- |
| Supabase | Base de données (comptes, analyses sauvegardées, journal) | Union européenne (Irlande) |
| Streamlit Community Cloud (Snowflake Inc.) | Hébergement et exécution de l'application | Non publiée par le prestataire [À VÉRIFIER] |
| Mistral AI | Rédaction des textes des Fonctions IA ; reçoit les données utiles à l'analyse demandée, identifiants masqués (article 8) | France ; utilisation pour l'entraînement des modèles désactivée depuis le 07/10/2026 |
| Stripe | Paiement des abonnements | [À VÉRIFIER selon le contrat Stripe] |

### Article 6 — Transferts hors de l'Union européenne

Certains prestataires peuvent traiter des données hors de l'Union européenne, notamment aux États-Unis. Ces transferts sont encadrés par les garanties prévues par le RGPD (décision d'adéquation ou clauses contractuelles types de la Commission européenne) [GARANTIES À CONFIRMER PRESTATAIRE PAR PRESTATAIRE].

### Article 7 — Sécurité

Les mots de passe sont chiffrés (bcrypt) et jamais stockés en clair. Les échanges sont chiffrés (HTTPS). L'accès direct à la base de données est fermé au public ; seul le serveur de l'application y accède. Les fichiers déposés ne sont pas enregistrés.

### Article 8 — Intelligence artificielle

Les textes rédigés par l'IA (Mistral AI) sont signalés comme tels dans le Service, conformément à l'article 50 du règlement européen sur l'IA. Avant tout envoi à Mistral AI, les identifiants détectés (SIREN, SIRET, numéro de TVA, IBAN, adresses e-mail, numéros de téléphone, nom de l'entreprise saisi) sont remplacés par des repères, puis remis en clair dans la réponse sur le serveur de l'application. Il s'agit d'une pseudonymisation partielle : les montants et le texte libre, dont un nom de personne, sont transmis tels quels. La comptabilisation des factures est calculée par des règles, sans IA. L'Utilisateur est invité à ne pas transmettre de données personnelles inutiles aux Fonctions IA.

### Article 9 — Vos droits

Vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation, d'opposition et de portabilité de vos données. Pour les exercer, écrivez à contact@smdconsulting.pro ; une réponse vous est apportée dans un délai d'un mois. Vous pouvez aussi introduire une réclamation auprès de la CNIL (cnil.fr).

### Article 10 — Mise à jour

Cette politique peut être modifiée. La date de dernière mise à jour figure en tête du document ; les modifications importantes sont signalées aux Utilisateurs.
"""

DOCUMENTS = {
    "cgu": ("Conditions générales d'utilisation", CGU_MD),
    "confidentialite": ("Politique de confidentialité", CONFIDENTIALITE_MD),
}


def lien(doc: str, texte: str) -> str:
    """Lien markdown vers une page légale (ouverte dans un nouvel onglet)."""
    return f"[{texte}](?doc={doc})"


def afficher_document(doc: str):
    """Affiche une page légale. Retourne False si le document est inconnu."""
    if doc not in DOCUMENTS:
        return False
    titre, texte = DOCUMENTS[doc]
    st.title(titre)
    st.caption(f"Superviseur IA Comptable · SMD Global Consulting LLC · {VERSION}")
    st.markdown(texte)
    autre = "confidentialite" if doc == "cgu" else "cgu"
    st.divider()
    st.markdown(lien(autre, DOCUMENTS[autre][0]))
    return True
