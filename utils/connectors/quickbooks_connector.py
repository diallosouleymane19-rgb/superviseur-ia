# -*- coding: utf-8 -*-
"""
utils/connectors/quickbooks_connector.py - SMD Consulting
Connecteur QuickBooks Online via API REST OAuth2.
Doc : https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities
"""

import requests
import pandas as pd
from utils.connectors.base import BaseConnector


class QuickBooksConnector(BaseConnector):

    NOM      = "QuickBooks"
    ICONE    = "🟢"
    DOCS_URL = "https://developer.intuit.com/app/developer/qbo/docs"

    BASE_URL_PROD    = "https://quickbooks.api.intuit.com/v3/company/"
    BASE_URL_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company/"

    # credentials : access_token, realm_id (company_id), sandbox (bool)

    def _base(self):
        if self.credentials.get("sandbox", False):
            return self.BASE_URL_SANDBOX
        return self.BASE_URL_PROD

    def _headers(self):
        return {
            "Authorization": "Bearer " + self.credentials.get("access_token", ""),
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        }

    def _query(self, sql):
        realm = self.credentials.get("realm_id", "")
        url   = self._base() + realm + "/query"
        r = requests.get(url, headers=self._headers(),
                         params={"query": sql, "minorversion": "70"}, timeout=30)
        r.raise_for_status()
        return r.json().get("QueryResponse", {})

    def _report(self, report_name, params=None):
        realm = self.credentials.get("realm_id", "")
        url   = self._base() + realm + "/reports/" + report_name
        r = requests.get(url, headers=self._headers(),
                         params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def tester_connexion(self) -> dict:
        try:
            data = self._query("SELECT * FROM CompanyInfo MAXRESULTS 1")
            info = data.get("CompanyInfo", [{}])[0]
            nom  = info.get("CompanyName", "inconnu")
            self._connected = True
            return {"ok": True, "info": "QuickBooks — " + nom}
        except Exception as e:
            return {"error": str(e)}

    # ─── Balance ──────────────────────────────────────────────────────────────

    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        try:
            params = {
                "start_date": str(exercice) + "-01-01",
                "end_date":   str(exercice) + "-12-31",
                "accounting_method": "Accrual",
            }
            report = self._report("TrialBalance", params)
            rows   = []
            for section in report.get("Rows", {}).get("Row", []):
                for row in section.get("Rows", {}).get("Row", []):
                    cols = row.get("ColData", [])
                    if len(cols) >= 3:
                        rows.append({
                            "compte":  str(cols[0].get("id", "")),
                            "libelle": str(cols[0].get("value", "")),
                            "debit":   self._montant(cols[1].get("value", 0)),
                            "credit":  self._montant(cols[2].get("value", 0)),
                            "solde":   self._montant(cols[1].get("value", 0)) - self._montant(cols[2].get("value", 0)),
                        })
            df = pd.DataFrame(rows) if rows else self._df_balance_vide()
            return df[df["libelle"] != ""].reset_index(drop=True)
        except Exception as e:
            return self._df_balance_vide()

    # ─── Ecritures ────────────────────────────────────────────────────────────

    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        try:
            date_from = str(exercice) + "-01-01"
            date_to   = str(exercice) + "-12-31"
            sql = (
                "SELECT * FROM JournalEntry WHERE TxnDate >= '" + date_from
                + "' AND TxnDate <= '" + date_to + "' MAXRESULTS 1000"
            )
            data = self._query(sql)
            entries = data.get("JournalEntry", [])
            rows = []
            for je in entries:
                num  = str(je.get("DocNumber", je.get("Id", "")))
                date = self._normaliser_date(je.get("TxnDate", ""))
                lib  = str(je.get("PrivateNote", je.get("Memo", "")) or "")
                for line in je.get("Line", []):
                    detail = line.get("JournalEntryLineDetail", {})
                    acc    = detail.get("AccountRef", {})
                    rows.append({
                        "JournalCode":  "JE",
                        "JournalLib":   "Journal Entries",
                        "EcritureNum":  num,
                        "EcritureDate": date,
                        "CompteNum":    str(acc.get("value", "")),
                        "CompteLib":    str(acc.get("name", "")),
                        "PieceRef":     num,
                        "PieceDate":    date,
                        "EcritureLib":  str(line.get("Description", lib) or ""),
                        "Debit":        self._montant(line.get("Amount", 0)) if detail.get("PostingType") == "Debit" else 0.0,
                        "Credit":       self._montant(line.get("Amount", 0)) if detail.get("PostingType") == "Credit" else 0.0,
                        "EcritureLet":  "",
                    })
            return pd.DataFrame(rows) if rows else self._df_ecritures_vide()
        except Exception as e:
            return self._df_ecritures_vide()

    # ─── Factures ─────────────────────────────────────────────────────────────

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        try:
            entity = "Bill" if type_piece == "fournisseur" else "Invoice"
            cond   = ""
            if exercice:
                cond = (" WHERE TxnDate >= '" + str(exercice) + "-01-01'"
                        + " AND TxnDate <= '" + str(exercice) + "-12-31'")
            sql  = "SELECT * FROM " + entity + cond + " MAXRESULTS " + str(min(limit, 1000))
            data = self._query(sql)
            items = data.get(entity, [])
            rows  = []
            for f in items:
                tier = f.get("VendorRef", f.get("CustomerRef", {}))
                rows.append({
                    "numero":            str(f.get("DocNumber", f.get("Id", ""))),
                    "date":              str(f.get("TxnDate", "")),
                    "fournisseur_client": str(tier.get("name", "")),
                    "montant_ht":        self._montant(f.get("TotalAmt", 0)),
                    "tva":               0.0,
                    "montant_ttc":       self._montant(f.get("TotalAmt", 0)),
                    "statut":            str(f.get("PaymentStatus", f.get("Balance", ""))),
                    "reference":         str(f.get("PrivateNote", "") or ""),
                })
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
