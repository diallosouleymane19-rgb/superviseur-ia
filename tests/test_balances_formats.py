# -*- coding: utf-8 -*-
"""Lecture des balances exportées par les logiciels (18/10/2026) : la balance de référence BAL_N
(résultat 19 500, total actif 141 000) doit être retrouvée quel que soit le format."""
import io
import pandas as pd
import pytest
from tests.test_calculs import BAL_N
from utils.intelligent_parser import parser_balance_intelligent, montants
from utils.sig_pcg import calculer_sig
from utils.bilan import calculer_bilan
from utils.audit_balance import auditer_balance


class Fichier(io.BytesIO):
    def __init__(self, contenu, nom):
        super().__init__(contenu)
        self.name = nom


def _lignes():
    for cpt, d, c in BAL_N.itertuples(index=False):
        solde = d - c
        an = round(solde * 0.6, 2) if str(cpt)[0] in "12345" else 0.0
        reste = solde - an
        md, mc = (reste + 1000, 1000) if reste >= 0 else (1000, -reste + 1000)
        if str(cpt)[0] in "67":
            md, mc = max(reste, 0), max(-reste, 0)
        yield str(cpt).ljust(6, "0"), max(an, 0), max(-an, 0), md, mc, max(solde, 0), max(-solde, 0)


def _verifier(f):
    df, info = parser_balance_intelligent(f)
    assert len(df) == len(BAL_N)
    assert calculer_sig(df)["resultat_net"] == pytest.approx(19500)
    assert calculer_bilan(df)["totaux"]["total_actif"] == pytest.approx(141000)
    a = auditer_balance(df.copy())
    assert a["kpis"]["total_debit"] == pytest.approx(a["kpis"]["total_credit"])
    assert not info.get("montants_illisibles")
    return info


def test_montants_formats_francais_et_anglais():
    s = pd.Series(["1 234,56", "1.234,56", "1,234.56", "(1 234,56)", "1 234,56-", "12,5 €", "", "30 000,00"])
    assert montants(s).tolist() == [1234.56, 1234.56, 1234.56, -1234.56, -1234.56, 12.5, 0.0, 30000.0]


def test_cegid_a_nouveaux_mouvements_soldes_espaces_insecables():
    fr = lambda x: f"{x:,.2f}".replace(",", " ").replace(".", ",") if x else ""
    txt = "Compte;Libellé;A nouveau Débit;A nouveau Crédit;Mouvements Débit;Mouvements Crédit;Solde Débit;Solde Crédit\n"
    txt += "".join(f"{c};Compte {c};" + ";".join(fr(x) for x in r) + "\n" for c, *r in _lignes())
    info = _verifier(Fichier(txt.encode("cp1252"), "cegid.csv"))
    assert info["montants_depuis"] == "soldes débiteurs et créditeurs"


def test_sage_titres_sous_totaux_milliers_en_point():
    fp = lambda x: f"{x:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".") if x else ""
    rows = [["SARL DEMO - Balance générale", "", "", ""], ["", "", "", ""], ["N° compte", "Intitulé", "Solde débiteur", "Solde créditeur"]]
    for cl in "1234567":
        sub = [l for l in _lignes() if l[0].startswith(cl)]
        rows += [[l[0], "x", fp(l[5]), fp(l[6])] for l in sub]
        rows.append([f"Total classe {cl}", "", fp(sum(l[5] for l in sub)), fp(sum(l[6] for l in sub))])
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, header=False, index=False)
    _verifier(Fichier(buf.getvalue(), "sage.xlsx"))


def test_pennylane_solde_unique_signe():
    txt = "Numéro de compte,Libellé,Solde\n" + "".join(f"{l[0]},Compte,{l[5] - l[6]:.2f}\n" for l in _lignes())
    _verifier(Fichier(txt.encode(), "pennylane.csv"))


def test_a_nouveaux_et_mouvements_sans_soldes():
    txt = "Compte;Libellé;AN Débit;AN Crédit;Débit;Crédit\n" + "".join(
        f"{l[0]};Compte;{l[1]:.2f};{l[2]:.2f};{l[3]:.2f};{l[4]:.2f}\n".replace(".", ",") for l in _lignes())
    _verifier(Fichier(txt.encode(), "an.csv"))


def test_montant_illisible_signale():
    txt = "Compte;Libellé;Débit;Crédit\n401000;Fourn;0;12?000,00\n512000;Banque;12 000,00;0\n"
    df, info = parser_balance_intelligent(Fichier(txt.encode(), "b.csv"))
    assert info["montants_illisibles"] == 1


def test_desequilibre_toujours_critique():
    from utils.coherence import verifier_coherence
    df = pd.DataFrame({"CompteNum": ["401000", "512000", "606000"], "CompteLib": ["a", "b", "c"],
                       "Debit": [0.0, 500.0, 120.0], "Credit": [1000.0, 0.0, 0.0]})
    assert auditer_balance(df.copy())["niveau"] == "Critique"
    assert verifier_coherence(df.copy())["niveau"] == "Critique"


def test_benford_balance_avec_titres_ecarte_les_numeros_de_compte():
    from utils.benford_module import charger_donnees_benford, colonnes_montants
    rows = [["SARL DEMO - Balance", "", ""], ["N° compte", "Solde débiteur", "Solde créditeur"]] + \
        [[l[0], f"{l[5]:.2f}".replace(".", ",") if l[5] else "", f"{l[6]:.2f}".replace(".", ",") if l[6] else ""] for l in _lignes()]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, header=False, index=False)
    df, err = charger_donnees_benford(Fichier(buf.getvalue(), "b.xlsx"))
    cols, (deb, cre) = colonnes_montants(df)
    assert err is None and (deb, cre) == ("Debit", "Credit")
