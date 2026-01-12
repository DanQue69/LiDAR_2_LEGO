"""
=== Création d'un modèle voxelisé 'couche par couche' d’un nuage de points LiDAR ===

Ce script permet de :
- Transformer un tableau Numpy d'un nuage de points LiDAR en un modèle voxelisé, défini par une taille horizontale (m) et une épaisseur verticale (m).
- Générer une série d’images GeoTIFF, enregistrées dans un dossier "LIDAR_couches", correspondant à des couches horizontales successives où les voxels sont représentés selon leur spécificité (noir = plein, blanc = vide, marron = sol).
- Créer une version "LEGO" ou "LDRAW" qui permet d’ajuster la proportion entre hauteur et largeur des voxels (5/3 ou 1.2).
- Assigner une couleur aux voxels selon leur classification ou comme valeur par défaut.

Informations complémentaires :
- Ce script constitue une étape essentielle pour la chaine de traitements des données LiDAR.
- Le modèle peut être utilisé dans QGIS afin de visualiser la structure des couches en sortie.
- Certaines fonctions ne sauvegardent pas le GeoTIFF pour alléger le workflow.

"""

# === Importations ===

import sys
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
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




# === Fonctions principales ===

def LIDAR_couches(lidar_numpy, taille_xy=1.0, hauteur_couche=1.0, densite_min=1):
    """
    Crée un modèle voxelisé 'couche par couche' à partir d'un tableau Numpy d'un nuage de points LiDAR.

    Paramètres
    ----------
    lidar_numpy : np.ndarray
        Tableau numpy structuré contenant au moins x, y, z.
    taille_xy : float
        Taille horizontale d’un voxel, résolution (en mètres).
    hauteur_couche : float
        Épaisseur verticale d’un layer (en mètres).
    densite_min : int
        Nombre minimum de points pour qu’un voxel soit considéré “plein”.

    Retour
    ------
    counts : np.ndarray
        Nombre de points par voxel (densité)
    class_maj : np.ndarray
        Classification majoritaire de chaque voxel
    """

    # === Étendue de la zone ===
    x, y, z = lidar_numpy["x"], lidar_numpy["y"], lidar_numpy["z"]
    classification = lidar_numpy["classification"]
    
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    z_min, z_max = z.min(), z.max()

    nx = int(np.ceil((x_max - x_min) / taille_xy))
    ny = int(np.ceil((y_max - y_min) / taille_xy))
    nz = int(np.ceil((z_max - z_min) / hauteur_couche))

    print(f"Dimensions voxel grille : {nx} x {ny} x {nz} (XY:{taille_xy}m, Z:{hauteur_couche:.2f}m)")

    # === Indexation vectorisée ===
    ix = np.floor((x - x_min) / taille_xy).astype(int)
    iy = np.floor((y - y_min) / taille_xy).astype(int)
    iz = np.floor((z - z_min) / hauteur_couche).astype(int)

    valid = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
    ix, iy, iz, classification = ix[valid], iy[valid], iz[valid], classification[valid]

    # === Comptage des voxels ===
    counts, _ = np.histogramdd(sample=np.vstack([iy, ix, iz]).T, bins=(ny, nx, nz)) # utilisation de la vectorisation au lieu d'une boucle for qui serait trop gourmande
    counts = counts.astype(int)

    # === Classe majoritaire vectorisée ===
    classes_uniques, class_indices = np.unique(classification, return_inverse=True)
    nbr_classes = len(classes_uniques)
    voxel_index = np.ravel_multi_index((iy, ix, iz), dims=(ny, nx, nz))

    class_counts = np.zeros((ny*nx*nz, nbr_classes), dtype=np.int32)
    for c in range(nbr_classes):
        mask = class_indices == c
        np.add.at(class_counts[:, c], voxel_index[mask], 1)

    class_counts = class_counts.reshape(ny, nx, nz, nbr_classes)

    # === Trouver l'indice correspondant à la classe 1 (Non classé) => Règle : ignorer "Non classé" (1) s'il y a une autre classe présente ===
    idx_non_classe = np.where(classes_uniques == 1)[0]
    if len(idx_non_classe) > 0:
        idx_non_classe = idx_non_classe[0]
        # Masque : voxels contenant au moins une autre classe
        mask_autre = (np.sum(class_counts > 0, axis=-1) > 1) & (class_counts[..., idx_non_classe] > 0)
        # On met à zéro la classe 1 dans ces voxels
        class_counts[mask_autre, idx_non_classe] = 0

    # === Classe majoritaire finale ===
    idx_max = np.argmax(class_counts, axis=-1)
    class_maj = classes_uniques[idx_max]

    # === Application du seuil de densité ===
    mask_trop_faible = counts < densite_min
    counts[mask_trop_faible] = 0
    class_maj[mask_trop_faible] = 0

    return counts, class_maj

def LIDAR_couches_export(lidar_numpy, taille_xy=1.0, hauteur_couche=1.0, densite_min=1, prefixe_sauvegarde="layer"):
    """
    Crée un modèle voxelisé 'couche par couche' à partir d'un tableau Numpy d'un nuage de points LiDAR.

    Chaque layer est exporté en GeoTIFF :
        - Noir = voxel plein
        - Blanc = voxel vide
        - Marron = couche de base (sol sous z_min)

    Paramètres
    ----------
    lidar_numpy : np.ndarray
        Tableau numpy structuré contenant au moins x, y, z.
    taille_xy : float
        Taille horizontale d’un voxel, résolution (en mètres).
    hauteur_couche : float
        Épaisseur verticale d’un layer (en mètres).
    densite_min : int
        Nombre minimum de points pour qu’un voxel soit considéré “plein”.
    prefixe_sauvegarde : str
        Préfixe des fichiers TIFF générés.

    Retour
    ------
    counts : np.ndarray
        Nombre de points par voxel (densité)
    class_maj : np.ndarray
        Classification majoritaire de chaque voxel
    """

    # === Étendue de la zone ===
    x, y, z = lidar_numpy["x"], lidar_numpy["y"], lidar_numpy["z"]
    classification = lidar_numpy["classification"]
    
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    z_min, z_max = z.min(), z.max()

    nx = int(np.ceil((x_max - x_min) / taille_xy))
    ny = int(np.ceil((y_max - y_min) / taille_xy))
    nz = int(np.ceil((z_max - z_min) / hauteur_couche))

    print(f"Dimensions voxel grille : {nx} x {ny} x {nz} (XY:{taille_xy}m, Z:{hauteur_couche:.2f}m)")

    # === Indexation vectorisée ===
    ix = np.floor((x - x_min) / taille_xy).astype(int)
    iy = np.floor((y - y_min) / taille_xy).astype(int)
    iz = np.floor((z - z_min) / hauteur_couche).astype(int)

    valid = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
    ix, iy, iz, classification = ix[valid], iy[valid], iz[valid], classification[valid]

    # === Comptage des voxels ===
    counts, _ = np.histogramdd(sample=np.vstack([iy, ix, iz]).T, bins=(ny, nx, nz)) # utilisation de la vectorisation au lieu d'une boucle for qui serait trop gourmande
    counts = counts.astype(int)

    # === Classe majoritaire vectorisée ===
    classes_uniques, class_indices = np.unique(classification, return_inverse=True)
    nbr_classes = len(classes_uniques)
    voxel_index = np.ravel_multi_index((iy, ix, iz), dims=(ny, nx, nz))

    class_counts = np.zeros((ny*nx*nz, nbr_classes), dtype=np.int32)
    for c in range(nbr_classes):
        mask = class_indices == c
        np.add.at(class_counts[:, c], voxel_index[mask], 1)

    class_counts = class_counts.reshape(ny, nx, nz, nbr_classes)

    # === Trouver l'indice correspondant à la classe 1 (Non classé) => Règle : ignorer "Non classé" (1) s'il y a une autre classe présente ===
    idx_non_classe = np.where(classes_uniques == 1)[0]
    if len(idx_non_classe) > 0:
        idx_non_classe = idx_non_classe[0]
        # Masque : voxels contenant au moins une autre classe
        mask_autre = (np.sum(class_counts > 0, axis=-1) > 1) & (class_counts[..., idx_non_classe] > 0)
        # On met à zéro la classe 1 dans ces voxels
        class_counts[mask_autre, idx_non_classe] = 0

    # === Classe majoritaire finale ===
    idx_max = np.argmax(class_counts, axis=-1)
    class_maj = classes_uniques[idx_max]

    # === Application du seuil de densité ===
    mask_trop_faible = counts < densite_min
    counts[mask_trop_faible] = 0
    class_maj[mask_trop_faible] = 0

    # === Création du dossier de sortie ===
    dossier_sortie = OUTPUT_DIR / "LIDAR_couches"
    os.makedirs(dossier_sortie, exist_ok=True)

    transform = from_origin(x_min, y_max, taille_xy, taille_xy) # crée la transform géoréférencée (affecte coordonnées réelles aux pixels).

    # === Boucle d'export ===
    for k in range(nz + 1):  # k = 0 → socle marron
        if k == 0:
            # Couche socle marron
            rgb = np.ones((ny, nx, 3), dtype=np.uint8) * 255
            rgb[:] = np.array([139, 69, 19], dtype=np.uint8)  # marron
            save_path = os.path.join(dossier_sortie, f"{prefixe_sauvegarde}_ground.tif")
        else:
            # Couches voxel
            couche = counts[:, :, k - 1]
            mask_plein = couche >= densite_min

            img = np.ones_like(couche, dtype=np.uint8) * 255
            img[mask_plein] = 0
            rgb = np.stack([img]*3, axis=-1)

            save_path = os.path.join(dossier_sortie, f"{prefixe_sauvegarde}_z{z_min + (k-1)*hauteur_couche:.2f}.tif")

        with rasterio.open(
            save_path,
            'w',
            driver='GTiff',
            height=ny,
            width=nx,
            count=3,
            dtype='uint8',
            crs='EPSG:2154',
            transform=transform
        ) as dst:
            rgb = np.flipud(rgb)
            for i in range(3):
                dst.write(rgb[:, :, i], i + 1)

    print(f"{nz + 1} couches TIFF exportées (socle inclus).")
    return counts, class_maj



def LIDAR_couches_LEGO(lidar_numpy, taille_xy=1.0, lego_ratio=5/3, densite_min=1):
    """Version LEGO-scalée avec verticale = 5/3 de l'horizontale"""

    hauteur_couche = taille_xy * lego_ratio
    return LIDAR_couches(
        lidar_numpy,
        taille_xy=taille_xy,
        hauteur_couche=hauteur_couche,
        densite_min=densite_min
    )

def LIDAR_couches_LEGO_export(lidar_numpy, taille_xy=1.0, lego_ratio=5/3, densite_min=1, prefixe_sauvegarde="layer_LEGO"):
    """Version LEGO-scalée avec verticale = 5/3 de l'horizontale"""

    hauteur_couche = taille_xy * lego_ratio
    return LIDAR_couches_export(
        lidar_numpy,
        taille_xy=taille_xy,
        hauteur_couche=hauteur_couche,
        densite_min=densite_min,
        prefixe_sauvegarde=prefixe_sauvegarde
    )



def LIDAR_couches_LEGO_LDRAW(lidar_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1):
    """Version LEGO-scalée pour LDRAW avec verticale = 1.2 de l'horizontale"""

    hauteur_couche = taille_xy * lego_ratio
    return LIDAR_couches(
        lidar_numpy,
        taille_xy=taille_xy,
        hauteur_couche=hauteur_couche,
        densite_min=densite_min
    )

def LIDAR_couches_LEGO_LDRAW_export(lidar_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1, prefixe_sauvegarde="layer_LEGO"):
    """Version LEGO-scalée pour LDRAW avec verticale = 1.2 de l'horizontale"""

    hauteur_couche = taille_xy * lego_ratio
    return LIDAR_couches_export(
        lidar_numpy,
        taille_xy=taille_xy,
        hauteur_couche=hauteur_couche,
        densite_min=densite_min,
        prefixe_sauvegarde=prefixe_sauvegarde
    )


# === Lancement du script ===

if __name__ == "__main__":

    # === FICHIER D'ENTRÉE ===
    nom_fichier = "sample.laz"   # Remplacer par le nom du fichier .laz souhaité
    file_path = DATA_DIR / nom_fichier

    # Vérification de sécurité
    if not file_path.exists():
        print(f"ERREUR : Le fichier {nom_fichier} est introuvable dans {DATA_DIR}")
        print("Veuillez placer un fichier .laz dans le dossier 'data'.")
        sys.exit(1) 

    print(f"Traitement du fichier : {nom_fichier}\n")
    

    # === IMPORT DES DONNEES ===

    # === Import des données complètes de la dalle LIDAR ===
    las = laz_to_las(file_path)
    LIDAR_numpy = LIDAR_numpy_utile(las)

    # === Import des données échantillonnées de la dalle LIDAR (aléatoire ou rectangle)===
    # === Version échantillon aléatoire ===
    test_LIDAR_numpy = LIDAR_carre_aleatoire(file_path, nb_points=10000000, taille_zone=64)
    # === Version échantillon rectangle ===
    test_LIDAR_numpy = LIDAR_rectangle(file_path, nb_points=10000000, x_min_coin=669680.0, y_min_coin=6860143.0, longueur_x=150, longueur_y=100)


    # === LANCEMENT DES SCRIPTS ===
    
    # === Pour les données complètes, ===
    # === Version classique ===
    LIDAR_couches_export(LIDAR_numpy, taille_xy=1.0, hauteur_couche=1.0, densite_min=1, prefixe_sauvegarde="layer")
    # === Version LEGO ===
    LIDAR_couches_LEGO_export(LIDAR_numpy, taille_xy=1.0, lego_ratio=5/3, densite_min=1, prefixe_sauvegarde="layer_LEGO")
    # === Version LEGO LDRAW ===
    LIDAR_couches_LEGO_LDRAW_export(LIDAR_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1, prefixe_sauvegarde="layer_LDRAW")

    # === Pour les données echantilonnées, ===
    # === Version classique ===
    LIDAR_couches_export(test_LIDAR_numpy, taille_xy=1.0, hauteur_couche=1.0, densite_min=1, prefixe_sauvegarde="layer")
    # === Version LEGO ===
    LIDAR_couches_LEGO_export(test_LIDAR_numpy, taille_xy=1.0, lego_ratio=5/3, densite_min=1, prefixe_sauvegarde="layer_LEGO")
    # === Version LEGO LDRAW ===
    LIDAR_couches_LEGO_LDRAW_export(test_LIDAR_numpy, taille_xy=1.0, lego_ratio=1.2, densite_min=1, prefixe_sauvegarde="layer_LDRAW")
