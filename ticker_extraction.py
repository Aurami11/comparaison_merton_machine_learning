import requests
from bs4 import BeautifulSoup
import re
import time
import random
import csv
import pandas as pd
from collections import Counter  # Ajouté uniquement pour le système de vote

# 1. Configuration de ton proxy rotatif
PROXY_USER = 'LnOH1m_0'
PROXY_PASS = 'ae5ai3yy'
PROXY_HOST = 'rg-42606.sp2.ovh'
PROXY_PORT = '1100'

# Construction de l'URL du proxy
PROXY_URL = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

from ddgs import DDGS

def extraire_ticker_par_consensus(resultats_recherche):
    """Système de vote basé sur les occurrences du ticker."""
    candidats = []
    
    patterns_url = [
        r'yahoo\.com/(?:quote|chart)/([A-Z]{1,5}Q?)',
        r'gurufocus\.com/stock/([A-Z0-9]+)',
        r'robinhood\.com/us/en/stocks/([A-Z]{1,5}Q?)/',
        r'advfn\.com/.*?/([A-Z]{1,5}Q?)/stock-price'
    ]
    pattern_titre = r'\((?:DELISTED:)?\s*([A-Z]{1,5}Q?)\s*\)'

    for item in resultats_recherche:
        url = item.get('href', '')
        titre = item.get('title', '')
        
        for pattern in patterns_url:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                candidats.append(match.group(1).upper())
                
        match_titre = re.search(pattern_titre, titre)
        if match_titre:
            candidats.append(match_titre.group(1).upper())

    if not candidats:
        return "NON_TROUVE"
        
    compteur = Counter(candidats)
    vainqueur, _ = compteur.most_common(1)[0]
    return vainqueur


def get_ticker_via_ddg(company_name):
    # Ta structure d'origine intacte
    with DDGS() as ddgs:
        results = ddgs.text(f"{company_name} Yahoo Finance ticker", max_results=20)
        
        # On convertit en liste au cas où DDGS renvoie un générateur
        liste_resultats = list(results)
        
        if not liste_resultats:
            return "NON_TROUVE"
            
        # On passe tes résultats au système de vote plutôt que de prendre le premier
        return extraire_ticker_par_consensus(liste_resultats)


if __name__ == "__main__":
    # Chargement de la base LoPucki
    df = pd.read_csv(r'c:\Users\chris\Downloads\risque_credit\Florida-UCLA-LoPucki Bankruptcy Research Database 1-12-2023.csv', sep=',', encoding="latin1")
    
    # Pour tester, on ne prend que les 50 premières entreprises
    liste_entreprises = df["NameCorp"].tolist()[580:]

    csv_filename = 'tickers_resultats.csv'
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Entreprise", "Ticker"])
        writer.writeheader()

    batch_resultats = []
    taille_lot = 10

    print("Démarrage de l'interrogation...")
    for i, entreprise in enumerate(liste_entreprises):
        print(f"Recherche de : {entreprise}...")
        ticker = get_ticker_via_ddg(entreprise)
        print(f"-> Résultat : {ticker}")
        
        batch_resultats.append({"Entreprise": entreprise, "Ticker": ticker})
        
        if (i + 1) % taille_lot == 0:
            with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["Entreprise", "Ticker"])
                writer.writerows(batch_resultats)
            print(f"--- Sauvegarde intermédiaire : {i + 1} entreprises traitées ---")
            batch_resultats = []
        
        time.sleep(random.uniform(10.0, 30.0))

    if batch_resultats:
        with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Entreprise", "Ticker"])
            writer.writerows(batch_resultats)
        
    print(f"\nExtraction terminée. Données sauvegardées dans {csv_filename}")