# -*- coding: utf-8 -*-
"""
utils/connectors/cegid_connector.py - SMD Global Consulting LLC
Connecteur Cegid Loop / Cegid Expert via API REST.
Doc : https://developer.cegid.com/
"""

import requests
import pandas as pd
from utils.connectors.base import BaseConnector


class CegidConnector(BaseConnector):

    NOM      = "Cegid"
    ICONE    = "🔵"
    DOCS_URL = "https://developer.cegid.com/"
    BASE_URL = "https://api.cegid.com"

    # credentials : client_id, client_secret, tenant_id, subscription_key

    def _get_token(self):
        token_url = (
            "https://login.microsoftonline.com/"
            + self.credentials.get("tenant_id", "common")
            + "/oauth2/v2.0/token"
        )
        data = {
            "grant_type":    "client_credentials",
            "client_id":     self.credentials.get("client_id", ""),
            "client_secret": self.credentials.get("client_secret", ""),
            "scope":         "https://api.cegid.com/.default",
        }
        r = requests.post(token_url, data=data, timeout=30)
        r.raise_for_status()
        token = r.json().get("access_token", "")
        self.credentials["_token"] = token
        return token

    def _headers(self):
        token = self.credentials.get("_token") or self._get_token()
        return {
            "Authorization":            "Bearer " + token,
            "Ocp-Apim-Subscription-Key": self.credentials.get("subscription_key", ""),
            "Accept":                   "application/json",
            "Content-Type":             "application/json",
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
            self._get_token()
            data = self._get("/accounting/v1/companies")
            companies = data.get("value", data.get("items", []))
            nom = companies[0].get("name", "inconnu") if companies else "inconnu"
            if companies and not self.credentials.get("company_id"):
                self.credentials["company_id"] = companies[0].get("id", "")
            self._connected = True
            return {"ok": True, "info": "Cegid — " + str(len(companies)) + " dossier(s) — " + nom}
        except Exception as e:
            return {"error": str(e)}

    # ─── Balance ──────────────────────────────────────────────────────────────

    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        try:
            company = self.credentials.get("company_id", "")
            params  = {
                "exercice": exercice,
                "pageSize": 500, "pageIndex": 0
            }
            rows = []
            while True:
                data  = self._get("/accounting/v1/companies/" + company + "/trial-balance", params)
                items = data.get("value", data.get("items", []))
                for a in items:
                    debit  = float(a.get("debitAmount", a.get("debit", 0)) or 0)
                    credit = float(a.get("creditAmount", a.get("credit", 0)) or 0)
                    rows.append({
                        "compte":  str(a.get("accountNumber", a.get("account", ""))),
                        "libelle": str(a.get("accountLabel", a.get("label", ""))),
                        "debit":   debit,
                        "credit":  credit,
                        "solde":   debit - credit,
                    })
                if not data.get("nextLink") and len(items) < params["pageSize"]:
                    break
                params["pageIndex"] += 1
            df = pd.DataFrame(rows) if rows else self._df_balance_vide()
            return df.sort_values("compte").reset_index(drop=True)
        except Exception as e:
            return self._df_balance_vide()

    # ─── Ecritures ────────────────────────────────────────────────────────────

    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        try:
            company = self.credentials.get("company_id", "")
            params  = {
                "exercice": exercice,
                "pageSize": 500, "pageIndex": 0
            }
            rows = []
            while True:
                data  = self._get("/accounting/v1/companies/" + company + "/journal-entries", params)
                items = data.get("value", data.get("items", []))
                for e in items:
                    rows.append({
                        "JournalCode":  str(e.get("journalCode", "OD"))[:6],
                        "JournalLib":   str(e.get("journalLabel", "Operations diverses")),
                        "EcritureNum":  str(e.get("entryNumber", e.get("id", ""))),
                        "EcritureDate": self._normaliser_date(e.get("entryDate", e.get("date", ""))),
                        "CompteNum":    str(e.get("accountNumber", e.get("account", ""))),
                        "CompteLib":    str(e.get("accountLabel", e.get("label", ""))),
                        "PieceRef":     str(e.get("pieceReference", e.get("reference", "")) or ""),
                        "PieceDate":    self._normaliser_date(e.get("pieceDate", e.get("date", ""))),
                        "EcritureLib":  str(e.get("entryLabel", e.get("description", "")) or ""),
                        "Debit":        self._montant(e.get("debitAmount", e.get("debit", 0))),
                        "Credit":       self._montant(e.get("creditAmount", e.get("credit", 0))),
                        "EcritureLet":  str(e.get("lettrage", e.get("matching", "")) or ""),
                    })
                if not data.get("nextLink") and len(items) < params["pageSize"]:
                    break
                params["pageIndex"] += 1
            return pd.DataFrame(rows) if rows else self._df_ecritures_vide()
        except Exception as e:
            return self._df_ecritures_vide()

    # ─── Factures ─────────────────────────────────────────────────────────────

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        try:
            company  = self.credentials.get("company_id", "")
            endpoint = "/accounting/v1/companies/" + company + "/"
            endpoint += "supplier-invoices" if type_piece == "fournisseur" else "customer-invoices"
            params   = {"pageSize": min(limit, 200), "pageIndex": 0}
            if exercice:
                params["exercice"] = exercice
            rows = []
            while len(rows) < limit:
                data  = self._get(endpoint, params)
                items = data.get("value", data.get("items", []))
                for f in items:
                    rows.append({
                        "numero":            str(f.get("invoiceNumber", f.get("number", ""))),
                        "date":              str(f.get("invoiceDate", f.get("date", ""))),
                        "fournisseur_client": str(f.get("thirdPartyName", f.get("name", ""))),
                        "montant_ht":        self._montant(f.get("amountExcludingTax", f.get("amountHT", 0))),
                        "tva":               self._montant(f.get("taxAmount", f.get("tva", 0))),
                        "montant_ttc":       self._montant(f.get("amountIncludingTax", f.get("amountTTC", 0))),
                        "statut":            str(f.get("status", f.get("paymentStatus", ""))),
                        "reference":         str(f.get("reference", "") or ""),
                    })
                if not data.get("nextLink") and len(items) < params["pageSize"]:
                    break
                params["pageIndex"] += 1
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
