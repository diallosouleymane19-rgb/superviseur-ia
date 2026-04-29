import datetime
import pandas as pd

# ---------------------------------------------------------
# FONCTION EXISTANTE : génération d'un FEC fictif
# ---------------------------------------------------------
def generer_fec():
    filename = f"FEC_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("Journal\tDate\tCompte\tLibellé\tDébit\tCrédit\n")
        f.write("AC\t20240101\t606\tAchat fournitures\t100.00\t0.00\n")

    return filename


# ---------------------------------------------------------
# 🔥 FONCTION MANQUANTE : utilisée par app.py
# ---------------------------------------------------------
def traiter_fec(fichier):
    """
    Lecture simple du FEC importé.
    Retourne un texte ou un tableau selon ton besoin.
    """

    try:
        # Lecture du fichier FEC (tabulation)
        df = pd.read_csv(fichier, sep="\t", dtype=str)

        # Retourner un aperçu
        return df.head()

    except Exception as e:
        return f"Erreur lors du traitement du FEC : {e}"

