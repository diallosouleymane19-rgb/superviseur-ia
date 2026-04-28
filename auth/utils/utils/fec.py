from datetime import datetime
from .ai import parse_montant, extraire_compte_valide

def generer_fec(infos: dict) -> tuple[str, str]:
    """
    Génère un FEC conforme DGFiP à partir des informations extraites.
    Retourne (contenu_csv, nom_fichier).
    """

    # ---------------- DATE ---------------- #
    date_raw = infos.get("date", datetime.now().strftime("%d/%m/%Y"))
    date_fec = None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            date_obj = datetime.strptime(date_raw, fmt)
            date_fec = date_obj.strftime("%Y%m%d")
            break
        except ValueError:
            continue

    if not date_fec:
        date_fec = datetime.now().strftime("%Y%m%d")

    # ---------------- CHAMPS ---------------- #
    fournisseur = infos.get("fournisseur", "FOURNISSEUR")[:35]
    num_facture = infos.get("num_facture", "FAC000")[:30]
    compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))

    ht = parse_montant(infos.get("montant_ht", 0))
    tva = parse_montant(infos.get("tva", 0))
    ttc = parse_montant(infos.get("montant_ttc", 0))

    # ---------------- FONCTION LIGNE ---------------- #
    def ligne(ecriture_num, compte_num, compte_lib, debit, credit):
        libelle_tronc = (compte_lib[:35] + '..') if len(compte_lib) > 35 else compte_lib
        montantdevise = "0"
        idevise = ""

        return (
            f"ACH;Achats;{ecriture_num};{date_fec};"
            f"{compte_num};{libelle_tronc};;;{num_facture};{date_fec};"
            f"{fournisseur};{debit:.2f};{credit:.2f};;{date_fec};{date_fec};"
            f"{montantdevise};{idevise}"
        )

    # ---------------- COLONNES ---------------- #
    colonnes = (
        "JournalCode;JournalLib;EcritureNum;EcritureDate;"
        "CompteNum;CompteLib;CompAuxNum;CompAuxLib;PieceRef;PieceDate;"
        "EcritureLib;Debit;Credit;EcritureLet;DateLet;ValidDate;Montantdevise;Idevise"
    )

    libelle = "Achat marchandise" if compte == "601000" else "Achat"

    lignes = [
        colonnes,
        ligne("001", compte,     libelle,          ht,   0),
        ligne("002", "445660", "TVA déductible",  tva,  0),
        ligne("003", "401000", "Fournisseur",      0,   ttc),
    ]

    contenu_csv = "\n".join(lignes).encode("utf-8-sig").decode("utf-8")
    nom_fichier = f"FEC_{num_facture}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return contenu_csv, nom_fichier

