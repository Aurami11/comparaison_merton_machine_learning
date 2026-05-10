import numpy as np
import pandas as pd
import glob
import os
import time
from scipy.stats import norm
from scipy.optimize import fsolve
from preprocess import merge_and_clean

def d1(va, d, r, sigma_a, t):
    return (np.log(va / d) + (r + 0.5 * sigma_a**2) * t) / (sigma_a * np.sqrt(t))

def d2(va, d, r, sigma_a, t):
    return d1(va, d, r, sigma_a, t) - sigma_a * np.sqrt(t)

def merton_equations(variables, ve, sigma_e, d, r, t):
    va, sigma_a = variables
    # Évite les divisions par zéro ou logs négatifs
    va = max(va, 1e-5)
    sigma_a = max(sigma_a, 1e-5)
    
    eq1 = va * norm.cdf(d1(va, d, r, sigma_a, t)) - d * np.exp(-r * t) * norm.cdf(d2(va, d, r, sigma_a, t)) - ve
    eq2 = (va / ve) * norm.cdf(d1(va, d, r, sigma_a, t)) * sigma_a - sigma_e
    return [eq1, eq2]

def calculate_merton_accounting(price_folder="price_data", 
                                lopucki_db="Florida-UCLA-LoPucki Bankruptcy Research Database 1-12-2023.csv", 
                                tickers_file="tickers_resultats_*.csv"):
    
    df_merged = merge_and_clean(tickers_file, lopucki_db)
    
    # Dictionnaire d'accès rapide avec suppression des doublons
    accounting_info = df_merged.drop_duplicates(subset=['Ticker']).set_index('Ticker')[['AssetsBefore', 'LiabBefore']].to_dict('index')

    files = glob.glob(os.path.join(price_folder, "*_prices.csv"))
    results = []
    errors = 0
    
    print(f"Lancement de la résolution Merton sur {len(files)} entreprises...")
    start_time = time.perf_counter()
    
    for file in files:
        ticker = os.path.basename(file).replace("_prices.csv", "")
        
        if ticker not in accounting_info:
            continue
            
        assets = accounting_info[ticker]['AssetsBefore']
        liabilities = accounting_info[ticker]['LiabBefore']
        book_equity = assets - liabilities
        
        # Valeur minimale stricte pour éviter un nombre d'actions négatif
        if book_equity <= 0:
            book_equity = 1.0 

        df_price = pd.read_csv(file, low_memory=False)
        
        if 'Close' not in df_price.columns:
            errors += 1
            continue
            
        # Conversion en numérique et suppression des lignes invalides
        df_price['Close'] = pd.to_numeric(df_price['Close'], errors='coerce')
        df_price = df_price.dropna(subset=['Close'])

        if df_price.empty or len(df_price) < 50:
            errors += 1
            continue
            
        p_initial = df_price['Close'].iloc[0]
        p_final = df_price['Close'].iloc[-1]
        
        # Filtre les faux positifs (prix supérieur à 5$ juste avant faillite)
        # Cela peut indiquer des données erronées ou des entreprises non réellement en difficulté
        # Ce seuil de 5$ est arbitraire
        if p_final > 5.0:
            continue
            
        n_shares = book_equity / p_initial
        ve = p_final * n_shares
        d = liabilities
        
        df_price['Return'] = np.log(df_price['Close'] / df_price['Close'].shift(1))
        sigma_e = df_price['Return'].std() * np.sqrt(252)
        
        r = 0.02
        t = 1.0
        
        va_guess = ve + d
        sigma_a_guess = sigma_e * (ve / (ve + d))
        
        try:
            va_opt, sigma_a_opt = fsolve(
                merton_equations, 
                x0=[va_guess, sigma_a_guess], 
                args=(ve, sigma_e, d, r, t)
            )
            
            num = np.log(va_opt / d) + (r - 0.5 * sigma_a_opt**2) * t
            den = sigma_a_opt * np.sqrt(t)
            distance_to_default = num / den
            probability_of_default = norm.cdf(-distance_to_default)
            
            results.append({
                "Ticker": ticker,
                "Accounting_Assets": assets,
                "Accounting_Debt_D": d,
                "Estimated_Shares_N": n_shares,
                "Market_Equity_Ve": ve,
                "Sigma_e": sigma_e,
                "Calculated_Va": va_opt,
                "Calculated_Sigma_a": sigma_a_opt,
                "Distance_to_Default": distance_to_default,
                "Probability_of_Default": probability_of_default
            })
            
        except Exception as e:
            print(f"Échec de convergence mathématique pour {ticker}")
            errors += 1

    end_time = time.perf_counter()
    duration = end_time - start_time
    
    df_results = pd.DataFrame(results)
    output_filename = "merton_results_accounting.csv"
    df_results.to_csv(output_filename, index=False)
    
    print("\n" + "=" * 50)
    print("RÉSUMÉ DE L'EXÉCUTION")
    print("=" * 50)
    print(f"Entreprises résolues        : {len(results)}")
    print(f"Échecs de convergence       : {errors}")
    print(f"Temps de calcul total       : {duration:.4f} secondes")
    if len(results) > 0:
        print(f"Temps moyen par entreprise  : {(duration / len(files)):.4f} secondes")
    print(f"Exporté dans                : {output_filename}")
    
    return df_results

if __name__ == "__main__":
    calculate_merton_accounting()