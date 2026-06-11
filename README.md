# Automation SEO Keyword Categorization

Application Streamlit publique pour categoriser et clusteriser des mots-cles SEO.

## Deploiement Streamlit Community Cloud

- Repository : `YN-CodingClub/automation-seo-keyword-categorization`
- Branch : `main`
- Main file path : `streamlit_app.py`
- App URL : `automation-seo-keyword-categorization`

URL cible :

```text
https://automation-seo-keyword-categorization.streamlit.app/
```

## Notes de deploiement

Cette app installe des dependances lourdes : `sentence-transformers`, `spacy`, `umap-learn`, `hdbscan` et le modele `fr_core_news_md`.

Sur Streamlit Community Cloud, utiliser Python 3.11 dans les parametres avances si le build echoue avec une version plus recente.

## Donnees

Le repo embarque uniquement les referentiels publics necessaires a la detection locale. Aucun fichier `.env` ni donnees client ne sont publies.
