# -*- coding: utf-8 -*-
"""
smd_mcp_server.py
=================
Serveur MCP (Model Context Protocol) - SMD Consulting
Plugin Claude Cowork | Comptable Augmente

5 Skills :
  1. analyse_facture     - OCR + suggestion compte PCG
  2. verification_tva    - Controle taux TVA applicable
  3. export_fec          - Generation fichier FEC DGFiP
  4. veille_fiscale      - Resume alertes fiscales RSS
  5. syscohada_analyse   - Analyse comptable SYSCOHADA/OHADA

Installation :
  pip install mcp requests feedparser

Lancement :
  py smd_mcp_server.py
"""

import json
import csv
import io
import os
import requests
import feedparser
from datetime import datetime, date
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

# --- Initialisation du serveur MCP -------------------------------------------

app = Server("smd-consulting")

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

def appel_mistral(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
    """Appel centralise a l'API Mistral avec gestion d'erreurs."""
    if not MISTRAL_API_KEY:
        return "ERREUR: Cle API Mistral manquante. Definissez MISTRAL_API_KEY en variable d'environnement."
    try:
        response = requests.post(
            MISTRAL_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MISTRAL_API_KEY}"
            },
            json={
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERREUR Mistral : {str(e)}"


# --- Referentiels comptables --------------------------------------------------

TAUX_TVA_FRANCE = {
    "20": "Taux normal - biens et services courants",
    "10": "Taux intermediaire - restauration, travaux, transports",
    "5.5": "Taux reduit - alimentation, livres, energie",
    "2.1": "Taux super-reduit - medicaments remboursables, presse",
    "0": "Exonere - exports, intracommunautaire sous conditions"
}

COMPTES_PCG_COURANTS = {
    "fournisseur": "401", "client": "411", "banque": "512",
    "caisse": "531", "tva collectee": "44571", "tva deductible": "44566",
    "salaires": "641", "charges sociales": "645", "loyer": "613",
    "telephone": "626", "electricite": "606", "fournitures": "606",
    "materiel": "215", "logiciel": "205", "honoraires": "622",
    "publicite": "623", "frais deplacement": "625", "assurance": "616",
    "amortissement": "681", "resultat": "120", "capital": "101"
}

COMPTES_SYSCOHADA_COURANTS = {
    "fournisseur": "401", "client": "411", "banque": "521",
    "caisse": "571", "tva collectee": "4431", "tva deductible": "4451",
    "salaires": "661", "charges sociales": "664", "loyer": "622",
    "materiel": "244", "logiciel": "221", "honoraires": "632",
    "publicite": "627", "frais deplacement": "625", "assurance": "616",
    "amortissement": "681", "resultat": "131", "capital": "101"
}


# --- SKILL 1 : Analyse de facture --------------------------------------------

@app.call_tool()
async def analyse_facture(name: str, arguments: dict) -> list[types.TextContent]:
    """Analyse une facture et suggere le compte PCG ou SYSCOHADA."""
    contenu = arguments.get("contenu_facture", "")
    referentiel = arguments.get("referentiel", "PCG")

    if not contenu:
        return [types.TextContent(type="text", text="ERREUR: Veuillez fournir le contenu de la facture.")]

    comptes = COMPTES_SYSCOHADA_COURANTS if referentiel == "SYSCOHADA" else COMPTES_PCG_COURANTS
    comptes_str = json.dumps(comptes, ensure_ascii=False, indent=2)

    system_prompt = f"Tu es expert-comptable {referentiel}. Comptes disponibles : {comptes_str}"

    user_prompt = f"""Analyse cette facture et fournis l'imputation comptable.

FACTURE :
{contenu}

Format de reponse :

=== ANALYSE DE FACTURE ===
Fournisseur : [nom]
Date : [date]
Montant HT : [montant]
TVA : [taux% - montant]
Montant TTC : [montant]
Nature : [description]

IMPUTATION {referentiel} :
Debit  -> Compte [N] - [Libelle] : [Montant]
Credit -> Compte [N] - [Libelle] : [Montant]

Points d attention : [anomalies]
Statut : [Valide / A verifier / Anomalie]"""

    resultat = appel_mistral(system_prompt, user_prompt, max_tokens=600)
    return [types.TextContent(type="text", text=resultat)]


# --- SKILL 2 : Verification TVA ----------------------------------------------

@app.call_tool()
async def verification_tva(name: str, arguments: dict) -> list[types.TextContent]:
    """Verifie le taux de TVA applicable pour un produit ou service."""
    description = arguments.get("description", "")
    montant_ht = arguments.get("montant_ht", 0)
    taux_applique = str(arguments.get("taux_applique", ""))

    if not description:
        return [types.TextContent(type="text", text="ERREUR: Veuillez decrire le produit ou service.")]

    taux_str = json.dumps(TAUX_TVA_FRANCE, ensure_ascii=False, indent=2)

    system_prompt = "Tu es expert en fiscalite francaise, specialise dans les taux de TVA."

    user_prompt = f"""Verifie le taux de TVA pour ce produit/service.

Description : {description}
Montant HT : {montant_ht} euros
Taux applique : {taux_applique}%

Taux TVA France :
{taux_str}

Format de reponse :

=== VERIFICATION TVA ===
Produit/Service : {description}
Taux correct : [X%]
Justification : [base legale]
Calcul correct :
  - HT : {montant_ht} euros
  - TVA ([X]%) : [montant] euros
  - TTC : [montant] euros
Ecart detecte : [oui/non - details]
Action recommandee : [correction si necessaire]"""

    resultat = appel_mistral(system_prompt, user_prompt, max_tokens=400)
    return [types.TextContent(type="text", text=resultat)]


# --- SKILL 3 : Export FEC DGFiP ----------------------------------------------

@app.call_tool()
async def export_fec(name: str, arguments: dict) -> list[types.TextContent]:
    """Genere un fichier FEC conforme a l article A47 A-1 LPF."""
    ecritures_json = arguments.get("ecritures", "[]")
    siren = arguments.get("siren", "000000000")
    exercice = arguments.get("exercice", str(date.today().year))
    nom_entreprise = arguments.get("nom_entreprise", "ENTREPRISE")

    try:
        ecritures = json.loads(ecritures_json) if isinstance(ecritures_json, str) else ecritures_json
    except json.JSONDecodeError:
        return [types.TextContent(type="text", text="ERREUR: Format JSON invalide pour les ecritures.")]

    champs_fec = [
        "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
        "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib",
        "PieceRef", "PieceDate", "EcritureLib",
        "Debit", "Credit", "EcritureLet", "DateLet",
        "ValidDate", "Montantdevise", "Idevise"
    ]

    output = io.StringIO()
    writer = csv.writer(output, delimiter="|", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(champs_fec)

    num_ecriture = 1
    erreurs = []

    for i, e in enumerate(ecritures):
        try:
            date_str = str(e.get("date", "")).replace("-", "").replace("/", "")
            date_fec = date_str if len(date_str) == 8 else datetime.today().strftime("%Y%m%d")
            writer.writerow([
                e.get("journal_code", "OD"),
                e.get("journal_lib", "Operations diverses"),
                f"EC{str(num_ecriture).zfill(6)}",
                date_fec,
                e.get("compte_num", ""),
                e.get("compte_lib", e.get("libelle", "")),
                e.get("compte_aux_num", ""),
                e.get("compte_aux_lib", ""),
                e.get("piece_ref", f"PC{str(num_ecriture).zfill(4)}"),
                date_fec,
                e.get("libelle", ""),
                f"{float(e.get('debit', 0)):.2f}".replace(".", ","),
                f"{float(e.get('credit', 0)):.2f}".replace(".", ","),
                "", "", datetime.today().strftime("%Y%m%d"), "", ""
            ])
            num_ecriture += 1
        except Exception as ex:
            erreurs.append(f"Ecriture {i+1} : {str(ex)}")

    contenu_fec = output.getvalue()
    nom_fichier = f"{siren}FEC{exercice}.txt"

    rapport = f"""=== EXPORT FEC DGFIP ===
Entreprise : {nom_entreprise}
SIREN : {siren}
Exercice : {exercice}
Fichier : {nom_fichier}
Ecritures generees : {num_ecriture - 1}
Erreurs : {len(erreurs) if erreurs else "Aucune"}

--- CONTENU FEC (Article A47 A-1 LPF) ---
{contenu_fec}
{"--- ERREURS ---" + chr(10) + chr(10).join(erreurs) if erreurs else ""}

NOTE: Copiez le contenu ci-dessus dans un fichier nomme {nom_fichier}
Encodage : UTF-8 | Separateur : pipe (|)"""

    return [types.TextContent(type="text", text=rapport)]


# --- SKILL 4 : Veille fiscale ------------------------------------------------

@app.call_tool()
async def veille_fiscale(name: str, arguments: dict) -> list[types.TextContent]:
    """Recupere et resume les dernieres actualites fiscales francaises."""
    nb_articles = arguments.get("nb_articles", 5)
    theme = arguments.get("theme", "tous")

    flux_rss = [
        "https://www.compta-online.com/flux-rss.php",
        "https://www.lesechos.fr/rss/rss_finance.xml",
        "https://www.lemonde.fr/economie/rss_full.xml"
    ]

    articles_collectes = []
    mots_fiscaux = ["tva", "impot", "taxe", "fiscal", "urssaf", "cotisation",
                    "declaration", "dgfip", "comptable", "fec", "bilan", "liasse"]

    for url in flux_rss:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:nb_articles]:
                titre = entry.get("title", "")
                description = entry.get("summary", "")[:500]
                if any(mot in (titre + description).lower() for mot in mots_fiscaux):
                    articles_collectes.append({
                        "titre": titre,
                        "description": description,
                        "lien": entry.get("link", "")
                    })
            if len(articles_collectes) >= nb_articles:
                break
        except Exception:
            continue

    if not articles_collectes:
        return [types.TextContent(type="text", text="AVERTISSEMENT: Aucune actualite fiscale trouvee. Verifiez votre connexion.")]

    system_prompt = "Tu es expert-comptable specialise en veille fiscale francaise (PCG, DGFiP, URSSAF)."

    user_prompt = f"""Resume ces actualites fiscales. Theme : {theme}

{json.dumps(articles_collectes[:nb_articles], ensure_ascii=False, indent=2)}

Format par article :

=== VEILLE FISCALE SMD CONSULTING - {datetime.today().strftime("%d/%m/%Y")} ===

[Pour chaque article :]
TITRE : [titre]
Impact : ELEVE / MOYEN / FAIBLE
Concerne : [qui est concerne]
En bref : [2-3 lignes]
Echeance : [si mentionnee]
Action : [1 action concrete]
Source : [lien]
---"""

    resultat = appel_mistral(system_prompt, user_prompt, max_tokens=800)
    return [types.TextContent(type="text", text=resultat)]


# --- SKILL 5 : Analyse SYSCOHADA ---------------------------------------------

@app.call_tool()
async def syscohada_analyse(name: str, arguments: dict) -> list[types.TextContent]:
    """Analyse comptable selon le referentiel SYSCOHADA/OHADA."""
    type_analyse = arguments.get("type_analyse", "imputation")
    contenu = arguments.get("contenu", "")
    pays = arguments.get("pays", "Senegal")

    if not contenu:
        return [types.TextContent(type="text", text="ERREUR: Veuillez fournir le contenu a analyser.")]

    comptes_str = json.dumps(COMPTES_SYSCOHADA_COURANTS, ensure_ascii=False, indent=2)

    system_prompt = f"""Tu es expert-comptable certifie SYSCOHADA/OHADA.
Pays : {pays}
Comptes SYSCOHADA : {comptes_str}
Divergences PCG/SYSCOHADA :
- Banque : 521 (vs 512 PCG)
- Caisse : 571 (vs 531 PCG)
- TVA collectee : 4431 (vs 44571 PCG)
- TVA deductible : 4451 (vs 44566 PCG)
- Salaires : 661 (vs 641 PCG)
- Charges sociales : 664 (vs 645 PCG)"""

    user_prompt = f"""Analyse ({type_analyse}) pour {pays} :

{contenu}

Format de reponse :

=== ANALYSE SYSCOHADA - {pays} ===
Nature : [description]
Montant : [montant en FCFA ou devise locale]

IMPUTATION SYSCOHADA :
Debit  -> Compte [N] - [Libelle] : [Montant]
Credit -> Compte [N] - [Libelle] : [Montant]

Equivalent PCG France : [comptes equivalents]
Particularites OHADA : [specificites]
Validation : [Conforme / A verifier]"""

    resultat = appel_mistral(system_prompt, user_prompt, max_tokens=700)
    return [types.TextContent(type="text", text=resultat)]


# --- Declaration des outils --------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="analyse_facture",
            description="Analyse une facture et propose l imputation comptable PCG France ou SYSCOHADA Afrique",
            inputSchema={
                "type": "object",
                "properties": {
                    "contenu_facture": {"type": "string", "description": "Texte extrait de la facture"},
                    "referentiel": {"type": "string", "enum": ["PCG", "SYSCOHADA"], "default": "PCG"}
                },
                "required": ["contenu_facture"]
            }
        ),
        types.Tool(
            name="verification_tva",
            description="Verifie le taux de TVA applicable pour un produit ou service en France",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Produit ou service"},
                    "montant_ht": {"type": "number", "description": "Montant HT en euros"},
                    "taux_applique": {"type": "number", "description": "Taux TVA applique"}
                },
                "required": ["description"]
            }
        ),
        types.Tool(
            name="export_fec",
            description="Genere un FEC conforme Article A47 A-1 LPF pour la DGFiP",
            inputSchema={
                "type": "object",
                "properties": {
                    "ecritures": {"type": "string", "description": "JSON des ecritures comptables"},
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                    "exercice": {"type": "string", "description": "Annee exercice"},
                    "nom_entreprise": {"type": "string", "description": "Denomination sociale"}
                },
                "required": ["ecritures"]
            }
        ),
        types.Tool(
            name="veille_fiscale",
            description="Recupere et resume les actualites fiscales francaises",
            inputSchema={
                "type": "object",
                "properties": {
                    "nb_articles": {"type": "integer", "default": 5},
                    "theme": {"type": "string", "enum": ["tous", "tva", "is", "paie", "bic"], "default": "tous"}
                }
            }
        ),
        types.Tool(
            name="syscohada_analyse",
            description="Analyse comptable SYSCOHADA/OHADA pour l Afrique francophone",
            inputSchema={
                "type": "object",
                "properties": {
                    "type_analyse": {"type": "string", "enum": ["imputation", "bilan", "question"], "default": "imputation"},
                    "contenu": {"type": "string", "description": "Facture, bilan ou question"},
                    "pays": {"type": "string", "description": "Pays OHADA", "default": "Senegal"}
                },
                "required": ["contenu"]
            }
        )
    ]


# --- Point d entree ----------------------------------------------------------

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    print("SMD Consulting - Serveur MCP demarre")
    print("En attente de connexion Claude Cowork...")
    asyncio.run(main())