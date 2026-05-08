import pandas as pd
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('fr_FR')

print("🚀 Génération du FEC synthétique...")

n_entries = 1000
data = []

for i in range(n_entries):
    amount = random.randint(10, 10000)
    account = random.choice(['411000', '401000', '606000', '706000', '512000'])
    
    # 5% d'anomalies Benford
    if random.random() < 0.05:
        digits = len(str(amount))
        amount = 9 * (10 ** (digits - 1))
        libelle = f"[ALERTE] {fake.sentence(nb_words=4)}"
    else:
        libelle = fake.sentence(nb_words=4)
    
    data.append({
        'PieceRef': f'F-{i+1:05d}',
        'EcritureNum': i + 1,
        'CompteNum': account,
        'EcritureDate': datetime(2025, 1, 1) + timedelta(days=random.randint(1, 365)),
        'Debit': amount if random.random() > 0.3 else 0,
        'Credit': 0 if random.random() > 0.3 else amount,
        'EcritureLib': libelle,
        'JournalCode': random.choice(['VE', 'AC', 'BQ'])
    })

df = pd.DataFrame(data)
df.to_csv('fec_synthetique_test.csv', sep=';', index=False, encoding='utf-8')

print(f"✅ FEC généré : {len(df)} écritures")
print(f"📁 Fichier : fec_synthetique_test.csv")
print(f"\n🔍 Anomalies : {len(df[df['EcritureLib'].str.contains('ALERTE')])}")
print(f"\n📊 Aperçu des 5 premières lignes :")
print(df.head(5).to_string())