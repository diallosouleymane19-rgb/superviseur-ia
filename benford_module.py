import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import chisquare

def analyse_benford_complete(df, col_montant='Montant'):
    """
    Module de supervision autonome.
    """
    try:
        # Nettoyage des données
        df_clean = df.copy()
        
        # Conversion en numérique (remplacement virgule par point)
        if df_clean[col_montant].dtype == object:
            df_clean[col_montant] = df_clean[col_montant].str.replace(',', '.')
        df_clean[col_montant] = pd.to_numeric(df_clean[col_montant], errors='coerce')
        
        # On garde les montants >= 1 pour la pertinence statistique
        data = df_clean[df_clean[col_montant].abs() >= 1][col_montant].abs().dropna()
        
        if data.empty:
            return None, "⚠️ Aucune donnée numérique valide pour l'analyse.", "N/A"
        
        # Extraction du premier chiffre
        first_digits = data.astype(str).str.lstrip('0.').str[0].astype(int)
        
        # Fréquences observées
        counts = first_digits.value_counts().sort_index().reindex(range(1, 10), fill_value=0)
        total = counts.sum()
        observed_freq = counts / total
        
        # Distribution théorique de Benford
        benford_probs = np.log10(1 + 1/np.arange(1, 10))
        expected_counts = benford_probs * total
        
        # Test Chi-Carré
        chi_stat, p_value = chisquare(f_obs=counts, f_exp=expected_counts)
        
        # Création du Graphique Plotly
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(range(1, 10)), 
            y=observed_freq, 
            name='Observé', 
            marker_color='#3498db'
        ))
        fig.add_trace(go.Scatter(
            x=list(range(1, 10)), 
            y=benford_probs, 
            name='Loi de Benford', 
            line=dict(color='#e74c3c', width=4)
        ))
        fig.update_layout(
            title="Test de Benford - Fiabilité des écritures",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            template="plotly_white", 
            height=400
        )
        
        # Rapport
        interpret = "✓ Cohérence statistique validée" if p_value > 0.05 else "⚠️ Écart statistique suspect"
        score_risque = "Faible" if p_value > 0.05 else ("Modéré" if p_value > 0.01 else "Élevé")
        
        rapport = f"""
**Résultat de l'audit :** {interpret}
*   **Indice de confiance (p-value) :** {p_value:.4f}
*   **Niveau de risque détecté :** `{score_risque}`
*   **Volume analysé :** {total} lignes.
        """
        
        return fig, rapport, score_risque
        
    except Exception as e:
        return None, f"Erreur module : {str(e)}", "Erreur"