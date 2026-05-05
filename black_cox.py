import numpy as np
import pandas as pd
from scipy.stats import norm
import time

# --- 1. BLACK-COX FUNCTIONS ---

def calculate_black_cox_pd(va, d, sigma_a, r, t):
    """
    Calcule la Probabilité de Défaut selon le modèle de First Passage Time (Black-Cox).
    """
    # La barrière de défaut (K). Dans la pratique KMV c'est STD + 0.5*LTD.
    # Ici on utilise la dette totale D faute de granularité.
    k = d 
    
    # Si la valeur de l'actif est déjà inférieure à la dette, le défaut est certain (PD = 100%)
    if va <= k:
        return 1.0
        
    mu = r  # Drift risque-neutre
    
    # Calcul des deux termes de la formule de First Passage Time
    term1_num = np.log(k / va) - (mu - 0.5 * sigma_a**2) * t
    term1_den = sigma_a * np.sqrt(t)
    d1_bc = term1_num / term1_den
    
    term2_num = np.log(k / va) + (mu - 0.5 * sigma_a**2) * t
    d2_bc = term2_num / term1_den
    
    # Le facteur d'ajustement de la barrière
    # Attention aux dépassements de capacité (overflow) si sigma_a est très proche de 0
    try:
        power = 1 - (2 * mu) / (sigma_a**2)
        barrier_factor = (va / k) ** power
    except OverflowError:
        barrier_factor = 0.0

    pd_bc = norm.cdf(d1_bc) + barrier_factor * norm.cdf(d2_bc)
    
    # On s'assure que la probabilité reste mathématiquement bornée entre 0 et 1
    return min(max(pd_bc, 0.0), 1.0)

# --- 2. DATA PROCESSING ---

def apply_black_cox(input_file="merton_results_accounting.csv", output_file="final_structural_models.csv"):
    start_time = time.perf_counter()
    
    print(f"Chargement des résultats de Merton depuis '{input_file}'...")
    df = pd.read_csv(input_file)
    initial_count = len(df)
    
    # 1. NETTOYAGE DES ABERRATIONS MATHÉMATIQUES (Filtre Quantitatif)
    # On supprime les lignes où le solveur Newton-Raphson a crashé ou trouvé des racines négatives
    df_clean = df[
        (df['Calculated_Va'] > 0) & 
        (df['Calculated_Sigma_a'] > 0) & 
        (df['Probability_of_Default'].notna())
    ].copy()
    
    dropped_count = initial_count - len(df_clean)
    
    # 2. APPLICATION DU MODÈLE DE BLACK-COX
    r = 0.02  # Taux sans risque (2%)
    t = 1.0   # Horizon temporel (1 an)
    
    print("Calcul des probabilités de défaut de Black-Cox (First Passage Time)...")
    
    # On applique la fonction ligne par ligne
    df_clean['Probability_of_Default_BC'] = df_clean.apply(
        lambda row: calculate_black_cox_pd(
            va=row['Calculated_Va'], 
            d=row['Accounting_Debt_D'], 
            sigma_a=row['Calculated_Sigma_a'], 
            r=r, 
            t=t
        ), axis=1
    )
    
    # 3. SAUVEGARDE ET COMPARAISON
    df_clean.to_csv(output_file, index=False)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print("\n" + "=" * 50)
    print("RÉSUMÉ DU MODÈLE DE BLACK-COX")
    print("=" * 50)
    print(f"Entreprises initiales      : {initial_count}")
    print(f"Aberrations supprimées     : {dropped_count} (Valeurs inexploitables de Merton)")
    print(f"Entreprises validées       : {len(df_clean)}")
    print(f"Temps de calcul total      : {duration:.4f} secondes")
    print(f"Résultats finaux exportés  : {output_file}")
    
    # Affichage d'un petit aperçu pour comparer les deux modèles
    print("\n--- Aperçu Comparatif (Merton vs Black-Cox) ---")
    preview = df_clean[['Ticker', 'Distance_to_Default', 'Probability_of_Default', 'Probability_of_Default_BC']].head(10)
    print(preview.to_string(index=False))

if __name__ == "__main__":
    apply_black_cox()