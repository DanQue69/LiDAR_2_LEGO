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
from LIDAR_LDRAW import voxel_LDRAW, voxel_LDRAW_classif

from merge import Brick

# === Paramètres de conversion LDraw ===
SCALE_XY = 20.0
SCALE_Z = 24.0

# === Mapping Couleurs (LIDAR -> LEGO) ===

# # === Dictionnaire classification LIDAR en couleur LDraw hexadécimal ===
# # Décommenter si besoin de correspondance visuelle stricte.
# LIDAR_TO_LEGO_COLORS_HEX = {
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
# Correspond aux couleurs standard de la palette LDraw et aux briques réelles LEGO.
LIDAR_TO_LEGO_COLORS = {
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

# si VISUALISATION = "GRIS"
DEFAULT_GRAY = 16 


def bricks_from_ldr(lignes):
    """
    Convertit des lignes LDraw en objets Brick en corrigeant l'échelle.
    Gère les coordonnées et la couleur.
    """
    bricks = []

    for line in lignes:
        parts = line.strip().split()
        
        if not parts or parts[0] != "1" or len(parts) < 5:
            continue

        try:
            color_code = int(parts[1])
            x_ldr = float(parts[2])
            z_ldr_hauteur = float(parts[3]) 
            y_ldr = float(parts[4])

            # Conversion inverse (LDraw -> Grille Voxel 1x1)
            # x_ldr = ix * 20
            ix = int(round(x_ldr / SCALE_XY))
            # y_ldr = iy * 20
            iy = int(round(y_ldr / SCALE_XY))
            # z_ldr = -iz * 24
            iz = int(round(-z_ldr_hauteur / SCALE_Z))

            b = Brick(
                layer=iz, 
                x=ix, 
                y=iy, 
                length=1, 
                width=1, 
                color=color_code, 
                orientation="H"
            )
            bricks.append(b)

        except ValueError:
            continue

    return bricks


def bricks_from_numpy(counts, class_maj=None, visualisation="COULEUR"):
    """
    Convertit les tableaux NumPy (voxels) en objets Brick.
    
    Paramètres
    ----------
    visualisation : str
        "COULEUR" => utilise la classification LIDAR mappée vers LEGO.
        "GRIS"    => utilise DEFAULT_GRAY (16).
    """
    bricks = []
    indices = np.argwhere(counts > 0)
    
    for iy, ix, iz in indices:
        
        lego_color = DEFAULT_GRAY

        # Gestion de la couleur
        if visualisation == "COULEUR" and class_maj is not None:
            c_lidar = class_maj[iy, ix, iz]
            lego_color = LIDAR_TO_LEGO_COLORS.get(c_lidar, DEFAULT_GRAY)
        
        # Création de la brique unitaire
        b = Brick(
            layer=iz,
            x=ix,
            y=iy,
            length=1,
            width=1,
            color=lego_color,
            orientation="H"
        )
        bricks.append(b)

    return bricks



if __name__ == "__main__":
    print("\n=== Lancement du test unitaire : brick_factory.py ===\n")

    # 1. PRÉPARATION DES DONNÉES (Simulation du workflow)
    # ---------------------------------------------------
    nom_fichier = "exemple.laz" 
    file_path = DATA_DIR / nom_fichier

    if not file_path.exists():
        print(f"[ATTENTION] Fichier {nom_fichier} introuvable. Test ignoré.")
        sys.exit(0)

    print(f"Chargement et voxelisation de {nom_fichier}...")
    
    # On prend un petit rectangle pour le test
    lidar_data = LIDAR_rectangle(file_path, nb_points=10000, x_min_coin=669680.0, y_min_coin=6860143.0, longueur_x=20, longueur_y=20)
    
    # Voxelisation
    counts, class_maj = LIDAR_couches_LEGO_LDRAW(lidar_data, taille_xy=1.0, lego_ratio=1.2, densite_min=1)
    
    # Exportation LDraw (simulation fichiers)
    print("Génération des instructions LDraw (simulation fichiers)...")
    ldraw_sans_class = voxel_LDRAW(counts, nom_fichier=OUTPUT_DIR/"test_factory_gris.ldr")
    ldraw_class = voxel_LDRAW_classif(counts, class_maj, nom_fichier=OUTPUT_DIR/"test_factory_color.ldr")
    
    nb_voxels = np.count_nonzero(counts)
    print(f"Données voxelisées : {nb_voxels} voxels pleins.")

    print("\n---------------------------------------------------")

    # 2. TEST : Numpy -> Briques (MODE COULEUR)
    # -----------------------------------------
    print("TEST A : Conversion NumPy -> Briques (COULEUR)")
    briques_numpy_couleur = bricks_from_numpy(counts, class_maj, visualisation="COULEUR")
    
    if len(briques_numpy_couleur) > 0:
        b = briques_numpy_couleur[0]
        print(f"   [OK] {len(briques_numpy_couleur)} briques générées.")
        
        # Validation nombre
        if len(briques_numpy_couleur) == nb_voxels:
            print("   [OK] Le nombre de briques correspond au nombre de voxels.")
        else:
            print(f"   [ERREUR] {len(briques_numpy_couleur)} briques vs {nb_voxels} voxels.")

        # Validation couleur
        b_colore = next((b for b in briques_numpy_couleur if b.color != 16), None)
        if b_colore:
            print(f"   [OK] Validation couleur : Trouvé brique couleur {b_colore.color} (Classe mappée).")
        else:
            print("   Note : Toutes les briques sont grises (peut-être normal selon l'échantillon).")
    else:
        print("   [!] Aucune brique générée.")

    print("\n---------------------------------------------------")

    # 3. TEST : Numpy -> Briques (MODE GRIS)
    # --------------------------------------
    print("TEST B : Conversion NumPy -> Briques (GRIS)")
    briques_gris = bricks_from_numpy(counts, class_maj, visualisation="GRIS")
    
    if len(briques_gris) > 0:
        # Vérification : Toutes les briques doivent être 16
        toutes_grises = all(bk.color == 16 for bk in briques_gris)
        if toutes_grises:
            print("   [OK] Validation réussie : Toutes les briques sont couleur 16 (DEFAULT_GRAY).")
        else:
            print("   [ERREUR] Certaines briques ne sont pas grises !")

    print("\n---------------------------------------------------")

    # 4. TEST : LDraw File -> Briques (Round-Trip Test)
    # -----------------------------------------------------------
    print("TEST C : Conversion Fichier LDraw -> Briques (Parsing)")
    print("   Utilisation des données générées par voxel_LDRAW_classif...")
    
    # On utilise les lignes générées à l'étape 1 (ldraw_class)
    briques_parsed = bricks_from_ldr(ldraw_class)

    print(f"   Briques parsées : {len(briques_parsed)}")

    if len(briques_parsed) == len(briques_numpy_couleur):
        print("   [OK] Nombre de briques identique entre NumPy Direct et LDraw Parsing.")
        
        # Comparaison de la première brique (Attention, l'ordre peut varier, on trie pour comparer)
        # On compare un échantillon au hasard
        idx = 0
        b_ref = briques_numpy_couleur[idx]
        # On cherche une brique correspondante dans parsed
        b_parsed_match = next((b for b in briques_parsed if b.x == b_ref.x and b.y == b_ref.y and b.layer == b_ref.layer), None)
        
        if b_parsed_match:
            print(f"   [OK] Correspondance géométrique trouvée pour la brique {b_ref}.")
            if b_parsed_match.color == b_ref.color:
                print(f"   [OK] La couleur correspond ({b_ref.color}).")
            else:
                 print(f"   [ERREUR] Couleur divergente : Ref={b_ref.color} vs Parsed={b_parsed_match.color}")
        else:
            print(f"   [ERREUR] Impossible de retrouver la brique {b_ref} dans le set parsé.")

    else:
        print(f"   [ERREUR] Différence de quantité : Direct={len(briques_couleur)} vs Parsed={len(briques_parsed)}")


    print("\n=== Fin du test ===\n")

    print(briques_numpy_couleur[:5])
    print("\n\n")
    print(briques_gris[:5])  
    print("\n\n")
    print(briques_parsed[:5])
    