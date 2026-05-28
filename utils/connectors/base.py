# -*- coding: utf-8 -*-
"""
utils/connectors/base.py - SMD Consulting
Classe de base abstraite pour tous les connecteurs ERP.
Chaque connecteur retourne des DataFrames normalises.
"""

from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime


class BaseConnector(ABC):
    """Connecteur ERP abstrait. Tous les connecteurs heritent de cette classe."""

    NOM       = "ERP Generique"
    ICONE     = "🔌"
    DOCS_URL  = ""

    def __init__(self, credentials: dict):
        self.credentials = credentials
        self._connected  = False

    # ─── Connexion ────────────────────────────────────────────────────────────

    @abstractmethod
    def tester_connexion(self) -> dict:
        """
        Teste la connexion. Retourne {"ok": True, "info": "..."} ou {"error": "..."}.
        """

    # ─── Imports de donnees ───────────────────────────────────────────────────

    @abstractmethod
    def get_balance(self, exercice: int, mois: int = None) -> pd.DataFrame:
        """
        Balance generale : colonnes [compte, libelle, debit, credit, solde].
        """

    @abstractmethod
    def get_ecritures(self, exercice: int) -> pd.DataFrame:
        """
        Ecritures comptables (format FEC) :
        colonnes [JournalCode, JournalLib, EcritureNum, EcritureDate,
                  CompteNum, CompteLib, PieceRef, PieceDate,
                  EcritureLib, Debit, Credit, EcritureLet].
        """

    def get_grand_livre(self, exercice: int, compte_prefix: str = None) -> pd.DataFrame:
        """
        Grand livre. Par defaut : filtre les ecritures par prefixe de compte.
        Les connecteurs peuvent surcharger cette methode pour appels API dedies.
        """
        df = self.get_ecritures(exercice)
        if df.empty:
            return df
        if compte_prefix:
            df = df[df["CompteNum"].astype(str).str.startswith(str(compte_prefix))]
        return df

    def get_factures(self, type_piece: str = "fournisseur",
                     exercice: int = None, limit: int = 500) -> pd.DataFrame:
        """
        Factures fournisseurs ou clients.
        Retourne DataFrame avec colonnes [numero, date, fournisseur_client,
                                          montant_ht, tva, montant_ttc, statut].
        Surcharger dans chaque connecteur.
        """
        return pd.DataFrame()

    # ─── Helpers internes ─────────────────────────────────────────────────────

    @staticmethod
    def _normaliser_date(val) -> str:
        """Convertit une date quelconque en format YYYYMMDD (norme FEC)."""
        if pd.isna(val) or val is None or val == "":
            return ""
        try:
            if isinstance(val, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
                    try:
                        return datetime.strptime(val[:10], fmt).strftime("%Y%m%d")
                    except Exception:
                        continue
            if hasattr(val, "strftime"):
                return val.strftime("%Y%m%d")
        except Exception:
            pass
        return str(val)

    @staticmethod
    def _montant(val) -> float:
        """Convertit une valeur en float (0.0 si erreur)."""
        try:
            return float(str(val).replace(",", ".").replace(" ", "")) or 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _df_ecritures_vide() -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
            "CompteNum", "CompteLib", "PieceRef", "PieceDate",
            "EcritureLib", "Debit", "Credit", "EcritureLet"
        ])

    @staticmethod
    def _df_balance_vide() -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "compte", "libelle", "debit", "credit", "solde"
        ])
