import pandas as pd 
df = pd.read_excel('fec_2025.xlsx') 
print("Colonnes disponibles :") 
for i, col in enumerate(df.columns): 
    print(f"{i}: '{col}'") 
