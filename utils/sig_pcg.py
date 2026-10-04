# -*- coding: utf-8 -*-
"""
utils/sig_pcg.py - SMD Global Consulting LLC
Soldes intermédiaires de gestion et postes clés du bilan, selon le PCG
(règlement ANC 2014-03, système de base).

Entrée : DataFrame avec CompteNum, Debit, Credit (FEC ou balance).
Contrôle intégré : le résultat net issu des SIG doit égaler classe 7 - classe 6.
"""
import pandas as pd


def _preparer(df):
    d = df.copy()
    for col, cible in (("Debit", "_d"), ("Credit", "_c")):
        if col in d.columns:
            d[cible] = pd.to_numeric(
                d[col].astype(str).str.replace(" ", "").str.replace(" ", "").str.replace(",", "."),
                errors="coerce").fillna(0.0)
        else:
            d[cible] = 0.0
    d["_cpt"] = d["CompteNum"].astype(str).str.strip()
    return d


def _solde(d, prefixes, exclus=(), sens="credit"):
    """Solde des comptes commençant par un des préfixes (hors exclus).
    sens='credit' : crédit - débit ; sens='debit' : débit - crédit."""
    m = d["_cpt"].str.startswith(tuple(prefixes))
    if exclus:
        m &= ~d["_cpt"].str.startswith(tuple(exclus))
    s = d.loc[m, "_c"].sum() - d.loc[m, "_d"].sum()
    return float(s if sens == "credit" else -s)


def calculer_sig(df):
    """Retourne un dict avec les SIG, les postes du bilan et les ratios."""
    d = _preparer(df)
    c = lambda p, ex=(): _solde(d, p, ex, "credit")
    dbt = lambda p, ex=(): _solde(d, p, ex, "debit")

    # --- Activité ---
    chiffre_affaires = c(["70"])
    ventes_marchandises = c(["707", "7097"])
    cout_achat_marchandises = dbt(["607", "6037", "6097"])
    marge_commerciale = ventes_marchandises - cout_achat_marchandises

    production_vendue = c(["70"], ["707", "7097"])
    production_stockee = c(["71"])
    production_immobilisee = c(["72"])
    produits_operations_lt = c(["73"])
    production_exercice = production_vendue + production_stockee + production_immobilisee + produits_operations_lt

    consommations_tiers = dbt(["60"], ["607", "6037", "6097"]) + dbt(["61", "62"])
    valeur_ajoutee = marge_commerciale + production_exercice - consommations_tiers

    subventions = c(["74"])
    impots_taxes = dbt(["63"])
    charges_personnel = dbt(["64"])
    ebe = valeur_ajoutee + subventions - impots_taxes - charges_personnel

    resultat_exploitation = (ebe + c(["75"]) + c(["781"]) + c(["791"])
                             - dbt(["65"]) - dbt(["681"]))
    resultat_financier = c(["76"]) + c(["786"]) + c(["796"]) - dbt(["66"]) - dbt(["686"])
    resultat_courant = resultat_exploitation + resultat_financier
    resultat_exceptionnel = c(["77"]) + c(["787"]) + c(["797"]) - dbt(["67"]) - dbt(["687"])
    participation_impots = dbt(["69"])
    resultat_net = resultat_courant + resultat_exceptionnel - participation_impots

    # Contrôle : résultat par les SIG = produits (7) - charges (6)
    resultat_controle = c(["7"]) - dbt(["6"])
    ecart_controle = round(resultat_net - resultat_controle, 2)

    # --- Bilan (postes nets) ---
    immobilisations_nettes = dbt(["2"])                       # 28 et 29 en déduction
    stocks_nets = dbt(["3"])                                  # 39 en déduction
    creances_clients = dbt(["411", "413", "416", "417", "418", "491"])  # hors 419 (avances reçues)
    tresorerie_nette = dbt(["50", "51", "53", "54"])          # 519 concours bancaires déduits
    capital_social = c(["101", "108", "109"])                 # 109 non appelé en déduction
    capitaux_propres = c(["10", "11", "12", "13", "14"]) + resultat_net
    dettes_financieres = c(["16", "17"])
    dettes_fournisseurs = c(["401", "403", "404", "405", "408"])  # hors 409 (débiteurs)

    pct = lambda x, base: (x / base * 100) if base > 0 else 0.0

    return {
        "chiffre_affaires": chiffre_affaires,
        "ventes_marchandises": ventes_marchandises,
        "marge_commerciale": marge_commerciale,
        "production_exercice": production_exercice,
        "consommations_tiers": consommations_tiers,
        "valeur_ajoutee": valeur_ajoutee,
        "ebe": ebe,
        "resultat_exploitation": resultat_exploitation,
        "resultat_financier": resultat_financier,
        "resultat_courant": resultat_courant,
        "resultat_exceptionnel": resultat_exceptionnel,
        "resultat_net": resultat_net,
        "masse_salariale": charges_personnel,
        "total_produits": c(["7"]),
        "total_charges": dbt(["6"]),
        "ecart_controle": ecart_controle,
        "immobilisations": immobilisations_nettes,
        "stocks": stocks_nets,
        "creances_clients": creances_clients,
        "tresorerie": tresorerie_nette,
        "capital": capital_social,
        "capitaux_propres": capitaux_propres,
        "dettes_financieres": dettes_financieres,
        "dettes_fournisseurs": dettes_fournisseurs,
        "taux_marge_commerciale": pct(marge_commerciale, ventes_marchandises),
        "taux_va": pct(valeur_ajoutee, chiffre_affaires),
        "taux_ebe": pct(ebe, chiffre_affaires),
        "taux_rentabilite": pct(resultat_net, chiffre_affaires),
        "poids_charges_personnel": pct(charges_personnel, chiffre_affaires),
    }
