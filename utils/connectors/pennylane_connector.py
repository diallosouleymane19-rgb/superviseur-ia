# -*- coding: utf-8 -*-
"""
utils/connectors/pennylane_connector.py - SMD Global Consulting LLC
Connecteur Pennylane via API REST (cle API).
Doc : https://pennylane.readme.io/reference
"""

import requests
import pandas as pd
from utils.connectors.base import BaseConnector


class PennylaneConnector(BaseConnector):

    NOM      = "Pennylane"
    ICONE    = "🟡"
    DOCS_URL = "https://pennylane.readme.io/reference"
    BASE_URL = "https://app.pennylane.com/api/external/v1"

    # credentials : api_key, company_id (optionnel)

    def _headers(self):
        return {
            "Authorization": "Bearer " + self.credentials.get("api_key", ""),
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def _get(self, endpoint, params=None):
        url = self.BASE_URL + endpoint
        r = requests.get(url, headers=self._headers(), params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def tester_connexion(self) -> dict:
        try:
            data = self._get("/companies")
            companies = data.get("companies", data.get("data", []))
            if not self.credentials.get("company_id") and companies:
                self.credentials["company_id"] = companies[0].get("id", "")
            nom = companies[0].get("name", "inconnu") if companies else "inconnu"
            self._connected = True
            return {"ok": True, "info": "Pennylane — " + str(len(companies)) + " societe(s) — " + nom}
        except Exception as e:
            return {"error": str(e)}

    # ─── Balance ──────────────────────────────────────────────────────────────

    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        try:
            params = {
                "filter[min_date]": str(exercice) + "-01-01",
                "filter[max_date]": str(exercice) + "-12-31",
                "page": 1, "per_page": 500
            }
            data = self._get("/ledger_accounts", params)
            accounts = data.get("ledger_accounts", data.get("data", []))
            rows = []
            for a in accounts:
                debit  = float(a.get("debit_total", 0) or 0)
                credit = float(a.get("credit_total", 0) or 0)
                rows.append({
                    "compte":  str(a.get("number", a.get("code", ""))),
                    "libelle": str(a.get("label", a.get("name", ""))),
                    "debit":   debit,
                    "credit":  credit,
                    "solde":   debit - credit,
                })
            df = pd.DataFrame(rows) if rows else self._df_balance_vide()
            return df.sort_values("compte").reset_index(drop=True)
        except Exception as e:
            return self._df_balance_vide()

    # ─── Ecritures ────────────────────────────────────────────────────────────

    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        try:
            params = {
                "filter[min_date]": str(exercice) + "-01-01",
                "filter[max_date]": str(exercice) + "-12-31",
                "page": 1, "per_page": 500
            }
            rows = []
            while True:
                data  = self._get("/journal_entries", params)
                items = data.get("journal_entries", data.get("data", []))
                for e in items:
                    for line in e.get("journal_entry_lines", [e]):
                        acc = line.get("ledger_account", {})
                        rows.append({
                            "JournalCode":  str(e.get("source_type", "OD"))[:6],
                            "JournalLib":   str(e.get("source_type", "Operations diverses")),
                            "EcritureNum":  str(e.get("id", "")),
                            "EcritureDate": self._normaliser_date(e.get("date", "")),
                            "CompteNum":    str(acc.get("number", acc.get("code", ""))),
                            "CompteLib":    str(acc.get("label", acc.get("name", ""))),
                            "PieceRef":     str(e.get("reference", "") or ""),
                            "PieceDate":    self._normaliser_date(e.get("date", "")),
                            "EcritureLib":  str(line.get("description", e.get("label", "")) or ""),
                            "Debit":        self._montant(line.get("debit", 0)),
                            "Credit":       self._montant(line.get("credit", 0)),
                            "EcritureLet":  str(line.get("reconciliation_id", "") or ""),
                        })
                meta = data.get("meta", {})
                if params["page"] >= meta.get("total_pages", 1):
                    break
                params["page"] += 1
            return pd.DataFrame(rows) if rows else self._df_ecritures_vide()
        except Exception as e:
            return self._df_ecritures_vide()

    # ─── Factures ─────────────────────────────────────────────────────────────

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        try:
            endpoint = "/supplier_invoices" if type_piece == "fournisseur" else "/customer_invoices"
            params   = {"page": 1, "per_page": min(limit, 100)}
            if exercice:
                params["filter[min_date]"] = str(exercice) + "-01-01"
                params["filter[max_date]"] = str(exercice) + "-12-31"
            rows = []
            while len(rows) < limit:
                data  = self._get(endpoint, params)
                items = data.get("invoices", data.get("data", []))
                for f in items:
                    tier = f.get("supplier", f.get("customer", {})) or {}
                    rows.append({
                        "numero":            str(f.get("invoice_number", f.get("number", ""))),
                        "date":              str(f.get("date", "")),
                        "fournisseur_client": str(tier.get("name", tier.get("label", ""))),
                        "montant_ht":        self._montant(f.get("amount", 0)),
                        "tva":               self._montant(f.get("tax_amount", 0)),
                        "montant_ttc":       self._montant(f.get("total_amount", 0)),
                        "statut":            str(f.get("status", f.get("payment_status", ""))),
                        "reference":         str(f.get("reference", "") or ""),
                    })
                meta = data.get("meta", {})
                if params["page"] >= meta.get("total_pages", 1):
                    break
                params["page"] += 1
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
