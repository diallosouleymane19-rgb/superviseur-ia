import tabula
import pandas as pd
import os

FICHIER_PDF = "Compte_de_Resultat.pdf"
FICHIER_SORTIE = "Compte_de_Resultat.xlsx"

print(f"📄 Lecture du PDF : {FICHIER_PDF}")

try:
    dfs = tabula.read_pdf(FICHIER_PDF, pages='all', multiple_tables=True)
    print(f"✅ {len(dfs)} table(s) trouvée(s)")

    with pd.ExcelWriter(FICHIER_SORTIE, engine='openpyxl') as writer:
        for i, df in enumerate(dfs):
            sheet_name = f"Table_{i+1}" if len(dfs) > 1 else "Compte_Resultat"
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"   📊 {sheet_name} : {df.shape[0]} lignes x {df.shape[1]} colonnes")

    print(f"\n🎉 Fichier cree : {os.path.abspath(FICHIER_SORTIE)}")

except Exception as e:
    print(f"❌ Erreur : {e}")