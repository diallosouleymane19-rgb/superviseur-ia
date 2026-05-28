# -*- coding: utf-8 -*-
"""
utils/connectors/sage_connector.py - SMD Consulting
Connecteur Sage Business Cloud Comptabilite (API REST OAuth2).
Doc : https://developer.sage.com/accounting/reference/
Compatible Sage 50cloud, Sage Business Cloud.
"""

import requests
import pandas as pd
from utils.connectors.base import BaseConnector


class SageConnector(BaseConnector):

    NOM      = "Sage"
    ICONE    = "🟩"
    DOCS_URL = "https://developer.sage.com/accounting/reference/"
    BASE_URL = "https://api.accounting.sage.com/v3.1"

    # credentials : access_token, refresh_token (optionnel)

    def _headers(self):
        return {
            "Authorization": "Bearer " + self.credentials.get("access_token", ""),
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        }

    def _get(self, endpoint, params=None):
        r = requests.get(
            self.BASE_URL + endpoint,
            headers=self._headers(),
            params=params or {},
            timeout=30
        )
        r.raise_for_status()
        return r.json()

    def tester_connexion(self) -> dict:
        try:
            data = self._get("/business")
            nom  = data.get("name", data.get("company_name", "inconnu"))
            self._connected = True
            return {"ok": True, "info": "Sage — " + str(nom)}
        except Exception as e:
            return {"error": str(e)}

    # ─── Balance ──────────────────────────────────────────────────────────────

    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        try:
            params = {
                "attributes": "displayed_as,nominal_code,debit_amount,credit_amount",
                "items_per_page": 200, "page": 1
            }
            rows = []
            while True:
                data  = self._get("/trial_balance", params)
                items = data.get("$items", data.get("items", []))
                for a in items:
                    debit  = float(a.get("debit_amount", {}).get("amount", 0) or 0)
                    credit = float(a.get("credit_amount", {}).get("amount", 0) or 0)
                    rows.append({
                        "compte":  str(a.get("nominal_code", "")),
                        "libelle": str(a.get("displayed_as", a.get("name", ""))),
                        "debit":   debit,
                        "credit":  credit,
                        "solde":   debit - credit,
                    })
                meta = data.get("$pagination", {})
                if meta.get("page_number", 1) >= meta.get("page_count", 1):
                    break
                params["page"] += 1
            df = pd.DataFrame(rows) if rows else self._df_balance_vide()
            return df.sort_values("compte").reset_index(drop=True)
        except Exception as e:
            return self._df_balance_vide()

    # ─── Ecritures ────────────────────────────────────────────────────────────

    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        try:
            params = {
                "from_date": str(exercice) + "-01-01",
                "to_date":   str(exercice) + "-12-31",
                "items_per_page": 200, "page": 1
            }
            rows = []
            while True:
                data  = self._get("/journal_codes/journals", params)
                items = data.get("$items", data.get("items", []))
                for j in items:
                    jcode = str(j.get("code", j.get("journal_type", {}).get("id", "OD")))
                    jlib  = str(j.get("displayed_as", j.get("description", "")))
                    for line in j.get("journal_lines", [j]):
                        acc = line.get("ledger_account", {})
                        rows.append({
                            "JournalCode":  jcode[:6],
                            "JournalLib":   jlib,
                            "EcritureNum":  str(j.get("transaction_id", j.get("id", ""))),
                            "EcritureDate": self._normaliser_date(j.get("date", "")),
                            "CompteNum":    str(acc.get("nominal_code", acc.get("id", ""))),
                            "CompteLib":    str(acc.get("displayed_as", "")),
                            "PieceRef":     str(j.get("reference", "") or ""),
                            "PieceDate":    self._normaliser_date(j.get("date", "")),
                            "EcritureLib":  str(line.get("description", j.get("description", "")) or ""),
                            "Debit":        self._montant(line.get("debit_or_credit", "") == "D" and line.get("amount", {}).get("amount", 0) or 0),
                            "Credit":       self._montant(line.get("debit_or_credit", "") == "C" and line.get("amount", {}).get("amount", 0) or 0),
                            "EcritureLet":  "",
                        })
                meta = data.get("$pagination", {})
                if meta.get("page_number", 1) >= meta.get("page_count", 1):
                    break
                params["page"] += 1
            return pd.DataFrame(rows) if rows else self._df_ecritures_vide()
        except Exception as e:
            return self._df_ecritures_vide()

    # ─── Factures ─────────────────────────────────────────────────────────────

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        try:
            endpoint = "/purchase_invoices" if type_piece == "fournisseur" else "/sales_invoices"
            params   = {"items_per_page": min(limit, 200), "page": 1}
            if exercice:
                params["from_date"] = str(exercice) + "-01-01"
                params["to_date"]   = str(exercice) + "-12-31"
            rows = []
            while len(rows) < limit:
                data  = self._get(endpoint, params)
                items = data.get("$items", data.get("items", []))
                for f in items:
                    tier = f.get("contact", {})
                    rows.append({
                        "numero":            str(f.get("invoice_number", f.get("reference", ""))),
                        "date":              str(f.get("date", "")),
                        "fournisseur_client": str(tier.get("displayed_as", tier.get("name", ""))),
                        "montant_ht":        self._montant(f.get("net_amount", {}).get("amount", 0)),
                        "tva":               self._montant(f.get("tax_amount", {}).get("amount", 0)),
                        "montant_ttc":       self._montant(f.get("total_amount", {}).get("amount", 0)),
                        "statut":            str(f.get("status", {}).get("id", "")),
                        "reference":         str(f.get("reference", "") or ""),
                    })
                meta = data.get("$pagination", {})
                if meta.get("page_number", 1) >= meta.get("page_count", 1):
                    break
                params["page"] += 1
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
