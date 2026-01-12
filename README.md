# Projet LiDAR_2_LEGO 

Ce projet propose une chaîne de traitement complète ("pipeline") permettant de convertir des nuages de points LiDAR (format .laz) en modèles 3D constitués de briques LEGO (format .ldr). 

L'objectif est de créer un support de médiation tangible et open source, capable de transformer des données géospatiales complexes en maquettes physiques assemblables, tout en optimisant la structure et le nombre de briques utilisées.

Conçu dans le cadre d'un Projet d'Initiation à la Recherche (ING2 - Géodata Paris), le code est optimisé pour traiter les données LiDAR HD de l'IGN (France).





---





## Architecture du projet

```text
LiDAR_2_LEGO/
│
├── data/                      # Dossier destiné aux fichiers .laz d'entrée
│                              # Placez votre fichier .laz ici
│                              
├── docs/                      # Documentation technique, rapports et livrables
│ 
├── outputs/                   # Dossier généré automatiquement contenant les résultats (modèles bruts, traités, finales, etc...) 
│
├── src/                       # Code source Python (Modules internes) :
│   ├── affichage_LIDAR.py                 # Visualisation des métadonnées du fichier LiDAR
│   ├── import_LIDAR.py                    # Lecture .laz/.las
│   ├── LIDAR_numpy.py                     # Conversion LAS -> Numpy
│   ├── donnees_echantillonnees_LIDAR.py   # Echantillonage des données LiDAR
│   ├── LIDAR_couches.py                   # Voxelisation 
│   ├── LIDAR_traitement.py                # Traitements structurels des données
│   ├── LIDAR_LDRAW.py                     # Génération fichiers .ldr intermédiaires
│   ├── brique_merge.py                    # Conversion Voxels -> Brick
│   ├── merge.py                           # Def Brick et règles fusion
│   ├── cost_function.py                   # Fonction coût 
│   └── solver.py                          # Algorithme optimisation 
│
├── main.py                    # Point d'entrée principal (Configuration & Exécution)
├── requirements.txt           # Liste des dépendances Python à installer sur votre machine
├── .gitignore                 
└── README.md                  
```





<br>

---

<br>





## Installation et Déploiement

### Prérequis

- Git : Pour cloner le projet.
- Python 3.9 ou supérieur.

<br>

### Récupération du projet

Ouvrez un terminal et clonez le dépôt sur votre machine :
```bash
git clone <URL_DU_DEPOT_GIT>
cd <NOM_DU_DOSSIER_CLONE>
```

<br>

### Installation des dépendances

Le projet utilise des librairies scientifiques et géospatiales (laspy, lazrs, numpy, networkx, rasterio). Installez-les via pip (présent depuis Python 3.4):
```bash
pip install -r requirements
```

<br>

### Gestion des données LiDAR

Un fichier `exemple.laz` est présent dans le dossier `data/`, vous pouvez lancer directement le pipeline via `main.py`.

Si vous voulez utilisez vos propres données `.laz` :
1. Téléchargez une dalle LiDAR HD via le site [Géoservices - IGN](https://cartes.gouv.fr/telechargement/IGNF_NUAGES-DE-POINTS-LIDAR-HD).
2. Placez le fichier téléchargé ou tout autre fichier `.laz` dans le dossier `data/`.
3. Ouvrez le fichier `main.py` et modifiez la variable `NOM_FICHIER` :
```python
NOM_FICHIER = "votre_fichier.laz"
```





<br>

---

<br>





## Prise en main et Configuration

Tout le contrôle du projet s'effectue via le fichier `main.py`. Il n'est pas nécessaire de modifier le code source dans `src/`.  

Ouvrez `main.py` dans votre éditeur de code (VS Code, PyCharm...) et ajustez la section PARAMÈTRES UTILISATEUR selon vos besoins :

<br>

### Import et Échantillonnage 

Le traitement complet d'une dalle (1km x 1km) peut être long et gourmand en mémoire. Utilisez les modes d'échantillonnage pour tester vos paramètres, par défaut `"AFFICHAGE_INFO_LIDAR"`:

```python
MODE_IMPORT = "MODE_CHOISI" 
```

- `"AFFICHAGE_INFO_LIDAR"` : Affiche les métadonnées du fichier `.laz`, utile pour récupérer les bornes géographiques (Bounding Box) pour paramétrer le mode `"ECHANTILLON_RECTANGLE"`. Détail dans le fichier `affichage_LIDAR.py`.

- `"COMPLET"` : Traite l'intégralité du fichier `.laz`. Détail dans le fichier `LIDAR_numpy.py`.

- `"ECHANTILLON_CARRE_ALEATOIRE"` : Prend une zone carrée au hasard dans le fichier définie par une longueur (m). Détail dans le fichier `donnees_echantillonnees_LIDAR.py`.
  - Paramètres :
    - `NB_POINTS_ALEATOIRE` (défaut 1000000000, pour prendre tous les points) : Nombre maximum de points LiDAR à récupérer
    - `TAILLE_ZONE_ALEATOIRE` (défaut 50) : Taille des côtés de la zone carrée en mètres

- `"ECHANTILLON_RECTANGLE"` : (Recommandé) Extrait une zone rectangulaire précise définie par les coordonnées X,Y du coin Sud/Ouest (Lambert 93) du rectangle et par sa longueur (m) en X et en Y. Détail dans le fichier `donnees_echantillonnees_LIDAR.py`.
  - Paramètres (réglés par défaut sur le bâtiment de Géodata Paris sur le fichier `exemple.laz`) : 
    - `NB_POINTS_RECTANGLE` (défaut 1000000000, pour prendre tous les points) : Nombre maximum de points LiDAR à récupérer
    - `X_MIN_RECTANGLE` (défaut 669680.0) : Coordonnée X du coin bas gauche du rectangle échantillonné
    - `Y_MIN_RECTANGLE` (défaut 6860143.0) : Coordonnée Y du coin bas gauche du rectangle échantillonné
    - `LONGUEUR_X_RECTANGLE` (défaut 150) : Longueur en x dans la direction Est-Ouest en mètres
    - `LONGUEUR_Y_RECTANGLE` (défaut 100) : Longueur en y dans la direction Nord-Sud en mètres

  <br>

### Workflow

Réglage des paramètres du workflow général.

```python
MODE_WORKFLOW = "WORKFLOW_CHOISI" 
```

- `"ETAPE_PAR_ETAPE"` : Génère un fichier export `.ldr` après chaque phase majeure (Voxelisation, Traitement, Optimisation). Idéal pour le debug ou pour visualiser les étapes intermédiaires.

- `"DIRECT"` : Ne génère que le modèle final optimisé.

<br>

### Visualisation graphique

Réglage des paramètres de visualisation graphique du fichier `.ldr` en sortie.

```python
VISUALISATION = "VISUALISATION_CHOISI" 
```

- `"COULEUR"` : Utilise la classification LiDAR standard pour colorer les briques LEGO.

- `"GRIS"` : Génère une maquette monochrome type "Architecture" où toutes les briques sont grises.

Si vous choisissez le mode de visualisation colorée `VISUALISATION = "COULEUR"`, vous pouvez choisir le type de couleur des briques :

- `"STANDARD"` : Couleurs des briques proches de la palette officielle LEGO. Idéal pour commander de vraies pièces.

- `"HEX"` : Couleurs en Hexadécimal réglables à la ligne 173 du script `main.py`. Peut offrir un rendu visuel plus proche.

<br>

### Voxelisation

Réglage des paramètres de voxelisation. Détail dans le fichier `LIDAR_couches.py`

- `TAILLE_VOXEL` : Résolution au sol (ex: 1.0 = 1 mètre pour une brique 1x1x1).

- `LDRAW_RATIO` : Échelle verticale. préréglé à 1.2 qui correspond au ratio standard d'une brique LEGO/LDRAW.

- `DENSITE_MIN` : Densité minimale de points par voxel pour être pris en compte (ex: 1.0 = 1 point LiDAR dans un voxel pour qu'il soir pris en compte).

<br>

### Briques autorisées

Réglage du catalogue de pièces que le solver est autorisé à utiliser pour optimiser l'assemblage.

- `INVENTAIRE_BRIQUES` : Ensemble de tuples (largeur, longueur) définissant les dimensions de briques disponibles.
  - Briques 1.x : par défaut (1x1), (1x2), (1x3), (1x4), (1x6), (1x8)
  - Briques 2.x : par défaut (2x2), (2x3), (2x4), (2x6)
  - Inverses : Les dimensions inversées doivent être présentes, par défaut (2, 1), (3, 1), (4, 1), (6, 1), (8, 1), (3, 2), (4, 2), (6, 2)


<br>

### Algorithmes de traitements structurels

Réglage des fonctions de traitements structurels avec leurs paramètres associés. Détail dans le fichier `LIDAR_traitement.py`.

Vous pouvez activer/désactiver (`True`/`False`) chaque étape du pipeline pour affiner le résultat :

<br>

**1. Correction des Données**
- Fonction : `corriger_voxels_non_classes_iteratif`
- Rôle : Bouche les trous d'information. Si un voxel est "Non classé" (ex: bruit ou erreur capteur) mais qu'il est entouré de "Bâtiment", il prendra la classe "Bâtiment".
- Paramètres :
  - `class_non_classe` (défaut `1`) : L'identifiant de la classe à corriger/remplacer.
  - `classes_a_propager` (défaut `[6]`) : Liste des classes "fortes" qui ont le droit d'écraser la classe inconnue (ex: `6` pour Bâti).
  - `max_iter` (défaut `5`) : Nombre de fois où l'algorithme passe sur le modèle. Plus ce chiffre est haut, plus la correction se propage loin.

<br>
 
**2. Filtrage Sémantique**
- Fonction : `graphe_filtre_classes`
- Rôle : Ne garde que les voxels dont la classe est dans la liste autorisée. Supprime tout le reste.
- Paramètres :
  - `classes_gardees` : Liste des identifiants LAS à conserver.
    - Par défaut `[1, 2, 3, 4, 5, 6]`; 1=Non Classé, 2=Sol, 3=Végétation basse, 4=Végétation moyenne, 5=Végétation haute, 6=Bati

<br>

**3. Filtrage Structurel** 
- Fonction : `graphe_filtre_sol`
- Rôle : Supprime les "objets volants". L'algorithme part du sol et parcourt tout le graphe. Tout ce qui n'est pas physiquement relié au sol (bruit dans le ciel, nuages, oiseaux) est supprimé.
- Paramètres :
  - `class_sol` (défaut `2`) : L'identifiant de la classe considérée comme le "point d'ancrage" de la maquette.

<br>
   
**4. Consolidation / Fondations**
- Fonctions : `ajouter_sol_coque_pillier`, `ajouter_sol_coque`, `ajouter_sol_rempli`
- Rôle : Génère un sol artificiel pour soutenir la maquette.
```python
TYPE_CONSOLIDATION = "TYPE_CONSOLIDATION_CHOISI" 
```
- Choix entre 3 Modes :
  - `"PILIERS"` : Crée une coque fine et ajoute des piliers verticaux réguliers.
  - `"COQUE"` : Créé une coque fine vide à l'intérieur.
  - `"REMPLI"` : Créé une coque et la remplie entièrement de sol.
  - `"AUCUN"` : Pas de consolidation de sol.
- Paramètres :
  - `class_sol` (défaut `2`) : La classe qui sera attribuée aux nouvelles briques de fondation.
  - `class_bat` (défaut `6`) : Classe utilisée comme "masque". L'algorithme évite de remplir l'intérieur des zones denses identifiées par cette classe.
  - `pillar_step` (défaut `4`) : Espacement entre deux piliers (en nombre de voxels).
  - `pillar_width` (défaut `2`) : Largeur du pilier carré (ex: 2 = pilier de 2x2 briques).
  - `n_min` (défaut `2`) : Paramètre de lissage pour la propagation horizontale du sol.

<br>

**5. Remplissage des Murs** 
- Fonction : `remplir_trous_verticaux`
- Rôle : Scanne les colonnes verticales. S'il détecte un trou entre deux voxels de "Bâtiment":`6` (ex: fenêtre non captée par le LiDAR, zone d'ombre), il le comble pour créer un mur solide.
- Paramètres :
  - `classes_batiment` (défaut `[6]`) : Liste des classes considérées comme des murs verticaux.

<br>

### Coût structurel

Le pipeline intègre une fonction d'évaluation qui attribue un "score de coût" à la structure. Plus ce score est bas, plus la maquette est solide. Détail dans le fichier `cost_function.py`.

Vous pouvez activer/désactiver (`True`/`False`) cette fonctionnalité : `CALCULER_COUT_STRUCTUREL`


<br>

---

<br>





## Exécution

Une fois le déploiement sur votre machine réalisée et votre configuration terminée dans `main.py`, vous pouvez éxécutez le script via le terminal : 

```bash
python main.py
```

Les résultats seront générés dans le dossier `outputs/`.

En fonction du choix de votre mode de workflow `MODE_WORKFLOW`, différents dossiers vont se crééer :

- Si `MODE_WORKFLOW = ETAPE_PAR_ETAPE`, 3 dossiers sont créés dans `outputs/` :
  - `outputs/1_Apres_Voxelisation/` : Fichiers `.ldr` bruts réalisés après la voxelisation et avant les traitements structurels.
  - `outputs/2_Apres_Traitement_Structurel/` : Fichiers `.ldr` traités (nettoyés et consolidés) réalisés après les traitements structurelse avant les algorithmes d'optimisation et de merging.
  - `outputs/3_Resultat_Final/` : Fichiers `.ldr` optimisés avec briques mergées, réalisés après les algorithmes d'optimisation et de merging.
 
- Si `MODE_WORKFLOW = DIRECT`, un seul dossier est créé dans `outputs/` :
  - `outputs/Resultat_Final/` : Uniquement les fichiers `.ldr` optimisés avec briques mergées, réalisés après les algorithmes d'optimisation et de merging.

<br>

Vous pouvez visualiser ces fichiers avec :
- LDView (Visualisation rapide).
- BrickLink Studio (Rendu photoréaliste et instructions de montage).





<br>

---

<br>





## Perspectives et Évolutions

- Génération de pages de montage via LPub3D.
- Optimisation des algorithmes de traitements structurels, peuvent être trop long pour de grands fichiers `.laz`.
- Ajout d'un algorithme génétique au lieu de notre actuel algorithme Greedy, `CALCULER_COUT_STRUCTUREL` sera alors intéressant à observer.




<br>

---

<br>





## Crédits et Licence

- Auteurs : Romain DE BLOTEAU VALCHUK et Dan Quê NGUYEN - Géodata Paris (ex-ENSG École Nationale des Sciences Géographiques) 
- Commanditaires : Corentin LE BIHAN GAUTIER et Théo SZANTO - Laboratoire LASTIG
- Données : LiDAR HD (IGN) via la plateforme Géoservices, Licence Ouverte MIT.












