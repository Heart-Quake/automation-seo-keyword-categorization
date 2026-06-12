"""
Application Streamlit principale pour Keyword Categorization App
"""

import os
import gzip
import zipfile
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from automation_seo_theme import apply_automation_seo_theme
from app import config
from app import utils
from app import clustering
from app import scraping


st.set_page_config(page_title="Keyword Categorization App", layout="wide")


def _suggest(label: str, help_text: str = ""):
    st.caption(f"💡 {label}" + (f" — {help_text}" if help_text else ""))


def _parse_textarea_list(value: str) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.replace("\r", "\n").split("\n") if v.strip()]


@st.cache_data(show_spinner=False)
def _read_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


def _source_name_from_file_path(file_path: str) -> str:
    """Retourne un nom source lisible à partir d'un chemin de fichier importé."""
    base_name = os.path.basename(file_path)
    if base_name.endswith(".gz"):
        base_name = base_name[:-3]
    if base_name.endswith(".csv"):
        base_name = base_name[:-4]
    return base_name or "source"


def _read_csv_from_zip_member(zip_ref: zipfile.ZipFile, member_name: str) -> pd.DataFrame:
    """Lit un CSV ou CSV.gz depuis une archive ZIP sans extraire de fichier sur disque."""
    with zip_ref.open(member_name) as member:
        if member_name.endswith(".gz"):
            with gzip.open(member, mode="rt", encoding="utf-8") as gzip_file:
                return pd.read_csv(gzip_file)
        return pd.read_csv(member)


def _extract_and_load_zip(zip_file, selected_files: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str]]:
    """Extrait les CSV/CSV.gz d'un ZIP et les agrège avec une colonne source_file."""
    zip_file.seek(0)
    selected_files = selected_files or []
    selected_file_names = {os.path.basename(file_name) for file_name in selected_files}
    dataframes = []
    processed_files = []

    with zipfile.ZipFile(zip_file) as zip_ref:
        candidate_files = [
            file_name
            for file_name in sorted(zip_ref.namelist())
            if not file_name.endswith("/") and (file_name.endswith(".csv") or file_name.endswith(".csv.gz"))
        ]

        if selected_files:
            candidate_files = [
                file_name
                for file_name in candidate_files
                if file_name in selected_files or os.path.basename(file_name) in selected_file_names
            ]

        for file_name in candidate_files:
            dataframe = _read_csv_from_zip_member(zip_ref, file_name)
            dataframe["source_file"] = _source_name_from_file_path(file_name)
            dataframes.append(dataframe)
            processed_files.append(file_name)

    if not dataframes:
        raise ValueError("Aucun fichier CSV ou CSV.gz valide trouvé dans le ZIP.")

    return pd.concat(dataframes, ignore_index=True), processed_files


def load_keywords_upload(uploaded_file) -> Tuple[pd.DataFrame, List[str]]:
    """Charge un fichier CSV, CSV.gz ou ZIP de mots-clés."""
    file_name = str(getattr(uploaded_file, "name", "")).lower()
    uploaded_file.seek(0)

    if file_name.endswith(".zip"):
        return _extract_and_load_zip(uploaded_file)

    if file_name.endswith(".csv.gz"):
        with gzip.open(uploaded_file, mode="rt", encoding="utf-8") as gzip_file:
            dataframe = pd.read_csv(gzip_file)
        dataframe["source_file"] = _source_name_from_file_path(file_name)
        return dataframe, [getattr(uploaded_file, "name", "upload.csv.gz")]

    dataframe = pd.read_csv(uploaded_file)
    return dataframe, [getattr(uploaded_file, "name", "upload.csv")]


def _progress_callback(pct: int, message: str):
    st.session_state["progress_pct"] = pct
    st.session_state["progress_msg"] = message


def _ensure_sort_and_width(df: pd.DataFrame, col_keyword_clean: str, col_volume: str) -> pd.DataFrame:
    df_sorted = utils.sort_keywords_view(df, col_keyword_clean=col_keyword_clean, col_volume=col_volume)
    st.dataframe(df_sorted, use_container_width=True)
    return df_sorted


def sidebar_controls():
    st.sidebar.header("Paramètres")

    lang = st.sidebar.selectbox(
        config.I18N.keys(),
        index=list(config.I18N.keys()).index("fr") if "fr" in config.I18N else 0,
        label=config.I18N.get("fr", {}).get("select_language", "Langue de l’analyse")
    )

    lemmatize = st.sidebar.checkbox(
        label=config.I18N.get(lang, {}).get("lemmatization", "Activer la lemmatisation (optionnel)"),
        value=False,
    )

    st.sidebar.divider()
    st.sidebar.subheader("Menu (optionnel)")
    url = st.sidebar.text_input("URL à scraper")
    if st.sidebar.button("Scraper le menu") and url:
        cats = scraping.scrape_menu(url)
        st.session_state["menu_categories"] = cats
    menu_categories = st.session_state.get("menu_categories", [])
    if menu_categories:
        st.sidebar.success(f"Catégories détectées: {len(menu_categories)}")
        with st.sidebar.expander("Voir les catégories"):
            st.write(menu_categories)

    st.sidebar.divider()
    st.sidebar.subheader("E-commerce (optionnel)")
    marques_txt = st.sidebar.text_area("Liste des marques (une par ligne)")
    modeles_txt = st.sidebar.text_area("Liste des modèles (une par ligne)")
    types_txt = st.sidebar.text_area("Liste des types de produits (une par ligne)")

    famille_mode = st.sidebar.selectbox(
        "Mode familles",
        ["Une seule famille dominante", "Plusieurs familles (n-grams)", "Aucune"],
        index=0,
    )
    ngram_size = st.sidebar.slider("Taille des n-grams", min_value=1, max_value=4, value=2)
    use_frequent_families = st.sidebar.checkbox("Ne garder que les n-grams fréquents", value=True)

    st.sidebar.divider()
    st.sidebar.subheader("Options avancées")
    st.sidebar.checkbox("Activer logs localités (KCA_DEBUG_LOCALITES)", key="debug_localites")
    if st.session_state.get("debug_localites"):
        os.environ["KCA_DEBUG_LOCALITES"] = "1"
    else:
        os.environ.pop("KCA_DEBUG_LOCALITES", None)

    return {
        "lang": lang,
        "lemmatize": lemmatize,
        "menu_categories": menu_categories,
        "famille_mode": famille_mode,
        "ngram_size": ngram_size,
        "use_frequent_families": use_frequent_families,
        "marques": _parse_textarea_list(marques_txt),
        "modeles": _parse_textarea_list(modeles_txt),
        "types_produits": _parse_textarea_list(types_txt),
    }


def main():
    apply_automation_seo_theme()
    i18n = config.I18N.get("fr", {})
    st.markdown(
        """
        <section class="tool-hero">
            <div class="tool-kicker">Keyword intelligence</div>
            <h1 class="tool-title">Keyword Categorization App</h1>
            <p class="tool-lead">Classe les listes de mots-cles par familles, intentions et regles metier pour preparer les exports SEO.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # Étape 1 — Import CSV / ZIP
    st.subheader("1️⃣ Importer un fichier de mots-clés")
    uploaded = st.file_uploader(
        i18n.get("upload_csv", "Importer un fichier CSV de mots-clés"),
        type=["csv", "gz", "zip"],
        help="Formats supportés : CSV, CSV.gz ou ZIP contenant plusieurs CSV/CSV.gz."
    )
    if uploaded is None:
        _suggest("Glissez un CSV, CSV.gz ou ZIP avec 'Mot-clé' et 'Volume'.")
        st.stop()

    try:
        df_src, processed_files = load_keywords_upload(uploaded)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier: {e}")
        st.stop()

    if processed_files:
        st.caption(f"{len(processed_files)} fichier(s) traité(s) : {', '.join(processed_files[:5])}")

    params = sidebar_controls()
    lang = params["lang"]
    col_kw = utils.detect_keyword_column(df_src) or ("Mot-clé" if "Mot-clé" in df_src.columns else None)
    col_vol = utils.detect_volume_column(df_src) or ("Volume" if "Volume" in df_src.columns else None)
    if not col_kw or not col_vol:
        st.error(i18n.get("error_missing_column", "Le fichier doit contenir les colonnes 'Mot-clé' (ou 'keyword') et 'Volume'."))
        st.stop()

    # Choix d'analyse: aperçu rapide (500) ou analyse complète
    colA, colB = st.columns(2)
    run_sample = colA.button("🔎 Aperçu rapide (500 premiers mots-clés)")
    run_full = colB.button(f"🚀 Lancer l’analyse complète ({len(df_src)}) mots-clés")
    if run_sample:
        df_base = df_src.head(500)
        st.warning("Clustering sur 500 mots-clés pour un aperçu rapide. Relancez l’analyse complète pour tout traiter.")
    elif run_full:
        df_base = df_src
    else:
        st.stop()

    # Étape 1 (optionnel) — Scraping du menu
    if params.get("menu_categories"):
        st.subheader("1️⃣ Scraping / catégories menu (optionnel)")
        st.success(f"Catégories détectées: {len(params['menu_categories'])}")
        with st.expander("Voir les catégories"):
            st.write(params["menu_categories"])

    # Étape 2 — Nettoyage
    st.subheader("2️⃣ Nettoyage")
    df_clean = utils.clean_keywords(df_base.copy(), col_keyword=col_kw, lemmatize=params["lemmatize"], lang=lang)
    _suggest("Tri appliqué: Volume décroissant puis mot-clé nettoyé A→Z")
    df_view = _ensure_sort_and_width(df_clean, col_keyword_clean="Mot-clé_nettoye", col_volume=col_vol)

    # Étape 2b (optionnel) — Détection e-commerce (strict n-grams)
    if params["marques"] or params["modeles"] or params["types_produits"]:
        st.subheader("2️⃣bis Détection e-commerce (optionnel)")
        df_ecom = utils.detect_ecommerce_entities(df_view, col_keyword=col_kw, marques=params["marques"], modeles=params["modeles"], types_produits=params["types_produits"])
        df_ecom = _ensure_sort_and_width(df_ecom, col_keyword_clean="Mot-clé_nettoye", col_volume=col_vol)
        st.session_state["df_ecom"] = df_ecom
    else:
        st.session_state.pop("df_ecom", None)

    # Étape 3 — Analyse sémantique et clustering
    st.subheader("3️⃣ Analyse sémantique et clustering")
    if "progress_pct" not in st.session_state:
        st.session_state["progress_pct"] = 0
        st.session_state["progress_msg"] = ""
    progress = st.progress(st.session_state["progress_pct"])  # type: ignore
    st.caption(st.session_state["progress_msg"])  # type: ignore

    def _cb(p, m):
        _progress_callback(p, m)
        progress.progress(p)
        st.session_state["progress_msg"] = m

    try:
        df_clusters = clustering.semantic_clustering(
            df_view.copy(),
            col_keyword=col_kw,
            col_volume=col_vol,
            lang=lang,
            progress_callback=_cb,
            menu_categories=params["menu_categories"],
            famille_mode=params["famille_mode"],
            ngram_size=params["ngram_size"],
            use_frequent_families=params["use_frequent_families"],
        )
        df_clusters = _ensure_sort_and_width(df_clusters, col_keyword_clean="Mot-clé_nettoye", col_volume=col_vol)
        st.session_state["df_clusters"] = df_clusters
    except Exception as e:
        st.error(f"Erreur clustering: {e}")
        st.stop()

    # Étape 4 — Mapping clusters / catégories menu (optionnel)
    df_final = st.session_state.get("df_clusters", df_view)
    if params["menu_categories"]:
        st.subheader("4️⃣ Mapping clusters / catégories menu")
        df_final = utils.map_clusters_to_menu(df_final, params["menu_categories"], col_keyword=col_kw)
        df_final = _ensure_sort_and_width(df_final, col_keyword_clean="Mot-clé_nettoye", col_volume=col_vol)

    # Étape 5 — Aperçu des résultats
    st.subheader("5️⃣ Aperçu des résultats")
    st.dataframe(df_final.head(50), use_container_width=True)

    # Étape 6 — Export
    st.subheader("6️⃣ Exporter les résultats")
    csv_bytes = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(i18n.get("export_csv", "Télécharger CSV"), data=csv_bytes, file_name="keywords_results.csv", mime="text/csv")
    try:
        xlsx_bytes = utils.to_excel_bytes(df_final)
        st.download_button(i18n.get("export_xlsx", "Télécharger XLSX"), data=xlsx_bytes, file_name="keywords_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.warning(f"Export XLSX indisponible: {e}")

    # Suggestions d’analyse contextuelles
    if params["menu_categories"] and "df_clusters" in st.session_state:
        _suggest("Filtrez par 'Catégorie_menu_guidée' pour explorer les clusters par navigation.")
    if params["marques"]:
        _suggest("Vérifiez 'Marque_détectée' et comparez les 'Score_marque'.")


if __name__ == "__main__":
    main()
