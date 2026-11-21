"""
Assemblage de la table communale et contrôles des jointures.

Principe : on part du référentiel des communes (AAV, géographie 2026,
France métropolitaine) et on ajoute les autres tables par des jointures
"à gauche" : le nombre de communes du référentiel ne doit jamais changer.
"""

import pandas as pd


def ajouter_table(base, table, nom_source):
    """Joint `table` à `base` par le code commune et décrit la qualité de la jointure.

    Renvoie (nouvelle base, une ligne du tableau de couverture).
    """
    # La table ajoutée doit avoir une seule ligne par commune
    assert table["code_commune"].is_unique, f"{nom_source} : codes commune en double"

    nb_lignes_avant = len(base)
    codes_hors_referentiel = ~table["code_commune"].isin(base["code_commune"])

    base = base.merge(table, on="code_commune", how="left",
                      validate="one_to_one", indicator=True)

    # La jointure à gauche ne doit ni ajouter ni supprimer de commune
    assert len(base) == nb_lignes_avant, f"{nom_source} : le nombre de communes a changé"

    ligne = {
        "source": nom_source,
        "communes du référentiel": nb_lignes_avant,
        "communes appariées": int((base["_merge"] == "both").sum()),
        "communes sans donnée": int((base["_merge"] == "left_only").sum()),
        "codes de la source hors référentiel": int(codes_hors_referentiel.sum()),
    }
    return base.drop(columns="_merge"), ligne


def construire_base(referentiel, tables):
    """Ajoute successivement chaque table au référentiel.

    `tables` est un dictionnaire {nom de la source: table}.
    Renvoie (base communale, tableau de couverture).
    """
    base = referentiel.copy()
    lignes = []
    for nom_source, table in tables.items():
        base, ligne = ajouter_table(base, table, nom_source)
        lignes.append(ligne)
    couverture = pd.DataFrame(lignes).set_index("source")
    return base, couverture


def codes_hors_referentiel(table, referentiel, colonne_effectif):
    """Liste les codes d'une source absents du référentiel, avec leur effectif.
    Utile pour vérifier qu'il s'agit bien de codes fictifs (ex. 59000) ou des DOM."""
    hors = table[~table["code_commune"].isin(referentiel["code_commune"])]
    return hors[["code_commune", colonne_effectif]].sort_values(colonne_effectif, ascending=False)


def verifier_cas_connus(base, codes, colonnes):
    """Affiche quelques communes connues pour vérifier les jointures à la main
    (code avec zéro initial, commune corse, commune hors attraction...)."""
    return base.loc[base["code_commune"].isin(codes), ["code_commune", "nom_commune"] + colonnes]
