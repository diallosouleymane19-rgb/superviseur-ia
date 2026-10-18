# -*- coding: utf-8 -*-
"""
Tests automatiques des calculs KontrolIA (PCG France).
Chaque résultat attendu est calculé à la main à partir d'une balance de référence (détail en commentaire).
Lancer : python -m pytest tests -q
"""
from datetime import date, datetime

import pandas as pd
import pytest

A = pytest.approx


def balance(lignes):
    """[(compte, debit, credit)] -> DataFrame CompteNum / Debit / Credit."""
    return pd.DataFrame(lignes, columns=["CompteNum", "Debit", "Credit"])


# ─── Balance de référence N (avant affectation) ──────────────────────────────
# Charges 156 000 au débit, 6037 crédit 5 000 ; produits 170 500 ; résultat 19 500.
BAL_N = balance([
    ("101", 0, 50000), ("106", 0, 10000), ("164", 0, 30000),
    ("2154", 60000, 0), ("28154", 0, 20000),
    ("37", 15000, 0),
    ("411", 24000, 0), ("491", 0, 2000), ("401", 0, 18000), ("409", 1000, 0),
    ("421", 0, 3000), ("431", 0, 4000), ("44566", 2000, 0), ("44571", 0, 5000),
    ("486", 500, 0),
    ("512", 60500, 0), ("5121", 0, 1500),
    ("607", 80000, 0), ("6037", 0, 5000), ("613", 12000, 0), ("626", 3000, 0), ("635", 2000, 0),
    ("641", 30000, 0), ("645", 12000, 0), ("6811", 10000, 0), ("6817", 2000, 0), ("661", 1500, 0),
    ("671", 500, 0), ("695", 3000, 0),
    ("707", 0, 150000), ("706", 0, 20000), ("764", 0, 200), ("771", 0, 300),
])

# ─── Balance N-1 (avant affectation) : résultat 8 000, dont 5 000 mis en réserve et 3 000 distribués en N
BAL_N1 = balance([
    ("101", 0, 50000), ("106", 0, 5000), ("164", 0, 40000),
    ("2154", 45000, 0), ("28154", 0, 10000),
    ("37", 10000, 0), ("411", 20000, 0), ("401", 0, 15000),
    ("421", 0, 2000), ("431", 0, 3000), ("44566", 1000, 0), ("44571", 0, 4000),
    ("512", 61000, 0),
    ("607", 92000, 0), ("707", 0, 100000),
])


def test_balances_de_reference_equilibrees():
    for b in (BAL_N, BAL_N1):
        assert b["Debit"].sum() == b["Credit"].sum()


# ═══ Soldes intermédiaires de gestion ════════════════════════════════════════

def test_sig():
    from utils.sig_pcg import calculer_sig
    k = calculer_sig(BAL_N)
    assert k["chiffre_affaires"] == A(170000)
    assert k["ventes_marchandises"] == A(150000)
    assert k["cout_achat_marchandises"] == A(75000)        # 80 000 - 5 000 (stock en hausse)
    assert k["marge_commerciale"] == A(75000)
    assert k["production_exercice"] == A(20000)
    assert k["consommations_tiers"] == A(15000)            # 613 + 626
    assert k["valeur_ajoutee"] == A(80000)
    assert k["ebe"] == A(36000)                            # 80 000 - 2 000 - 42 000
    assert k["resultat_exploitation"] == A(24000)          # - 6811 - 6817
    assert k["resultat_financier"] == A(-1300)
    assert k["resultat_courant"] == A(22700)
    assert k["resultat_exceptionnel"] == A(-200)
    assert k["resultat_net"] == A(19500)
    assert k["ecart_controle"] == A(0)


def test_sig_quote_part_operations_en_commun_hors_exploitation():
    """PCG : 655 / 755 sont entre le résultat d'exploitation et le résultat courant."""
    from utils.sig_pcg import calculer_sig
    k = calculer_sig(balance([("706", 0, 1000), ("755", 0, 300), ("655", 100, 0), ("512", 0, 0)]))
    assert k["resultat_exploitation"] == A(1000)
    assert k["resultat_courant"] == A(1200)
    assert k["resultat_net"] == A(1200)
    assert k["ecart_controle"] == A(0)


def test_sig_montants_en_texte_format_francais():
    from utils.sig_pcg import calculer_sig
    k = calculer_sig(pd.DataFrame({"CompteNum": ["706", "512"], "Debit": ["0", "1 234,50"],
                                   "Credit": ["1 234,50", "0"]}))
    assert k["chiffre_affaires"] == A(1234.5)


def test_formats_francais():
    from utils.sig_pcg import nb_fr, eur_fr, pct_fr, nb_fr_signe
    assert nb_fr(61497) == "61 497"
    assert nb_fr(-0.001) == "0"
    assert eur_fr(1234.5, 2) == "1 234,50 €"
    assert pct_fr(82.83) == "82,8 %"
    assert nb_fr_signe(5) == "+5"


# ═══ Compte de résultat ═══════════════════════════════════════════════════════

def test_compte_resultat():
    from utils.compte_resultat import calculer_compte_resultat
    r = calculer_compte_resultat(BAL_N)
    s = r["sig"]
    assert s["Chiffre d'affaires"] == A(170000)
    assert s["Marge commerciale"] == A(75000)
    assert s["Valeur ajoutée (VA)"] == A(80000)
    assert s["Excédent brut d'exploitation (EBE)"] == A(36000)
    assert s["Résultat net"] == A(19500)
    assert r["ecart_controle"] == A(0)
    assert r["ratios"]["Taux de marge commerciale (%)"] == A(50)
    assert r["ratios"]["Taux d'EBE (%)"] == A(36000 / 170000 * 100)
    assert r["charges"]["Charges sociales (645)"] == A(12000)


# ═══ Bilan ════════════════════════════════════════════════════════════════════

def test_bilan():
    from utils import bilan as B
    r = B.calculer_bilan(BAL_N, "31/12/2025")
    a, p, t = r["actif"], r["passif"], r["totaux"]
    assert a[B.AI_CORP] == A(40000)
    assert a[B.STOCKS] == A(15000)
    assert a[B.CLIENTS] == A(22000)                 # 411 - 491
    assert a[B.AUTRES_CREANCES] == A(3000)          # 409 débiteur + 44566
    assert a[B.CCA] == A(500)
    assert a[B.DISPO] == A(60500)
    assert a[B.TOTAL_ACTIF] == A(141000)
    assert p[B.CAPITAL] == A(60000)
    assert p[B.RESULTAT] == A(19500)
    assert p[B.TOTAL_CP] == A(79500)
    assert p[B.EMPRUNTS] == A(30000)
    assert p[B.CONCOURS] == A(1500)                 # 5121 créditeur
    assert p[B.FOURN] == A(18000)
    assert p[B.FISC_SOC] == A(12000)
    assert p[B.TOTAL_PASSIF] == A(141000)
    assert t["ecart"] == A(0)
    ratios = r["ratios"]
    assert ratios[B.R_FRNG] == A(69500)
    assert ratios[B.R_BFR] == A(10500)
    assert ratios[B.R_TN] == A(59000)
    assert ratios[B.R_FRNG] - ratios[B.R_BFR] == A(ratios[B.R_TN])
    assert not any(x["type"] == "CRITIQUE" for x in r["analyse"])


def test_bilan_apres_cloture_resultat_en_12():
    from utils import bilan as B
    r = B.calculer_bilan(balance([("101", 0, 1000), ("120", 0, 500), ("512", 1500, 0)]))
    assert r["passif"][B.RESULTAT] == A(500)
    assert r["totaux"]["ecart"] == A(0)


def test_bilan_balance_desequilibree_signalee():
    from utils.bilan import calculer_bilan
    r = calculer_bilan(balance([("101", 0, 1000), ("512", 900, 0)]))
    assert r.get("balance_desequilibree") is True


# ═══ TVA ══════════════════════════════════════════════════════════════════════

def test_tva_saisie():
    from utils.tva import _calculer_tva
    r = _calculer_tva({"Ventes soumises à 20%": 10000, "Ventes soumises à 5,5%": 2000,
                       "Acquisitions intracommunautaires (20%)": 1000,
                       "TVA déductible sur achats (ABS)": 1500, "TVA déductible sur immobilisations": 400,
                       "TVA intracommunautaire déductible": 200, "Crédit de TVA période précédente": 100})
    assert r["tva_collectee"] == A(2310)          # 2 000 + 110 + 200
    assert r["tva_deductible"] == A(2100)
    assert r["a_payer"] == A(110)
    assert r["credit_genere"] == A(0)


def test_tva_credit():
    from utils.tva import _calculer_tva
    r = _calculer_tva({"Ventes soumises à 10%": 1000, "TVA déductible sur achats (ABS)": 300})
    assert r["credit_genere"] == A(200)
    assert r["a_payer"] == A(0)


def test_tva_depuis_balance():
    from utils.tva import _extraire_tva_depuis_balance, _calculer_tva_depuis_balance_extrait
    e = _extraire_tva_depuis_balance(BAL_N)
    assert e["TVA collectée (44571)"] == A(5000)
    assert e["TVA déductible ABS (44566)"] == A(2000)
    r = _calculer_tva_depuis_balance_extrait(e)
    assert r["a_payer"] == A(3000)


def test_tva_pdf_lignes_officielles_ca3():
    """Numéros de lignes du formulaire 3310-CA3-SD (08 = 20 %, 9B = 10 %, 09 = 5,5 %, B2 acquisitions intracom.,
    16 TVA brute, 23 TVA déductible y compris le report 22, TD / 28 TVA due, 25 / 27 crédit)."""
    import io
    from pypdf import PdfReader
    from utils.tva import _calculer_tva, _generer_pdf_ca3_ca12
    data = {"Ventes soumises à 20%": 10000, "Ventes soumises à 10%": 1000, "Ventes soumises à 5,5%": 2000,
            "Acquisitions intracommunautaires (20%)": 1000, "TVA déductible sur achats (ABS)": 1500,
            "Crédit de TVA période précédente": 100}
    res = _calculer_tva(data)
    texte = "".join(p.extract_text() for p in PdfReader(io.BytesIO(
        _generer_pdf_ca3_ca12(res, data, "09/2026", "Test", "CA3 — Réel normal"))).pages)
    for attendu in ("9B", "B2", "TD", "28"):
        assert attendu in texte, attendu
    assert "1 600,00" in texte                     # ligne 23 = 1 500 + report 100
    assert "Autoliquidation — Achats" not in texte


@pytest.mark.parametrize("data", [
    {"Ventes soumises à 20%": 10000, "Acquisitions intracommunautaires (20%)": 1000,
     "TVA déductible sur achats (ABS)": 1500, "TVA intracommunautaire déductible": 200,
     "Crédit de TVA période précédente": 100},                                  # TVA due 300
    {"Ventes soumises à 10%": 1000, "TVA déductible sur immobilisations": 900,
     "Crédit de TVA période précédente": 50},                                    # crédit 850
])
def test_tva_ecriture_liquidation_equilibree(data):
    from utils.tva import _calculer_tva, ecriture_liquidation
    res = _calculer_tva(data)
    lignes = ecriture_liquidation(res)
    assert sum(d for _, _, d, _ in lignes) == A(sum(c for _, _, _, c in lignes))
    comptes = {c for c, *_ in lignes}
    assert ("44551" in comptes) == (res["a_payer"] > 0)
    if "Acquisitions intracommunautaires (20%)" in data:
        assert "4452" in comptes


# ═══ Tableau de flux de trésorerie ═══════════════════════════════════════════

def test_tft():
    from utils.tft import _extraire_tft
    v = _extraire_tft(BAL_N, BAL_N1)
    assert v["Résultat net (bénéfice + / perte -)"] == A(19500)
    assert v["Dotations aux amortissements et provisions (nettes de reprises)"] == A(12000)
    assert v["Variation des stocks (augmentation -)"] == A(-5000)
    assert v["Variation des créances d'exploitation (augmentation -)"] == A(-5000)
    assert v["Variation des dettes d'exploitation (augmentation +)"] == A(5000)
    assert v["Variation des autres créances (augmentation -)"] == A(-500)
    assert v["Acquisitions d'immobilisations corporelles"] == A(-15000)
    assert v["Remboursements d'emprunts"] == A(-10000)
    assert v["Dividendes versés aux actionnaires"] == A(-3000)
    assert v["_treso_ouverture"] == A(61000)
    assert v["_treso_cloture"] == A(59000)
    flux = sum(x for k, x in v.items() if not k.startswith("_"))
    assert flux == A(-2000)
    assert not v["_alertes"]


def test_tft_subvention_investissement():
    """Subvention reçue 10 000 (financement), dont 1 000 virés au résultat (777, sans effet de trésorerie)."""
    from utils.tft import _extraire_tft
    n1 = balance([("101", 0, 1000), ("512", 1000, 0)])
    n = balance([("101", 0, 1000), ("131", 0, 10000), ("139", 1000, 0), ("512", 10000, 0),
                 ("777", 0, 1000), ("613", 1000, 0)])    # résultat 0 ; loyer payé 1 000
    v = _extraire_tft(n, n1)
    assert v["Subventions d'investissement reçues"] == A(10000)
    assert v["Quote-part des subventions d'investissement virée au résultat"] == A(-1000)
    flux = sum(x for k, x in v.items() if not k.startswith("_"))
    assert flux == A(9000)
    assert not v["_alertes"]


def test_tft_cession():
    """Machine 10 000 amortie 6 000 cédée 5 000 ; dotation de l'exercice 2 000."""
    from utils.tft import _extraire_tft
    n1 = balance([("101", 0, 10000), ("2154", 10000, 0), ("28154", 0, 4000), ("512", 4000, 0)])
    n = balance([("101", 0, 10000), ("512", 9000, 0), ("6811", 2000, 0), ("675", 4000, 0), ("775", 0, 5000)])
    for vnc, prix in (("675", "775"), ("657", "757")):    # PCG avant 2025, puis règlement ANC 2022-06
        n = balance([("101", 0, 10000), ("512", 9000, 0), ("6811", 2000, 0), (vnc, 4000, 0), (prix, 0, 5000)])
        v = _extraire_tft(n, n1)
        assert v["Cessions d'immobilisations corporelles et incorporelles"] == A(5000)
        assert v["Plus-values de cessions nettes d'impôts"] == A(-1000)
        flux = sum(x for k, x in v.items() if not k.startswith("_"))
        assert flux == A(5000)
        assert len(v["_alertes"]) == 1             # seulement l'information « cessions détectées »


def test_tft_calcul_sections():
    from utils.tft import _calculer_tft
    r = _calculer_tft({"Résultat net (bénéfice + / perte -)": {"N": 100},
                       "Acquisitions d'immobilisations corporelles": {"N": -40},
                       "Remboursements d'emprunts": {"N": -10},
                       "Trésorerie à l'ouverture": {"N": 5}}, ["N"])["N"]
    assert r["Variation nette (I+II+III)"] == A(50)
    assert r["Trésorerie clôture"] == A(55)


# ═══ Immobilisations ══════════════════════════════════════════════════════════

def test_amortissement_lineaire_prorata():
    from utils.immobilisations import calculer_amortissement_lineaire
    t = calculer_amortissement_lineaire(10000, 5, date(2024, 4, 1))   # 270 jours / 360 la 1re année
    assert list(t["Année"]) == [2024, 2025, 2026, 2027, 2028, 2029]
    assert list(t["Dotation (€)"]) == A([1500, 2000, 2000, 2000, 2000, 500])
    assert t["Dotation (€)"].sum() == A(10000)
    assert t["VNC (€)"].iloc[-1] == A(0)


def test_amortissement_lineaire_premier_janvier():
    from utils.immobilisations import calculer_amortissement_lineaire
    t = calculer_amortissement_lineaire(9000, 3, date(2025, 1, 1))
    assert list(t["Dotation (€)"]) == A([3000, 3000, 3000])


def test_amortissement_degressif():
    from utils.immobilisations import calculer_amortissement_degressif
    t = calculer_amortissement_degressif(10000, 5, date(2024, 4, 1))   # coefficient 1,75 : taux 35 %
    assert t["Taux Dégressif (%)"].iloc[0] == A(35)
    assert list(t["Dotation (€)"]) == A([2625, 2581.25, 1677.81, 1557.97, 1557.97])
    assert t["Dotation (€)"].sum() == A(10000)
    assert t["VNC Fin (€)"].iloc[-1] == A(0)


@pytest.mark.parametrize("duree,coeff", [(3, 1.25), (4, 1.25), (5, 1.75), (6, 1.75), (7, 2.25), (12, 2.25)])
def test_coefficients_degressifs(duree, coeff):
    from utils.immobilisations import calculer_amortissement_degressif
    t = calculer_amortissement_degressif(1000, duree, date(2025, 1, 1))
    assert t["Taux Dégressif (%)"].iloc[0] == A(round(100 / duree * coeff, 2))


def test_degressif_refuse_moins_de_3_ans():
    from utils.immobilisations import calculer_amortissement_degressif
    with pytest.raises(ValueError):
        calculer_amortissement_degressif(1000, 2, date(2025, 1, 1))


@pytest.mark.parametrize("prix,resultat,jour,cpt_prix,cpt_vnc", [
    (5000, 1000, date(2025, 6, 30), "757", "657"), (3000, -1000, date(2025, 6, 30), "757", "657"),
    (5000, 1000, date(2024, 6, 30), "775", "675")])
def test_cession_ecriture_equilibree(prix, resultat, jour, cpt_prix, cpt_vnc):
    """Cession : 512 / 757 pour le prix ; 28 + 657 / 2 pour la sortie (règlement ANC 2022-06, exercices
    ouverts depuis 2025) ; 775 / 675 avant."""
    from utils.immobilisations import calculer_cession
    r = calculer_cession(10000, 6000, prix, jour)
    assert r["vnc"] == A(4000)
    assert r["resultat_cession"] == A(resultat)
    e = r["ecritures"]
    assert e["Débit"].sum() == A(e["Crédit"].sum())
    par_compte = {c: (d, k) for c, d, k in zip(e["Compte"], e["Débit"], e["Crédit"])}
    assert par_compte[cpt_prix] == (0, A(prix))
    assert par_compte[cpt_vnc] == (A(4000), 0)
    assert par_compte["28xx"] == (A(6000), 0)
    assert par_compte["2xxx"] == (0, A(10000))


def test_caf_et_sig_pcg_2025():
    """747 (quote-part de subvention virée) hors EBE mais dans le résultat d'exploitation ; 657/757 : cession
    neutralisée dans la CAF."""
    from utils.sig_pcg import calculer_sig
    from utils.plan_financement import _extraire_caf_bfr_pcg
    b = balance([("101", 0, 10000), ("512", 15000, 0), ("641", 1000, 0), ("706", 0, 5000),
                 ("747", 0, 500), ("657", 4000, 0), ("757", 0, 4500)])
    k = calculer_sig(b)
    assert k["ebe"] == A(4000)
    assert k["resultat_exploitation"] == A(5000) and k["resultat_net"] == A(5000)
    csv = "Compte;Débit;Crédit\n" + "\n".join(f"{c};{d};{x}" for c, d, x in b.itertuples(index=False))
    caf = _extraire_caf_bfr_pcg(csv.encode(), "b.csv")["CAF"]
    assert caf == A(5000 + 4000 - 4500 - 500)


# ═══ Travaux d'inventaire ═════════════════════════════════════════════════════

def test_provision_creances_sur_ht():
    from utils.inventaire import calculer_provision_creances
    df = pd.DataFrame([{"Client": "A", "Montant TTC": 1200, "TVA (%)": 20, "Ancienneté": 120},
                       {"Client": "B", "Montant TTC": 600, "TVA (%)": 20, "Ancienneté": 400},
                       {"Client": "C", "Montant TTC": 900, "TVA (%)": 20, "Ancienneté": 30}])
    t, total = calculer_provision_creances(df)
    assert list(t["Dépréciation (€)"]) == A([250, 500, 0])
    assert total == A(750)


def test_regularisations_prorata_jours():
    from utils.inventaire import calculer_regularisations
    t = calculer_regularisations([
        {"type": "CCA", "libelle": "Assurance", "montant_total": 1200,
         "date_debut": date(2025, 7, 1), "date_fin": date(2026, 6, 30), "date_cloture": date(2025, 12, 31)},
        {"type": "CAP", "libelle": "Électricité", "montant_total": 900,
         "date_debut": date(2025, 11, 1), "date_fin": date(2026, 1, 31), "date_cloture": date(2025, 12, 31)},
    ])
    assert t["Montant régularisé (€)"].iloc[0] == A(round(1200 * 181 / 365, 2))   # part 2026 : 181 jours
    assert t["Compte"].iloc[0] == "486"
    assert t["Montant régularisé (€)"].iloc[1] == A(round(900 * 61 / 92, 2))      # nov. + déc.
    assert t["Compte"].iloc[1] == "408"


def test_variation_stock():
    from utils.inventaire import calculer_variation_stock
    r = calculer_variation_stock(10000, 12000, "marchandises")
    e = r["ecriture"]
    assert r["variation"] == A(2000)
    assert list(e["Compte"]) == ["37", "6037"] and list(e["Débit"]) == A([2000, 0])
    r = calculer_variation_stock(5000, 3000, "produits_finis")
    assert list(r["ecriture"]["Compte"]) == ["7135", "35"]


def test_provision_risque():
    from utils.inventaire import calculer_provision_risque
    assert calculer_provision_risque("Litige", 8000, "Probable")["provision"] == A(8000)
    assert calculer_provision_risque("Litige", 8000, "Possible, mais non probable")["provision"] == 0


# ═══ FEC ══════════════════════════════════════════════════════════════════════

def _fec(lignes):
    cols = ["JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum", "CompteLib", "CompAuxNum",
            "CompAuxLib", "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet",
            "ValidDate", "Montantdevise", "Idevise"]
    out = []
    for j, num, dt, cpt, d, c in lignes:
        out.append({"JournalCode": j, "JournalLib": j, "EcritureNum": num, "EcritureDate": dt, "CompteNum": cpt,
                    "CompteLib": cpt, "CompAuxNum": "", "CompAuxLib": "", "PieceRef": num, "PieceDate": dt,
                    "EcritureLib": "Lib", "Debit": d, "Credit": c, "EcritureLet": "", "DateLet": "",
                    "ValidDate": dt, "Montantdevise": "", "Idevise": ""})
    return pd.DataFrame(out, columns=cols)


def test_fec_conforme():
    from utils.fec import valider_fec
    r = valider_fec(_fec([("VT", "1", "20250105", "411", "120,00", "0,00"),
                          ("VT", "1", "20250105", "706", "0,00", "100,00"),
                          ("VT", "1", "20250105", "44571", "0,00", "20,00")]))
    assert r["_meta"]["score_conformite"] == 100


def test_fec_ecriture_desequilibree_detectee_meme_si_total_equilibre():
    """DGFiP : chaque écriture doit être équilibrée, pas seulement le total."""
    from utils.fec import valider_fec
    r = valider_fec(_fec([("VT", "1", "20250105", "411", "100,00", "0,00"),
                          ("VT", "1", "20250105", "706", "0,00", "90,00"),
                          ("VT", "2", "20250106", "411", "90,00", "0,00"),
                          ("VT", "2", "20250106", "706", "0,00", "100,00")]))
    assert r["_meta"]["score_conformite"] < 100
    assert any(not v["valide"] for k, v in r.items() if k != "_meta" and "quilibre" in k)


def test_fec_date_invalide_apres_100_lignes():
    from utils.fec import valider_fec
    lignes = [("VT", str(i), "20250105", "411", "1,00", "0,00") for i in range(150)]
    lignes += [("VT", str(i), "05/01/2025", "706", "0,00", "1,00") for i in range(150)]
    r = valider_fec(_fec(lignes))
    assert not r["Format dates (AAAAMMJJ)"]["valide"]


def test_fec_format_montant_sens():
    """A47 A-1 : le FEC peut présenter Montant + Sens (D/C) au lieu de Debit / Credit."""
    from utils.fec import valider_fec
    df = _fec([("VT", "1", "20250105", "411", "120,00", "0,00"), ("VT", "1", "20250105", "706", "0,00", "120,00")])
    df = df.drop(columns=["Debit", "Credit"]).assign(Montant=["120,00", "120,00"], Sens=["D", "C"])
    r = valider_fec(df)
    assert r["_meta"]["score_conformite"] == 100


def test_fec_anomalies():
    from utils.fec import detecter_anomalies_fec
    df = _fec([("VT", "1", "20250105", "411", "0,00", "0,00")] * 2)
    types = {a["type"] for a in detecter_anomalies_fec(df)}
    assert {"Écritures montants nuls", "Doublons exacts"} <= types


# ═══ Loi de Benford ═══════════════════════════════════════════════════════════

def test_benford_theorique():
    from utils.benford_module import loi_benford_theorique, extraire_premier_chiffre, _nombres
    assert sum(loi_benford_theorique(d) for d in range(1, 10)) == A(1)
    assert loi_benford_theorique(1) == A(0.30103, rel=1e-4)
    assert extraire_premier_chiffre(0.0456) == 4
    assert extraire_premier_chiffre(-987.1) == 9
    assert extraire_premier_chiffre(0) is None
    v = _nombres(pd.Series(["1 234,56", "1234.56", "1.234,56", "-12,5", "411000", "abc"]))
    assert list(v[:4]) == A([1234.56, 1234.56, 1234.56, -12.5])
    assert pd.isna(v.iloc[5])


# ═══ Lecture des balances (exports de logiciels) ══════════════════════════════

def _fichier(chemin_ou_octets, nom):
    import io
    b = io.BytesIO(open(chemin_ou_octets, "rb").read() if isinstance(chemin_ou_octets, str) else chemin_ou_octets)
    b.name = nom
    return b


def test_balance_sans_entete_avec_sous_totaux():
    """Export brut sans en-tête : compte, libellé, mouvements D/C, soldes D/C et lignes « ** » de sous-totaux."""
    import os
    from utils.intelligent_parser import charger_balance_ou_fec
    from utils import bilan as B
    from utils.sig_pcg import calculer_sig
    df, _, info = charger_balance_ou_fec(_fichier(os.path.join(os.path.dirname(__file__), "BALANCE-TEST.xlsx"),
                                                  "BALANCE-TEST.xlsx"))
    assert info["colonnes_mappees"] == {"col_0": "CompteNum", "col_1": "CompteLib", "col_4": "Debit", "col_5": "Credit"}
    comptes = set(df["CompteNum"].astype(str))
    assert not comptes & {"1", "7", "10", "12", "70", "701", "707"}          # sous-totaux retirés
    assert {"10100", "701005", "707100"} <= comptes
    r = B.calculer_bilan(df)
    assert r["totaux"]["ecart_balance"] == A(0) and r["totaux"]["ecart"] == A(0)
    k = calculer_sig(df)
    assert k["chiffre_affaires"] == A(901876.45)                            # sous-total « 70 » du fichier
    assert k["ecart_controle"] == A(0)


def test_balance_csv_avec_entete_et_sous_total_par_racine():
    from utils.intelligent_parser import charger_balance_ou_fec
    csv = ("Compte;Libellé;Débit;Crédit\n401000;Fournisseur A;;1 200,00\n401100;Fournisseur B;;300,00\n"
           "401;Total 401;;1 500,00\n512000;Banque;1 500,00;\n").encode("cp1252")
    df, _, info = charger_balance_ou_fec(_fichier(csv, "balance.csv"))
    assert list(df["CompteNum"].astype(str)) == ["401000", "401100", "512000"]
    from utils.bilan import calculer_bilan
    assert calculer_bilan(df)["totaux"]["ecart_balance"] == A(0)


def test_racine_conservee_si_ce_n_est_pas_un_sous_total():
    from utils.intelligent_parser import nettoyer_balance
    df = balance([("411", 100, 0), ("411DUPONT", 50, 0), ("706", 0, 150)])
    assert len(nettoyer_balance(df)) == 3


def test_fichier_sans_numero_de_compte_refuse():
    """Colonnes mal reconnues : erreur claire, jamais « balance équilibrée »."""
    from utils.bilan import calculer_bilan
    from utils.compte_resultat import calculer_compte_resultat
    df = pd.DataFrame({"CompteNum": ["Capital", "Banque"], "Debit": [0, 100], "Credit": [100, 0]})
    assert "erreur" in calculer_bilan(df)
    assert "erreur" in calculer_compte_resultat(df)


# ═══ Contrôle de balance, alertes, cohérence ══════════════════════════════════

def test_audit_balance_colonnes_accentuees():
    from utils.audit_balance import auditer_balance
    df = pd.DataFrame({"Compte": ["512", "706"], "Libellé": ["Banque", "Ventes"],
                       "Débit": ["100,00", "0"], "Crédit": ["0", "100,00"]})
    a = auditer_balance(df)
    assert a["controles"]["Équilibre Débit/Crédit"]["statut"] == "OK"
    assert a["kpis"]["produits_totaux"] == A(100)


def test_audit_balance_desequilibre():
    from utils.audit_balance import auditer_balance
    a = auditer_balance(balance([("512", 100, 0), ("706", 0, 90)]))
    assert a["controles"]["Équilibre Débit/Crédit"]["statut"] == "KO"


def test_alertes_balance_sans_fausse_alerte_debit_credit():
    from utils.alertes import detecter_alertes
    titres = {a["titre"] for a in detecter_alertes(balance([("401", 500, 800), ("512", 800, 500)]))}
    assert "Débit ET Crédit simultanés" not in titres
    fec = _fec([("BQ", "1", "20250106", "512", "10,00", "10,00"), ("BQ", "1", "20250106", "401", "0", "0")])
    titres = {a["titre"] for a in detecter_alertes(fec)}
    assert "Débit ET Crédit simultanés" in titres


def test_alertes_montants_tres_eleves():
    from utils.alertes import detecter_alertes
    lignes = [(str(600000 + i), 100 + i, 0) for i in range(40)] + [("218", 1_000_000, 0)]
    titres = {a["titre"] for a in detecter_alertes(balance(lignes))}
    assert "Montants très élevés" in titres
    titres = {a["titre"] for a in detecter_alertes(balance(lignes[:40]))}
    assert "Montants très élevés" not in titres


def test_coherence_score():
    from utils.coherence import verifier_coherence
    r = verifier_coherence(balance([("512", 100, 0), ("706", 0, 100)]))
    assert r["score_qualite"] == 100


# ═══ Rapprochement bancaire ═══════════════════════════════════════════════════

def test_rapprochement_respecte_le_sens():
    """Un encaissement de 500 ne doit pas être rapproché d'un décaissement de 500."""
    from utils.rapprochement import rapprocher_bancaire
    releve = pd.DataFrame({"Date": ["02/03/2026", "05/03/2026"], "Libellé": ["VIR CLIENT DUPONT", "PRLV EDF"],
                           "Débit": ["", "500,00"], "Crédit": ["1 200,00", ""]})
    ecr = pd.DataFrame({"Date": ["01/03/2026", "05/03/2026", "06/03/2026"],
                        "Libellé": ["Client Dupont", "Remboursement trop-perçu", "EDF mars"],
                        "Débit": ["1200", "500", "0"], "Crédit": ["0", "0", "500"]})
    r = rapprocher_bancaire(releve, ecr)
    assert r["nb_rapproches"] == 2
    assert r["nb_non_rapproches_ecritures"] == 1
    assert r["non_rapproches_ecritures"]["Libellé"].iloc[0] == "Remboursement trop-perçu"


def test_rapprochement_montant_signe_convention_inverse():
    from utils.rapprochement import rapprocher_bancaire
    releve = pd.DataFrame({"Date": ["02/03/2026", "05/03/2026"], "Libellé": ["VIR", "CB"],
                           "Montant": ["-1200", "300"]})                  # relevé signé à l'envers
    ecr = pd.DataFrame({"Date": ["02/03/2026", "05/03/2026"], "Libellé": ["Client", "Achat"],
                        "Débit": ["1200", "0"], "Crédit": ["0", "300"]})
    assert rapprocher_bancaire(releve, ecr)["nb_rapproches"] == 2


# ═══ Factures ═════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("texte,attendu", [("2 500,00 €", 2500.0), ("2,500.00", 2500.0), ("18.32", 18.32),
                                           ("1.234,56", 1234.56), ("-45,5", -45.5), ("abc", None)])
def test_parse_montant(texte, attendu):
    from utils.compta_facture import parse_montant
    assert parse_montant(texte) == attendu


def test_parse_date_et_siren():
    from utils.compta_facture import parse_date, date_en_lettres, siren_valide
    assert parse_date("20/04/2026") == datetime(2026, 4, 20)
    assert parse_date("2026-04-20") == datetime(2026, 4, 20)
    assert date_en_lettres("9 septembre 2026") == datetime(2026, 9, 9)
    assert siren_valide("443 061 841") and not siren_valide("123456789")


FACTURE_TELECOM = """FACTURE N° FA-2026-0142
Date : 15/09/2026
ORANGE BUSINESS SERVICES
SIREN 443061841
Client : SMD GLOBAL CONSULTING LLC
Désignation : Abonnement téléphonie mobile et internet septembre 2026
Total HT : 100,00 €
TVA 20 % : 20,00 €
Total TTC : 120,00 €
"""

FACTURE_ORDINATEUR = """FACTURE N° 2026-77
Date : 02/10/2026
BUREAU PLUS SARL
SIREN 552032534
Client : SMD GLOBAL CONSULTING LLC
Désignation : Ordinateur portable Dell Latitude
Total HT : 1 250,00 €
TVA 20 % : 250,00 €
Total TTC : 1 500,00 €
"""


def _ecriture(texte, societe="SMD GLOBAL CONSULTING"):
    from utils.compta_facture import analyser
    r = analyser([{"texte": texte, "source": "f.pdf"}], ma_societe=societe)[0]
    lignes = r["ecriture"]["lignes"]
    assert sum(l["debit"] for l in lignes) == A(sum(l["credit"] for l in lignes))
    return r, {l["compte"]: (l["debit"], l["credit"]) for l in lignes}


def test_facture_achat_service():
    r, e = _ecriture(FACTURE_TELECOM)
    assert r["sens"] == "achat"
    assert r["donnees"]["ttc"] == A(120)
    assert e["626000"] == (A(100), 0)               # frais de télécommunications
    assert e["445800"] == (A(20), 0)                # TVA sur services : exigible au paiement
    assert e["401000"] == (0, A(120))


def test_facture_achat_immobilisation():
    r, e = _ecriture(FACTURE_ORDINATEUR)
    assert e["218300"] == (A(1250), 0)              # matériel de bureau et informatique
    assert e["445620"] == (A(250), 0)
    assert e["404000"] == (0, A(1500))              # fournisseur d'immobilisations


def test_facture_vente():
    texte = FACTURE_TELECOM.replace("ORANGE BUSINESS SERVICES", "SMD GLOBAL CONSULTING LLC") \
        .replace("Client : SMD GLOBAL CONSULTING LLC", "Client : CABINET MARTIN") \
        .replace("Abonnement téléphonie mobile et internet septembre 2026", "Mission de conseil comptable")
    r, e = _ecriture(texte)
    assert r["sens"] == "vente"
    assert e["411000"] == (A(120), 0)
    assert e["445800"] == (0, A(20))   # prestation de services : TVA exigible à l'encaissement


# ═══ Plan de financement, comparatif ═════════════════════════════════════════

def test_caf_et_bfr_depuis_balance():
    from utils.plan_financement import _extraire_caf_bfr_pcg
    csv = "Compte;Débit;Crédit\n" + "\n".join(f"{c};{d};{k}" for c, d, k in BAL_N.itertuples(index=False))
    r = _extraire_caf_bfr_pcg(csv.encode(), "balance.csv")
    assert r["Résultat net"] == A(19500)
    assert r["CAF"] == A(31500)                      # 19 500 + 12 000 de dotations
    assert r["BFR à la clôture"] == A(10500)


def test_ecart_comparatif():
    from utils.comparatif import _ecart
    assert _ecart(120, 100) == (20, A(20))
    assert _ecart(-50, -100) == (50, A(50))          # perte réduite : amélioration
    assert _ecart(10, 0) == (10, 100.0)


# ═══ Confidentialité : masquage avant envoi à l'IA ═══════════════════════════

def test_pseudonymisation_aller_retour():
    from utils.pseudonymisation import masquer, demasquer
    texte = ("Client DUPONT SARL, SIREN 443 061 841, TVA FR40443061841, IBAN FR76 3000 6000 0112 3456 7890 189, "
             "contact jean@dupont.fr, tél. 06 12 34 56 78. Montant 443061841,00 €")
    m, table = masquer(texte, noms=["DUPONT SARL"])
    for secret in ("DUPONT SARL", "443 061 841", "FR40443061841", "jean@dupont.fr", "06 12 34 56 78", "FR76 3000"):
        assert secret not in m, secret
    assert "443061841,00" in m                       # un montant n'est jamais masqué
    assert demasquer(m, table) == texte


# ═══ Facture électronique (UBL) ═══════════════════════════════════════════════

def test_facture_electronique_ubl():
    from utils.facture_electronique import lire_facture_xml
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>F-2026-001</cbc:ID><cbc:IssueDate>2026-09-15</cbc:IssueDate><cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
 <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
 <cac:AccountingSupplierParty><cac:Party><cac:PartyLegalEntity><cbc:RegistrationName>FOURNISSEUR SAS</cbc:RegistrationName>
  <cbc:CompanyID schemeID="0002">443061841</cbc:CompanyID></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
 <cac:AccountingCustomerParty><cac:Party><cac:PartyLegalEntity><cbc:RegistrationName>CLIENT SARL</cbc:RegistrationName>
  </cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>
 <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">40.00</cbc:TaxAmount>
  <cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">200.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="EUR">40.00</cbc:TaxAmount>
  <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>20</cbc:Percent></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
 <cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount currencyID="EUR">200.00</cbc:TaxExclusiveAmount>
  <cbc:TaxInclusiveAmount currencyID="EUR">240.00</cbc:TaxInclusiveAmount><cbc:PayableAmount currencyID="EUR">240.00</cbc:PayableAmount>
 </cac:LegalMonetaryTotal>
</Invoice>"""
    d, msg = lire_facture_xml(xml, "f.xml")
    assert msg == ""
    assert (d["numero"], d["ht"], d["tva"], d["ttc"]) == ("F-2026-001", A(200), A(40), A(240))
    assert d["fournisseur"] == "FOURNISSEUR SAS"
