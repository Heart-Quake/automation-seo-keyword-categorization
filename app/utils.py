"""
Fonctions utilitaires pour Keyword Categorization App
Nettoyage, extraction familles, détection d’intention, mapping menu, export XLSX.
"""

import pandas as pd
import re
import unicodedata
from app import config
import io
from typing import List, Optional
import os
import unidecode
import json

# --- Chargement des localités françaises (communes, départements, régions) ---
from functools import lru_cache

@lru_cache(maxsize=1)
def load_localities():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    # Communes
    communes_path = os.path.join(data_dir, 'communes_fr.csv')
    if os.path.exists(communes_path):
        communes = pd.read_csv(communes_path, dtype=str)
        commune_names = set(unidecode.unidecode(n.lower()) for n in communes['nom'].dropna().unique())
    else:
        commune_names = set()
    # Départements
    departements_path = os.path.join(data_dir, 'departements_fr.csv')
    if os.path.exists(departements_path):
        departements = pd.read_csv(departements_path, dtype=str)
        dep_names = set(unidecode.unidecode(n.lower()) for n in departements['nom'].dropna().unique())
        dep_nums = set(str(n).zfill(2) for n in departements['code'].dropna().unique() if 'code' in departements.columns)
    else:
        dep_names = set()
        dep_nums = set()
    # Régions
    regions_path = os.path.join(data_dir, 'regions_fr.csv')
    if os.path.exists(regions_path):
        regions = pd.read_csv(regions_path, dtype=str)
        region_names = set(unidecode.unidecode(n.lower()) for n in regions['nom'].dropna().unique())
    else:
        region_names = set()
    return commune_names, dep_names, dep_nums, region_names

@lru_cache(maxsize=1)
def load_localities_json():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    # Communes
    communes_path = os.path.join(data_dir, 'communes.json')
    commune_names = set()
    if os.path.exists(communes_path):
        with open(communes_path, encoding='utf-8') as f:
            communes_data = json.load(f)
            if isinstance(communes_data, dict) and 'data' in communes_data:
                communes_data = communes_data['data']
            if isinstance(communes_data, list):
                for c in communes_data:
                    for key in ['nom_standard', 'nom_sans_accent', 'nom_sans_pronom', 'nom_a', 'nom_de']:
                        if key in c:
                            commune_names.add(normalize_text(c[key]))
    # Départements et régions
    depreg_path = os.path.join(data_dir, 'departements-regions.json')
    dep_names = set()
    dep_nums = set()
    region_names = set()
    if os.path.exists(depreg_path):
        with open(depreg_path, encoding='utf-8') as f:
            depreg_data = json.load(f)
            if isinstance(depreg_data, list):
                for d in depreg_data:
                    if 'dep_name' in d:
                        dep_names.add(normalize_text(d['dep_name']))
                    if 'num_dep' in d:
                        dep_nums.add(str(d['num_dep']).zfill(2))
                    if 'region_name' in d:
                        region_names.add(normalize_text(d['region_name']))
    # Log temporaire pour debug controlé par variable d'environnement
    if os.getenv('KCA_DEBUG_LOCALITES') == '1':
        with open('/tmp/debug_localites.txt', 'w', encoding='utf-8') as f:
            f.write(f'Communes ({len(commune_names)}):\n' + '\n'.join(list(commune_names)[:10]) + '\n')
            f.write(f'Départements ({len(dep_names)}):\n' + '\n'.join(list(dep_names)[:10]) + '\n')
            f.write(f'Codes départements ({len(dep_nums)}):\n' + '\n'.join(list(dep_nums)[:10]) + '\n')
            f.write(f'Régions ({len(region_names)}):\n' + '\n'.join(list(region_names)[:10]) + '\n')
    return list(commune_names), list(dep_names), list(dep_nums), list(region_names)

def normalize_text(text):
    text = unidecode.unidecode(str(text).lower())
    for art in [" le ", " la ", " les ", " d'", " de ", " du ", " des ", " l'", " l’"]:
        text = text.replace(art, " ")
    text = text.replace("-", " ").replace("'", " ").replace("’", " ")
    text = " ".join(text.split())
    return text

# --- Détection automatique des colonnes ---
def detect_keyword_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.lower() in ["mot-clé", "mot_cle", "keyword"]:
            return col
    return None

def detect_volume_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.lower() == "volume":
            return col
    return None

# --- Nettoyage linguistique ---
def clean_keywords(df: pd.DataFrame, col_keyword: str, lemmatize: bool, lang: str, extra_stopwords: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Nettoie les mots-clés : minuscule, accents, ponctuation, stopwords, lemmatisation (optionnel), et normalisation singulier/pluriel simple.
    Ajoute une colonne 'Mot-clé_lemmatisé' si lemmatisation activée.
    Permet d'ajouter des stopwords métier via extra_stopwords.
    """
    def normalize(text):
        text = str(text).lower()
        text = unicodedata.normalize('NFD', text)
        text = ''.join([c for c in text if unicodedata.category(c) != 'Mn'])
        text = re.sub(r'[^ - \w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    def normalize_plural(word):
        # Règles simples pour le français (peut être enrichi)
        if word.endswith('s') and len(word) > 3:
            if word.endswith('aux'):
                return word[:-3] + 'al'  # animaux > animal
            if word.endswith('eaux'):
                return word[:-4] + 'eau'  # châteaux > château
            if word.endswith('eux'):
                return word[:-3] + 'eu'  # feux > feu
            if word.endswith('oux'):
                return word[:-3] + 'ou'  # bijoux > bijou
            if word.endswith('ils'):
                return word[:-1]  # outils > outil
            if word.endswith('s') and not word.endswith('us') and not word.endswith('is'):
                return word[:-1]  # bienfaits > bienfait, pommes > pomme
        return word
    stopwords = set(config.STOPWORDS[lang])
    if extra_stopwords:
        stopwords.update(extra_stopwords)
    df['Mot-clé_nettoye'] = df[col_keyword].apply(normalize)
    df['Mot-clé_nettoye'] = df['Mot-clé_nettoye'].apply(lambda x: ' '.join([normalize_plural(w) for w in x.split() if w not in stopwords]))
    # Lemmatisation française avec spaCy (import paresseux)
    if lemmatize and lang == 'fr':
        import spacy  # lazy import
        nlp = spacy.load('fr_core_news_md')
        def lemmatize_text(text):
            doc = nlp(text)
            return ' '.join([token.lemma_ for token in doc])
        df['Mot-clé_lemmatisé'] = df['Mot-clé_nettoye'].apply(lemmatize_text)
    elif lemmatize:
        # Placeholder pour d'autres langues
        df['Mot-clé_lemmatisé'] = df['Mot-clé_nettoye']
    return df

from typing import Tuple

def match_localite_exhaustif(kw: str) -> Tuple[str, str, str]:
    """
    Pour un mot-clé donné, détecte s'il contient une localité française (ville, département, code, région) :
    - Matching exact (après normalisation) sur tous les n-grams (1 à 4 mots) du mot-clé contre les bases JSON.
    - Retourne ('Locale', 'Localité détectée', 'Type localité')
    - Priorité : commune > département > code département > région
    - Si aucune correspondance : ('', '', '')
    """
    try:
        commune_names, dep_names, dep_nums, region_names = load_localities_json()
    except Exception:
        return '', '', ''
    kw_norm = normalize_text(kw)
    tokens = kw_norm.split()
    ngram_list = []
    # 1. Commune (ville) - matching exact sur tous les n-grams (1 à 4)
    for n in range(4, 0, -1):
        for i in range(len(tokens)-n+1):
            ngram = ' '.join(tokens[i:i+n])
            ngram_norm = normalize_text(ngram)
            ngram_list.append(ngram_norm)
            if ngram_norm in commune_names:
                # Log debug optionnel
                if os.getenv('KCA_DEBUG_LOCALITES') == '1':
                    with open('/tmp/debug_localites_match.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[COMMUNE] kw: {kw} | ngram: {ngram_norm}\n")
                return 'Ville', ngram_norm, 'commune'
    # 2. Département (nom) - matching exact
    for n in range(4, 0, -1):
        for i in range(len(tokens)-n+1):
            ngram = ' '.join(tokens[i:i+n])
            ngram_norm = normalize_text(ngram)
            if ngram_norm in dep_names:
                if os.getenv('KCA_DEBUG_LOCALITES') == '1':
                    with open('/tmp/debug_localites_match.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[DEPARTEMENT] kw: {kw} | ngram: {ngram_norm}\n")
                return 'Département', ngram_norm, 'departement'
    # 3. Département (code)
    for num in dep_nums:
        if f" {num} " in f" {kw_norm} ":
            if os.getenv('KCA_DEBUG_LOCALITES') == '1':
                with open('/tmp/debug_localites_match.txt', 'a', encoding='utf-8') as f:
                    f.write(f"[DEPARTEMENT_CODE] kw: {kw} | code: {num}\n")
            return 'Département_code', num, 'departement_code'
    # 4. Région - matching exact
    for n in range(4, 0, -1):
        for i in range(len(tokens)-n+1):
            ngram = ' '.join(tokens[i:i+n])
            ngram_norm = normalize_text(ngram)
            if ngram_norm in region_names:
                if os.getenv('KCA_DEBUG_LOCALITES') == '1':
                    with open('/tmp/debug_localites_match.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[REGION] kw: {kw} | ngram: {ngram_norm}\n")
                return 'Région', ngram_norm, 'region'
    # Log debug si aucun match (optionnel)
    if os.getenv('KCA_DEBUG_LOCALITES') == '1':
        with open('/tmp/debug_localites_match.txt', 'a', encoding='utf-8') as f:
            f.write(f"[NO_MATCH] kw: {kw} | ngrams: {ngram_list}\n")
            f.write(f"communes: {list(commune_names)[:10]}\n")
            f.write(f"departements: {list(dep_names)[:10]}\n")
            f.write(f"regions: {list(region_names)[:10]}\n")
            f.write(f"codes: {list(dep_nums)[:10]}\n")
    return '', '', ''

# --- Extraction familles (n-grams dominants) ---
def extract_families_and_intentions(df: pd.DataFrame, col_keyword: str, lang: str, all_families: bool = False, ngram_size: int = 2, frequent_only: bool = True) -> pd.DataFrame:
    """
    Extrait la/les familles (n-grams dominants) et l’intention SEO pour chaque mot-clé.
    Ajoute les colonnes 'Intention', 'Locale', 'Localité détectée', 'Type localité' selon enrichissement exhaustif.
    """
    # 1. Calculer la fréquence de tous les n-grams du corpus
    all_ngrams = []
    for kw in df['Mot-clé_nettoye']:
        tokens = kw.split()
        ngrams = [' '.join(tokens[i:i+ngram_size]) for i in range(len(tokens)-ngram_size+1)]
        all_ngrams.extend(ngrams)
    from collections import Counter
    ngram_counts = Counter(all_ngrams)
    # Seuil : on garde les n-grams présents dans au moins 2 mots-clés (modifiable)
    min_freq = 2
    frequent_ngrams = {ng for ng, c in ngram_counts.items() if c >= min_freq}
    familles = []
    intentions = []
    locales = []
    localites = []
    type_localites = []
    logs = []
    for i, kw in enumerate(df['Mot-clé_nettoye']):
        tokens = kw.split()
        ngrams = [' '.join(tokens[i:i+ngram_size]) for i in range(len(tokens)-ngram_size+1)]
        if frequent_only:
            ngrams = [ng for ng in ngrams if ng in frequent_ngrams]
        if all_families:
            famille = ', '.join(ngrams) if ngrams else (tokens[0] if tokens else "")
        else:
            famille = ngrams[0] if ngrams else (tokens[0] if tokens else "")
        familles.append(famille)
        # Détection locale indépendante
        locale, localite_ex, type_loc_ex = match_localite_exhaustif(kw)
        locales.append(locale)
        localites.append(localite_ex)
        type_localites.append(type_loc_ex)
        # Intention (Consumer Journey, etc.)
        intent, _, _ = detect_intention(kw, lang)
        if intent == "locale":
            intent = "autre"
        intentions.append(intent)
        if i < 20:
            logs.append(f"{kw}\t{intent}\t{locale}\t{localite_ex}\t{type_loc_ex}")
    # Log debug optionnel
    if os.getenv('KCA_DEBUG_LOCALITES') == '1':
        with open("/tmp/detect_localite_debug.txt", "w", encoding="utf-8") as f:
            f.write("Mot-clé\tIntention\tLocale\tLocalité\tType\n")
            for l in logs:
                f.write(l + "\n")
    df['Famille'] = familles
    df['Intention'] = intentions
    df['Locale'] = locales
    df['Localité détectée'] = localites
    df['Type localité'] = type_localites
    return df

# Ajout des patterns Consumer Journey
CONSUMER_JOURNEY_PATTERNS = {
    "decouverte": [
        "qu'est-ce que", "definition", "c'est quoi", "pourquoi", "avantage", "inconvenient", "bienfait", "utilite", "a quoi sert", "meilleur", "meilleure", "meilleurs", "meilleures", "top", "guide", "conseil", "astuce", "idee", "exemple", "exemples", "tendance", "tendances", "univers", "categorie", "catégorie", "categories", "catégories", "produit", "produits", "marque", "marques", "type", "types", "variete", "variété", "variétés", "varietes"
    ],
    "consideration": [
        "comparatif", "comparaison", "vs", "ou", "choisir", "difference", "différence", "avis", "test", "review", "retour", "retours", "fonctionnement", "utilisation", "utiliser", "comment", "pour", "contre", "prix", "tarif", "cout", "coût", "budget", "promo", "promotion", "reduction", "réduction", "offre", "offres", "option", "options", "caracteristique", "caractéristique", "caractéristiques", "caracteristiques", "fournisseur", "fournisseurs", "magasin", "boutique", "acheter", "vente", "location", "louer", "disponible", "disponibilite", "stock", "livraison", "commande", "panier", "abonnement", "abonner", "abonnez", "abonne", "abonnements", "abonnés", "abonnées", "abonnée", "abonné", "abonnement"
    ],
    "transaction": [
        "acheter", "achat", "commander", "commande", "livraison", "prix", "tarif", "promo", "réduction", "code promo", "panier", "abonnement", "offre", "vente", "magasin", "boutique", "acheter en ligne", "location", "louer", "disponible", "stock", "ajouter au panier", "acheter maintenant", "meilleur prix", "acheter pas cher", "acheter en promo", "acheter avec livraison", "acheter sur internet", "acheter en magasin", "acheter en ligne", "acheter sur amazon", "acheter sur cdiscount", "acheter sur fnac", "acheter sur darty", "acheter sur boulanger", "acheter sur rakuten", "acheter sur ebay", "acheter sur leboncoin"
    ],
    "information": [
        "avis", "test", "review", "retour", "retours", "conseil", "conseils", "astuce", "astuces", "blog", "article", "guide", "tutoriel", "tuto", "explication", "expliquer", "expliqué", "expliquée", "expliqués", "expliquées", "expliquer", "expliquant", "explications", "exemple", "exemples", "idee", "idée", "idées", "idée", "meilleur", "meilleure", "meilleurs", "meilleures", "pourquoi", "comment", "fonctionnement", "utilisation", "utiliser", "utilité", "a quoi sert", "qu'est-ce que", "definition", "c'est quoi"
    ]
}

def detect_intention(kw: str, lang: str):
    """
    Détecte l’intention Consumer Journey (découverte, considération, transaction, information) via patterns/dictionnaire et détection locale.
    Retourne (intention, localité détectée, type_localité) si locale, sinon (intention, '', '').
    """
    from app import config
    kw_norm = normalize_text(kw)
    tokens = kw_norm.split()
    # Détection locale par pattern (prioritaire)
    for pat in config.INTENT_PATTERNS[lang].get('locale', []):
        if pat in kw_norm:
            return 'locale', pat, 'pattern'
    # Détection locale exhaustive (communes, départements, régions, code) sur tous les n-grams (1 à 4)
    commune_names, dep_names, dep_nums, region_names = load_localities_json()
    for n in range(4, 0, -1):
        for i in range(len(tokens)-n+1):
            ngram = ' '.join(tokens[i:i+n])
            if ngram in commune_names:
                return 'locale', ngram, 'commune'
            if ngram in dep_names:
                return 'locale', ngram, 'departement'
            if ngram in region_names:
                return 'locale', ngram, 'region'
    for num in dep_nums:
        if f" {num} " in f" {kw_norm} ":
            return 'locale', num, 'departement_code'
    # Détection Consumer Journey avec priorité explicite
    # Priorité: transaction > consideration > information > decouverte
    intent_priority = [
        "transaction",
        "consideration",
        "information",
        "decouverte",
    ]
    classic_map = {
        "transaction": "transactionnelle",
        "information": "informationnelle",
        "consideration": "informationnelle",
        "decouverte": "informationnelle",
    }
    for intent in intent_priority:
        patterns = CONSUMER_JOURNEY_PATTERNS.get(intent, [])
        for pat in patterns:
            if pat in kw_norm:
                return classic_map.get(intent, intent), '', ''
    # Fallback sur les intentions classiques
    for intent, patterns in config.INTENT_PATTERNS[lang].items():
        if intent == 'locale':
            continue
        for pat in patterns:
            if pat in kw_norm:
                return intent, '', ''
    return "autre", '', ''

# --- Mapping clusters/menu (optionnel) ---
def map_clusters_to_menu(df: pd.DataFrame, menu_categories: List[str], col_keyword: str, fuzzy_threshold: float = 0.6, min_shared_ngrams: int = 1) -> pd.DataFrame:
    """
    Matching avancé : associe chaque mot-clé à une ou plusieurs catégories menu selon un score de similarité (fuzzy matching)
    ET un nombre minimal de n-grams partagés (hors stopwords).
    Ajoute une colonne Catégories_menu_matchées (liste séparée par virgule), Score_menu (score max), et Ngrams_partagés (max n-grams partagés).
    Garantit qu'aucun matching n'est validé si len(shared) < min_shared_ngrams.
    """
    # Détection automatique de la langue (prend la première ligne du DataFrame)
    lang = 'fr'
    if hasattr(config, 'STOPWORDS') and len(df) > 0:
        for l in config.STOPWORDS.keys():
            sample = str(df[col_keyword].iloc[0]).lower()
            if any(w in sample for w in config.STOPWORDS[l]):
                lang = l
                break
    stopwords = set(config.STOPWORDS.get(lang, []))

    def normalize_token(token: str) -> str:
        t = unidecode.unidecode(token.lower().strip())
        t = re.sub(r"[^\w\s-]", " ", t)
        t = t.replace("-", " ")
        t = " ".join(t.split())
        # singularisation simple FR/EN
        if len(t) > 3 and t.endswith('s') and not t.endswith(('us', 'is')):
            if t.endswith('aux'):
                return t[:-3] + 'al'
            if t.endswith('eaux'):
                return t[:-4] + 'eau'
            if t.endswith('eux'):
                return t[:-3] + 'eu'
            if t.endswith('oux'):
                return t[:-3] + 'ou'
            if t.endswith('ils'):
                return t[:-1]
            return t[:-1]
        return t

    def tokens_no_stop(text: str) -> List[str]:
        raw_tokens = re.split(r"\s+", unidecode.unidecode(str(text).lower()))
        norm = [normalize_token(tok) for tok in raw_tokens if tok]
        return [t for t in norm if t and t not in stopwords]

    def build_ngrams(tokens: List[str], n: int) -> set:
        if n <= 0:
            return set()
        if len(tokens) < n:
            return set()
        return set(' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1))

    all_matches_col = []
    best_scores_col = []
    best_shared_col = []
    best_single_col = []

    for kw in df[col_keyword].astype(str).tolist():
        kw_tokens = tokens_no_stop(kw)
        kw_ngrams = build_ngrams(kw_tokens, min_shared_ngrams)
        matches = []
        scores = []
        shared_counts = []
        for cat in menu_categories:
            cat_tokens = tokens_no_stop(cat)
            cat_ngrams = build_ngrams(cat_tokens, min_shared_ngrams)
            shared = kw_ngrams & cat_ngrams
            if len(shared) >= min_shared_ngrams:
                # score = proportion de n-grams partagés (strict, sans fuzzy)
                denom = max(len(kw_ngrams), len(cat_ngrams)) or 1
                score = len(shared) / denom
                matches.append(cat)
                scores.append(score)
                shared_counts.append(len(shared))
        if matches:
            # choisir le meilleur: score max puis partage n-grams max puis longueur libellé min
            best_idx = max(range(len(matches)), key=lambda i: (scores[i], shared_counts[i], -len(matches[i])))
            best_single = matches[best_idx]
            best_score = scores[best_idx]
            best_shared = shared_counts[best_idx]
            all_matches_col.append(', '.join(matches))
            best_scores_col.append(best_score)
            best_shared_col.append(best_shared)
            best_single_col.append(best_single)
        else:
            all_matches_col.append('')
            best_scores_col.append(0.0)
            best_shared_col.append(0)
            best_single_col.append('')

    df_result = df.copy()
    df_result['Catégories_menu_matchées'] = all_matches_col
    df_result['Score_menu'] = best_scores_col
    df_result['Ngrams_partagés'] = best_shared_col
    df_result['Catégorie menu'] = best_single_col
    return df_result

def sort_keywords_view(df: pd.DataFrame, col_keyword_clean: str, col_volume: str) -> pd.DataFrame:
    """
    Trie les données d'affichage par Volume décroissant puis mot-clé nettoyé A→Z.
    Si la colonne nettoyée n'existe pas, utilise la colonne fournie telle quelle.
    """
    if col_volume and col_volume in df.columns:
        if col_keyword_clean in df.columns:
            return df.sort_values([col_volume, col_keyword_clean], ascending=[False, True])
        # fallback sur la première colonne textuelle
        for c in df.columns:
            if c != col_volume and df[c].dtype == object:
                return df.sort_values([col_volume, c], ascending=[False, True])
        return df.sort_values(col_volume, ascending=False)
    # si pas de volume, trier par mot-clé seul si présent
    if col_keyword_clean in df.columns:
        return df.sort_values(col_keyword_clean, ascending=True)
    return df

# --- Export XLSX (en mémoire) ---
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    Exporte un DataFrame en XLSX (bytes) pour Streamlit.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- Fonction pour s'assurer que toutes les colonnes e-commerce existent ---
def ensure_ecommerce_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    S'assure que toutes les colonnes e-commerce nécessaires existent dans le DataFrame.
    Utile pour les données qui ont été traitées avant les améliorations.
    """
    df_result = df.copy()
    
    # Colonnes de base
    ecommerce_columns = {
        'Marque_détectée': '',
        'Modèle_détecté': '',
        'Type_produit_détecté': '',
        'Score_marque': 0.0,
        'Score_modèle': 0.0,
        'Score_type': 0.0,
        'Ngrams_marque_partagés': 0,
        'Ngrams_modèle_partagés': 0,
        'Ngrams_type_partagés': 0
    }
    
    # Ajouter les colonnes manquantes
    for col, default_value in ecommerce_columns.items():
        if col not in df_result.columns:
            df_result[col] = default_value
    
    return df_result

# --- Détection e-commerce (marques, modèles, types) ---
def detect_ecommerce_entities(df: pd.DataFrame, col_keyword: str, marques: Optional[List[str]] = None, 
                            modeles: Optional[List[str]] = None, types_produits: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Détecte les correspondances avec les marques, modèles et types de produits dans les mots-clés.
    Utilise un matching robuste basé sur les n-grams partagés ET le fuzzy matching.
    
    Args:
        df: DataFrame contenant les mots-clés
        col_keyword: Nom de la colonne contenant les mots-clés
        marques: Liste des marques à détecter
        modeles: Liste des modèles à détecter
        types_produits: Liste des types de produits à détecter
    
    Returns:
        DataFrame enrichi avec les colonnes Marque_détectée, Modèle_détecté, Type_produit_détecté
    """
    # S'assurer que toutes les colonnes nécessaires existent
    df_result = ensure_ecommerce_columns(df)
    
    def get_ngrams(text: str, n: int = 1) -> set:
        """
        Extrait les n-grams d'un texte (mots consécutifs).
        """
        tokens = text.lower().split()
        ngrams = set()
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            if len(ngram.strip()) > 0:
                ngrams.add(ngram.strip())
        return ngrams
    
    def find_best_match_robust(text: str, candidates: List[str], threshold: float = 0.7, min_shared_ngrams: int = 1) -> tuple:
        """
        Trouve la meilleure correspondance avec une logique robuste basée sur l'exact match :
        1. Correspondance exacte (insensible à la casse)
        2. Correspondance basée sur les n-grams partagés (priorité)
        3. Correspondance implicite (ex: "iphone" → "Apple")
        NO FUZZY MATCHING - uniquement exact match
        """
        if not candidates:
            return '', 0.0, 0
        
        # Normaliser le texte
        text_norm = text.lower().strip()
        text_ngrams = get_ngrams(text_norm, 1)  # Unigrams pour commencer
        
        best_match = ''
        best_score = 0.0
        best_ngrams_shared = 0
        
        # Correspondances implicites (marques connues par leurs produits)
        correspondances_implicites = {
            'iphone': 'Apple',
            'ipad': 'Apple', 
            'macbook': 'Apple',
            'apple watch': 'Apple',
            'airpods': 'Apple',
            'galaxy': 'Samsung',
            'galaxy s': 'Samsung',
            'galaxy a': 'Samsung',
            'galaxy note': 'Samsung',
            'redmi': 'Xiaomi',
            'xiaomi mi': 'Xiaomi',
            'pixel': 'Google',
            'nexus': 'Google'
        }
        
        for candidate in candidates:
            candidate_norm = candidate.lower().strip()
            candidate_ngrams = get_ngrams(candidate_norm, 1)
            
            # 1. Correspondance exacte (priorité absolue)
            if candidate_norm in text_norm or text_norm in candidate_norm:
                return candidate, 1.0, len(candidate_ngrams)
            
            # 2. Correspondance basée sur les n-grams partagés
            shared_ngrams = text_ngrams & candidate_ngrams
            ngrams_shared = len(shared_ngrams)
            
            if ngrams_shared >= min_shared_ngrams:
                # Calculer un score basé sur la proportion de n-grams partagés
                score = ngrams_shared / max(len(text_ngrams), len(candidate_ngrams))
                
                # Si on a des n-grams partagés, c'est prioritaire
                if score > best_score or (score == best_score and ngrams_shared > best_ngrams_shared):
                    best_match = candidate
                    best_score = score
                    best_ngrams_shared = ngrams_shared
            
            # 3. Correspondance implicite (vérifier si le texte contient un produit de la marque)
            for produit, marque in correspondances_implicites.items():
                if marque.lower() == candidate_norm and produit in text_norm:
                    # Si c'est une correspondance implicite, donner un score élevé mais pas parfait
                    score_implicite = 0.9
                    if score_implicite > best_score:
                        best_match = candidate
                        best_score = score_implicite
                        best_ngrams_shared = 1  # Au moins un mot partagé
        
        # 4. Essayer avec des n-grams plus longs si pas de correspondance
        if not best_match:
            for n in range(2, 4):  # Bigrams et trigrams
                text_ngrams_n = get_ngrams(text_norm, n)
                for candidate in candidates:
                    candidate_norm = candidate.lower().strip()
                    candidate_ngrams_n = get_ngrams(candidate_norm, n)
                    shared_ngrams = text_ngrams_n & candidate_ngrams_n
                    
                    if len(shared_ngrams) >= min_shared_ngrams:
                        score = len(shared_ngrams) / max(len(text_ngrams_n), len(candidate_ngrams_n))
                        if score > best_score:
                            best_match = candidate
                            best_score = score
                            best_ngrams_shared = len(shared_ngrams)
        
        # NO FUZZY MATCHING - retourner le meilleur match trouvé ou rien
        return best_match, best_score, best_ngrams_shared
    
    # Détecter les marques
    if marques:
        for idx, row in df_result.iterrows():
            keyword = str(row[col_keyword])
            marque, score, ngrams_shared = find_best_match_robust(keyword, marques, threshold=0.7, min_shared_ngrams=1)
            df_result.at[idx, 'Marque_détectée'] = marque
            df_result.at[idx, 'Score_marque'] = score
            df_result.at[idx, 'Ngrams_marque_partagés'] = ngrams_shared
    
    # Détecter les modèles
    if modeles:
        for idx, row in df_result.iterrows():
            keyword = str(row[col_keyword])
            modele, score, ngrams_shared = find_best_match_robust(keyword, modeles, threshold=0.7, min_shared_ngrams=1)
            df_result.at[idx, 'Modèle_détecté'] = modele
            df_result.at[idx, 'Score_modèle'] = score
            df_result.at[idx, 'Ngrams_modèle_partagés'] = ngrams_shared
    
    # Détecter les types de produits
    if types_produits:
        for idx, row in df_result.iterrows():
            keyword = str(row[col_keyword])
            type_produit, score, ngrams_shared = find_best_match_robust(keyword, types_produits, threshold=0.7, min_shared_ngrams=1)
            df_result.at[idx, 'Type_produit_détecté'] = type_produit
            df_result.at[idx, 'Score_type'] = score
            df_result.at[idx, 'Ngrams_type_partagés'] = ngrams_shared
    
    return df_result
