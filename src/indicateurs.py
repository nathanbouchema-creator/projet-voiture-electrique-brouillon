"""
Construction des indicateurs et tableaux de résultats.

Rappel important (cahier des charges) : on garde toujours le numérateur et le
dénominateur, et on distingue deux résumés pour un groupe de communes :
- la MÉDIANE des parts communales (la commune "du milieu") ;
- la PART AGRÉGÉE : somme des voitures électriques / somme de toutes les voitures.
"""

import pandas as pd

from src import config


def part(numerateur, denominateur):
    """Part en % ; reste manquante si le dénominateur vaut 0 (part indéfinie)."""
    return 100 * numerateur / denominateur.where(denominateur > 0)


def ratio(numerateur, denominateur, pour=1000):
    """Nombre pour `pour` unités du dénominateur (ex. points pour 1 000 habitants).
    Reste manquant si le dénominateur vaut 0 ou est manquant."""
    numerateur = pd.to_numeric(numerateur, errors="coerce")
    denominateur = pd.to_numeric(denominateur, errors="coerce")
    return pour * numerateur / denominateur.where(denominateur > 0)


def calculer_indicateurs(base, irve_exhaustif):
    """Ajoute les parts électriques et la densité de recharge à la base communale.

    irve_exhaustif : True si tous les points IRVE ont pu être rattachés à une commune
    (par code Insee ou coordonnées). Dans ce cas, une commune absente de l'IRVE a
    "aucun point recensé" (0). Sinon, on laisse la valeur manquante.
    """
    base = base.copy()
    for nom in ["parc", "neuf", "occasion"]:
        base[f"part_{nom}"] = part(base[f"vp_{nom}_elec"], base[f"vp_{nom}"])
        base[f"part_{nom}_men"] = part(base[f"vp_{nom}_elec_men"], base[f"vp_{nom}_men"])

    if irve_exhaustif:
        base["nb_points"] = base["nb_points"].fillna(0)
        base["nb_points_rapides"] = base["nb_points_rapides"].fillna(0)

    # Infrastructures de recharge
    base["points_pour_1000_vp"] = ratio(base["nb_points"], base["vp_parc"], 1000)
    base["points_pour_100_ve"] = ratio(base["nb_points"], base["vp_parc_elec"], 100)
    base["points_pour_1000_hab"] = ratio(base["nb_points"], base["population"], 1000)

    # Transports (BPE) : une commune absente de la BPE n'a aucun équipement recensé
    if base["nb_equip_transport"].notna().any():
        base["nb_gares"] = base["nb_gares"].fillna(0)
        base["nb_equip_transport"] = base["nb_equip_transport"].fillna(0)
        base["gare"] = (base["nb_gares"] > 0).astype(int)          # 1 = au moins une gare
    else:
        base["gare"] = pd.NA
    base["equip_transport_pour_1000_hab"] = ratio(base["nb_equip_transport"], base["population"], 1000)
    base["gares_pour_1000_hab"] = ratio(base["nb_gares"], base["population"], 1000)
    return base


def controler_base(base):
    """Contrôles de cohérence avant l'analyse. Renvoie un petit tableau :
    chaque ligne doit afficher 0 problème."""
    resultats = []
    for nom in ["parc", "neuf", "occasion"]:
        total, elec, p = f"vp_{nom}", f"vp_{nom}_elec", f"part_{nom}"
        resultats.append({
            "table": nom,
            "effectifs négatifs": int((base[[total, elec]] < 0).sum().sum()),
            "électriques > total": int((base[elec] > base[total]).sum()),
            "parts hors [0, 100]": int(((base[p] < 0) | (base[p] > 100)).sum()),
            "parts indéfinies (total = 0 ou manquant)": int(base[p].isna().sum()),
        })
    return pd.DataFrame(resultats).set_index("table")


def resume_par_groupe(base, groupe, nom="parc", menages=False):
    """Pour chaque groupe : nombre de communes, quartiles des parts communales
    et part agrégée.

    nom : "parc", "neuf" ou "occasion" ; menages=True pour le seul statut ménages.
    """
    suffixe = "_men" if menages else ""
    total = f"vp_{nom}{suffixe}"
    elec = f"vp_{nom}_elec{suffixe}"
    col_part = f"part_{nom}{suffixe}"

    # On ne garde que les communes renseignées pour les variables utilisées
    donnees = base.dropna(subset=[groupe, col_part])

    resume = donnees.groupby(groupe, observed=True).agg(
        nb_communes=(col_part, "size"),
        q1=(col_part, lambda s: s.quantile(0.25)),
        mediane=(col_part, "median"),
        q3=(col_part, lambda s: s.quantile(0.75)),
        vp_elec=(elec, "sum"),
        vp_total=(total, "sum"),
    )
    resume["part_agregee"] = 100 * resume["vp_elec"] / resume["vp_total"]
    return resume.round(2)


def ajouter_groupes_revenu(base, nb_groupes=config.NB_GROUPES_REVENU):
    """Groupes de niveau de vie médian communal (quartiles si nb_groupes = 4).

    Échantillon : communes avec un niveau de vie connu et au moins une voiture.
    Les mêmes bornes servent ensuite pour tous les sous-groupes comparés.
    Renvoie (base, bornes des groupes).
    """
    base = base.copy()
    echantillon = base["niveau_vie_median"].notna() & (base["vp_parc"] > 0)
    if echantillon.sum() == 0:
        print("Pas de niveau de vie communal : groupes de revenu non calculés.")
        base["groupe_revenu"] = pd.NA
        return base, None

    etiquettes = [f"Q{i}" for i in range(1, nb_groupes + 1)]
    etiquettes[0] += " (plus modestes)"
    etiquettes[-1] += " (plus aisées)"
    base["groupe_revenu"], bornes = pd.qcut(
        base["niveau_vie_median"].where(echantillon), nb_groupes,
        labels=etiquettes, retbins=True,
    )
    return base, bornes.round(0)


def ajouter_classes_recharge(base, colonne="points_pour_1000_hab"):
    """Groupes de densité de recharge : "Aucun point recensé" (si l'information
    est fiable), puis trois tiers de `colonne` parmi les communes qui ont au moins un point."""
    base = base.copy()
    ordre = ["Aucun point recensé", "Faible", "Moyenne", "Élevée"]
    classes = pd.Series(pd.NA, index=base.index, dtype="object")

    classes[base["nb_points"] == 0] = "Aucun point recensé"
    avec_points = (base["nb_points"] > 0) & base[colonne].notna()
    classes[avec_points] = pd.qcut(base.loc[avec_points, colonne], 3,
                                   labels=["Faible", "Moyenne", "Élevée"]).astype(str)

    base["classe_recharge"] = pd.Categorical(classes, categories=ordre, ordered=True)
    return base


def sensibilite_petits_effectifs(base, groupe, nom="neuf", seuil=config.SEUIL_PETITS_EFFECTIFS):
    """Compare les résultats avec toutes les communes et sans celles qui ont
    moins de `seuil` immatriculations. Affiche ce qui est retiré."""
    petites = base[f"vp_{nom}"] < seuil
    print(f"Communes retirées (moins de {seuil} immatriculations) : {petites.sum():,}")
    print(f"Immatriculations retirées : {base.loc[petites, f'vp_{nom}'].sum():,.0f} "
          f"sur {base[f'vp_{nom}'].sum():,.0f}")

    complet = resume_par_groupe(base, groupe, nom)[["nb_communes", "mediane", "part_agregee"]]
    filtre = resume_par_groupe(base[~petites], groupe, nom)[["nb_communes", "mediane", "part_agregee"]]
    return pd.concat({"toutes les communes": complet, f"au moins {seuil} immat.": filtre}, axis=1)


def tableau_croise(base, ligne, colonne, nom="parc"):
    """Croisement de deux groupes (ex. quartile de revenu x position AAV).
    Renvoie deux tableaux : la part agrégée de chaque case et le nombre de communes."""
    total, elec, col_part = f"vp_{nom}", f"vp_{nom}_elec", f"part_{nom}"
    donnees = base.dropna(subset=[ligne, colonne, col_part])
    groupes = donnees.groupby([ligne, colonne], observed=True)

    parts = (100 * groupes[elec].sum() / groupes[total].sum()).unstack()
    nb_communes = groupes.size().unstack()
    return parts.round(2), nb_communes


def tableau_synthese(base, groupe="region"):
    """Tableau de synthèse par groupe (région par défaut) : chaque indicateur est calculé
    sur le total du groupe (somme des numérateurs / somme des dénominateurs), ce qui permet
    de comparer des groupes de tailles différentes. Dernière ligne : France métropolitaine."""
    colonnes = ["vp_parc", "vp_parc_elec", "vp_neuf", "vp_neuf_elec", "nb_points",
                "population", "nb_gares", "nb_equip_transport", "gare"]
    donnees = base[[groupe] + colonnes].copy()
    for col in colonnes:
        donnees[col] = pd.to_numeric(donnees[col], errors="coerce")

    sommes = donnees.groupby(groupe, observed=True)[colonnes].sum(min_count=1)
    sommes.loc["France métropolitaine"] = donnees[colonnes].sum(min_count=1)
    nb_communes = donnees.groupby(groupe, observed=True).size()
    nb_communes["France métropolitaine"] = len(donnees)

    tableau = pd.DataFrame({
        "nb_communes": nb_communes,
        "part VE parc (%)": 100 * sommes["vp_parc_elec"] / sommes["vp_parc"],
        "taux VE immat. neuves (%)": 100 * sommes["vp_neuf_elec"] / sommes["vp_neuf"],
        "points de charge": sommes["nb_points"],
        "points pour 100 VE": 100 * sommes["nb_points"] / sommes["vp_parc_elec"],
        "points pour 1 000 hab.": 1000 * sommes["nb_points"] / sommes["population"],
        "communes avec gare (%)": 100 * sommes["gare"] / nb_communes,
        "gares pour 100 000 hab.": 100000 * sommes["nb_gares"] / sommes["population"],
        "équip. transport pour 1 000 hab.": 1000 * sommes["nb_equip_transport"] / sommes["population"],
    })
    # on retire les colonnes vides (source non disponible)
    return tableau.dropna(axis=1, how="all").round(2)
