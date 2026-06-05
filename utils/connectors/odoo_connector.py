# -*- coding: utf-8 -*-
"""
utils/connectors/odoo_connector.py - SMD Global Consulting LLC
Connecteur Odoo via XML-RPC (standard Odoo, aucune dependance externe).
Compatible Odoo 14, 15, 16, 17 - On-premise & Cloud.
"""

import xmlrpc.client
import pandas as pd
from datetime import datetime
from utils.connectors.base import BaseConnector


class OdooConnector(BaseConnector):

    NOM      = "Odoo"
    ICONE    = "🟣"
    DOCS_URL = "https://www.odoo.com/documentation/17.0/developer/reference/external_api.html"

    # credentials attendus : url, db, username, password

    def tester_connexion(self) -> dict:
        try:
            url      = self.credentials["url"].rstrip("/")
            db       = self.credentials["db"]
            username = self.credentials["username"]
            password = self.credentials["password"]
            common   = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common")
            uid      = common.authenticate(db, username, password, {})
            if not uid:
                return {"error": "Identifiants incorrects (uid=0)."}
            self.credentials["uid"] = uid
            self._connected = True
            info = common.version()
            return {"ok": True, "info": "Odoo " + str(info.get("server_version", "")) + " — uid=" + str(uid)}
        except Exception as e:
            return {"error": str(e)}

    def _models(self):
        url = self.credentials["url"].rstrip("/")
        return xmlrpc.client.ServerProxy(url + "/xmlrpc/2/object")

    def _call(self, model, method, domain=None, fields=None, limit=5000, offset=0):
        domain = domain or []
        fields = fields or []
        db       = self.credentials["db"]
        uid      = self.credentials.get("uid", 0)
        password = self.credentials["password"]
        return self._models().execute_kw(
            db, uid, password, model, method,
            [domain],
            {"fields": fields, "limit": limit, "offset": offset}
        )

    # ─── Balance ──────────────────────────────────────────────────────────────

    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        try:
            date_from = str(exercice) + "-01-01"
            date_to   = str(exercice) + "-12-31"
            if mois:
                date_from = str(exercice) + "-" + str(mois).zfill(2) + "-01"
                import calendar
                last = calendar.monthrange(exercice, mois)[1]
                date_to = str(exercice) + "-" + str(mois).zfill(2) + "-" + str(last)

            domain = [
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("parent_state", "=", "posted"),
                ("display_type", "not in", ["line_section", "line_note"]),
            ]
            lines = self._call("account.move.line", "read_group",
                               domain=domain,
                               fields=["account_id", "debit", "credit"])
            # read_group syntax different
            lines = self._models().execute_kw(
                self.credentials["db"],
                self.credentials.get("uid", 0),
                self.credentials["password"],
                "account.move.line", "read_group",
                [domain],
                {"fields": ["account_id", "debit:sum", "credit:sum"],
                 "groupby": ["account_id"],
                 "lazy": False}
            )
            rows = []
            for l in lines:
                acc = l.get("account_id", [None, ""])
                debit  = float(l.get("debit", 0) or 0)
                credit = float(l.get("credit", 0) or 0)
                rows.append({
                    "compte":  str(acc[1]).split(" ")[0] if acc else "",
                    "libelle": " ".join(str(acc[1]).split(" ")[1:]) if acc else "",
                    "debit":   debit,
                    "credit":  credit,
                    "solde":   debit - credit,
                })
            df = pd.DataFrame(rows) if rows else self._df_balance_vide()
            return df.sort_values("compte").reset_index(drop=True)
        except Exception as e:
            return self._df_balance_vide()

    # ─── Ecritures (FEC) ──────────────────────────────────────────────────────

    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        try:
            domain = [
                ("date", ">=", str(exercice) + "-01-01"),
                ("date", "<=", str(exercice) + "-12-31"),
                ("parent_state", "=", "posted"),
                ("display_type", "not in", ["line_section", "line_note"]),
            ]
            fields = [
                "move_id", "journal_id", "account_id", "date",
                "name", "ref", "debit", "credit", "matching_number",
            ]
            raw = self._call("account.move.line", "search_read",
                             domain=domain, fields=fields, limit=50000)
            rows = []
            for l in raw:
                jcode = str(l.get("journal_id", [None, ""])[1] or "")
                acode = str(l.get("account_id", [None, ""])[1] or "").split(" ")[0]
                alib  = " ".join(str(l.get("account_id", [None, ""])[1] or "").split(" ")[1:])
                move  = l.get("move_id", [None, ""])
                rows.append({
                    "JournalCode":  jcode[:6],
                    "JournalLib":   jcode,
                    "EcritureNum":  str(move[1] if move else ""),
                    "EcritureDate": self._normaliser_date(l.get("date", "")),
                    "CompteNum":    acode,
                    "CompteLib":    alib,
                    "PieceRef":     str(l.get("ref", "") or ""),
                    "PieceDate":    self._normaliser_date(l.get("date", "")),
                    "EcritureLib":  str(l.get("name", "") or ""),
                    "Debit":        self._montant(l.get("debit", 0)),
                    "Credit":       self._montant(l.get("credit", 0)),
                    "EcritureLet":  str(l.get("matching_number", "") or ""),
                })
            return pd.DataFrame(rows) if rows else self._df_ecritures_vide()
        except Exception as e:
            return self._df_ecritures_vide()

    # ─── Factures ─────────────────────────────────────────────────────────────

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        try:
            move_type = "in_invoice" if type_piece == "fournisseur" else "out_invoice"
            domain = [("move_type", "=", move_type), ("state", "=", "posted")]
            if exercice:
                domain += [("invoice_date", ">=", str(exercice) + "-01-01"),
                           ("invoice_date", "<=", str(exercice) + "-12-31")]
            fields = ["name", "invoice_date", "partner_id",
                      "amount_untaxed", "amount_tax", "amount_total",
                      "payment_state", "ref"]
            raw = self._call("account.move", "search_read",
                             domain=domain, fields=fields, limit=limit)
            rows = []
            for f in raw:
                partner = f.get("partner_id", [None, ""])
                rows.append({
                    "numero":            str(f.get("name", "")),
                    "date":              str(f.get("invoice_date", "")),
                    "fournisseur_client": str(partner[1] if partner else ""),
                    "montant_ht":        self._montant(f.get("amount_untaxed", 0)),
                    "tva":               self._montant(f.get("amount_tax", 0)),
                    "montant_ttc":       self._montant(f.get("amount_total", 0)),
                    "statut":            str(f.get("payment_state", "")),
                    "reference":         str(f.get("ref", "") or ""),
                })
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
