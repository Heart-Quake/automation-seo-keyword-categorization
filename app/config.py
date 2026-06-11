"""
Configuration globale, stopwords, patterns d’intention et i18n pour Keyword Categorization App
"""

# --- Stopwords SEO (français et anglais, extensibles) ---
STOPWORDS = {
    "fr": [
        "le", "la", "les", "un", "une", "des", "du", "de", "d'", "en", "et", "ou", "pour", "avec", "sans", "sur", "dans", "par", "au", "aux", "ce", "ces", "cette", "son", "sa", "ses", "leur", "leurs", "mon", "ma", "mes", "ton", "ta", "tes", "notre", "nos", "votre", "vos", "à", "chez", "sous", "plus", "moins", "très", "trop", "bien", "mal", "meilleur", "meilleure", "meilleurs", "meilleures", "nouveau", "nouvelle", "nouveaux", "nouvel", "ancien", "ancienne", "anciens", "anciennes", "grand", "grande", "grands", "grandes", "petit", "petite", "petits", "petites", "premier", "première", "premiers", "premières", "dernier", "dernière", "derniers", "dernières", "autre", "autres", "tout", "toute", "tous", "toutes", "aucun", "aucune", "chaque", "quel", "quelle", "quels", "quelles", "qui", "que", "quoi", "dont", "où", "quand", "comment", "combien", "pourquoi", "lui", "elle", "on", "nous", "vous", "ils", "elles", "ceci", "cela", "ça", "c'", "y", "en", "ne", "pas", "plus", "moins", "jamais", "toujours", "souvent", "parfois", "rarement", "déjà", "encore", "aussi", "si", "même", "comme", "depuis", "avant", "après", "pendant", "vers", "entre", "chez", "contre", "sous", "sur", "dans", "hors", "devant", "derrière", "près", "loin", "ici", "là", "partout", "nulle part", "ailleurs", "ensemble", "seul", "seule", "seuls", "seules"
    ],
    "en": [
        "the", "a", "an", "and", "or", "for", "with", "without", "on", "in", "by", "to", "from", "of", "at", "as", "is", "are", "was", "were", "be", "been", "being", "this", "that", "these", "those", "his", "her", "its", "their", "my", "your", "our", "their", "all", "any", "each", "every", "some", "no", "not", "but", "if", "then", "else", "when", "where", "why", "how", "who", "whom", "which", "what", "whose", "can", "could", "should", "would", "will", "shall", "may", "might", "must", "do", "does", "did", "done", "have", "has", "had", "having", "more", "most", "less", "least", "very", "too", "also", "just", "even", "still", "yet", "already", "again", "once", "ever", "never", "always", "often", "sometimes", "rarely", "together", "apart", "alone", "only"
    ]
}

# --- Patterns d’intention SEO (transactionnelle, informationnelle, navigationnelle) ---
INTENT_PATTERNS = {
    "fr": {
        "transactionnelle": ["acheter", "prix", "promo", "réduction", "commande", "livraison", "panier", "code promo", "réserver", "abonnement", "offre", "vente", "boutique", "magasin", "acheter en ligne", "achat"],
        "informationnelle": ["avis", "test", "comparatif", "guide", "conseil", "astuce", "tutoriel", "comment", "pourquoi", "fonctionnement", "utilisation", "meilleur", "meilleure", "meilleurs", "meilleures", "idée", "idées", "exemple", "exemples", "définition", "explication", "différence", "avantage", "inconvénient"],
        "navigationnelle": ["site officiel", "page", "accueil", "contact", "connexion", "espace client", "mon compte", "adresse", "plan", "horaires", "localisation", "proche", "près de", "autour de", "près"],
        "locale": [
            'près de moi', 'autour de moi', 'proche de', 'à ', 'dans ', 'magasin', 'boutique', 'local', 'en région', 'en france', 'autour', 'près', 'proximité', 'zone', 'quartier', 'ville', 'commune', 'département', 'région'
        ]
    },
    "en": {
        "transactional": ["buy", "price", "order", "delivery", "cart", "discount", "offer", "shop", "store", "online", "purchase", "subscribe", "subscription", "deal", "sale"],
        "informational": ["review", "test", "comparison", "guide", "advice", "tips", "tutorial", "how", "why", "use", "best", "idea", "example", "definition", "explanation", "difference", "advantage", "disadvantage"],
        "navigational": ["official site", "homepage", "contact", "login", "account", "address", "map", "hours", "location", "near", "around", "close to"]
    }
}

# Liste simplifiée de villes françaises pour détection locale
VILLES_FR = [
    'paris', 'marseille', 'lyon', 'toulouse', 'nice', 'nantes', 'strasbourg', 'montpellier', 'bordeaux', 'lille',
    'rennes', 'reims', 'le havre', 'saint-étienne', 'toulon', 'grenoble', 'dijon', 'angers', 'nîmes', 'villeurbanne'
]

# --- Structure i18n (extensible) ---
I18N = {
    "fr": {
        "upload_csv": "Importer un fichier CSV de mots-clés",
        "select_language": "Langue de l’analyse",
        "lemmatization": "Activer la lemmatisation (optionnel)",
        "scrape_menu": "Scraper le menu d’un site web ?",
        "export_csv": "Télécharger CSV",
        "export_xlsx": "Télécharger XLSX",
        "results_preview": "Aperçu des résultats",
        "error_missing_column": "Le fichier doit contenir les colonnes 'Mot-clé' (ou 'keyword') et 'Volume'."
    },
    "en": {
        "upload_csv": "Upload a keyword CSV file",
        "select_language": "Analysis language",
        "lemmatization": "Enable lemmatization (optional)",
        "scrape_menu": "Scrape a website menu?",
        "export_csv": "Download CSV",
        "export_xlsx": "Download XLSX",
        "results_preview": "Results preview",
        "error_missing_column": "The file must contain 'keyword' and 'volume' columns."
    }
}
