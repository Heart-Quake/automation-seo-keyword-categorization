"""
Module de clustering sémantique pour Keyword Categorization App
Utilise sentence-transformers, UMAP et HDBSCAN pour regrouper les mots-clés par similarité sémantique.
"""

import pandas as pd
from sentence_transformers import SentenceTransformer
import umap
import hdbscan
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import streamlit as st
from typing import List, Optional

# --- Modèles d'embeddings disponibles ---
EMBEDDING_MODELS = {
    "fr": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "en": "sentence-transformers/all-MiniLM-L6-v2"
}
from functools import lru_cache

@lru_cache(maxsize=4)
def get_sentence_model(lang: str) -> SentenceTransformer:
    model_name = EMBEDDING_MODELS.get(lang, EMBEDDING_MODELS["fr"])
    return SentenceTransformer(model_name)



def semantic_clustering(
    df: pd.DataFrame,
    col_keyword: str,
    col_volume: str,
    lang: str = "fr",
    progress_callback=None,
    menu_categories: Optional[List[str]] = None,
    famille_mode: str = "Une seule famille dominante",
    ngram_size: int = 2,
    use_frequent_families: bool = True,
    n_neighbors: int = 15,
    n_components: int = 5,
    min_cluster_size: int = 3,
    min_samples: int = 1
) -> pd.DataFrame:
    """
    Effectue le clustering sémantique des mots-clés, avec option de guidage par les catégories menu.
    Si menu_categories est fourni, chaque mot-clé est rapproché de la catégorie menu la plus proche (fuzzy matching),
    et la catégorie est ajoutée comme contexte lors du calcul des embeddings.
    """
    if progress_callback: progress_callback(0, "Préparation des données...")
    keywords = df[col_keyword].astype(str).tolist()
    # Si menu guidage, associer chaque mot-clé à la meilleure catégorie via n-grams partagés (strict)
    menu_match = [None] * len(keywords)
    if menu_categories:
        from app import config as _cfg
        import re as _re
        import unidecode as _unidecode

        stopwords = set(_cfg.STOPWORDS.get(lang, []))

        def _norm_token(t: str) -> str:
            t = _unidecode.unidecode(str(t).lower().strip())
            t = _re.sub(r"[^\w\s-]", " ", t)
            t = t.replace("-", " ")
            t = " ".join(t.split())
            return t

        def _tokens_no_stop(text: str):
            toks = [_norm_token(tok) for tok in _re.split(r"\s+", _unidecode.unidecode(str(text)))]
            return [t for t in toks if t and t not in stopwords]

        def _ngrams(tokens, n):
            if len(tokens) < n:
                return set()
            return set(' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1))

        for i, kw in enumerate(keywords):
            kw_tokens = _tokens_no_stop(kw)
            kw_ngrams = _ngrams(kw_tokens, 1)
            best_cat = ""
            best_score = 0.0
            for cat in menu_categories:
                cat_tokens = _tokens_no_stop(cat)
                cat_ngrams = _ngrams(cat_tokens, 1)
                shared = kw_ngrams & cat_ngrams
                if len(shared) >= 1:
                    denom = max(len(kw_ngrams), len(cat_ngrams)) or 1
                    score = len(shared) / denom
                    if score > best_score or (score == best_score and len(cat) < len(best_cat) if best_cat else True):
                        best_score = score
                        best_cat = cat
            menu_match[i] = best_cat
        # Ajout du contexte menu strict à chaque mot-clé
        keywords = [f"{kw} {cat}" if cat else kw for kw, cat in zip(keywords, menu_match)]
        df['Catégorie_menu_guidée'] = menu_match
    if progress_callback: progress_callback(10, "Calcul des embeddings...")
    model = get_sentence_model(lang)
    embeddings = model.encode(keywords, show_progress_bar=False)
    if progress_callback: progress_callback(35, "Réduction de dimension (UMAP)...")
    # Ajustements robustes pour petits jeux de données
    n_samples = len(keywords)
    nn = max(2, min(n_neighbors, max(2, n_samples - 1)))
    nc = min(n_components, 2 if n_samples < 5 else n_components)
    reducer = umap.UMAP(n_neighbors=nn, n_components=nc, metric='cosine', random_state=42)
    embeddings_umap = reducer.fit_transform(embeddings)
    if progress_callback: progress_callback(70, "Clustering (HDBSCAN)...")
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples, metric='euclidean', prediction_data=True)
    clusters = clusterer.fit_predict(embeddings_umap)
    if progress_callback: progress_callback(85, "Enrichissement des résultats...")
    # Normalisation robuste du volume (gérer espaces insécables, milliers, etc.)
    scaler = MinMaxScaler()
    vol_str = df[col_volume].astype(str)
    # Supprimer tout ce qui n'est pas chiffre (ex: \u202F, \u00A0, espaces, points, virgules)
    vol_digits = vol_str.str.replace(r"[^0-9]", "", regex=True)
    vol_numeric = pd.to_numeric(vol_digits, errors='coerce').fillna(0.0).astype(float)
    df['Volume_norm'] = scaler.fit_transform(vol_numeric.to_numpy().reshape(-1, 1))
    df['Cluster'] = clusters
    df['Embedding_1'] = embeddings_umap[:, 0]
    # Gestion du cas où n_components==1
    if embeddings_umap.shape[1] == 1:
        df['Embedding_1'] = embeddings_umap[:, 0]
        df['Embedding_2'] = 0.0
    else:
        df['Embedding_1'] = embeddings_umap[:, 0]
        df['Embedding_2'] = embeddings_umap[:, 1]
    if progress_callback: progress_callback(100, "Clustering terminé.")
    # Ajout de la colonne Famille (n-gram) et Intention
    from app.utils import extract_families_and_intentions
    # Assurer la présence de la colonne nettoyée pour l'extraction
    if 'Mot-clé_nettoye' not in df.columns:
        try:
            from app.utils import clean_keywords as _clean_keywords
            df = _clean_keywords(df, col_keyword=col_keyword, lemmatize=False, lang=lang)
        except Exception:
            pass
    if famille_mode == "Aucune":
        df['Famille'] = ""
        from app.utils import detect_intention
        # detect_intention retourne (intention, localité, type_localité). Ne garder que la chaîne d'intention.
        df['Intention'] = df[col_keyword].apply(lambda kw: detect_intention(kw, lang)[0])
    elif famille_mode == "Plusieurs familles (n-grams)":
        df = extract_families_and_intentions(df, col_keyword, lang, all_families=True, ngram_size=locals().get('ngram_size', 2), frequent_only=locals().get('use_frequent_families', True))
    else:  # "Une seule famille dominante"
        df = extract_families_and_intentions(df, col_keyword, lang, all_families=False, ngram_size=locals().get('ngram_size', 2), frequent_only=locals().get('use_frequent_families', True))
    return df
