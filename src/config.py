"""
Configuration du projet : chemins des fichiers et constantes.

Tous les chemins sont RELATIFS au dossier du projet : chaque membre du groupe
place les fichiers bruts dans `data/raw/` sur son ordinateur et le notebook
fonctionne sans rien modifier. Les données ne sont pas envoyées sur GitHub
(voir le fichier .gitignore).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Dossiers
# ---------------------------------------------------------------------------
# Path(__file__) = ce fichier (src/config.py). parents[1] = le dossier du projet.
RACINE = Path(__file__).resolve().parents[1]

DOSSIER_BRUT = RACINE / "data" / "raw"          # fichiers téléchargés, jamais modifiés
DOSSIER_PREP = RACINE / "data" / "processed"    # tables préparées par le code
DOSSIER_FIGURES = RACINE / "figures"            # graphiques exportés

# ---------------------------------------------------------------------------
# 2. Noms des fichiers bruts (à placer dans data/raw/)
# ---------------------------------------------------------------------------
FICHIERS = {
    # SDES (DiDo) - parc de véhicules au 1er janvier, par commune
    "parc": "Donnees-sur-le-parc-de-vehicules-au-niveau-communal_2026-06.csv",
    # SDES (DiDo) - immatriculations de véhicules neufs, par commune
    "neuf": "Immatriculations-de-vehicules-achetes-neufs-au-niveau-communal_2026-02.csv",
    # SDES (DiDo) - immatriculations de véhicules d'occasion, par commune
    "occasion": "Immatriculations-de-vehicules-achetes-doccasion-au-niveau-communal_2026-02.csv",
    # Insee - zonage en aires d'attraction des villes (géographie 2026)
    "aav": "AAV2020_au_01-01-2026.xlsx",
    # Insee - Filosofi 2023 "tous niveaux géographiques" (zip FILOSOFI_CC_csv.zip)
    "filosofi": "DS_FILOSOFI_CC_2023_data.csv",
    # transport.data.gouv.fr - base consolidée IRVE (points de recharge publics)
    "irve": "consolidation-etalab-schema-irve-statique-v-2_3_1-20261019.csv",
    # Insee - BPE 2025, dénombrement des équipements (zip DS_BPE_CSV_FR.zip)
    "bpe": "DS_BPE_2025_data.csv",
    # Insee - populations de référence 2023 (zip DS_POPULATIONS_REFERENCE_2023_CSV_FR)
    # Attention : population au 1er janvier 2023 dans les limites communales de 2025
    "population": "DS_POPULATIONS_REFERENCE_2023_data.csv",
    # Etalab - contours des communes 2026 (facultatif : carte + rattachement spatial
    # des bornes sans code commune). Fichier GeoJSON simplifié à 50 m.
    "contours": "communes-50m.geojson",
}

# Contours des départements (carte interactive). Si le fichier n'est pas dans
# data/raw/, le notebook le télécharge automatiquement depuis cette adresse publique.
FICHIER_DEPARTEMENTS = "departements-version-simplifiee.geojson"
URL_DEPARTEMENTS = ("https://raw.githubusercontent.com/gregoiredavid/france-geojson/"
                    "master/departements-version-simplifiee.geojson")

# Colonne du code commune dans le fichier de contours
# (contours Etalab : "code" ; ADMIN EXPRESS de l'IGN : "INSEE_COM")
CONTOURS_COL_CODE = "code"

# Date de l'archive IRVE retenue (à citer dans le notebook)
DATE_IRVE = "19/10/2026"

# ---------------------------------------------------------------------------
# 3. Dates de référence
# ---------------------------------------------------------------------------
ANNEE_PARC = 2026    # parc au 1er janvier 2026  -> colonne PARC_2026
ANNEE_IMMAT = 2025   # immatriculations de l'année 2025 -> colonne IMMAT_2025

# ---------------------------------------------------------------------------
# 4. Modalités des fichiers SDES (vérifiées dans les fichiers)
# ---------------------------------------------------------------------------
CATEGORIE_VP = "VP"                                # voitures particulières

# Le libellé "électrique" n'est PAS le même dans le parc et dans les immatriculations
ELEC_PARC = "Electrique"                           # le parc sépare "Hydrogène et autre ZE"
ELEC_IMMAT = "Electrique et hydrogène"             # les immatriculations regroupent les deux

# Statut de l'utilisateur : modalité qui correspond aux ménages
MENAGE_PARC = "Particulier"                        # autre modalité : "Professionel"
MENAGE_IMMAT = "PP"                                # PP = personne physique, PM = personne morale

# ---------------------------------------------------------------------------
# 5. Nomenclatures utiles
# ---------------------------------------------------------------------------
# Paris, Lyon et Marseille sont détaillés par arrondissement municipal dans le parc.
# On ramène chaque arrondissement au code de sa commune.
# Dictionnaire {code arrondissement: code commune}, par exemple {"75101": "75056", ...}
ARRONDISSEMENTS = {}
for i in range(1, 21):                      # Paris : 75101 à 75120
    ARRONDISSEMENTS[f"751{i:02d}"] = "75056"
for i in range(1, 10):                      # Lyon : 69381 à 69389
    ARRONDISSEMENTS[f"6938{i}"] = "69123"
for i in range(1, 17):                      # Marseille : 13201 à 13216
    ARRONDISSEMENTS[f"132{i:02d}"] = "13055"

# Position de la commune dans l'aire d'attraction (CATEAAV2020)
POSITION_AAV = {
    "11": "Pôle",   # commune-centre
    "12": "Pôle",   # autre commune du pôle principal
    "13": "Pôle",   # commune d'un pôle secondaire
    "20": "Couronne",
    "30": "Hors attraction",
}

# Taille de l'aire (TAAV2017, population de l'aire en 2017)
TAILLE_AAV = {
    "0": "Hors attraction",
    "1": "Moins de 50 000 hab.",
    "2": "50 000 à 200 000 hab.",
    "3": "200 000 à 700 000 hab.",
    "4": "700 000 hab. ou plus (hors Paris)",
    "5": "Aire de Paris",
}

# Régions de France métropolitaine (code -> libellé)
REGIONS = {
    "11": "Île-de-France",
    "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté",
    "28": "Normandie",
    "32": "Hauts-de-France",
    "44": "Grand Est",
    "52": "Pays de la Loire",
    "53": "Bretagne",
    "75": "Nouvelle-Aquitaine",
    "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur",
    "94": "Corse",
}

# Équipements de transport de la BPE (domaine E, sous-domaine E1 "Infrastructures de transports")
TYPES_GARES = ["E107", "E108", "E109"]          # gares de voyageurs d'intérêt national, régional, local
TYPES_TRANSPORT = ["E101", "E102"] + TYPES_GARES  # + taxi-VTC (E101) et aéroport (E102)

# Nombre de groupes de revenu : 4 = quartiles, 5 = quintiles
NB_GROUPES_REVENU = 4

# Seuil (en kW) au-delà duquel un point de charge est dit "rapide"
SEUIL_RAPIDE_KW = 50

# Seuil illustratif pour le test de sensibilité sur les petits effectifs
SEUIL_PETITS_EFFECTIFS = 20

# ---------------------------------------------------------------------------
# 6. Couleurs des graphiques
# ---------------------------------------------------------------------------
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"]
COULEUR_MANQUANT = "#d9d8d4"   # gris pour les données manquantes sur la carte
