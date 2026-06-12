# Automation SEO Keyword Categorization

Application Streamlit publique pour nettoyer, enrichir, catégoriser et clusteriser des listes de mots-clés SEO. L'outil accepte des CSV simples, CSV.gz ou archives ZIP contenant plusieurs exports, puis produit un fichier de résultats enrichi.

## Source live

| Élément | Valeur |
|---|---|
| Live URL | https://automation-seo-keyword-categorization.streamlit.app/ |
| Repository principal | https://github.com/Heart-Quake/automation-seo-keyword-categorization |
| Miroir | https://github.com/YN-CodingClub/automation-seo-keyword-categorization |
| Branche live | `main` |
| Entrypoint Streamlit Cloud | `streamlit_app.py` |
| Entrypoint métier | `app/main.py` |
| Commande locale | `streamlit run streamlit_app.py` |
| Compilation | `python3 -m py_compile streamlit_app.py app/main.py automation_seo_theme.py` |
| Tests | Aucun test automatisé à date |
| Build marker live vérifié | `automation-seo-keyword-categorization:5886ea3` |
| Secrets | Aucun secret requis |

## Rôle produit

L'outil sert à transformer une liste brute de mots-clés en dataset exploitable :

- nettoyage et normalisation ;
- détection localités et intentions ;
- détection marques, modèles et types de produits ;
- scraping optionnel d'un menu de site pour récupérer des catégories ;
- clustering sémantique avec embeddings ;
- mapping optionnel des clusters vers des catégories de menu ;
- export CSV/XLSX.

Hors périmètre :

- collecte SERP ;
- scoring business final ;
- stockage des données ;
- traitement de très gros volumes sans contrainte mémoire.

## Quickstart

```bash
cd /Users/vincentflaceliere/Github/automation-seo-keyword-categorization
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Vérification minimale :

```bash
python3 -m py_compile streamlit_app.py app/main.py automation_seo_theme.py
```

## Documentation

- [Contrats de données](docs/DATA_CONTRACTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Runbook Streamlit](docs/RUNBOOK.md)

## Flux fonctionnel

```text
upload CSV/CSV.gz/ZIP
  -> détection colonnes keyword/volume
  -> nettoyage
  -> options e-commerce
  -> clustering sémantique
  -> mapping menu optionnel
  -> exports CSV/XLSX
```

## Dépendances lourdes

L'application installe notamment :

- `sentence-transformers`
- `spacy`
- `fr_core_news_md`
- `umap-learn`
- `hdbscan`

Sur Streamlit Community Cloud, utiliser Python 3.11 dans les paramètres avancés si le build échoue avec une version plus récente.

## Design system

L'app doit rester alignée avec le design Automation SEO :

- `automation_seo_theme.py` chargé au début de `main()`.
- `logo-sidebar-cream.png` présent à la racine.
- hero `.tool-hero`.
- marqueur caché `data-app-build`.
- patterns interdits : `#2BAF9C`, `DR SEO`, `Dr. SEO`, `base = "light"`.

## Tests et dette

Le repo ne contient pas encore de tests automatisés. Priorités recommandées :

- tests de détection de colonnes ;
- tests de chargement CSV/CSV.gz/ZIP ;
- tests de nettoyage keyword ;
- tests de détection e-commerce ;
- smoke test de clustering sur un petit dataset.

## Gouvernance Git

Ne pas commiter :

- exports keyword client ;
- fichiers ZIP clients ;
- outputs CSV/XLSX générés ;
- caches de modèles ;
- `.DS_Store`.

Le repo embarque uniquement les référentiels publics nécessaires à la détection locale. Aucun fichier `.env` ni donnée client ne doit être publié.
