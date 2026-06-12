# Architecture, Keyword Categorization App

## Modules

```text
streamlit_app.py
  -> wrapper Streamlit Cloud, importe app.main

app/main.py
  -> UI Streamlit, upload, orchestration, exports

app/utils.py
  -> nettoyage, détection colonnes, localités, intentions, e-commerce, mapping menu

app/clustering.py
  -> embeddings sentence-transformers, UMAP, HDBSCAN

app/scraping.py
  -> scraping best-effort du menu d'un site

app/config.py
  -> libellés i18n et paramètres de configuration

automation_seo_theme.py
  -> design system Automation SEO
```

## Flux principal

```text
main()
  -> apply_automation_seo_theme
  -> load_keywords_upload
  -> detect_keyword_column / detect_volume_column
  -> sidebar_controls
  -> clean_keywords
  -> detect_ecommerce_entities, optionnel
  -> semantic_clustering
  -> map_clusters_to_menu, optionnel
  -> dataframe preview
  -> CSV/XLSX export
```

## Chargement des données

- `_extract_and_load_zip` lit tous les CSV/CSV.gz d'une archive.
- `_read_csv_from_zip_member` lit chaque membre sans extraction durable.
- `load_keywords_upload` choisit le parseur selon l'extension.
- `_source_name_from_file_path` normalise le nom source.

## Sidebar

`sidebar_controls` gère :

- langue ;
- lemmatisation ;
- scraping menu ;
- marques ;
- modèles ;
- types de produits ;
- mode familles ;
- n-gram size ;
- familles fréquentes ;
- debug localités.

## Nettoyage

`utils.clean_keywords` :

- normalise le texte ;
- retire stopwords ;
- simplifie pluriels ;
- ajoute `Mot-clé_nettoye` ;
- ajoute `Mot-clé_lemmatisé` si activé.

## Localités et intentions

`utils` charge des référentiels locaux de communes, départements et régions. Le mode debug `KCA_DEBUG_LOCALITES` peut écrire des traces locales.

## Clustering

`semantic_clustering` :

- prépare les textes d'embedding ;
- ajoute éventuellement la catégorie menu au texte ;
- encode avec SentenceTransformer ;
- réduit avec UMAP ;
- clusterise avec HDBSCAN ;
- ajoute volume normalisé, embeddings et cluster.

## Mapping menu

Si l'utilisateur scrape une URL de menu, `scraping.scrape_menu` récupère les catégories, puis `utils.map_clusters_to_menu` peut rapprocher les clusters des catégories détectées.

## Design system

`app/main.py` doit appeler `apply_automation_seo_theme()` au début de `main()`. Le thème fournit :

- logo sidebar ;
- hero `.tool-hero` ;
- build marker `data-app-build` ;
- styles dark UI.

## Points de vigilance

- Ne pas charger les modèles embeddings avant nécessité.
- Ne pas écrire de logs debug localités dans Git.
- Garder `streamlit_app.py` comme wrapper Cloud si Streamlit Cloud pointe dessus.
- Toute évolution de clustering doit être testée sur un petit dataset fixe.
- Les dépendances `hdbscan` et `umap-learn` peuvent casser selon version Python.
