# La transition vers la voiture électrique en France

Projet de data science (Python pour la data science, ENSAE). Statistiques descriptives à l'échelle des communes de France métropolitaine.

**Question de recherche.** Comment la part des voitures 100 % électriques varie-t-elle entre les communes de France métropolitaine, et comment ces écarts se répartissent-ils selon le niveau de vie, la position dans les aires d'attraction des villes et l'offre de recharge publique ?

## Organisation du dépôt

```
projet-voiture-electrique/
├── notebook.ipynb        <- rapport final (à exécuter de haut en bas)
├── src/                  <- code Python importé par le notebook
│   ├── config.py         <- chemins relatifs, noms des fichiers, modalités
│   ├── preparation.py    <- lecture et nettoyage de chaque source
│   ├── fusion.py         <- jointures et tableau de couverture
│   ├── indicateurs.py    <- parts électriques, résumés par groupe, quartiles, régions
│   └── graphiques.py     <- graphiques
├── data/
│   ├── raw/              <- fichiers bruts téléchargés (NON versionnés)
│   └── processed/        <- tables préparées par le code (NON versionnées)
├── figures/              <- graphiques exportés par le notebook
├── requirements.txt
└── README.md
```

Les données ne sont pas sur GitHub (voir `.gitignore`). Tous les chemins du code sont **relatifs au dossier du projet** (`src/config.py`) : il suffit de placer les fichiers dans `data/raw/` pour que le notebook tourne sur n'importe quel ordinateur.

## Installation

```bash
git clone <url-du-depot>
cd projet-voiture-electrique
pip install -r requirements.txt
```

## Données à télécharger dans `data/raw/`

Garder **exactement** les noms de fichiers ci-dessous (ils sont définis dans `src/config.py`).

| Source | Fichier attendu dans `data/raw/` | Où le trouver |
|---|---|---|
| SDES – parc communal de véhicules au 1er janvier | `Donnees-sur-le-parc-de-vehicules-au-niveau-communal_2026-06.csv` | [data.gouv.fr – Parc de véhicules routiers](https://www.data.gouv.fr/datasets/parc-de-vehicules-routiers) (export DiDo) |
| SDES – immatriculations de véhicules neufs | `Immatriculations-de-vehicules-achetes-neufs-au-niveau-communal_2026-02.csv` | [data.gouv.fr – Immatriculations de véhicules routiers](https://www.data.gouv.fr/datasets/immatriculations-de-vehicules-routiers) |
| SDES – immatriculations de véhicules d'occasion | `Immatriculations-de-vehicules-achetes-doccasion-au-niveau-communal_2026-02.csv` | même page |
| Insee – zonage en aires d'attraction des villes | `AAV2020_au_01-01-2026.xlsx` | [Insee – Base des aires d'attraction des villes 2020](https://www.insee.fr/fr/information/4803954) |
| Insee – Filosofi 2023 (niveau de vie des communes) | `DS_FILOSOFI_CC_2023_data.csv` | [FILOSOFI_CC_csv.zip](https://www.insee.fr/fr/statistiques/fichier/8984752/FILOSOFI_CC_csv.zip) (page [Insee 8984752](https://www.insee.fr/fr/statistiques/8984752), « Tous les niveaux géographiques », csv) |
| Insee – BPE 2025 (gares, équipements de transport) | `DS_BPE_2025_data.csv` | [DS_BPE_CSV_FR.zip](https://www.insee.fr/fr/statistiques/fichier/8217527/DS_BPE_CSV_FR.zip) (page [Insee 8217527](https://www.insee.fr/fr/statistiques/8217527)) |
| Insee – populations de référence 2023 | `DS_POPULATIONS_REFERENCE_2023_data.csv` | [fichier Insee (zip)](https://api.insee.fr/melodi/file/DS_POPULATIONS_REFERENCE/DS_POPULATIONS_REFERENCE_2023_CSV_FR) (page [data.gouv.fr – Populations de référence](https://www.data.gouv.fr/datasets/populations-de-reference)) |
| Base consolidée IRVE (points de recharge publics) | `consolidation-etalab-schema-irve-statique-v-2_3_1-20261019.csv` | [transport.data.gouv.fr – Bornes de recharge](https://transport.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques) (citer la date de l'archive utilisée) |
| Etalab – contours des communes 2026 (facultatif : carte) | `communes-50m.geojson` | [communes-50m.geojson](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2026/geojson/communes-50m.geojson) |

Les contours des départements (carte interactive, projet libre [france-geojson](https://github.com/gregoiredavid/france-geojson)) sont **téléchargés automatiquement** dans `data/raw/` à la première exécution.

Pour les fichiers Insee téléchargés en `.zip` : dézipper et garder le fichier qui finit par `_data.csv`, **sans le renommer**.

Chaque fichier manquant est signalé par un message « ATTENTION » et les indicateurs correspondants restent vides : le notebook va quand même jusqu'au bout. Sans les contours, le notebook tourne aussi : la carte n'est pas tracée et les bornes IRVE sans code commune ne sont pas rattachées (le notebook l'indique). Sans le fichier Filosofi communal, les sections sur le niveau de vie sont vides.

Si un nom de fichier change (nouveau millésime), modifier uniquement le dictionnaire `FICHIERS` dans `src/config.py`.

## Exécution

```bash
jupyter notebook notebook.ipynb
```

Exécuter toutes les cellules dans l'ordre (*Kernel → Restart & Run All*). La première cellule de code indique les fichiers présents ou manquants. Durée : moins d'une minute ; mémoire : environ 1 Go.

Ordre des traitements dans le notebook :
1. référentiel des communes (classeur AAV, géographie 2026, France métropolitaine) ;
2. parc, immatriculations neuves et d'occasion (SDES), agrégés par commune ;
3. Filosofi (niveau de vie médian, taux de pauvreté) ;
4. IRVE (points de recharge distincts par commune) ;
5. jointures à gauche sur le référentiel, tableau de couverture et contrôles ;
6. indicateurs, tableaux et graphiques.

## Principaux choix de traitement

- **Voitures particulières** : catégorie `VP` des fichiers SDES.
- **Électrique** : `Electrique` dans le parc ; `Electrique et hydrogène` dans les immatriculations (le SDES ne sépare pas l'hydrogène dans ces fichiers). Les hybrides rechargeables restent au dénominateur.
- **Total d'une commune** : somme de toutes les motorisations (les fichiers n'ont pas de ligne « Ensemble »).
- **Ménages** : statut `Particulier` (parc) et `PP`, personne physique (immatriculations).
- **Paris, Lyon, Marseille** : les arrondissements sont additionnés au code de la commune (75056, 69123, 13055).
- **Codes fictifs SDES** (`XX000`, commune inconnue) et DOM : hors référentiel, listés dans le notebook.
- **Deux résumés par groupe** : médiane des parts communales et part agrégée (somme des électriques / somme des voitures).
- **Revenus** : quartiles de niveau de vie médian communal (`NB_GROUPES_REVENU` dans `config.py`).
- **Recharge** : points de charge distincts (doublons d'identifiant supprimés), pour 1 000 habitants et pour 100 voitures électriques.
- **Transports** : présence d'une gare de voyageurs (0/1, types BPE E107, E108, E109) ; équipements de transport du domaine E de la BPE (gares, taxis-VTC, aéroports) pour 1 000 habitants. Les taxis-VTC représentent l'essentiel de ces équipements : l'indicateur gare est plus lisible.
- **Population** : populations de référence 2023 (limites communales 2025) ; quelques communes modifiées au 1er janvier 2026 peuvent manquer (voir le tableau de couverture).
- **Carte interactive** : Plotly, par département ; enregistrée aussi dans `figures/carte_departements.html` (GitHub n'affiche pas les cartes interactives dans les notebooks).
- **Régions** : indicateurs calculés sur le total de chaque région (somme des numérateurs / somme des dénominateurs).
