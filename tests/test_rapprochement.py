# -*- coding: utf-8 -*-
"""Rapprochement bancaire sur des fichiers réels : relevé Crédit Agricole (en-tête de la banque, cp1252,
espaces insécables) et FEC complet (seul le 512 est retenu) ; état de rapprochement."""
import io
from utils.rapprochement import lire_operations, ecritures_banque, rapprocher_bancaire, etat_rapprochement

NB = " "
RELEVE = f"""Téléchargement du 03/10/2026;;;;
CREDIT AGRICOLE;;;;
Solde au 30/09/2026 : 12{NB}480,50 €;;;;
;;;;
Date;Libellé;Débit euros;Crédit euros;
02/09/2026;PRLV SEPA EDF SA;144,00;;
05/09/2026;VIR RECU BOULANGERIE MARTIN;;3{NB}000,00;
15/09/2026;FRAIS TENUE DE COMPTE;12,50;;
"""
FEC = """JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise
BQ|Banque|1|20260902|512000|Banque|||P1|20260902|Prlv EDF|0,00|144,00||||| 
BQ|Banque|1|20260902|401000|Fourn|||P1|20260902|Prlv EDF|144,00|0,00|||||
BQ|Banque|2|20260904|512000|Banque|||P2|20260904|Règlement Boulangerie Martin|3000,00|0,00|||||
BQ|Banque|2|20260904|411000|Clients|||P2|20260904|Règlement Boulangerie Martin|0,00|3000,00|||||
BQ|Banque|3|20260928|512000|Banque|||P3|20260928|Chèque 0045 Dupont|0,00|560,00|||||
BQ|Banque|3|20260928|401000|Fourn|||P3|20260928|Chèque 0045 Dupont|560,00|0,00|||||
"""


class F(io.BytesIO):
    def __init__(self, contenu, nom):
        super().__init__(contenu)
        self.name = nom


def test_rapprochement_et_etat():
    dr, solde = lire_operations(F(RELEVE.encode("cp1252"), "releve.csv"))
    assert list(dr.columns[:4]) == ["Date", "Libellé", "Débit euros", "Crédit euros"] and solde == 12480.50
    de, banques = ecritures_banque(lire_operations(F(FEC.encode(), "fec.txt"))[0])
    assert banques == ["512000"] and len(de) == 3
    r = rapprocher_bancaire(dr, de)
    assert r["nb_rapproches"] == 2
    assert r["non_rapproches_releve"]["Montant"].tolist() == [-12.5]
    assert r["non_rapproches_ecritures"]["Montant"].tolist() == [-560.0]
    e = etat_rapprochement(r, solde, 12480.50 - 560 + 12.50)
    assert e["= Solde bancaire rectifié"] == 11920.50 and e["Écart"] == 0


def test_ecritures_de_regularisation():
    import pandas as pd
    from utils.rapprochement import ecritures_regularisation
    nr = pd.DataFrame({"Date": pd.to_datetime(["2026-09-15", "2026-09-20", "2026-09-30", "2026-09-30"]),
                       "Libellé": ["FRAIS TENUE DE COMPTE", "PRLV SEPA URSSAF", "INTERETS CREDITEURS", "VIR INCONNU"],
                       "Montant": [-12.5, -1250.0, 3.2, 500.0]})
    e = ecritures_regularisation(nr)
    assert e["Débit"].sum() == e["Crédit"].sum() == 12.5 + 1250 + 3.2 + 500
    paires = [(e.iloc[i]["Compte"], e.iloc[i + 1]["Compte"]) for i in range(0, len(e), 2)]
    assert paires == [("627000", "512000"), ("431000", "512000"), ("512000", "768000"), ("512000", "471000")]
