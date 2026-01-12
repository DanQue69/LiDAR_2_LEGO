"""
=== Création d'un modèle voxelisé 'couche par couche' d’un nuage de points LiDAR ===

Ce script permet de :
- Visualiser, grâce à la librairie LDRAW, les couches successives voxelisées en brique de LEGO 1x1x1.
- Assigner une couleur de briques LDRAW selon la classification LIDAR du voxel associé.

Informations complémentaires :
- Ce script constitue une étape intéressante pour la chaîne de traitements des données LiDAR.
- Les modèles générés peuvent être visualisés dans LDView en y important le fichier .ldr.

"""


# === Importations ===
import sys
import os
import numpy as np
from pathlib import Path

# --- Configuration des chemins ---
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

sys.path.append(str(SRC_DIR))

# --- Imports des modules du projet ---
from donnees_echantillonnees_LIDAR import LIDAR_carre_aleatoire, LIDAR_rectangle
from import_LIDAR import laz_to_las
from LIDAR_numpy import LIDAR_numpy_utile
from LIDAR_couches import LIDAR_couches, LIDAR_couches_LEGO, LIDAR_couches_LEGO_LDRAW



# === Fonctions principales ===

def voxel_LDRAW(counts, nom_fichier="modele_LEGO.ldr"): 
    """
    Crée un fichier LDraw à partir d'un modèle voxelisé simple.

    Chaque voxel plein devient une brique LEGO dans le fichier .ldr.
    La couleur par défaut est fixée (16 : gris).

    Paramètres
    ----------
    counts : np.ndarray
        Tableau 3D indiquant le nombre de points dans chaque voxel.
    densite_min : int
        Nombre minimum de points pour qu’un voxel soit considéré “plein”.
    nom_fichier : str, optional
        Nom du fichier LDraw à générer (par défaut "modele_LEGO.ldr").

    Retour
    ------
    int
        Nombre total de briques générées.
    """

    # === Récupération des voxels pleins et des indices ===
    voxel_plein = np.argwhere(counts > 0)
    iy, ix, iz = voxel_plein[:,0], voxel_plein[:,1], voxel_plein[:,2] 
    
    # === Conversion en coordonnées LDraw ===
    x = ix * 20 
    y = iy * 20 
    z = -iz * 24 
    
    # === Génération des lignes pour les briques ===
    lignes = [
        f"1 16 {xi} {zi} {yi} 1 0 0 0 1 0 0 0 1 3005.dat\n"
        for xi, yi, zi in zip(x, y, z)
    ]
    
    # === Génération du fichier ===
    header = ["0 Generated from LiDAR voxel model\n", "0 Author: Python Script\n"] 
    with open(nom_fichier, "w") as f: 
        f.writelines(header) 
        f.writelines(lignes) 
        
    print(f"{nom_fichier} (Total: {len(voxel_plein)} briques) ") 
    return lignes



def voxel_LDRAW_classif(counts, class_maj, nom_fichier="modele_LEGO_classif.ldr"):
    """
    Crée un fichier LDraw à partir d'un modèle voxelisé avec classification.

    Chaque voxel plein devient une brique LEGO dans le fichier .ldr.
    La couleur de la brique est assignée selon la classification majoritaire du voxel.
    Si la classification n'est pas définie dans le dictionnaire de couleurs, une couleur par défaut est utilisée.

    Paramètres
    ----------
    counts : np.ndarray
        Tableau 3D indiquant le nombre de points dans chaque voxel.
    class_maj : np.ndarray
        Tableau 3D de mêmes dimensions que counts indiquant la classification majoritaire de chaque voxel.
    densite_min : int
        Nombre minimum de points pour qu’un voxel soit considéré “plein”.
    nom_fichier : str, optional
        Nom du fichier LDraw à générer (par défaut "modele_LEGO_classif.ldr").

    Retour
    ------
    int
        Nombre total de briques générées.
    """

    # === Récupération des voxels pleins et des classifications ===
    voxel_plein = np.argwhere(counts > 0)
    iy, ix, iz = voxel_plein[:,0], voxel_plein[:,1], voxel_plein[:,2]
    voxel_class = class_maj[iy, ix, iz]

    # === Conversion en coordonnées LDraw ===
    x = ix * 20
    y = iy * 20
    z = -iz * 24  

    # # === Dictionnaire classification LIDAR en couleur LDraw hexadécimal ===
    # # Décommenter si besoin de correspondance visuelle stricte.
    # ldraw_couleurs = {
    #     1: 0x2000000,   # Non classé => noir
    #     2: 0x28B4513,   # Sol => marron
    #     3: 0x290EE90,   # Végétation basse  => vert clair
    #     4: 0x2008000,   # Végétation moyenne => vert
    #     5: 0x200561B,   # Végétation haute => vert foncé
    #     6: 0x2555555,   # Bâtiment => gris
    #     9: 0x20000FF,   # Eau => bleu
    #     17:0x2FF0000,   # Tablier de pont => rouge 
    #     64:0x2FFA500,   # Sursol => orange
    #     66:0x2FFFFFF,   # Points virtuels => blanc
    #     67:0x2FFFF00,   # Divers bâtis => jaune
    # }

    # === Dictionnaire classification LIDAR en couleur LDraw classique ===
    ldraw_couleurs = {
        1: 0,   # Non classé → Noir
        2: 6,   # Sol → Brun
        3: 10,  # Végétation basse → Vert vif
        4: 2,   # Végétation moyenne → Vert
        5: 288, # Végétation haute → Vert sapin 
        6: 7,   # Bâtiment → Gris clair 
        9: 1,   # Eau → Bleu
        17: 4,  # Pont → Rouge
        64: 14, # Sursol → Jaune
        66: 15, # Virtuels → Blanc
        67: 8,  # Divers bâtis → Gris foncé 
    }

    couleurs = np.array([ldraw_couleurs.get(c, 24) for c in voxel_class], dtype=int)

    # === Génération du header ===
    header = [
        "0 Generated from LiDAR voxel model\n",
        "0 Author: Python Script\n",
    ]

    # === Génération des lignes pour les briques ===
    lignes = [
        f"1 {c} {xi} {zi} {yi} 1 0 0 0 1 0 0 0 1 3005.dat\n"
        for c, xi, yi, zi in zip(couleurs, x, y, z)
    ]

    # === Génération du fichier ===
    with open(nom_fichier, "w") as f:
        f.writelines(header)
        f.writelines(lignes)

    print(f"{nom_fichier} (Total: {len(voxel_plein)} briques)")
    return lignes





# === Lancement du script ===

if __name__ == "__main__":

    # === IMPORT DU FICHIER LIDAR_traitement ===
    from LIDAR_traitement import (
        voxel_graphe,
        corriger_voxels_non_classes_iteratif,
        graphe_filtre_classes,
        ajouter_sol_coque_pillier,
        remplir_trous_verticaux,
        graphe_voxel
    )

    # === FICHIER D'ENTRÉE ===
    nom_fichier = "sample.laz"   # Remplacer par le nom du fichier .laz souhaité
    file_path = DATA_DIR / nom_fichier
    output_path_test = OUTPUT_DIR / "LIDAR_LDRAW"


    # Vérification de sécurité
    if not file_path.exists():
        print(f"ERREUR : Le fichier {nom_fichier} est introuvable dans {DATA_DIR}")
        print("Veuillez placer un fichier .laz dans le dossier 'data'.")
        sys.exit(1) 

    print(f"Traitement du fichier : {nom_fichier}\n")
    
    # === IMPORT DES DONNEES ===

    # === Import des données complètes de la dalle LIDAR ===
    # las = laz_to_las(file_path)
    # LIDAR_numpy = LIDAR_numpy_utile(las)
    # counts, class_maj = LIDAR_couches_LEGO_LDRAW(LIDAR_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1)

    # === Import des données échantillonnées de la dalle LIDAR ===
    # === Version échantillon aléatoire ===
    # test_LIDAR_numpy = LIDAR_carre_aleatoire(file_path, nb_points=10000000, taille_zone=64)
    # counts, class_maj = LIDAR_couches_LEGO_LDRAW(test_LIDAR_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1)
    # === Version échantillon rectangle ===
    test_LIDAR_numpy = LIDAR_rectangle(file_path, nb_points=10000000, x_min_coin=669680.0, y_min_coin=6860143.0, longueur_x=150, longueur_y=100)
    counts, class_maj = LIDAR_couches_LEGO_LDRAW(test_LIDAR_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1)
    
    
    # === LANCEMENT DES SCRIPTS ===
    
    # === Pour les données complètes, ===
    # === Version sans classification ===
    # voxel_LDRAW(counts, nom_fichier=output_path_test / "modele_ZoneEntiere_LDRAW.ldr")
    # === Version avec classification ===
    # voxel_LDRAW_classif(counts, class_maj, nom_fichier=output_path_test / "modele_ZoneEntiere_classif.ldr")

    # === Pour les données echantilonnées, ===
    # === Version sans classification ===
    # voxel_LDRAW(counts, nom_fichier=output_path_test / "modele_echantillon_LDRAW.ldr")
    # === Version avec classification ===
    voxel_LDRAW_classif(counts, class_maj, nom_fichier=output_path_test / "modele_echantillon_classif.ldr")