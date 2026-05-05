import os
import pandas as pd
import glob
import yfinance as yf
from datetime import timedelta

# 1. Fusion et Nettoyage
import pandas as pd
import glob

def merge_and_clean(tickers_pattern, merton_path):
    # Lecture de la base LoPucki
    merton_df = pd.read_csv(merton_path, sep=',', encoding="latin1")
    
    # Concaténation de tous tes fichiers de résultats
    fichiers_tickers = glob.glob(tickers_pattern)
    df_list = [pd.read_csv(f) for f in fichiers_tickers]
    tickers_df = pd.concat(df_list, ignore_index=True)
    
    # Jointure
    merged_df = pd.merge(merton_df, tickers_df, left_on='NameCorp', right_on='Entreprise', how='left')
    
    # Filtrage strict : on vire les NON_TROUVE, les erreurs et les vides
    clean_df = merged_df[~merged_df['Ticker'].isin(['NON_TROUVE', 'ERREUR_REQUETE'])]
    clean_df = clean_df.dropna(subset=['Ticker', 'DateFiled'])
    
    # Conversion de la date de faillite en objet datetime
    clean_df['DateFiled'] = pd.to_datetime(clean_df['DateFiled'], errors='coerce')
    clean_df = clean_df.dropna(subset=['DateFiled'])

    # Suppression étendue des tickers (Géants du S&P 500 et erreurs évidentes de scraping)
    tickers_a_exclure = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.A', 'NVDA', 'JPM', 'V',
        'DIS', 'AXP', 'ALL', 'LUV', 'YUM', 'INTC', 'VLO', 'CMCSA', 'CZR', 'HON', 
        'PII', 'UNP', 'O', 'T', 'DAL', 'KR', 'M', 'IP'
    ]
    clean_df = clean_df[~clean_df['Ticker'].isin(tickers_a_exclure)]
    
    return clean_df

# 2. Téléchargement de l'historique ciblé
def get_historical_prices(df_sample, output_dir="price_data"):
    # Création du dossier s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    succes = 0
    for index, row in df_sample.iterrows():
        ticker = row['Ticker']
        date_faillite = row['DateFiled']
        entreprise = row['NameCorp']
        
        # On calcule la fenêtre temporelle : de (Faillite - 1 an) jusqu'à (Faillite)
        start_date = date_faillite - timedelta(days=365)
        
        print(f"Téléchargement pour {ticker} ({entreprise}) du {start_date.date()} au {date_faillite.date()}")
        
        try:
            # Téléchargement via yfinance
            data = yf.download(ticker, start=start_date, end=date_faillite, progress=False)
            if not data.empty and len(data) > 50: # On s'assure d'avoir assez de jours de cotation
                filepath = os.path.join(output_dir, f"{ticker}_prices.csv")
                data.to_csv(filepath)
                succes += 1
            else:
                print(f"  -> Données insuffisantes ou vides pour {ticker} sur cette période.")
                
        except Exception as e:
            print(f"  -> Erreur yfinance pour {ticker}: {e}")

    print(f"\nTerminé : {succes} historiques valides téléchargés dans '{output_dir}/'")

# --- Exécution ---
if __name__ == "__main__":
    print("Fusion et nettoyage des données...")
    # Assure-toi que le pattern correspond bien aux noms de tes fichiers
    df_propre = merge_and_clean("tickers_resultats_*.csv", "Florida-UCLA-LoPucki Bankruptcy Research Database 1-12-2023.csv")
    
    # Sélection des 200 premières entreprises disposant d'un ticker valide
    df_echantillon = df_propre.copy()
    print(f"Échantillon sélectionné : {len(df_echantillon)} entreprises.")
    
    get_historical_prices(df_echantillon)