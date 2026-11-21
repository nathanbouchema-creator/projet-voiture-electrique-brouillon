"""
Lecture et préparation des fichiers bruts.

Une fonction par source. Chaque fonction renvoie une table avec UNE ligne par
commune et une colonne `code_commune` (texte sur 5 caractères), prête à être
jointe aux autres.
"""

import json
import urllib.request

import numpy as np
import pandas as pd

from src import config


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------
def chemin_brut(cle):
    """Renvoie le chemin d'un fichier brut à partir de sa clé dans config.FICHIERS."""
    return config.DOSSIER_BRUT / config.FICHIERS[cle]


def regrouper_arrondissements(codes):
    """Remplace les codes d'arrondissement de Paris, Lyon et Marseille
    par le code de la commune (ex. 75115 -> 75056). Les autres codes ne changent pas."""
    return codes.replace(config.ARRONDISSEMENTS)


def garder_communes(df):
    """Garde les lignes communales d'un fichier Insee au format long (colonnes GEO, GEO_OBJECT).

    Paris, Lyon et Marseille peuvent n'être diffusées que par arrondissement
    (GEO_OBJECT = "ARM"). Dans ce cas, on ramène les arrondissements au code de la
    commune ; il faudra ensuite SOMMER les valeurs (valable pour des effectifs,
    pas pour une médiane). Si la commune est déjà diffusée, ses arrondissements sont ignorés.
    """
    communes = df[df["GEO_OBJECT"] == "COM"]
    arrondissements = df[df["GEO_OBJECT"] == "ARM"].copy()
    arrondissements["GEO"] = regrouper_arrondissements(arrondissements["GEO"])
    arrondissements = arrondissements[~arrondissements["GEO"].isin(communes["GEO"])]
    return pd.concat([communes, arrondissements])


def verifier_une_seule_annee(df, nom_source):
    """Évite d'additionner plusieurs années par erreur."""
    if "TIME_PERIOD" in df.columns:
        annees = df["TIME_PERIOD"].unique()
        assert len(annees) == 1, f"{nom_source} : plusieurs années {annees}, en choisir une"


# ---------------------------------------------------------------------------
# 1. Fichiers automobiles du SDES (parc, neuf, occasion)
# ---------------------------------------------------------------------------
def lire_fichier_sdes(cle, colonnes_valeurs):
    """Lit un fichier communal du SDES et garde uniquement les voitures particulières.

    Particularités des fichiers DiDo :
    - séparateur ";"
    - DEUX lignes d'en-tête : la 1re contient les libellés longs, la 2e les codes
      (COMMUNE_CODE, CARBURANT...). On saute la 1re avec skiprows=1.
    - le code commune doit être lu comme du texte pour garder les zéros initiaux.
    """
    colonnes = ["COMMUNE_CODE", "CARBURANT", "STATUT_UTILISATEUR", "CATEGORIE"]
    df = pd.read_csv(
        chemin_brut(cle),
        sep=";",
        skiprows=1,
        usecols=colonnes + colonnes_valeurs,
        dtype={"COMMUNE_CODE": str},
    )
    df = df[df["CATEGORIE"] == config.CATEGORIE_VP].copy()
    df["code_commune"] = regrouper_arrondissements(df["COMMUNE_CODE"])
    return df


def preparer_vehicules(df, colonne, libelle_elec, statut_menage, nom):
    """Agrège un fichier SDES au niveau commune.

    Le fichier contient une ligne par commune x carburant x statut (x Crit'Air).
    Il n'y a pas de ligne "Ensemble" : le total d'une commune est donc la somme
    de TOUTES les lignes (tous carburants, y compris "Inconnu").

    Renvoie, pour chaque commune :
    - vp_{nom}            : toutes les voitures
    - vp_{nom}_elec       : voitures électriques
    - vp_{nom}_men        : voitures des ménages (particuliers)
    - vp_{nom}_elec_men   : voitures électriques des ménages
    """
    est_elec = df["CARBURANT"] == libelle_elec
    est_menage = df["STATUT_UTILISATEUR"] == statut_menage

    # .where(condition, 0) garde la valeur si la condition est vraie, sinon met 0
    df = df.assign(
        total=df[colonne],
        elec=df[colonne].where(est_elec, 0),
        total_men=df[colonne].where(est_menage, 0),
        elec_men=df[colonne].where(est_elec & est_menage, 0),
    )
    table = df.groupby("code_commune")[["total", "elec", "total_men", "elec_men"]].sum()
    table = table.reset_index().rename(columns={
        "total": f"vp_{nom}",
        "elec": f"vp_{nom}_elec",
        "total_men": f"vp_{nom}_men",
        "elec_men": f"vp_{nom}_elec_men",
    })
    return table


def serie_metropole(df, prefixe, libelle_elec):
    """Série annuelle France métropolitaine : effectif total, électrique et part.

    On garde aussi les codes fictifs des départements métropolitains (ex. 59000),
    qui font partie du total national. On exclut les DOM (codes en 97...)
    et le code "00000" (commune et département inconnus).
    """
    metro = df[~df["code_commune"].str.startswith("97") & (df["code_commune"] != "00000")]
    colonnes = [c for c in metro.columns if c.startswith(prefixe)]

    total = metro[colonnes].sum()
    elec = metro.loc[metro["CARBURANT"] == libelle_elec, colonnes].sum()

    serie = pd.DataFrame({
        "annee": [int(c.split("_")[1]) for c in colonnes],   # "PARC_2026" -> 2026
        "total": total.values,
        "elec": elec.values,
    })
    serie["part_elec"] = 100 * serie["elec"] / serie["total"]
    return serie


# ---------------------------------------------------------------------------
# 2. Aires d'attraction des villes (Insee)
# ---------------------------------------------------------------------------
def preparer_aav():
    """Table de référence des communes de France métropolitaine avec leur
    position dans l'aire d'attraction et la taille de l'aire.

    - Les noms de colonnes sont à la ligne 6 du classeur -> skiprows=5.
    - engine="calamine" : le classeur Insee a des styles Excel que openpyxl
      n'arrive pas à lire ; calamine ignore les styles et lit les valeurs.
    """
    chemin = chemin_brut("aav")
    compo = pd.read_excel(chemin, sheet_name="Composition_communale",
                          skiprows=5, dtype=str, engine="calamine")
    aires = pd.read_excel(chemin, sheet_name="AAV2020",
                          skiprows=5, dtype=str, engine="calamine")

    compo = compo[["CODGEO", "LIBGEO", "AAV2020", "LIBAAV2020", "CATEAAV2020", "DEP", "REG"]]
    aires = aires[["AAV2020", "TAAV2017"]]

    # Plusieurs communes -> une seule aire : validate="many_to_one" le vérifie
    aav = compo.merge(aires, on="AAV2020", how="left", validate="many_to_one")

    # France métropolitaine (Corse comprise) : les DOM ont un code département à 3 caractères
    aav = aav[aav["DEP"].str.len() == 2].copy()

    # Catégories ordonnées : les tableaux et graphiques suivront cet ordre
    aav["position_aav"] = pd.Categorical(aav["CATEAAV2020"].map(config.POSITION_AAV),
                                         categories=["Pôle", "Couronne", "Hors attraction"],
                                         ordered=True)
    aav["taille_aav"] = pd.Categorical(aav["TAAV2017"].map(config.TAILLE_AAV),
                                       categories=list(config.TAILLE_AAV.values()),
                                       ordered=True)
    aav["region"] = aav["REG"].map(config.REGIONS)

    aav = aav.rename(columns={"CODGEO": "code_commune", "LIBGEO": "nom_commune"})
    return aav.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Revenus : Filosofi 2023 (Insee)
# ---------------------------------------------------------------------------
def preparer_filosofi():
    """Niveau de vie médian (MED_SL) et taux de pauvreté (PR_MD60) par commune.

    Le fichier est au format "long" : une ligne par territoire x indicateur.
    On garde les communes, puis on passe à une colonne par indicateur (pivot).
    Les valeurs sous secret statistique sont vides -> elles restent manquantes.
    """
    colonnes_sortie = ["code_commune", "niveau_vie_median", "taux_pauvrete"]
    chemin = chemin_brut("filosofi")
    if not chemin.exists():
        print(f"ATTENTION : fichier Filosofi introuvable ({chemin.name}). "
              "Les variables de revenu seront manquantes.")
        return pd.DataFrame(columns=colonnes_sortie)

    filo = pd.read_csv(chemin, sep=";", dtype={"GEO": str})
    filo = filo[filo["GEO_OBJECT"] == "COM"]

    # Si le fichier a des ventilations (âge, sexe, logement), on garde le total "_T"
    for col in ["AGE_GP", "SEX", "TSH"]:
        if col in filo.columns:
            filo = filo[filo[col] == "_T"]

    filo = filo[filo["FILOSOFI_MEASURE"].isin(["MED_SL", "PR_MD60"])].copy()
    filo["OBS_VALUE"] = pd.to_numeric(filo["OBS_VALUE"], errors="coerce")

    if filo.empty:
        print("ATTENTION : le fichier Filosofi ne contient aucune ligne communale "
              "(GEO_OBJECT = 'COM'). Vérifier que c'est bien le fichier des communes.")
        return pd.DataFrame(columns=colonnes_sortie)

    # Contrôle avant le pivot : une seule valeur par commune et indicateur
    nb_doublons = filo.duplicated(["GEO", "FILOSOFI_MEASURE"]).sum()
    assert nb_doublons == 0, f"{nb_doublons} doublons commune x indicateur dans Filosofi"

    table = filo.pivot(index="GEO", columns="FILOSOFI_MEASURE", values="OBS_VALUE")
    table = table.reset_index().rename(columns={
        "GEO": "code_commune",
        "MED_SL": "niveau_vie_median",
        "PR_MD60": "taux_pauvrete",
    })
    table.columns.name = None
    return table[colonnes_sortie]


# ---------------------------------------------------------------------------
# 4. Points de recharge publics (IRVE)
# ---------------------------------------------------------------------------
def lire_contours():
    """Contours des communes avec une colonne `code_commune`, ou None si le
    fichier est absent ou si la colonne du code n'a pas le nom attendu."""
    chemin = chemin_brut("contours")
    if not chemin.exists():
        print(f"Contours communaux absents ({chemin.name}).")
        return None
    import geopandas as gpd   # importé ici : geopandas ne sert que si les contours existent

    communes = gpd.read_file(chemin)
    if config.CONTOURS_COL_CODE not in communes.columns:
        print(f"ATTENTION : colonne '{config.CONTOURS_COL_CODE}' absente des contours. "
              f"Colonnes : {list(communes.columns)} -> modifier CONTOURS_COL_CODE dans config.py")
        return None
    communes = communes.rename(columns={config.CONTOURS_COL_CODE: "code_commune"})
    return communes[["code_commune", "geometry"]]


def rattacher_par_coordonnees(points, communes):
    """Trouve la commune de chaque point grâce à ses coordonnées
    (jointure spatiale "point dans polygone" avec les contours communaux)."""
    import geopandas as gpd

    # Dans l'IRVE, les coordonnées sont en degrés (WGS84, code EPSG:4326)
    geo = gpd.GeoDataFrame(
        index=points.index,
        geometry=gpd.points_from_xy(points["consolidated_longitude"].astype(float),
                                    points["consolidated_latitude"].astype(float)),
        crs="EPSG:4326",
    )
    geo = geo.to_crs(communes.crs)          # même projection que les contours

    jointure = gpd.sjoin(geo, communes, how="left", predicate="within")
    jointure = jointure[~jointure.index.duplicated()]   # un point sur une frontière : 1 seule commune
    return jointure["code_commune"].reindex(points.index)


def preparer_irve(codes_reference):
    """Nombre de points de charge publics distincts par commune.

    Étapes :
    1. supprimer les doublons résiduels d'identifiant de point de charge ;
    2. rattacher chaque point à une commune avec son code Insee ;
    3. si les contours communaux sont disponibles, rattacher les points
       sans code valide grâce à leurs coordonnées ;
    4. compter les points (une ligne = un point de charge, on ne somme
       PAS nbre_pdc qui répète la capacité de la station sur chaque ligne).

    Renvoie (table par commune, table des points avec la méthode de rattachement).
    """
    colonnes = ["id_pdc_itinerance", "code_insee_commune", "puissance_nominale",
                "consolidated_longitude", "consolidated_latitude"]
    irve = pd.read_csv(chemin_brut("irve"), usecols=colonnes, dtype=str)
    print(f"Lignes dans le fichier IRVE : {len(irve):,}")

    # 1. Doublons : "Non concerné" n'est pas un identifiant, on ne dédoublonne pas ces lignes
    a_un_identifiant = irve["id_pdc_itinerance"] != "Non concerné"
    doublon = a_un_identifiant & irve.duplicated("id_pdc_itinerance")
    irve = irve[~doublon].copy()
    print(f"Doublons d'identifiant supprimés : {doublon.sum():,}")

    # 2. Rattachement par le code Insee
    irve["code_commune"] = regrouper_arrondissements(irve["code_insee_commune"])
    irve["rattachement"] = np.where(irve["code_commune"].isin(codes_reference),
                                    "code Insee", "non apparié")

    # 3. Rattachement par les coordonnées (si les contours sont disponibles)
    communes = lire_contours()
    if communes is not None:
        a_rattacher = irve["rattachement"] == "non apparié"
        irve.loc[a_rattacher, "code_commune"] = rattacher_par_coordonnees(irve[a_rattacher], communes)
        trouve = a_rattacher & irve["code_commune"].isin(codes_reference)
        irve.loc[trouve, "rattachement"] = "coordonnées"
    else:
        print("Pas de rattachement des bornes par coordonnées.")

    # 4. Comptage par commune
    irve["puissance_kw"] = pd.to_numeric(irve["puissance_nominale"], errors="coerce")
    # au-delà de 1 000 kW la valeur est sans doute saisie en W : on ne la classe pas "rapide"
    irve["rapide"] = irve["puissance_kw"].between(config.SEUIL_RAPIDE_KW, 1000)

    apparies = irve[irve["rattachement"] != "non apparié"]
    table = apparies.groupby("code_commune").agg(
        nb_points=("id_pdc_itinerance", "size"),
        nb_points_rapides=("rapide", "sum"),
    ).reset_index()
    return table, irve


# ---------------------------------------------------------------------------
# 5. Équipements de transport : BPE 2025 (Insee)
# ---------------------------------------------------------------------------
def preparer_bpe():
    """Nombre de gares et d'équipements de transport par commune.

    Format du fichier (comme Filosofi) : une ligne par territoire x type d'équipement,
    le nombre d'équipements est dans OBS_VALUE. On garde les communes (GEO_OBJECT = "COM")
    et les types d'équipements de transport listés dans config.TYPES_TRANSPORT.
    """
    colonnes_sortie = ["code_commune", "nb_gares", "nb_equip_transport"]
    chemin = chemin_brut("bpe")
    if not chemin.exists():
        print(f"ATTENTION : fichier BPE introuvable ({chemin.name}). "
              "Les variables de transport seront manquantes.")
        return pd.DataFrame(columns=colonnes_sortie)

    bpe = pd.read_csv(chemin, sep=";", dtype={"GEO": str, "FACILITY_TYPE": str})
    bpe = garder_communes(bpe)
    bpe = bpe[bpe["FACILITY_TYPE"].isin(config.TYPES_TRANSPORT)].copy()
    verifier_une_seule_annee(bpe, "BPE")
    bpe["OBS_VALUE"] = pd.to_numeric(bpe["OBS_VALUE"], errors="coerce")
    print("Équipements de transport par type (France entière) :")
    print(bpe.groupby("FACILITY_TYPE")["OBS_VALUE"].sum())

    est_gare = bpe["FACILITY_TYPE"].isin(config.TYPES_GARES)
    table = pd.DataFrame({
        "nb_gares": bpe[est_gare].groupby("GEO")["OBS_VALUE"].sum(),
        "nb_equip_transport": bpe.groupby("GEO")["OBS_VALUE"].sum(),
    }).fillna(0)
    return table.rename_axis("code_commune").reset_index()


# ---------------------------------------------------------------------------
# 6. Population communale (Insee)
# ---------------------------------------------------------------------------
def preparer_population():
    """Population municipale par commune (populations de référence 2023).

    Format Insee "long" : GEO, GEO_OBJECT, POPREF_MEASURE, TIME_PERIOD, OBS_VALUE.
    On garde les communes et la population municipale (POPREF_MEASURE = "PMUN").
    Si le format ne correspond pas, la fonction affiche les colonnes du fichier
    et renvoie une table vide (le notebook continue sans la population).
    """
    colonnes_sortie = ["code_commune", "population"]
    chemin = chemin_brut("population")
    if not chemin.exists():
        print(f"ATTENTION : fichier de population introuvable ({chemin.name}). "
              "Les indicateurs pour 1 000 habitants seront manquants.")
        return pd.DataFrame(columns=colonnes_sortie)

    pop = pd.read_csv(chemin, sep=";", dtype={"GEO": str})
    if not {"GEO", "GEO_OBJECT", "OBS_VALUE"}.issubset(pop.columns):
        print("ATTENTION : format du fichier de population non reconnu. Colonnes :", list(pop.columns))
        return pd.DataFrame(columns=colonnes_sortie)

    pop = garder_communes(pop)
    # Si le fichier est ventilé (sexe, âge...), on garde le total "_T" de chaque ventilation
    for col in pop.columns:
        if col not in ["GEO", "GEO_OBJECT"] and "_T" in set(pop[col].astype(str)):
            pop = pop[pop[col].astype(str) == "_T"]
    colonnes_mesure = [c for c in pop.columns if c.endswith("_MEASURE")]
    for col in colonnes_mesure:
        if "PMUN" in set(pop[col]):
            pop = pop[pop[col] == "PMUN"]
    verifier_une_seule_annee(pop, "Population")

    pop["population"] = pd.to_numeric(pop["OBS_VALUE"], errors="coerce")
    # somme par commune (utile seulement pour les arrondissements de Paris, Lyon, Marseille)
    table = pop.groupby("GEO")["population"].sum().rename_axis("code_commune").reset_index()
    return table[colonnes_sortie]


# ---------------------------------------------------------------------------
# 7. Contours des départements (carte interactive)
# ---------------------------------------------------------------------------
def lire_departements():
    """Contours des départements au format GeoJSON (dictionnaire Python).
    Le fichier est téléchargé dans data/raw/ s'il n'y est pas encore."""
    chemin = config.DOSSIER_BRUT / config.FICHIER_DEPARTEMENTS
    if not chemin.exists():
        print(f"Téléchargement des contours des départements : {config.URL_DEPARTEMENTS}")
        urllib.request.urlretrieve(config.URL_DEPARTEMENTS, chemin)
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)
