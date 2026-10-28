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


def test_vente_services_tva_exigible_a_l_encaissement():
    r = _un(VENTE)
    comptes = {l["compte"] for l in r["ecriture"]["lignes"]}
    assert "445800" in comptes and "445710" not in comptes


def test_vente_services_tva_directe_ou_option_debits():
    from utils.compta_facture import generer_ecriture
    d = {"type": "facture", "numero": "1", "client": "X", "ht": 100.0, "tva": 20.0, "ttc": 120.0}
    assert "445710" in {l["compte"] for l in generer_ecriture(d, "vente", "706000", "service", "directe")["lignes"]}
    d["option_debits"] = True
    assert "445710" in {l["compte"] for l in generer_ecriture(d, "vente", "706000", "service")["lignes"]}
    d["option_debits"] = False
    assert "445710" in {l["compte"] for l in generer_ecriture(d, "vente", "707000", "bien")["lignes"]}


# Facture télécom (structure réelle La Poste Mobile, données client fictives) — cas corrigé le 28/10/2026
TELECOM = """Bonjour, voici votre facture du 03 octobre 2026.
Montant total prélevé ce mois-ci*
21,99 € TTC
HT
TTC
Montant de votre facture
18,32 €
21,99 €
(dont montant de TVA à 20,00 % acquittée sur les débits : 3,67 €)
Vos abonnements, forfaits et options du 03/10/2026 au 02/11/2026
· F+M 150Go
18,32 €
21,99 €
Numéro de Facture : 1116116865
Montant € TTC : 21,99 €
Client : M JEAN MARTIN
LA POSTE TELECOM - SAS au capital de 10 000 000€ - 855 av. R. Salengro - 92370 Chaville - RCS Nanterre n° 525 254 736 - TVA FR 93525254736
Numéro de facture
1116116865
Total : 18,32 € HT soit 21,99 € TTC
delà de votre forfait (après avoir consommé les communications incluses dans votre forfait) pour le mois précédent.
Remboursement ou exonération de la rémunération pour usage professionnel : www.copiefrance.fr.
"""


def test_facture_telecom_mentions_legales_et_glossaire():
    r = analyser([{"source": "telecom.pdf", "texte": TELECOM}], "SMD GLOBAL CONSULTING")[0]
    d = r["donnees"]
    assert d["type"] == "facture"                       # « après avoir consommé » n'est pas un avoir
    assert d["numero"] == "1116116865"
    assert d["fournisseur"] == "LA POSTE TELECOM"
    assert d["siren"] == "525254736"                    # lu après « RCS Nanterre n° »
    assert (d["ht"], d["tva"], d["ttc"]) == (18.32, 3.67, 21.99)   # glossaire « exonération » ignoré
    assert d["option_debits"] is True
    assert "150Go" in d["objet"]
    assert r["sens"] == "achat" and r["compte"] == "626000"
    comptes = {l["compte"]: (l["debit"], l["credit"]) for l in r["ecriture"]["lignes"]}
    assert comptes["626000"] == (18.32, 0) and comptes["445660"] == (3.67, 0)   # TVA sur les débits : déductible
    assert comptes["401000"] == (0, 21.99)


def test_avoir_reconnu_comme_document():
    t = "AVOIR N° AV-2026-03\nDate : 10/10/2026\nFournisseur : ACME SARL\nSIRET : 552 100 554 00012\n" \
        "Total HT : 100,00 €\nTVA 20 % : 20,00 €\nTotal TTC : 120,00 €\n"
    assert analyser([{"source": "a.txt", "texte": t}])[0]["donnees"]["type"] == "avoir"


USD = """Invoice
Invoice number EKQOTNK0-0005
Date of issue October 7, 2026
Celonis Inc.
One World Trade Center
New York, New York 10007
United States
Bill to
JEAN MARTIN
France
Description Qty Unit price Amount
Make Core plan (10000 credits / month) - monthly subscription   1   $10.59   $10.59
Subtotal $10.59
Total $10.59
Amount due $10.59 USD
"""


def test_facture_usd_abonnement_et_cours_saisi():
    from utils.compta_facture import convertir_au_cours
    r = analyser([{"source": "usd.pdf", "texte": USD}], "SMD GLOBAL CONSULTING")[0]
    d = r["donnees"]
    assert d["devise"] == "USD" and d["hors_ue"] and r["compte"] == "651000"
    assert any(s == "KO" and "NON convertis" in m for s, m in r["controles"])
    for tx in (0.86, 0.8612):          # un second cours remplace le premier, sans cumul
        convertir_au_cours(d, tx)
        imputer(r, "SMD GLOBAL CONSULTING")
    assert (d["ht"], d["tva"], d["ttc"]) == (9.12, 0.0, 9.12)
    assert d["montants_devise"]["ttc"] == 10.59
    assert {l["compte"]: (l["debit"], l["credit"]) for l in r["ecriture"]["lignes"]} == \
        {"651000": (9.12, 0), "401000": (0, 9.12)}
    assert not any(s == "KO" for s, _ in r["controles"])


def test_facture_usd_montant_preleve_releve():
    from utils.compta_facture import convertir_au_montant_preleve
    r = analyser([{"source": "usd.pdf", "texte": USD}], "SMD GLOBAL CONSULTING")[0]
    d = r["donnees"]
    convertir_au_montant_preleve(d, 9.18)
    imputer(r, "SMD GLOBAL CONSULTING")
    assert (d["ht"], d["tva"], d["ttc"]) == (9.18, 0.0, 9.18)   # au centime près du relevé
    assert round(d["taux_change"], 4) == 0.8669
    assert {l["compte"]: (l["debit"], l["credit"]) for l in r["ecriture"]["lignes"]} == \
        {"651000": (9.18, 0), "401000": (0, 9.18)}
    assert any("montant prélevé" in m for s, m in r["controles"] if s == "OK")
