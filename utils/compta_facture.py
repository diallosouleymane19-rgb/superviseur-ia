# -*- coding: utf-8 -*-
"""
utils/compta_facture.py - SMD Global Consulting LLC
Détection, analyse et comptabilisation de factures SANS API payante.

Chaîne : lecture du document -> détection facture / avoir -> extraction par règles
-> sens (achat / vente) -> compte PCG -> traitement TVA -> écriture équilibrée
-> contrôles (mentions, cohérence, doublons) -> export au format FEC.

Comptes : nomenclature du PCG (règlement ANC 2014-03), présentés sur 6 chiffres.
"""
import io
import re
import unicodedata
from datetime import datetime

# ─── Plan de comptes utilisé (libellés PCG) ──────────────────────────────────
PCG = {
    "205000": "Concessions et droits similaires, brevets, licences, logiciels",
    "215400": "Matériel industriel",
    "218200": "Matériel de transport",
    "218300": "Matériel de bureau et matériel informatique",
    "218400": "Mobilier",
    "401000": "Fournisseurs",
    "404000": "Fournisseurs d'immobilisations",
    "411000": "Clients",
    "445200": "TVA due intracommunautaire",
    "445620": "TVA sur immobilisations",
    "445660": "TVA sur autres biens et services",
    "445710": "TVA collectée",
    "445800": "Taxes sur le chiffre d'affaires à régulariser ou en attente",
    "471000": "Compte d'attente",
    "601000": "Achats stockés - Matières premières",
    "604000": "Achats d'études et prestations de services",
    "606100": "Fournitures non stockables (eau, énergie)",
    "606300": "Fournitures d'entretien et de petit équipement",
    "606400": "Fournitures administratives",
    "607000": "Achats de marchandises",
    "611000": "Sous-traitance générale",
    "613200": "Locations immobilières",
    "613500": "Locations mobilières",
    "614000": "Charges locatives et de copropriété",
    "615200": "Entretien et réparations sur biens immobiliers",
    "615500": "Entretien et réparations sur biens mobiliers",
    "615600": "Maintenance",
    "616000": "Primes d'assurances",
    "618100": "Documentation générale",
    "618500": "Frais de colloques, séminaires, conférences",
    "621100": "Personnel intérimaire",
    "622600": "Honoraires",
    "622700": "Frais d'actes et de contentieux",
    "623100": "Annonces et insertions",
    "623400": "Cadeaux à la clientèle",
    "623600": "Catalogues et imprimés",
    "624100": "Transports sur achats",
    "625100": "Voyages et déplacements",
    "625600": "Missions",
    "625700": "Réceptions",
    "626000": "Frais postaux et de télécommunications",
    "627000": "Services bancaires et assimilés",
    "628100": "Concours divers (cotisations...)",
    "651000": "Redevances pour concessions, brevets, licences, logiciels",
    "701000": "Ventes de produits finis",
    "706000": "Prestations de services",
    "707000": "Ventes de marchandises",
    "708000": "Produits des activités annexes",
}

# ─── Règles d'imputation des achats : (mots-clés, compte, nature, confiance) ──
# nature : "service" (TVA exigible à l'encaissement), "bien", "immo"
# L'ordre compte : la première règle qui correspond l'emporte.
REGLES_ACHAT = [
    (["ordinateur", "pc portable", "laptop", "macbook", "serveur", "imprimante", "ecran", "tablette"], "218300", "immo", "haute"),
    (["mobilier", "bureau assis", "fauteuil", "armoire", "chaise"], "218400", "immo", "moyenne"),
    (["vehicule", "voiture", "camionnette", "utilitaire"], "218200", "immo", "moyenne"),
    (["apostille", "notariz", "notaris", "legalisation", "legalization", "certified document",
      "certification de documents", "formalites", "formalities", "frais d'actes"], "622700", "service", "haute"),
    (["honoraires", "conseil", "consulting", "legal fees", "attorney", "lawyer", "accounting fees", "expertise comptable", "expert-comptable", "commissaire aux comptes",
      "avocat", "audit", "notaire"], "622600", "service", "haute"),
    (["huissier", "frais d'actes", "contentieux", "greffe"], "622700", "service", "haute"),
    (["telecom", "telephone", "telephonie", "mobile", "forfait", "internet", "fibre", "box", "affranchissement",
      "timbre", "colissimo", "la poste", "postage", "postal", "orange", "sfr", "bouygues", "free pro"], "626000", "service", "haute"),
    (["loyer", "location de bureaux", "location des locaux", "bail commercial"], "613200", "service", "haute"),
    (["charges locatives", "copropriete"], "614000", "service", "haute"),
    (["location", "leasing", "loa", "lld"], "613500", "service", "moyenne"),
    (["electricite", "edf", "engie", "gaz", "eau", "energie", "carburant", "gasoil", "gazole", "essence"], "606100", "bien", "haute"),
    (["fournitures de bureau", "papeterie", "cartouche", "toner", "ramette", "papier"], "606400", "bien", "haute"),
    (["petit materiel", "petit equipement", "outillage", "produits d'entretien"], "606300", "bien", "haute"),
    (["maintenance", "contrat de maintenance", "support technique", "infogerance"], "615600", "service", "haute"),
    (["reparation", "entretien"], "615500", "service", "moyenne"),
    (["assurance", "insurance", "prime d'assurance", "responsabilite civile", "multirisque"], "616000", "service", "haute"),
    (["licence", "license", "logiciel", "software", "saas", "abonnement logiciel"], "651000", "service", "moyenne"),
    (["sous-traitance", "sous traitance"], "611000", "service", "haute"),
    (["interim", "interimaire", "travail temporaire"], "621100", "service", "haute"),
    (["publicite", "annonce", "insertion", "google ads", "campagne"], "623100", "service", "haute"),
    (["catalogue", "imprimes", "flyers", "cartes de visite", "impression"], "623600", "service", "moyenne"),
    (["transport", "livraison", "fret", "transporteur"], "624100", "service", "moyenne"),
    (["train", "sncf", "billet d'avion", "vol ", "taxi", "vtc", "peage", "parking"], "625100", "service", "haute"),
    (["hotel", "hebergement", "lodging", "accommodation"], "625600", "service", "haute"),
    (["restaurant", "repas", "reception", "traiteur"], "625700", "service", "moyenne"),
    (["frais bancaires", "commission bancaire", "frais de tenue de compte"], "627000", "service", "haute"),
    (["cotisation", "adhesion", "abonnement professionnel"], "628100", "service", "moyenne"),
    (["documentation", "revue", "ouvrage", "livre"], "618100", "bien", "moyenne"),
    (["seminaire", "colloque", "conference", "salon"], "618500", "service", "moyenne"),
    (["marchandises", "achat pour revente", "articles"], "607000", "bien", "moyenne"),
    (["matieres premieres", "matiere premiere"], "601000", "bien", "haute"),
    (["prestation", "prestations de services", "etude"], "604000", "service", "moyenne"),
]

REGLES_VENTE = [
    (["marchandises", "articles", "produits revendus"], "707000", "bien", "moyenne"),
    (["produits finis", "fabrication"], "701000", "bien", "moyenne"),
    (["refacturation", "frais refactures", "location", "commission"], "708000", "service", "moyenne"),
    (["prestation", "conseil", "honoraires", "mission", "formation", "service", "maintenance", "audit",
      "accompagnement", "developpement"], "706000", "service", "haute"),
]

# Nouvelles mentions obligatoires (réforme de la facturation électronique), selon impots.gouv.fr
DATE_MENTIONS_2026 = datetime(2026, 9, 1)   # SIREN client, catégorie d'opération, option débits
DATE_MENTIONS_2027 = datetime(2027, 9, 1)   # adresse de livraison si différente

# Seuil de la tolérance fiscale pour les biens de faible valeur (charges plutôt qu'immobilisations)
SEUIL_IMMO_HT = 500.0
TAUX_TVA = [20.0, 10.0, 5.5, 2.1, 8.5, 13.0, 0.9]  # métropole + DOM / Corse


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def _sans_accents(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def parse_montant(txt):
    """'2 500,00 €' -> 2500.0 ; '2,500.00' -> 2500.0 ; '18.32' -> 18.32"""
    if txt is None:
        return None
    s = str(txt).replace(" ", " ").replace(" ", " ").replace("€", "").replace("EUR", "").strip()
    s = re.sub(r"[^\d,.\-]", "", s.replace(" ", ""))
    if not s or s in "-.,":
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):          # 2.500,00
            s = s.replace(".", "").replace(",", ".")
        else:                                     # 2,500.00
            s = s.replace(",", "")
    elif "," in s:
        ent, _, dec = s.rpartition(",")
        s = (ent.replace(",", "") + "." + dec) if len(dec) in (1, 2) else s.replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_date(txt):
    """'20/04/2026', '20-04-26', '2026-04-20' -> datetime"""
    if not txt:
        return None
    t = str(txt).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None


MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "fev": 2, "mar": 3, "apr": 4, "avr": 4, "jun": 6, "jul": 7, "aug": 8,
        "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_MOIS_RE = "|".join(sorted(MOIS, key=len, reverse=True))


def date_en_lettres(txt):
    """'September 9, 2026', 'Sep 9 2026', '9 septembre 2026', '9th September 2026' -> datetime"""
    ts = _sans_accents(txt)
    m = re.search(rf"\b({_MOIS_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", ts)
    if m:
        mois, jour, an = MOIS[m.group(1)], int(m.group(2)), int(m.group(3))
    else:
        m = re.search(rf"\b(\d{{1,2}})(?:er|st|nd|rd|th)?\s+({_MOIS_RE})\.?\s+(\d{{4}})\b", ts)
        if not m:
            return None
        jour, mois, an = int(m.group(1)), MOIS[m.group(2)], int(m.group(3))
    try:
        return datetime(an, mois, jour)
    except ValueError:
        return None


# Pays (adresse de l'émetteur) pour les factures de fournisseurs étrangers
PAYS_UE = ["germany", "allemagne", "deutschland", "spain", "espagne", "espana", "italy", "italie", "italia",
           "belgium", "belgique", "netherlands", "pays-bas", "ireland", "irlande", "luxembourg", "portugal",
           "poland", "pologne", "austria", "autriche", "sweden", "suede", "denmark", "danemark", "finland",
           "finlande", "greece", "grece", "czech", "tcheque", "romania", "roumanie", "hungary", "hongrie"]
PAYS_HORS_UE = ["united states", "usa", "u.s.a", "etats-unis", "united kingdom", "royaume-uni", "england",
                "canada", "china", "chine", "hong kong", "switzerland", "suisse", "japan", "japon", "singapore",
                "singapour", "australia", "australie", "india", "inde", "united arab emirates", "emirats",
                "turkey", "turquie", "morocco", "maroc", "senegal", "cote d'ivoire", "guinee", "mali",
                "cameroun", "cameroon", "tunisie", "tunisia", "algerie", "algeria", "norway", "norvege"]
DEVISES = {"USD": [r"\$", r"\bUSD\b"], "GBP": [r"£", r"\bGBP\b"], "CHF": [r"\bCHF\b"],
           "CAD": [r"\bCAD\b"], "CNY": [r"\bCNY\b", r"\bRMB\b", r"¥"], "XOF": [r"\bXOF\b", r"\bFCFA\b"],
           "EUR": [r"€", r"\bEUR\b"]}


def _devise(t):
    """Devise majoritaire du document (nombre d'occurrences des symboles / codes)."""
    comptes = {dev: sum(len(re.findall(m, t)) for m in motifs) for dev, motifs in DEVISES.items()}
    dev = max(comptes, key=comptes.get)
    return dev if comptes[dev] else "EUR"


def _convertir_euros(d, t):
    """Facture en devise : conversion en euros avec le montant réellement débité en euros
    ou le cours de change indiqué sur la pièce. Sinon, montants laissés en devise (contrôle KO)."""
    dev = d["devise"]
    d["montants_devise"] = {k: d.get(k) for k in ("ht", "tva", "ttc")}
    taux = None
    m = re.search(rf"(?i)1\s*{dev}\s*=\s*{_NUM}\s*(?:€|EUR)", t)
    if m:
        try:
            taux = float(m.group(1).replace(" ", "").replace(",", "."))
        except ValueError:
            taux = None
    m = re.search(rf"€\s?{_NUM}|{_NUM}\s?€|\bEUR\s+{_NUM}", t)
    eur = parse_montant(next(g for g in m.groups() if g)) if m else None
    ttc = d.get("ttc")
    if eur and ttc:
        facteur, d["conversion"] = eur / ttc, "montant débité en euros indiqué sur la pièce"
    elif taux:
        facteur, d["conversion"] = taux, "cours de change indiqué sur la pièce"
        eur = round(ttc * taux, 2) if ttc is not None else None
    else:
        d["taux_change"] = None
        return d
    d["taux_change"] = taux or round(facteur, 6)
    d["facteur_devise"] = facteur
    ht = d.get("ht")
    d["ttc"] = eur
    d["ht"] = round(ht * facteur, 2) if ht is not None else None
    if d["ht"] is not None and d["ttc"] is not None:
        d["tva"] = round(d["ttc"] - d["ht"], 2)
    for l in d.get("lignes_tva", []):
        if l.get("montant") is not None:
            l["montant"] = d["tva"] if len(d["lignes_tva"]) == 1 else round(l["montant"] * facteur, 2)
    return d


def code_auxiliaire(nom, prefixe):
    """'SOPRA STERIA' -> 'FSOPRASTER' (préfixe F fournisseur, C client)"""
    base = re.sub(r"[^A-Z0-9]", "", _sans_accents(nom).upper())
    return (prefixe + base)[:10] if base else prefixe + "DIVERS"


def siren_valide(siren):
    """Clé de Luhn du SIREN (9 chiffres)."""
    d = re.sub(r"\D", "", str(siren))[:9]
    if len(d) != 9:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


# ─── Lecture des documents ───────────────────────────────────────────────────

OCR_MAX_PAGES = 10


def tesseract_disponible():
    """Vrai si le moteur Tesseract (gratuit, local) est installé."""
    import shutil
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def ocr_tesseract(image_bytes: bytes) -> str:
    """OCR gratuit et local d'une image (photo ou page scannée) avec Tesseract, en français."""
    import pytesseract
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)          # photo de smartphone : orientation EXIF
    img = ImageOps.grayscale(img)
    if max(img.size) < 2000:                    # petites photos : agrandir pour l'OCR
        f = 2000 / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    langues = pytesseract.get_languages(config="")
    lang = "fra" if "fra" in langues else "eng"
    return pytesseract.image_to_string(img, lang=lang, config="--psm 6")


def lire_document(contenu: bytes, nom: str):
    """
    Retourne une liste de « pièces » à analyser :
      {"source": nom, "texte": str}  ou  {"source": nom, "ligne_csv": dict}
    + liste de messages d'information.
    """
    nom_l = nom.lower()
    infos = []
    if nom_l.endswith(".pdf"):
        texte = ""
        try:
            import pymupdf
            with pymupdf.open(stream=contenu, filetype="pdf") as doc:
                texte = "\n".join(p.get_text() for p in doc)
        except Exception as e:
            infos.append(f"{nom} : lecture PDF impossible ({e})")
        if len(texte.strip()) < 20:
            # PDF scanné : rendu des pages en image puis OCR Tesseract (gratuit, local)
            if not tesseract_disponible():
                infos.append(f"{nom} : PDF scanné, OCR Tesseract non installé sur ce serveur.")
                return [], infos
            try:
                import pymupdf
                pages = []
                with pymupdf.open(stream=contenu, filetype="pdf") as doc:
                    for page in list(doc)[:OCR_MAX_PAGES]:
                        pages.append(ocr_tesseract(page.get_pixmap(dpi=300).tobytes("png")))
                texte = "\n".join(pages)
            except Exception as e:
                infos.append(f"{nom} : OCR impossible ({e})")
                return [], infos
            if len(texte.strip()) < 20:
                infos.append(f"{nom} : PDF scanné illisible par l'OCR (qualité insuffisante).")
                return [], infos
            infos.append(f"{nom} : PDF scanné lu par OCR Tesseract - vérifiez les montants.")
            return [{"source": nom, "texte": t, "ocr": True} for t in _decouper_factures(texte)], infos
        return [{"source": nom, "texte": t} for t in _decouper_factures(texte)], infos
    if nom_l.endswith((".png", ".jpg", ".jpeg")):
        if not tesseract_disponible():
            infos.append(f"{nom} : image, OCR Tesseract non installé sur ce serveur.")
            return [{"source": nom, "image": contenu}], infos
        try:
            texte = ocr_tesseract(contenu)
        except Exception as e:
            infos.append(f"{nom} : OCR impossible ({e})")
            return [], infos
        if len(texte.strip()) < 20:
            infos.append(f"{nom} : image illisible par l'OCR (photo floue, trop sombre ou trop petite).")
            return [], infos
        infos.append(f"{nom} : image lue par OCR Tesseract - vérifiez les montants.")
        return [{"source": nom, "texte": t, "ocr": True} for t in _decouper_factures(texte)], infos

    texte = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            texte = contenu.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texte is None:
        return [], [f"{nom} : encodage non reconnu"]

    lignes = [l for l in texte.splitlines() if l.strip()]
    if lignes and _ressemble_csv(lignes):
        return _lire_csv(texte, nom), infos
    return [{"source": nom, "texte": t} for t in _decouper_factures(texte)], infos


def _ressemble_csv(lignes):
    entete = _sans_accents(lignes[0])
    sep = max([";", ",", "\t", "|"], key=lambda s: lignes[0].count(s))
    return lignes[0].count(sep) >= 2 and any(k in entete for k in ("ht", "ttc", "montant", "tva")) \
        and len(lignes) >= 2 and lignes[1].count(sep) == lignes[0].count(sep)


def _lire_csv(texte, nom):
    import csv
    premiere = texte.splitlines()[0]
    sep = max([";", ",", "\t", "|"], key=lambda s: premiere.count(s))
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=sep)
    return [{"source": f"{nom} (ligne {i + 2})", "ligne_csv": {k.strip(): (v or "").strip() for k, v in row.items() if k}}
            for i, row in enumerate(lecteur)]


def _decouper_factures(texte):
    """Sépare un texte contenant plusieurs factures (« Facture n° … » répété)."""
    reperes = [m.start() for m in re.finditer(r"(?im)^\s*(facture|avoir|invoice)\s*(n[°o]|num)", texte)]
    if len(reperes) <= 1:
        return [texte]
    reperes.append(len(texte))
    return [texte[a:b] for a, b in zip(reperes, reperes[1:])]


# ─── Extraction ──────────────────────────────────────────────────────────────

_NUM = r"(-?\d[\d   .,]*\d|-?\d)"


def _champ(texte, libelles):
    for lib in libelles:
        m = re.search(rf"(?im)^\s*{lib}\s*[:\-]\s*(.+?)\s*$", texte)
        if m:
            return m.group(1).strip()
    return ""


def _montant_libelle(texte, motif):
    m = re.search(rf"(?im){motif}[^\n\d\-]{{0,25}}{_NUM}\s*(?:€|eur)?", texte)
    return parse_montant(m.group(1)) if m else None


def _montant_ligne(texte, motif):
    """Montant sur la même ligne que le libellé ou sur la ligne suivante (« Total » puis « $340.00 »)."""
    m = re.search(rf"(?im)^\s*(?:{motif})\b[^\n\d\-]{{0,20}}\n?[^\n\d\-]{{0,6}}{_NUM}", texte)
    return parse_montant(m.group(1)) if m else None


def _emetteur_entete(t, client=""):
    """Sans étiquette « Fournisseur : », l'émetteur est la première ligne de l'en-tête
    qui ressemble à un nom (ni titre, ni date, ni adresse, ni le client)."""
    cl = _sans_accents(client)
    for l in [x.strip() for x in t.splitlines() if x.strip()][:12]:
        ls = _sans_accents(l)
        if re.search(r"facture|avoir|invoice|receipt|recu\b|quittance|date|page|siret|siren|tva|tel|mail|@|www|^\d|\d{5}", ls):
            continue
        if re.fullmatch(r"[A-Za-z0-9\-/_.#]+", l) and re.search(r"\d", l):   # référence / code
            continue
        if date_en_lettres(l):
            continue
        if cl and (cl in ls or ls in cl):
            continue
        if len(re.sub(r"[^a-z]", "", ls)) >= 3:
            return l[:80]
    return ""


def _lignes_tableau(t):
    """Libellés des lignes d'articles sous un en-tête « Désignation / Description », jusqu'aux totaux."""
    lignes = t.splitlines()
    for i, l in enumerate(lignes):
        if re.search(r"(?i)d[ée]signation|description|libell[ée]|article", l) and not re.search(r"[:\-]\s*\S", l.split("|")[0][-3:]):
            libs = []
            for x in lignes[i + 1:i + 30]:
                if re.search(r"(?i)\btotal|sub-?total|\bnet [àa] payer|\bh\.?t\.?\s*:|\bamount (paid|due)", x):
                    break
                if re.fullmatch(r"(?i)\s*(qty|quantity|qt[ée]|quantit[ée]|unit price|price|prix( unitaire)?|p\.?u\.?( ht)?|"
                                r"amount|montant( ht)?|rate|taux|tva|vat|tax|unit[ée]?)\s*", x):
                    continue
                lib = re.sub(r"[\d\s.,€%x×]+$", "", x).strip(" -|\t")
                if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", lib)) >= 3:
                    libs.append(lib)
            if libs:
                return " ; ".join(libs)[:200]
    return ""


_ETIQ_CLIENT = r"^\s*(client|destinataire|acheteur|factur[ée]e?\s+[àa]|adress[ée]e?\s+[àa]|bill(?:ed)?\s+to|sold\s+to|invoice\s+to|customer)\b"


def _bloc_client(t):
    """Sépare le bloc client (étiquette « Client : » + 4 lignes suivantes) du reste du document."""
    lignes = t.splitlines()
    dans, reste = [], []
    i = 0
    while i < len(lignes):
        if re.match(_ETIQ_CLIENT, lignes[i], re.I):
            bloc = lignes[i:i + 5]
            # le bloc s'arrête à la première ligne vide ou à une autre rubrique
            for j, l in enumerate(bloc[1:], 1):
                if not l.strip() or re.match(r"(?i)\s*(objet|d[ée]signation|total|montant|date|facture)", l):
                    bloc = bloc[:j]
                    break
            dans += bloc
            i += len(bloc)
        else:
            reste.append(lignes[i])
            i += 1
    return "\n".join(dans), "\n".join(reste)


def _siren_dans(txt, libelle_requis=True):
    """Premier SIREN (ou SIRET tronqué à 9 chiffres) précédé de « SIREN » ou « SIRET »."""
    m = re.search(r"(?i)\bsire[nt]\b[^\d\n]{0,25}(\d{3}\s?\d{3}\s?\d{3})", txt)
    if not m and not libelle_requis:
        m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3})\b", txt)
    return re.sub(r"\D", "", m.group(1))[:9] if m else ""


def _categorie(ts):
    """Catégorie d'opération : LB (livraison de biens), PS (prestations de services), LBPS (mixte)."""
    m = re.search(r"categorie[^\n:]{0,25}:\s*([^\n]+)", ts)
    zone = m.group(1) if m else ts
    biens = re.search(r"livraisons? de biens|\blb\b", zone)
    services = re.search(r"prestations? de services|\bps\b", zone)
    if re.search(r"\bmixte\b|\blbps\b", zone) or (biens and services):
        return "LBPS"
    if biens:
        return "LB"
    if services and (m or re.search(r"operation[s]?\s*:?\s*prestations? de services|nature de l.operation", ts)):
        return "PS"
    return ""


def extraire_texte(texte, source=""):
    """Extraction par règles d'une facture au format texte."""
    t = texte.replace(" ", " ")
    ts = _sans_accents(t)
    d = {"source": source, "texte": texte}

    d["type"] = "avoir" if re.search(r"\bavoir\b|note de credit|credit note", ts) else \
                "facture" if re.search(r"\bfacture\b|\binvoice\b|\breceipt\b|\brecu\b", ts) else None

    m = re.search(r"(?i)(?:facture|avoir|invoice)\s*(?:n[°o]\.?|num[ée]ro|number|no\b\.?|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/_.]*)", t)
    d["numero"] = m.group(1).rstrip(".") if m else _champ(t, ["n[°o] de facture", "num[ée]ro"])

    m = re.search(r"(?im)date(?:\s+(?:de\s+)?(?:la\s+)?(?:facture|facturation|[ée]mission))?\s*[:\-]\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{4}-\d{2}-\d{2})", t)
    if not m:
        m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", t)
    d["date"] = parse_date(m.group(1)) if m else date_en_lettres(t)

    d["fournisseur"] = _champ(t, ["fournisseur", "[ée]metteur", "vendeur", "prestataire", "soci[ée]t[ée] [ée]mettrice"])
    d["client"] = _champ(t, ["client", "destinataire", "acheteur", "factur[ée] [àa]", "adress[ée] [àa]"])
    if not d["client"]:   # « Bill to » seul sur sa ligne, nom à la ligne suivante
        m = re.search(r"(?im)^\s*(?:bill(?:ed)?\s+to|sold\s+to|invoice\s+to|customer)\s*:?\s*\n\s*(\S[^\n]*)", t)
        d["client"] = m.group(1).strip() if m else ""
    if not d["fournisseur"]:
        d["fournisseur"] = _emetteur_entete(t, d["client"])
        d["emetteur_deduit"] = bool(d["fournisseur"])
    d["objet"] = _champ(t, ["objet", "d[ée]signation", "description", "libell[ée]", "prestation", "nature"]) \
        or _lignes_tableau(t)

    bloc_client, hors_client = _bloc_client(t)
    d["siren"] = _siren_dans(hors_client)
    d["siren_client"] = _siren_dans(bloc_client) or _siren_dans(
        "\n".join(re.findall(r"(?im)^.*siren\s+(?:du\s+)?(?:client|acheteur).*$", t)), libelle_requis=False)
    if d["siren_client"] and d["siren"] == d["siren_client"]:
        d["siren"] = ""
    d["categorie"] = _categorie(ts)
    d["adresse_livraison"] = bool(re.search(r"adresse de livraison|livre a :|lieu de livraison", ts))
    m = re.search(r"\b(FR\s?[0-9A-Z]{2}\s?\d{3}\s?\d{3}\s?\d{3}|[A-Z]{2}\s?[0-9A-Z]{8,12})\b", t) \
        if re.search(r"(?i)tva\s*intra|n[°o]\s*tva|vat", t) else None
    d["tva_intra"] = re.sub(r"\s", "", m.group(1)) if m else ""
    d["adresse"] = bool(re.search(r"(?i)\b\d{5}\b\s+[A-Za-zÀ-ÿ]", t))
    # Fournisseur étranger : pays dans l'en-tête (hors bloc client), sans SIREN ni n° TVA français
    hc = _sans_accents(hors_client)
    francais = bool(d["siren"] or d["tva_intra"].startswith("FR") or re.search(r"\b\d{5}\b[ \t]+[a-z]", hc))
    pays = lambda liste: next((p for p in liste if re.search(rf"(?<![a-z]){re.escape(p)}(?![a-z])", hc)), "")
    d["pays_hors_ue"], d["pays_ue"] = pays(PAYS_HORS_UE), pays(PAYS_UE)
    d["devise"] = _devise(t)
    d["etranger"] = not francais and bool(d["pays_hors_ue"] or d["pays_ue"] or d["devise"] != "EUR")
    d["hors_ue"] = d["etranger"] and not d["pays_ue"] and (bool(d["pays_hors_ue"]) or d["devise"] != "EUR")
    if d["etranger"] and (d["pays_hors_ue"] or d["pays_ue"]):
        d["adresse"] = True

    d["ht"] = _montant_libelle(t, r"\b(?:total\s+|montant\s+)?h\.?\s?t\.?(?![a-z])")
    d["ttc"] = _montant_libelle(t, r"\b(?:total\s+|montant\s+)?t\.?t\.?c\.?(?![a-z])") \
        or _montant_libelle(t, r"net\s+[àa]\s+payer")
    # Factures en anglais : Subtotal / Total / Amount due / Amount paid (montant parfois à la ligne)
    if d["ht"] is None:
        d["ht"] = _montant_ligne(t, r"sub-?total")
    if d["ttc"] is None:
        d["ttc"] = _montant_ligne(t, r"(?:grand\s+)?total(?:\s+(?:due|amount))?|amount\s+due|amount\s+paid|balance\s+due")

    # TVA : une ou plusieurs lignes « TVA 20 % : 500,00 » (hors numéro de TVA intracommunautaire)
    lignes_tva = []
    # Les lignes de mention légale (« TVA non applicable, art. 293 B », « autoliquidation »...) ne portent pas de montant
    mention = re.compile(r"(?i)non applicable|exon|autoliquid|auto-liquid|art(icle)?\.?\s*\d|intra|d'apr[eè]s les d[ée]bits")
    texte_montants = "\n".join(l for l in t.splitlines() if not mention.search(l))
    for m in re.finditer(rf"(?im)^.*?\btva\b[^\n\d]*?(\d{{1,2}}(?:[.,]\d{{1,2}})?)\s*%[^\n\d\-]*{_NUM}", texte_montants):
        lignes_tva.append({"taux": float(m.group(1).replace(",", ".")), "montant": parse_montant(m.group(2))})
    if not lignes_tva:
        m = re.search(rf"(?im)^\s*(?:total\s+|montant\s+)?tva\b[^\n\d\-]*{_NUM}", texte_montants)
        if m:
            lignes_tva.append({"taux": None, "montant": parse_montant(m.group(1))})
    if not lignes_tva:
        tx = _montant_ligne(texte_montants, r"(?:sales\s+)?tax|vat")
        if tx is not None:
            lignes_tva.append({"taux": None, "montant": tx})
    d["lignes_tva"] = lignes_tva
    d["tva"] = round(sum(l["montant"] or 0 for l in lignes_tva), 2) if lignes_tva else None

    d["autoliquidation"] = bool(re.search(r"autoliquidation|auto-liquidation|reverse charge|283-2|283 2", ts))
    d["franchise"] = bool(re.search(r"293\s?b|tva non applicable", ts))
    d["option_debits"] = bool(re.search(r"(paiement|acquittement) de la taxe d'apres les debits|option.{0,20}debits", ts))
    d["exoneration"] = bool(re.search(r"exoneration|exonere|art(icle)?\.?\s*26[12]", ts))
    if d["franchise"] or d["exoneration"]:
        d["lignes_tva"], d["tva"] = [], None   # aucune TVA facturée
    d = _completer(d)
    if d["devise"] != "EUR":
        _convertir_euros(d, t)
    return d


def extraire_csv(ligne, source=""):
    """Extraction d'une ligne de liste de factures (CSV)."""
    cle = {_sans_accents(k): v for k, v in ligne.items()}
    def get(*noms):
        for n in noms:
            for k, v in cle.items():
                if n in k and v:
                    return v
        return ""
    d = {"source": source, "texte": " ; ".join(f"{k}: {v}" for k, v in ligne.items())}
    d["type"] = "avoir" if "avoir" in _sans_accents(get("type", "nature")) else "facture"
    d["numero"] = get("numero", "num", "piece", "facture")
    d["date"] = parse_date(get("date"))
    d["fournisseur"] = get("fournisseur", "emetteur", "vendeur", "tiers")
    d["client"] = get("client", "destinataire")
    d["objet"] = get("objet", "designation", "libelle", "description", "nature")
    d["siren"] = re.sub(r"\D", "", next((v for k, v in cle.items() if ("siren" in k or "siret" in k) and "client" not in k), ""))[:9]
    d["siren_client"] = re.sub(r"\D", "", get("siren client", "siret client"))[:9]
    d["categorie"] = _categorie(_sans_accents(get("categorie")) + " ") if get("categorie") else ""
    d["adresse_livraison"] = bool(get("adresse de livraison", "livraison"))
    d["tva_intra"] = get("tva intra", "n tva", "vat")
    d["adresse"] = bool(get("adresse"))
    d["ht"] = parse_montant(get("ht"))
    d["ttc"] = parse_montant(get("ttc"))
    tva = parse_montant(next((v for k, v in cle.items() if k.startswith("tva") and "intra" not in k and "taux" not in k), ""))
    taux = parse_montant(get("taux"))
    d["lignes_tva"] = [{"taux": taux, "montant": tva}] if tva is not None else []
    d["tva"] = tva
    d["autoliquidation"] = d["franchise"] = d["option_debits"] = d["exoneration"] = False
    return _completer(d)


def _completer(d):
    """Complète le montant manquant et déduit le taux de TVA."""
    ht, tva, ttc = d.get("ht"), d.get("tva"), d.get("ttc")
    if tva is None and ht is not None and ttc is not None:
        tva = round(ttc - ht, 2)
        d["lignes_tva"] = [{"taux": None, "montant": tva}]
    if ht is None and tva is not None and ttc is not None:
        ht = round(ttc - tva, 2)
    if ttc is None and ht is not None and tva is not None:
        ttc = round(ht + tva, 2)
    if (d.get("franchise") or d.get("autoliquidation") or d.get("exoneration")) and tva is None and ht is not None:
        tva = 0.0
        ttc = ttc if ttc is not None else ht
    d["ht"], d["tva"], d["ttc"] = ht, tva, ttc
    for l in d.get("lignes_tva", []):
        if l["taux"] is None and ht and l["montant"] is not None and len(d["lignes_tva"]) == 1:
            l["taux"] = 0.0 if l["montant"] == 0 else min(TAUX_TVA, key=lambda r: abs(ht * r / 100 - l["montant"]))
    return d


# ─── Analyse comptable ───────────────────────────────────────────────────────

def determiner_sens(d, ma_societe=""):
    """'achat' ou 'vente' selon l'émetteur. Retourne (sens, justification)."""
    soc = _sans_accents(ma_societe).strip()
    if soc:
        siren_soc = re.sub(r"\D", "", soc)
        emet = _sans_accents(d.get("fournisseur", ""))
        if (siren_soc and len(siren_soc) >= 9 and d.get("siren", "")[:9] == siren_soc[:9]) or (soc and soc in emet):
            return "vente", "Votre société est l'émettrice"
        if soc in _sans_accents(d.get("client", "")):
            return "achat", "Votre société est la destinataire"
    if d.get("fournisseur"):
        return "achat", "Document avec un fournisseur identifié"
    if d.get("client"):
        return "vente", "Document avec un client identifié"
    return "achat", "Sens non déterminé : achat par défaut, à vérifier"


def _texte_imputation(d, sens, ma_societe=""):
    """Zones lues pour l'imputation, de la plus fiable à la moins fiable.
    Les noms du client et de votre société sont retirés (ex. « Consulting » ne doit pas imputer en honoraires)."""
    exclus = [x for x in (d.get("client"), ma_societe, d.get("fournisseur") if sens == "vente" else "") if x]
    corps = []
    for l in str(d.get("texte", ""))[:3000].splitlines():
        ls = _sans_accents(l)
        if re.match(r"\s*(client|destinataire|acheteur|factur|adresse|siren|siret|tva intra)", ls):
            continue
        if any(_sans_accents(x) in ls for x in exclus):
            continue
        corps.append(l)
    zones = [("désignation", d.get("objet", ""))]
    if sens == "achat":
        zones.append(("nom du fournisseur", d.get("fournisseur", "")))
    zones.append(("corps du document", "\n".join(corps)))
    return [(nom, _sans_accents(z)) for nom, z in zones if z]


def proposer_compte(d, sens, ma_societe=""):
    """Retourne (compte, nature, confiance, règle)."""
    regles = REGLES_ACHAT if sens == "achat" else REGLES_VENTE
    for zone, texte in _texte_imputation(d, sens, ma_societe):
        for mots, compte, nature, confiance in regles:
            mot = next((m for m in mots if re.search(rf"\b{re.escape(m.strip())}", texte)), None)
            if not mot:
                continue
            if zone == "corps du document" and confiance == "haute":
                confiance = "moyenne"
            if nature == "immo" and (d.get("ht") or 0) < SEUIL_IMMO_HT:
                return "606300", "bien", "haute", f"« {mot} » ({zone}) < {SEUIL_IMMO_HT:.0f} € HT : petit équipement en charge (tolérance fiscale)"
            return compte, nature, confiance, f"Mot-clé « {mot} » ({zone})"
    if sens == "vente":
        return "706000", "service", "basse", "Aucun mot-clé : prestations de services par défaut"
    return "471000", "service", "basse", "Nature non identifiée : compte d'attente à affecter"


def nature_compte(compte):
    """Nature déduite du compte choisi : immobilisation, bien ou service (pour la TVA et le tiers)."""
    c = str(compte)
    if c.startswith("2"):
        return "immo"
    if c.startswith(("601", "602", "603", "606", "607", "701", "707")):
        return "bien"
    return "service"


def generer_ecriture(d, sens, compte, nature, tva_services="exigibilite", journal_achat="AC", journal_vente="VE"):
    """
    Lignes d'écriture équilibrées.
    tva_services : 'exigibilite' (4458 jusqu'au paiement sauf option débits) ou 'directe' (44566).
    """
    ht, tva, ttc = d.get("ht") or 0.0, d.get("tva") or 0.0, d.get("ttc") or 0.0
    avoir = d.get("type") == "avoir"
    tiers_nom = d.get("fournisseur") if sens == "achat" else (d.get("client") or "Client")
    lib = f"{'Avoir' if avoir else 'Fact.'} {d.get('numero') or ''} {tiers_nom or ''}".strip()[:60]
    L = []
    def ligne(cpt, aux, deb, cre, libelle=lib):
        if avoir:
            deb, cre = cre, deb
        if round(deb, 2) or round(cre, 2):
            L.append({"compte": cpt, "aux": aux, "libelle": libelle, "debit": round(deb, 2), "credit": round(cre, 2)})

    if sens == "achat":
        tiers = "404000" if nature == "immo" else "401000"
        aux = code_auxiliaire(tiers_nom or "", "F")
        if d.get("autoliquidation"):
            tva_auto = round(ht * 0.20, 2)
            ligne(compte, "", ht, 0)
            ligne("445660", "", tva_auto, 0, lib + " TVA autoliquidée")
            ligne("445200", "", 0, tva_auto, lib + " TVA autoliquidée")
            ligne(tiers, aux, 0, ht)
        else:
            if nature == "immo":
                cpt_tva = "445620"
            elif nature == "service" and tva_services == "exigibilite" and not d.get("option_debits"):
                cpt_tva = "445800"
            else:
                cpt_tva = "445660"
            ligne(compte, "", ht, 0)
            ligne(cpt_tva, "", tva, 0)
            ligne(tiers, aux, 0, ttc)
    else:
        aux = code_auxiliaire(tiers_nom or "", "C")
        ligne("411000", aux, ttc, 0)
        ligne(compte, "", 0, ht)
        ligne("445710", "", 0, tva)
    return {"journal": journal_achat if sens == "achat" else journal_vente, "lignes": L}


def controler(d, ecriture=None):
    """Contrôles de conformité (art. 242 nonies A annexe II CGI) et de cohérence."""
    C = []
    ok = lambda m: C.append(("OK", m))
    ko = lambda m: C.append(("KO", m))
    av = lambda m: C.append(("ALERTE", m))
    (ok if d.get("type") else ko)("Document identifié comme " + (d.get("type") or "inconnu"))
    (ok if d.get("numero") else ko)("Numéro de facture" + ("" if d.get("numero") else " absent"))
    (ok if d.get("date") else ko)("Date de facture" + ("" if d.get("date") else " absente ou illisible"))
    (ok if d.get("fournisseur") or d.get("client") else ko)("Identité du tiers")
    etranger = d.get("etranger")
    if etranger:
        pays = (d.get("pays_hors_ue") or d.get("pays_ue") or "pays non identifié").title()
        ok(f"Fournisseur établi hors de France ({pays}) : SIREN non applicable")
    elif d.get("siren"):
        (ok if siren_valide(d["siren"]) else ko)(f"SIREN {d['siren']} " + ("valide" if siren_valide(d["siren"]) else "invalide (clé de contrôle)"))
    else:
        ko("SIREN / SIRET de l'émetteur absent (mention obligatoire)")
    if etranger and d.get("hors_ue"):
        ok("N° de TVA intracommunautaire non applicable (fournisseur hors UE)")
    elif not d.get("franchise"):
        (ok if d.get("tva_intra") else ko)("N° de TVA intracommunautaire" + ("" if d.get("tva_intra") else " absent (mention obligatoire)"))
    (ok if d.get("adresse") else av)("Adresses" + ("" if d.get("adresse") else " non détectées (mention obligatoire)"))
    (ok if d.get("client") else av)("Nom du client" + ("" if d.get("client") else " non indiqué (mention obligatoire)"))
    (ok if d.get("objet") else av)("Désignation" + ("" if d.get("objet") else " absente : imputation impossible à déterminer"))
    ht, tva, ttc = d.get("ht"), d.get("tva"), d.get("ttc")
    if None in (ht, tva, ttc):
        ko("Montants HT / TVA / TTC incomplets")
    else:
        ecart = round(ht + tva - ttc, 2)
        (ok if abs(ecart) <= 0.01 else ko)("HT + TVA = TTC" + ("" if abs(ecart) <= 0.01 else f" : écart de {ecart:.2f} €".replace(".", ",")))
        for l in d.get("lignes_tva", []):
            if l.get("taux") and len(d["lignes_tva"]) == 1 and ht:
                theo = ht * l["taux"] / 100
                e = abs(theo - (l["montant"] or 0))
                if e <= 0.011:
                    ok(f"TVA cohérente avec le taux de {str(l['taux']).replace('.', ',').rstrip('0').rstrip(',')} %"
                       + (" (arrondi)" if e > 0.005 else ""))
                else:
                    ko(f"TVA {l['montant']:.2f} € incohérente avec {l['taux']} % de {ht:.2f} € (attendu {theo:.2f} €)".replace(".", ","))
                if l["taux"] not in TAUX_TVA:
                    av(f"Taux de TVA {l['taux']} % inhabituel")
    # Nouvelles mentions de la facturation électronique (impots.gouv.fr, « données de facture »)
    date = d.get("date")
    if d.get("devise", "EUR") != "EUR":
        dev, md = d["devise"], d.get("montants_devise", {})
        if d.get("taux_change"):
            ok(f"Facture en {dev} : {nb_dev(md.get('ttc'))} {dev} convertis en {nb_dev(d.get('ttc'))} € "
               f"({d.get('conversion')}, 1 {dev} = {str(round(d['taux_change'], 4)).replace('.', ',')} €)")
        else:
            ko(f"Facture en {dev} sans montant en euros ni cours de change : montants NON convertis, "
               f"à convertir au cours du jour de l'opération avant import")
    if etranger and d.get("hors_ue") and not d.get("tva") and not d.get("autoliquidation"):
        av("Fournisseur hors UE, aucune TVA facturée. Si votre société est assujettie à la TVA en France : "
           "prestation de services → TVA à autoliquider (art. 283-2 du CGI, 445660 / 445200) ; "
           "marchandises → TVA à l'importation. Sinon, aucune TVA.")
    if etranger:
        ok("Nouvelles mentions de la facturation électronique française non applicables (fournisseur étranger)")
    elif date and date >= DATE_MENTIONS_2026:
        if d.get("siren_client"):
            (ok if siren_valide(d["siren_client"]) else ko)(
                f"SIREN du client {d['siren_client']} " + ("valide" if siren_valide(d["siren_client"]) else "invalide (clé de contrôle)"))
        else:
            av("SIREN du client absent (attendu depuis le 01/09/2026 pour les clients professionnels)")
        libs = {"LB": "livraison de biens", "PS": "prestation de services", "LBPS": "opération mixte"}
        (ok if d.get("categorie") else av)(
            f"Catégorie d'opération : {libs[d['categorie']]}" if d.get("categorie")
            else "Catégorie d'opération absente (biens / services / mixte, attendue depuis le 01/09/2026)")
        if d.get("option_debits"):
            ok("Option pour le paiement de la TVA d'après les débits mentionnée")
        if date >= DATE_MENTIONS_2027 and not d.get("adresse_livraison"):
            av("Adresse de livraison non indiquée (attendue depuis le 01/09/2027 si elle diffère de l'adresse du client)")
    elif date:
        ok(f"Nouvelles mentions de la facturation électronique non exigées (facture du {date.strftime('%d/%m/%Y')}, avant le 01/09/2026)")
    if d.get("autoliquidation"):
        av("Autoliquidation : TVA calculée à 20 % par l'acquéreur, à vérifier selon l'opération")
    if d.get("franchise"):
        ok("Franchise en base (art. 293 B du CGI) : pas de TVA")
    if ecriture:
        D = round(sum(l["debit"] for l in ecriture["lignes"]), 2)
        Cr = round(sum(l["credit"] for l in ecriture["lignes"]), 2)
        (ok if D == Cr else ko)("Écriture équilibrée" + ("" if D == Cr else f" : débit {D} ≠ crédit {Cr}"))
    return C


def nb_dev(x):
    return "?" if x is None else f"{x:,.2f}".replace(",", " ").replace(".", ",")


def cle_doublon(d):
    """Même tiers + même date + même TTC = doublon probable (le n° peut différer d'un document à l'autre)."""
    tiers = re.sub(r"[^a-z0-9]", "", _sans_accents(d.get("fournisseur") or d.get("client") or ""))
    date = d["date"].strftime("%Y%m%d") if d.get("date") else ""
    return f"{tiers}|{date}|{d.get('ttc')}"


def analyser(pieces, ma_societe="", tva_services="exigibilite"):
    """Analyse complète d'une liste de pièces (sortie de lire_document)."""
    resultats, vus = [], {}
    for p in pieces:
        if "image" in p:
            continue
        d = extraire_csv(p["ligne_csv"], p["source"]) if "ligne_csv" in p else extraire_texte(p["texte"], p["source"])
        sens, why_sens = determiner_sens(d, ma_societe)
        compte, nature, confiance, regle = proposer_compte(d, sens, ma_societe)
        ecr = generer_ecriture(d, sens, compte, nature, tva_services)
        ctrl = controler(d, ecr)
        if p.get("ocr"):
            d["ocr"] = True
            ctrl.append(("ALERTE", "Pièce lue par OCR (scan ou photo) : vérifiez montants, dates et numéros avec l'original"))
        r = {"donnees": d, "sens": sens, "justif_sens": why_sens, "compte": compte,
             "libelle_compte": PCG.get(compte, ""), "nature": nature, "confiance": confiance,
             "regle": regle, "ecriture": ecr, "controles": ctrl, "doublon_de": None}
        k = cle_doublon(d)
        if k in vus:
            # On conserve la pièce la plus complète (imputation la plus sûre) ; l'autre est marquée doublon
            garde, ecarte = (r, vus[k]) if _score(r) > _score(vus[k]) else (vus[k], r)
            vus[k] = garde
            garde["doublon_de"] = None
            garde["controles"] = [c for c in garde["controles"] if not c[1].startswith("Doublon")]
            nom = f"{garde['donnees'].get('numero')} ({garde['donnees']['source']})"
            ecarte["doublon_de"] = nom
            ecarte["controles"] = [c for c in ecarte["controles"] if not c[1].startswith("Doublon")] + \
                [("KO", f"Doublon probable de {nom} (même tiers, même date, même TTC) : exclu de l'export")]
        else:
            vus[k] = r
        resultats.append(r)   # chaque pièce n'est ajoutée qu'une fois, doublon ou non
    return resultats


def _score(r):
    return {"haute": 3, "moyenne": 2, "basse": 1}[r["confiance"]] + (1 if r["donnees"].get("objet") else 0)


# ─── Export ──────────────────────────────────────────────────────────────────

COLONNES_FEC = ["JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum", "CompteLib",
                "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
                "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise"]
JOURNAUX = {"AC": "Achats", "VE": "Ventes"}


def _devise_fec(d, l):
    """Colonnes Montantdevise / Idevise (vides pour une pièce en euros)."""
    f = d.get("facteur_devise")
    if d.get("devise", "EUR") == "EUR" or not f:
        return ["", ""]
    return [f"{(l['debit'] or l['credit']) / f:.2f}".replace(".", ","), d["devise"]]


def export_fec(resultats, inclure_doublons=False):
    """Écritures au format FEC (séparateur |, montants à virgule)."""
    out = ["|".join(COLONNES_FEC)]
    n = 0
    for r in resultats:
        if r.get("doublon_de") and not inclure_doublons:
            continue
        d, e = r["donnees"], r["ecriture"]
        n += 1
        date = d["date"].strftime("%Y%m%d") if d.get("date") else ""
        tiers = d.get("fournisseur") if r["sens"] == "achat" else d.get("client")
        for l in e["lignes"]:
            out.append("|".join([
                e["journal"], JOURNAUX.get(e["journal"], e["journal"]), f"{e['journal']}{n:05d}", date,
                l["compte"], PCG.get(l["compte"], ""), l["aux"], (tiers or "") if l["aux"] else "",
                d.get("numero") or "", date, l["libelle"],
                f"{l['debit']:.2f}".replace(".", ","), f"{l['credit']:.2f}".replace(".", ","),
                "", "", "", *_devise_fec(d, l)]))
    return "\n".join(out) + "\n"
