# Runbook, Keyword Categorization App

## Déploiement live

| Élément | Valeur |
|---|---|
| Live URL | https://automation-seo-keyword-categorization.streamlit.app/ |
| Repository principal | `Heart-Quake/automation-seo-keyword-categorization` |
| Miroir | `YN-CodingClub/automation-seo-keyword-categorization` |
| Branche | `main` |
| Entrypoint Cloud | `streamlit_app.py` |
| Entrypoint métier | `app/main.py` |
| Dernier build marker vérifié | `automation-seo-keyword-categorization:5886ea3` |

## Commandes locales

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

## Smoke test live

Dans l'iframe Streamlit `streamlitApp`, vérifier :

- `.tool-hero` count = 1 ;
- `.sidebar-logo img` count = 1 ;
- `[data-app-build]` count = 1 ;
- `--yn-bg` présent ;
- uploader CSV visible ;
- pas de traceback ;
- message d'import attendu si aucun fichier n'est chargé.

## Build Streamlit Cloud

Dépendances sensibles :

- `sentence-transformers` ;
- `spacy` ;
- `fr_core_news_md` ;
- `umap-learn` ;
- `hdbscan`.

Si le build échoue :

1. vérifier la version Python dans les paramètres avancés Streamlit Cloud ;
2. privilégier Python 3.11 ;
3. vérifier `requirements.txt` ;
4. relancer `python3 -m py_compile streamlit_app.py app/main.py automation_seo_theme.py` localement.

## Dépannage fonctionnel

### Erreur colonnes manquantes

Cause :

- colonne keyword absente ;
- colonne volume absente ;
- nom de colonne non reconnu.

Action :

- renommer en `Mot-clé` ou `keyword` ;
- renommer en `Volume` ;
- ajouter un alias dans `utils.detect_keyword_column` ou `utils.detect_volume_column` si le format devient récurrent.

### Clustering lent

Cause :

- gros dataset ;
- premier chargement du modèle SentenceTransformer ;
- UMAP/HDBSCAN coûteux.

Action :

- utiliser l'aperçu rapide 500 mots-clés ;
- réduire le volume d'entrée ;
- vérifier mémoire Streamlit Cloud.

### Scraping menu vide

Cause :

- site rendu en JS ;
- blocage réseau ;
- navigation non sémantique ;
- liens externes filtrés.

Action :

- vérifier l'URL ;
- inspecter manuellement le menu ;
- fournir les catégories manuellement via un futur champ si nécessaire.

### Debug localités

L'option `Activer logs localités (KCA_DEBUG_LOCALITES)` écrit des traces locales. Ne pas commiter ces fichiers si générés.

## Règles UI

- Conserver le design system Automation SEO.
- Ne pas réintroduire l'ancien branding.
- Éviter les composants HTML custom pour des interactions disponibles en Streamlit natif.
- Ne pas afficher d'informations techniques non utiles dans l'interface utilisateur.

## Fichiers à ne pas commiter

- exports keyword client ;
- fichiers ZIP clients ;
- outputs CSV/XLSX ;
- logs debug localités ;
- caches de modèles ;
- `.DS_Store`.
