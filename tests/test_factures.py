# -*- coding: utf-8 -*-
"""Factures : cas réels corrigés le 18/10/2026 (imputation, fournisseur UE, n° de TVA, listes CSV)."""
from utils.compta_facture import analyser, extraire_csv, imputer, determiner_sens

HONORAIRES = """CABINET DURAND EXPERTISE
12 rue Nationale, 37000 Tours
SIRET : 552 100 554 00012
TVA intracommunautaire : FR40552100554
FACTURE N° 2026-0412
Date : 05/10/2026
Client : SAS MOMENTO
SIREN client : 732 829 320
Catégorie d'opération : prestations de services
Désignation   Qté   PU HT   Montant HT
Mission de tenue comptable septembre   1   850,00   850,00
Établissement déclaration TVA   1   150,00   150,00
Total HT : 1 000,00 €
TVA 20 % : 200,00 €
Total TTC : 1 200,00 €
"""

ALLEMAGNE = """Softwerk GmbH
Friedrichstraße 100, 10117 Berlin, Germany
USt-IdNr / VAT : DE811569869
Invoice No. SW-2026-771
Date: 01/10/2026
Bill to:
SAS MOMENTO
15 rue Denis Papin, 41000 Blois, France
VAT FR21732829320
Description   Qty   Price   Amount
Software maintenance support Q4   1   900.00   900.00
Subtotal: 900.00 EUR
VAT 0%: 0.00 EUR
Total: 900.00 EUR
Reverse charge - Autoliquidation article 283-2 CGI
"""

VENTE = """SAS MOMENTO
15 rue Denis Papin, 41000 Blois
SIRET 732 829 320 00074
TVA : FR21732829320
Facture n° F2026-055
Date : 10/10/2026
Client : BOULANGERIE MARTIN
Objet : accompagnement à la mise en place de la caisse
Total HT : 2 500,00 €
TVA 20 % : 500,00 €
Total TTC : 3 000,00 €
"""


def _un(texte):
    return analyser([{"source": "t.pdf", "texte": texte}], ma_societe="SAS MOMENTO")[0]


def test_categorie_operation_ne_decide_pas_du_compte():
    r = _un(HONORAIRES)
    assert r["compte"] == "622600"


def test_fournisseur_ue_autoliquidation():
    r = _un(ALLEMAGNE)
    d = r["donnees"]
    assert d["etranger"] and d["tva_intra"] == "DE811569869"
    assert d["tva"] == 0 and d["ttc"] == 900
    lignes = {l["compte"]: (l["debit"], l["credit"]) for l in r["ecriture"]["lignes"]}
    assert lignes["445660"] == (180.0, 0) and lignes["445200"] == (0, 180.0) and lignes["401000"] == (0, 900.0)
    assert not [c for c in r["controles"] if c[0] == "KO"]


def test_numero_tva_sans_mot_intra():
    r = _un(VENTE)
    assert r["sens"] == "vente" and r["donnees"]["tva_intra"] == "FR21732829320"


def test_liste_csv_sans_faux_controles_de_mentions():
    d = extraire_csv({"Date": "02/10/2026", "N° facture": "EDF-1", "Fournisseur": "EDF", "Désignation": "Electricité",
                      "Montant HT": "120,00", "TVA": "24,00", "Montant TTC": "144,00"}, "liste.csv")
    r = {"donnees": d, "sens": determiner_sens(d)[0]}
    imputer(r)
    assert r["compte"] == "606100"
    assert not [c for c in r["controles"] if c[0] != "OK"]
