# Contrats de données, Keyword Categorization App

## Formats acceptés

L'uploader Streamlit accepte :

- `.csv` ;
- `.csv.gz` ;
- `.zip` contenant un ou plusieurs `.csv` ou `.csv.gz`.

Les fichiers ZIP sont parcourus sans extraction permanente sur disque. Chaque fichier traité ajoute une colonne `source_file`.

## Colonnes obligatoires

L'application doit détecter :

| Concept | Noms attendus |
|---|---|
| mot-clé | `Mot-clé`, `keyword`, ou variante détectée par `utils.detect_keyword_column` |
| volume | `Volume`, ou variante détectée par `utils.detect_volume_column` |

Si l'une des deux colonnes est absente, l'app stoppe avec :

```text
Le fichier doit contenir les colonnes 'Mot-clé' (ou 'keyword') et 'Volume'.
```

## Lecture CSV

Lecture actuelle :

- `pd.read_csv` pour CSV ;
- `gzip.open(..., mode="rt", encoding="utf-8")` pour CSV.gz ;
- `zipfile.ZipFile` pour ZIP.

Le contrat recommandé pour limiter les erreurs :

- encodage UTF-8 ;
- séparateur standard détectable par Pandas ;
- une ligne d'en-tête ;
- colonne volume numérique ou coercible.

## Données optionnelles

L'utilisateur peut fournir en sidebar :

- URL de menu à scraper ;
- liste de marques ;
- liste de modèles ;
- liste de types de produits ;
- mode de familles ;
- taille des n-grams ;
- activation des familles fréquentes ;
- activation debug localités.

## Colonnes ajoutées

Colonnes principales ajoutées ou transformées :

| Colonne | Source | Rôle |
|---|---|---|
| `source_file` | upload ZIP ou CSV.gz | origine du fichier |
| `Mot-clé_nettoye` | `utils.clean_keywords` | keyword normalisé |
| `Mot-clé_lemmatisé` | option lemmatisation | variante lemmatisée |
| `Volume_norm` | clustering | volume normalisé |
| `Embedding_1` / `Embedding_2` | UMAP | coordonnées embeddings |
| `Cluster` | HDBSCAN | cluster sémantique |
| familles / intentions | `utils` | enrichissements métier |
| colonnes e-commerce | `utils.detect_ecommerce_entities` | marque, modèle, type produit |

## Clustering

Le clustering utilise :

- modèle `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` en français ;
- modèle `sentence-transformers/all-MiniLM-L6-v2` en anglais ;
- réduction UMAP ;
- clustering HDBSCAN.

Paramètres clés calculés dans `app/clustering.py` :

- `n_neighbors` adapté au nombre de keywords ;
- `n_components` adapté à la taille du dataset ;
- `min_cluster_size` et `min_samples` adaptés au volume.

## Exports

Exports disponibles :

- CSV `keywords_results.csv` ;
- XLSX `keywords_results.xlsx` si le module Excel est disponible.

Les exports contiennent le DataFrame final enrichi.

## Limites

- Les gros ZIP peuvent être coûteux en mémoire.
- Les dépendances embeddings peuvent ralentir le premier démarrage.
- Le scraping menu dépend du HTML public du site cible et peut échouer si navigation JS ou blocage.
- La lemmatisation dépend du modèle spaCy `fr_core_news_md`.
- Sans tests automatisés, toute évolution de détection de colonnes ou clustering doit être vérifiée manuellement.
