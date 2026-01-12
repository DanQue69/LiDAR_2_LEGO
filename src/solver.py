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

from merge import Brick, merge_bricks, merge_bricks_side, VALID_SIZES
from collections import defaultdict, Counter
from cost_function import total_cost_function



# =============================================================================
# CATALOGUE DE PIÈCES LDRAW
# Mapping (Largeur, Longueur) -> Fichier .dat
# =============================================================================
LEGO_PARTS = {
    # --- Briques 1.x ---
    (1, 1): "3005.dat",  # Brick 1 x 1
    (1, 2): "3004.dat",  # Brick 1 x 2
    (1, 3): "3622.dat",  # Brick 1 x 3
    (1, 4): "3010.dat",  # Brick 1 x 4
    (1, 6): "3009.dat",  # Brick 1 x 6
    (1, 8): "3008.dat",  # Brick 1 x 8
    (1, 10): "6111.dat", # Brick 1 x 10
    (1, 12): "6112.dat", # Brick 1 x 12
    (1, 16): "2465.dat", # Brick 1 x 16
    
    # --- Briques 2.x ---
    (2, 2): "3003.dat",  # Brick 2 x 2
    (2, 3): "3002.dat",  # Brick 2 x 3
    (2, 4): "3001.dat",  # Brick 2 x 4
    (2, 6): "2456.dat",  # Brick 2 x 6
    (2, 8): "3007.dat",  # Brick 2 x 8
    (2, 10): "3006.dat", # Brick 2 x 10
}


def print_brick_stats(bricks):
    """
    Affiche le décompte des briques par type (Inventaire).
    """
    stats = Counter()
    
    for b in bricks:
        # Normalisation des dimensions (petit x grand) pour que 2x4 et 4x2 soient comptés ensemble
        dims = tuple(sorted((b.width, b.length)))
        stats[dims] += 1
        
    print("\n" + "="*40)
    print("      INVENTAIRE FINAL (BOM)      ")
    print("="*40)
    print(f"{'TYPE':<15} | {'REF LDRAW':<10} | {'QTÉ':<5}")
    print("-" * 36)
    
    # Tri par largeur puis longueur pour l'affichage
    sorted_keys = sorted(stats.keys())
    
    total_bricks = 0
    
    for (w, l) in sorted_keys:
        count = stats[(w, l)]
        total_bricks += count
        
        # Récupération de la référence LDraw
        ref = LEGO_PARTS.get((w, l), "CUSTOM")
        
        label = f"{w} x {l}"
        print(f"{label:<15} | {ref:<10} | {count:<5}")
        
    print("-" * 36)
    print(f"{'TOTAL':<15} | {'':<10} | {total_bricks:<5}")
    print("="*40 + "\n")


def export_to_ldr(bricks, filename):
    """Génère le fichier .ldr final avec positionnement corrigé."""
    header = ["0 Optimized LEGO Model\n", "0 Name: " + str(filename) + "\n", "0 Author: Greedy Solver\n"]
    lines = []
    
    # Paramètres LDraw
    LDR_UNIT = 20.0
    LDR_HEIGHT = 24.0

    for b in bricks:
        # Coordonnées du coin "Grid" converties en LDraw
        x_coin = b.x * LDR_UNIT
        y_coin = b.y * LDR_UNIT
        z_pos = -b.layer * LDR_HEIGHT 

        # Dimensions réelles de la brique
        dim_x = b.length * LDR_UNIT
        dim_y = b.width * LDR_UNIT
        
        # Centre géométrique
        center_x = x_coin + (dim_x / 2.0)
        center_y = y_coin + (dim_y / 2.0)

        dims_sorted = tuple(sorted((b.width, b.length)))
        part_file = LEGO_PARTS.get(dims_sorted)

        if part_file:
            # Gestion Rotation (LDraw standard aligné sur X)
            a, b_rot, c, d, e, f, g, h, i = 1, 0, 0, 0, 1, 0, 0, 0, 1
            
            if b.width > b.length:
                 # Rotation 90° autour de Y (Vertical)
                 a, b_rot, c = 0, 0, 1
                 d, e, f     = 0, 1, 0
                 g, h, i     = -1, 0, 0
            
            line = f"1 {b.color} {center_x:.2f} {z_pos:.2f} {center_y:.2f} {a} {b_rot} {c} {d} {e} {f} {g} {h} {i} {part_file}\n"
        else:
            # Fallback
            mat_a = b.length
            mat_i = b.width
            line = f"1 {b.color} {center_x:.2f} {z_pos:.2f} {center_y:.2f} {mat_a} 0 0 0 1 0 0 0 {mat_i} 3005.dat\n"

        lines.append(line)

    with open(filename, "w") as f:
        f.writelines(header)
        f.writelines(lines)
    print(f"[Export] Fichier généré : {filename} ({len(bricks)} briques)")


def get_best_partition(total_length, width_ref):
    """
    Découpe une longueur totale en segments valides (les plus grands possibles).
    Exemple (Target 7) -> [4, 3] (car 7 n'existe pas, mais 4 et 3 oui).
    """
    parts = []
    remaining = total_length
    
    valid_lengths = []
    for (l, w) in VALID_SIZES:
        if w == width_ref: valid_lengths.append(l)
        if l == width_ref: valid_lengths.append(w)
    
    valid_lengths = sorted(list(set(valid_lengths)), reverse=True)
    
    while remaining > 0:
        found = False
        for L in valid_lengths:
            if L <= remaining:
                parts.append(L)
                remaining -= L
                found = True
                break
        if not found:
            parts.append(1)
            remaining -= 1
            
    return parts

def optimize_layer_smart(bricks, orientation):
    """
    Passe 1 (Intelligente) : 
    1. Identifie les "runs" continus de briques (même couleur, alignées).
    2. Calcule la longueur totale.
    3. Partitionne cette longueur en briques optimales selon VALID_SIZES.
    """
    # Tri
    if orientation == "H":
        bricks.sort(key=lambda b: (b.y, b.x)) 
        attr_main = 'x' 
        attr_cross = 'y' 
        dim_main = 'length'
        dim_cross = 'width'
    else: # V
        bricks.sort(key=lambda b: (b.x, b.y))
        attr_main = 'y'
        attr_cross = 'x'
        dim_main = 'width' 
        dim_cross = 'length' 

    optimized = []
    if not bricks: return []

    current_run = [bricks[0]]
    
    for b in bricks[1:]:
        last = current_run[-1]
        
        is_continuous = (
            getattr(b, attr_cross) == getattr(last, attr_cross) and 
            b.color == last.color and
            getattr(b, attr_main) == getattr(last, attr_main) + getattr(last, dim_main)
        )
        
        if is_continuous:
            current_run.append(b)
        else:
            optimized.extend(process_run(current_run, orientation))
            current_run = [b]
            
    optimized.extend(process_run(current_run, orientation))
    return optimized

def process_run(run_bricks, orientation):
    """Transforme une suite de briques brutes (ex: 7x 1x1) en briques optimisées (ex: 1x4 + 1x3)."""
    if not run_bricks: return []
    
    ref_b = run_bricks[0]
    
    if orientation == "H":
        # Somme des longueurs
        total_len = sum(b.length for b in run_bricks)
        width_ref = ref_b.width # Doit être à 1 normalement
        
        # Partitionnement optimal
        segments = get_best_partition(total_len, width_ref)
        
        # Création des nouvelles briques
        new_bricks = []
        curr_x = ref_b.x
        for seg_len in segments:
            new_bricks.append(Brick(ref_b.layer, curr_x, ref_b.y, seg_len, width_ref, ref_b.color, "H"))
            curr_x += seg_len
            
    else: # V
        # Somme des largeurs 
        total_len = sum(b.width for b in run_bricks)
        width_ref = ref_b.length 
        
        segments = get_best_partition(total_len, width_ref)
        
        new_bricks = []
        curr_y = ref_b.y
        for seg_len in segments:
            # En Vertical : length=largeur(X), width=longueur(Y)
            new_bricks.append(Brick(ref_b.layer, ref_b.x, curr_y, width_ref, seg_len, ref_b.color, "V"))
            curr_y += seg_len
            
    return new_bricks

def optimize_layer_2d_side(bricks, orientation):
    """Passe 2 : Fusion latérale (Élargissement) pour créer du 2xN."""
    if orientation == "H":
        bricks.sort(key=lambda b: (b.x, b.y))
    else: 
        bricks.sort(key=lambda b: (b.y, b.x))
    
    merged_list = []
    if not bricks: return []
    
    i = 0
    while i < len(bricks):
        current = bricks[i]
        # Fusion si possible avec le voisin immédiat dans la liste triée
        if i + 1 < len(bricks):
            next_b = bricks[i+1]
            merged = merge_bricks_side(current, next_b)
            if merged:
                merged_list.append(merged)
                i += 2 # On a consommé 2 briques
                continue
        # Sinon on garde la brique telle quelle
        merged_list.append(current)
        i += 1
    return merged_list


def solve_greedy_stripe(bricks):
    """Stratégie : Rayures + Partitionnement Intelligent + Fusion 2D."""
    print(f"[Solver] Démarrage... ({len(bricks)} briques initiales)")
    
    layers = defaultdict(list)
    for b in bricks:
        layers[b.layer].append(b)
    
    final_bricks = []
    
    for layer_idx in sorted(layers.keys()):
        layer_content = layers[layer_idx]
        
        if layer_idx % 2 == 0:
            orient = "H"
        else:
            orient = "V"

        # Passe 1 : Partitionnement Intelligent (1x1 -> 1xN optimal)
        pass1_bricks = optimize_layer_smart(layer_content, orient)
        
        # Passe 2 : Élargissement (1xN -> 2xN)
        pass2_bricks = optimize_layer_2d_side(pass1_bricks, orient)
        
        final_bricks.extend(pass2_bricks)

    reduction = 100 * (1 - len(final_bricks) / len(bricks))
    print(f"[Solver] Terminé. Briques : {len(bricks)} -> {len(final_bricks)} (Réduction : {reduction:.1f}%)")
    
    return final_bricks


if __name__ == "__main__":
    
    # === 1. IMPORTS DYNAMIQUES ===
    try:
        from brick_factory import bricks_from_numpy
    except ImportError:
        try:
            from brique_merge import bricks_from_numpy
        except ImportError:
            print("ERREUR CRITIQUE : Impossible d'importer 'bricks_from_numpy'.")
            sys.exit(1)

    # Imports de la chaîne de traitement LiDAR
    try:
        from donnees_echantillonnees_LIDAR import LIDAR_rectangle
        from LIDAR_couches import LIDAR_couches_LEGO_LDRAW
        from LIDAR_traitement import (
            voxel_graphe, 
            corriger_voxels_non_classes_iteratif,
            graphe_filtre_classes,
            graphe_filtre_sol, 
            remplir_trous_verticaux, 
            ajouter_sol_coque_pillier, 
            graphe_voxel
        )
        DATA_AVAILABLE = True
    except ImportError as e:
        DATA_AVAILABLE = False
        print(f"[Info] Modules LiDAR manquants : {e}")
        print("Impossible de lancer le test complet.")
        sys.exit(1)


    print("\n=== LANCEMENT DU TEST : PIPELINE COMPLET (TRAITEMENT + SOLVER) ===\n")

    if DATA_AVAILABLE:
        # === A. PARAMÈTRES ===
        nom_fichier = "exemple.laz"
        file_path = DATA_DIR / nom_fichier
        
        if not file_path.exists():
            print(f"[ERREUR] Fichier {nom_fichier} introuvable pour le test.")
            sys.exit(1)

        # === B. CHARGEMENT & VOXELISATION ===
        print("1. Chargement et Voxelisation...")
        lidar_data = LIDAR_rectangle(
            file_path, 
            nb_points=1000000000,   
            x_min_coin=669680.0,    
            y_min_coin=6860143.0,   
            longueur_x=150,         
            longueur_y=100          
        )

        counts, class_maj = LIDAR_couches_LEGO_LDRAW(lidar_data, taille_xy=1.0, lego_ratio=1.2, densite_min=1)
        print(f"   -> Grille initiale : {counts.shape}")


        # === C. TRAITEMENTS STRUCTURELS (Comme dans main.py) ===
        print("\n2. Traitements Structurels (Graphe, Nettoyage, Piliers)...")
        
        # 1. Graphe
        G = voxel_graphe(counts, class_maj)

        G = corriger_voxels_non_classes_iteratif(G, class_non_classe=1, classes_a_propager=[6], class_sol=2, max_iter=5)

        G = graphe_filtre_classes(G, classes_gardees=[1, 2, 3, 4, 5, 6])
        
        # 2. Nettoyage sol
        G = graphe_filtre_sol(G, class_sol=2)

        # 4. Consolidation (Piliers)
        G = ajouter_sol_coque_pillier(G, class_sol=2, class_bat=6, n_min=2, pillar_step=4, pillar_width=2)
        
        # 3. Remplissage Murs
        G = remplir_trous_verticaux(G, classes_batiment=[6])
        
        # 5. Retour vers Grille
        counts_traite, class_maj_traite = graphe_voxel(G)
        
        
        # === D. CONVERSION EN OBJETS BRIQUES ===
        print("\n3. Conversion Numpy -> Objets Brick...")
        # On utilise les données TRAITÉES ici
        raw_bricks = bricks_from_numpy(counts_traite, class_maj_traite, visualisation="COULEUR")
        print(f"   -> Nombre de briques (1x1) à optimiser : {len(raw_bricks)}")

        # === E. OPTIMISATION (SOLVER) ===
        print("\n4. Exécution du Solver (Greedy Stripe)...")
        optimized_bricks = solve_greedy_stripe(raw_bricks)

        # === F. EXPORT ===
        print("\n5. Exportation du résultat...")
        nom_sortie = OUTPUT_DIR / "Test_Complet_Traite_Optimise.ldr"
        export_to_ldr(optimized_bricks, str(nom_sortie))
        
        print(f"\n[SUCCÈS] Fichier de sortie : {nom_sortie}")
        print("Ce modèle contient la structure optimisée (piliers) ET les briques fusionnées.")

        print_brick_stats(optimized_bricks)
