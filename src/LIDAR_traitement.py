"""
=== Traitement Topologique et Structurel de données LiDAR ===

Ce code permet de :
- Convertir un modèle voxelisé en graphe 6-connexe (via NetworkX).
- Nettoyer les données (suppression des éléments volants, filtrage par classe).
- Corriger les imperfections (remplissage des trous verticaux dans les murs).
- Optimiser la structure pour l'export LEGO (création de coques, ajout de piliers de soutènement).

Informations complémentaires :
- Ce module constitue une étape essentielle pour la chaine de traitements des données LiDAR.
- Il transforme une simple grille de voxels brute en une structure cohérente, nettoyée et optimisée pour la construction physique ou virtuelle.

"""



# === Importations ===

import sys
import numpy as np
import networkx as nx
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

def voxel_graphe(counts, class_maj):
    """
    Crée un graphe 6-connexe à partir d’un modèle voxelisé LiDAR.

    Chaque voxel plein devient un nœud avec :
        - coord : position (y, x, z)
        - class_maj : classe majoritaire du voxel

    Paramètres
    ----------
    counts : np.ndarray
        Tableau 3D contenant le nombre de points LiDAR par voxel.
    class_maj : np.ndarray
        Tableau 3D des classes majoritaires par voxel.
    densite_min : int
        Seuil minimal de densité pour qu’un voxel soit considéré "plein".

    Retour
    ------
    G : networkx.Graph
        Graphe 6-connexe des voxels pleins avec attributs.
    """

    # --- Voxels pleins ---
    mask = counts > 0
    coords = np.argwhere(mask)
    coord_tuples = [tuple(map(int, c)) for c in coords] 
    id_map = {coord: i for i, coord in enumerate(coord_tuples)}

    # --- Voisinage 6-connexe ---
    voisins = np.array([
        [1, 0, 0], [-1, 0, 0],
        [0, 1, 0], [0, -1, 0],
        [0, 0, 1], [0, 0, -1]
    ])
    voisins_coords = (coords[:, None, :] + voisins[None, :, :]).reshape(-1, 3)

    # --- Arêtes entre voxels pleins ---
    plein_set = set(coord_tuples)
    voisin_pairs = [
        (tuple(map(int, c1)), tuple(map(int, c2)))
        for c1, c2 in zip(np.repeat(coords, 6, axis=0), voisins_coords)
        if tuple(map(int, c2)) in plein_set
    ]
    aretes = [(id_map[a], id_map[b]) for a, b in voisin_pairs]

    # --- Création du graphe ---
    G = nx.Graph()
    G.add_nodes_from(range(len(coords)))
    G.add_edges_from(aretes)

    # --- Attributs clairs ---
    nx.set_node_attributes(G, {i: (int(coords[i][1]), int(coords[i][0]), int(coords[i][2])) for i in range(len(coords))}, name='coord')
    nx.set_node_attributes(G, {i: int(class_maj[tuple(coords[i])]) for i in range(len(coords))}, name='class_maj')

    print(f"Graphe initial créé : {len(G.nodes())} nœuds, {len(G.edges())} arêtes.")
    return G



def corriger_voxels_non_classes_iteratif(G, class_non_classe=1, classes_a_propager=[6], class_sol=2, max_iter=5):
    """
    Corrige les voxels non classés (1) par propagation itérative de classes 
    spécifiques (ex: bâtiments) à partir de leurs voisins 6-connexes.

    Paramètres
    ----------
    G : networkx.Graph
        Graphe voxelisé.
    class_non_classe : int
        Code de la classe 'non classé'.
    classes_a_propager : list[int]
        Liste des classes à propager (ex: bâtiments, végétation…).
    class_sol : int
        Classe sol, qu’on ne doit pas propager.
    max_iter : int
        Nombre maximum d’itérations.

    Retour
    ------
    G_corr : networkx.Graph
        Graphe corrigé.
    """

    G_corr = G.copy()

    total_remplaces = 0
    
    for it in range(max_iter):
        nodes_nc = [n for n, d in G_corr.nodes(data=True) if d['class_maj'] == class_non_classe]
        if not nodes_nc:
            break  # Plus de voxels non classés

        changements = 0

        for n in nodes_nc:
            voisins = list(G_corr.neighbors(n))
            classes_voisins = [
                G_corr.nodes[v]['class_maj']
                for v in voisins
                if G_corr.nodes[v]['class_maj'] in classes_a_propager
            ]

            if classes_voisins:
                c_new = max(set(classes_voisins), key=classes_voisins.count)
                G_corr.nodes[n]['class_maj'] = c_new
                changements += 1

        total_remplaces += changements

        if changements == 0:
            break  # Stabilisation atteinte

    print(f"Correction classes : {total_remplaces} voxels non classés remplacés en classe {classes_a_propager} (Total: {len(G_corr.nodes())} nœuds).")
    return G_corr



def graphe_filtre_classes(G, classes_gardees=[1, 2, 3, 4, 5, 6]):
    """
    Filtre le graphe pour ne conserver que les voxels dont la classe
    appartient à `classes_gardees`.

    Paramètres
    ----------
    G : networkx.Graph
    classes_gardees : liste d'int
        Classes conservées : [1, 2, 3, 4, 5, 6] => NON_CLASSE + SOL + VÉGÉTATIONS(basse, moyenne, haute) + BÂTIMENT

    Retour
    ------
    G_filtre : Graph
        Graphe réduit.
    """

    nb_avant = len(G.nodes())

    nodes_valides = [
        n for n, d in G.nodes(data=True)
        if d.get('class_maj') in classes_gardees
    ]

    G_filtre = G.subgraph(nodes_valides).copy()
    nb_apres = len(G_filtre.nodes())

    print(f"Filtrage classes : {nb_avant - nb_apres} nœuds enlevés (Total: {nb_apres} nœuds).")
    return G_filtre



def graphe_filtre_sol(G, class_sol=2):
    """
    Supprime les composants du graphe non connectés à un voxel de classe 'sol'.

    Paramètres
    ----------
    G : networkx.Graph
        Graphe voxelisé.
    class_sol : int
        Code de la classe 'sol' dans la classification LIDAR.

    Retour
    ------
    G_filtre : networkx.Graph
        Graphe réduit, ne contenant que les composants connectés au sol.
    """

    nb_avant = len(G.nodes())

    # Trouver les nœuds de classe 'sol'
    nodes_sol = [n for n, d in G.nodes(data=True) if d.get('class_maj') == class_sol]

    # Identifier les composantes connexes
    composantes = list(nx.connected_components(G))

    # Garder celles qui contiennent au moins un voxel de sol
    composantes_valides = [
        c for c in composantes if any(n in nodes_sol for n in c)
    ]

    # Fusionner les composantes valides
    nodes_valides = set().union(*composantes_valides)
    G_filtre = G.subgraph(nodes_valides).copy()

    nb_apres = len(G_filtre.nodes())

    print(f"Filtrage sol : {nb_avant - nb_apres} nœuds enlevés (Total: {nb_apres} nœuds).")
    return G_filtre



def ajouter_sol_coque_pillier(G, class_sol=2, class_bat=3, n_min=2, pillar_step=4, pillar_width=2):
    """
    Propagation du sol avec propagation de la HAUTEUR.
    + OPTIMISATION COQUE : Ne conserve qu'une "coque" du sol.
    + STRUCTURE : Garde des piliers verticaux pour la solidité.
    
    Paramètres additionnels :
    pillar_step : int
        Intervalle entre les piliers (ex: 10).
    pillar_width : int
        Largeur du pilier en voxels. 
        Ex: pillar_width=2 crée des piliers de 2x2 briques (plus solides).
    """

    nb_avant = len(G.nodes())
    coords = np.array([d['coord'] for _, d in G.nodes(data=True)], dtype=int)
    classes = np.array([d['class_maj'] for _, d in G.nodes(data=True)], dtype=int)
    if len(coords) == 0: return G.copy()

    # Grille Dense
    min_coords = coords.min(axis=0)
    coords_shifted = coords - min_coords 
    nx_max, ny_max, nz_max = coords_shifted.max(axis=0) + 1
    grid = np.zeros((nx_max, ny_max, nz_max), dtype=np.int8) 
    grid[coords_shifted[:,0], coords_shifted[:,1], coords_shifted[:,2]] = classes

    # Propagation (Toujours identique au début)
    sol_mask = (grid == class_sol); bat_mask = (grid == class_bat)
    z_indices = np.arange(nz_max); z_height_map = np.zeros((nx_max, ny_max), dtype=int)
    
    sol_exist = sol_mask.any(axis=2)
    if np.any(sol_exist):
        z_height_map[sol_exist] = nz_max - 1 - np.argmax(sol_mask[..., ::-1], axis=2)[sol_exist]

    sol_fill = sol_exist[:, :, None] & (z_indices[None, None, :] <= z_height_map[:, :, None])
    grid[sol_fill] = np.where((grid[sol_fill] == 0) | (grid[sol_fill] == class_sol), class_sol, grid[sol_fill])
    sol_mask = (grid == class_sol)

    interior_mask = bat_mask.any(axis=2)
    processed_mask = np.zeros((nx_max, ny_max), dtype=bool)
    voisins8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    # Propagation Ext
    changed = True
    while changed:
        changed = False
        sol_xy = sol_mask.any(axis=2).astype(np.int8)
        neighbor_count = np.zeros_like(sol_xy); neighbor_max_z = np.zeros((nx_max, ny_max), dtype=int)
        for dx, dy in voisins8:
            shifted_sol = np.roll(np.roll(sol_xy, dx, axis=0), dy, axis=1)
            neighbor_count += shifted_sol
            shifted_h = np.roll(np.roll(z_height_map, dx, axis=0), dy, axis=1)
            neighbor_max_z = np.maximum(neighbor_max_z, shifted_h * shifted_sol)
        candidate = (neighbor_count >= n_min) & (sol_xy == 0) & (~interior_mask) & (~processed_mask)
        if np.any(candidate):
            changed = True
            processed_mask[candidate] = True
            xs, ys = np.where(candidate)
            z_targets = neighbor_max_z[xs, ys]
            for x, y, zt in zip(xs, ys, z_targets):
                if zt < 0: continue
                grid[x, y, :zt+1] = np.where(grid[x, y, :zt+1] == 0, class_sol, grid[x, y, :zt+1])
                z_height_map[x, y] = zt
            sol_mask = (grid == class_sol)

    # Propagation Sous Bâtiments
    interior_processing = interior_mask.copy()
    changed_int = True
    while changed_int:
        changed_int = False
        h_current = z_height_map.copy(); h_max_neighbor = np.zeros_like(h_current)
        for dx, dy in voisins8:
            shifted_h = np.roll(np.roll(h_current, dx, axis=0), dy, axis=1)
            h_max_neighbor = np.maximum(h_max_neighbor, shifted_h)
        update_mask = interior_processing & (z_height_map == 0) & (h_max_neighbor > 0)
        if np.any(update_mask):
            changed_int = True
            z_height_map[update_mask] = h_max_neighbor[update_mask]

    xs, ys = np.where(interior_mask)
    if len(xs) > 0:
        z_tops = z_height_map[xs, ys]
        for x, y, zt in zip(xs, ys, z_tops):
             if zt > 0:
                 col_slice = grid[x, y, :zt+1]
                 mask_writable = (col_slice == 0) | (col_slice == class_sol)
                 col_slice[mask_writable] = class_sol

    # === COQUE AVEC PILIERS ===
    sol_final_mask = (grid == class_sol)
    is_internal = sol_final_mask.copy()
    
    is_internal[:-1, :, :] &= sol_final_mask[1:, :, :]  
    is_internal[1:, :, :]  &= sol_final_mask[:-1, :, :]  
    is_internal[:, :-1, :] &= sol_final_mask[:, 1:, :]  
    is_internal[:, 1:, :]  &= sol_final_mask[:, :-1, :]  
    is_internal[:, :, :-1] &= sol_final_mask[:, :, 1:]  
    is_internal[:, :, 1:]  &= sol_final_mask[:, :, :-1]  
    
    is_internal[0, :, :] = False; is_internal[-1, :, :] = False
    is_internal[:, 0, :] = False; is_internal[:, -1, :] = False
    is_internal[:, :, 0] = False; is_internal[:, :, -1] = False

    # Protection des piliers
    if pillar_step > 0: 
        x_indices = np.arange(nx_max)
        y_indices = np.arange(ny_max)
        # Piliers de largeur configurable
        x_pillar_mask = (x_indices % pillar_step) < pillar_width
        y_pillar_mask = (y_indices % pillar_step) < pillar_width
        pillar_mask_2d = x_pillar_mask[:, None] & y_pillar_mask[None, :]
        is_internal[pillar_mask_2d, :] = False # On ne supprime pas les piliers

    grid[is_internal] = 0

    # Reconstruction
    G_sol = nx.Graph()
    voxels_finaux = np.argwhere(grid != 0)
    nodes_list = []
    for i, (x, y, z) in enumerate(voxels_finaux):
        real_coord = (x + min_coords[0], y + min_coords[1], z + min_coords[2])
        nodes_list.append((i, {"coord": real_coord, "class_maj": int(grid[x, y, z])}))
    G_sol.add_nodes_from(nodes_list)
    
    print(f"Ajout sol (Coque+Piliers) : {len(G_sol.nodes()) - nb_avant} voxels ajoutés.")
    return G_sol

def ajouter_sol_coque(G, class_sol=2, class_bat=3, n_min=2):
    """
    Propagation du sol avec propagation de la HAUTEUR (bouche les trous sous les objets).
    + OPTIMISATION : Ne conserve qu'une "coque" (shell) du sol pour économiser les briques.
    """
    
    nb_avant = len(G.nodes())
    coords = np.array([d['coord'] for _, d in G.nodes(data=True)], dtype=int)
    classes = np.array([d['class_maj'] for _, d in G.nodes(data=True)], dtype=int)
    if len(coords) == 0: return G.copy()

    # Grille Dense
    min_coords = coords.min(axis=0)
    coords_shifted = coords - min_coords 
    nx_max, ny_max, nz_max = coords_shifted.max(axis=0) + 1
    grid = np.zeros((nx_max, ny_max, nz_max), dtype=np.int8) 
    grid[coords_shifted[:,0], coords_shifted[:,1], coords_shifted[:,2]] = classes

    # Propagation (Identique à Rempli pour avoir le volume complet d'abord)
    sol_mask = (grid == class_sol); bat_mask = (grid == class_bat)
    z_indices = np.arange(nz_max); z_height_map = np.zeros((nx_max, ny_max), dtype=int)
    
    sol_exist = sol_mask.any(axis=2)
    if np.any(sol_exist):
        z_height_map[sol_exist] = nz_max - 1 - np.argmax(sol_mask[..., ::-1], axis=2)[sol_exist]

    sol_fill = sol_exist[:, :, None] & (z_indices[None, None, :] <= z_height_map[:, :, None])
    grid[sol_fill] = np.where((grid[sol_fill] == 0) | (grid[sol_fill] == class_sol), class_sol, grid[sol_fill])
    sol_mask = (grid == class_sol)

    interior_mask = bat_mask.any(axis=2)
    processed_mask = np.zeros((nx_max, ny_max), dtype=bool)
    voisins8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    # Propagation Ext
    changed = True
    while changed:
        changed = False
        sol_xy = sol_mask.any(axis=2).astype(np.int8)
        neighbor_count = np.zeros_like(sol_xy); neighbor_max_z = np.zeros((nx_max, ny_max), dtype=int)
        for dx, dy in voisins8:
            shifted_sol = np.roll(np.roll(sol_xy, dx, axis=0), dy, axis=1)
            neighbor_count += shifted_sol
            shifted_h = np.roll(np.roll(z_height_map, dx, axis=0), dy, axis=1)
            neighbor_max_z = np.maximum(neighbor_max_z, shifted_h * shifted_sol)
        candidate = (neighbor_count >= n_min) & (sol_xy == 0) & (~interior_mask) & (~processed_mask)
        if np.any(candidate):
            changed = True
            processed_mask[candidate] = True
            xs, ys = np.where(candidate)
            z_targets = neighbor_max_z[xs, ys]
            for x, y, zt in zip(xs, ys, z_targets):
                if zt < 0: continue
                grid[x, y, :zt+1] = np.where(grid[x, y, :zt+1] == 0, class_sol, grid[x, y, :zt+1])
                z_height_map[x, y] = zt
            sol_mask = (grid == class_sol)

    # Propagation Sous Bâtiments
    interior_processing = interior_mask.copy()
    changed_int = True
    while changed_int:
        changed_int = False
        h_current = z_height_map.copy(); h_max_neighbor = np.zeros_like(h_current)
        for dx, dy in voisins8:
            shifted_h = np.roll(np.roll(h_current, dx, axis=0), dy, axis=1)
            h_max_neighbor = np.maximum(h_max_neighbor, shifted_h)
        update_mask = interior_processing & (z_height_map == 0) & (h_max_neighbor > 0)
        if np.any(update_mask):
            changed_int = True
            z_height_map[update_mask] = h_max_neighbor[update_mask]

    xs, ys = np.where(interior_mask)
    if len(xs) > 0:
        z_tops = z_height_map[xs, ys]
        for x, y, zt in zip(xs, ys, z_tops):
             if zt > 0:
                 col_slice = grid[x, y, :zt+1]
                 mask_writable = (col_slice == 0) | (col_slice == class_sol)
                 col_slice[mask_writable] = class_sol

    # === ÉROSION POUR CRÉER LA COQUE ===
    sol_final_mask = (grid == class_sol)
    is_internal = sol_final_mask.copy()
    
    # Un voxel est interne si ses 6 voisins directs sont aussi du sol
    is_internal[:-1, :, :] &= sol_final_mask[1:, :, :]  
    is_internal[1:, :, :]  &= sol_final_mask[:-1, :, :]  
    is_internal[:, :-1, :] &= sol_final_mask[:, 1:, :]  
    is_internal[:, 1:, :]  &= sol_final_mask[:, :-1, :]  
    is_internal[:, :, :-1] &= sol_final_mask[:, :, 1:]  
    is_internal[:, :, 1:]  &= sol_final_mask[:, :, :-1]  
    
    # Bords jamais internes
    is_internal[0, :, :] = False; is_internal[-1, :, :] = False
    is_internal[:, 0, :] = False; is_internal[:, -1, :] = False
    is_internal[:, :, 0] = False; is_internal[:, :, -1] = False
    
    grid[is_internal] = 0 # Suppression de l'intérieur

    # Reconstruction
    G_sol = nx.Graph()
    voxels_finaux = np.argwhere(grid != 0)
    nodes_list = []
    for i, (x, y, z) in enumerate(voxels_finaux):
        real_coord = (x + min_coords[0], y + min_coords[1], z + min_coords[2])
        nodes_list.append((i, {"coord": real_coord, "class_maj": int(grid[x, y, z])}))
    G_sol.add_nodes_from(nodes_list)
    
    print(f"Ajout sol (Coque) : {len(G_sol.nodes()) - nb_avant} voxels ajoutés.")
    return G_sol

def ajouter_sol_rempli(G, class_sol=2, class_bat=3, n_min=2):

    """
    Propagation du sol avec propagation.Ajoute un sol MASSIF sous toute la scène, y compris sous les bâtiments.
    Propage la hauteur du sol pour éviter les trous.
    """

    nb_avant = len(G.nodes())
    coords = np.array([d['coord'] for _, d in G.nodes(data=True)], dtype=int)
    classes = np.array([d['class_maj'] for _, d in G.nodes(data=True)], dtype=int)
    if len(coords) == 0: return G.copy()

    # Grille Dense
    min_coords = coords.min(axis=0)
    coords_shifted = coords - min_coords 
    nx_max, ny_max, nz_max = coords_shifted.max(axis=0) + 1
    
    grid = np.zeros((nx_max, ny_max, nz_max), dtype=np.int8) 
    grid[coords_shifted[:,0], coords_shifted[:,1], coords_shifted[:,2]] = classes

    # Masques & Hauteurs
    sol_mask = (grid == class_sol)
    bat_mask = (grid == class_bat)
    z_indices = np.arange(nz_max)
    z_height_map = np.zeros((nx_max, ny_max), dtype=int)
    
    sol_exist = sol_mask.any(axis=2)
    if np.any(sol_exist):
        z_height_map[sol_exist] = nz_max - 1 - np.argmax(sol_mask[..., ::-1], axis=2)[sol_exist]

    # Remplissage initial sous sol existant
    sol_fill = sol_exist[:, :, None] & (z_indices[None, None, :] <= z_height_map[:, :, None])
    grid[sol_fill] = np.where((grid[sol_fill] == 0) | (grid[sol_fill] == class_sol), class_sol, grid[sol_fill])
    sol_mask = (grid == class_sol)

    interior_mask = bat_mask.any(axis=2)
    processed_mask = np.zeros((nx_max, ny_max), dtype=bool)
    voisins8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    # 1. Propagation Extérieure
    changed = True
    while changed:
        changed = False
        sol_xy = sol_mask.any(axis=2).astype(np.int8)
        neighbor_count = np.zeros_like(sol_xy)
        neighbor_max_z = np.zeros((nx_max, ny_max), dtype=int)
        
        for dx, dy in voisins8:
            shifted_sol = np.roll(np.roll(sol_xy, dx, axis=0), dy, axis=1)
            neighbor_count += shifted_sol
            shifted_h = np.roll(np.roll(z_height_map, dx, axis=0), dy, axis=1)
            valid_h = shifted_h * shifted_sol 
            neighbor_max_z = np.maximum(neighbor_max_z, valid_h)

        candidate = (neighbor_count >= n_min) & (sol_xy == 0) & (~interior_mask) & (~processed_mask)
        if np.any(candidate):
            changed = True
            processed_mask[candidate] = True
            xs, ys = np.where(candidate)
            z_targets = neighbor_max_z[xs, ys]
            for x, y, zt in zip(xs, ys, z_targets):
                if zt < 0: continue
                grid[x, y, :zt+1] = np.where(grid[x, y, :zt+1] == 0, class_sol, grid[x, y, :zt+1])
                z_height_map[x, y] = zt
            sol_mask = (grid == class_sol)

    # 2. Propagation SOUS les bâtiments (Correction Robuste)
    interior_processing = interior_mask.copy()
    changed_int = True
    while changed_int:
        changed_int = False
        h_current = z_height_map.copy()
        h_max_neighbor = np.zeros_like(h_current)
        for dx, dy in voisins8:
            shifted_h = np.roll(np.roll(h_current, dx, axis=0), dy, axis=1)
            h_max_neighbor = np.maximum(h_max_neighbor, shifted_h)
        
        update_mask = interior_processing & (z_height_map == 0) & (h_max_neighbor > 0)
        if np.any(update_mask):
            changed_int = True
            z_height_map[update_mask] = h_max_neighbor[update_mask]

    # 3. Remplissage Final
    xs, ys = np.where(interior_mask)
    if len(xs) > 0:
        z_tops = z_height_map[xs, ys]
        for x, y, zt in zip(xs, ys, z_tops):
             if zt > 0:
                 col_slice = grid[x, y, :zt+1]
                 mask_writable = (col_slice == 0) | (col_slice == class_sol)
                 col_slice[mask_writable] = class_sol

    # Reconstruction
    G_sol = nx.Graph()
    voxels_finaux = np.argwhere(grid != 0)
    nodes_list = []
    for i, (x, y, z) in enumerate(voxels_finaux):
        real_coord = (x + min_coords[0], y + min_coords[1], z + min_coords[2])
        nodes_list.append((i, {"coord": real_coord, "class_maj": int(grid[x, y, z])}))
    G_sol.add_nodes_from(nodes_list)
    
    print(f"Ajout sol (Rempli) : {len(G_sol.nodes()) - nb_avant} voxels ajoutés.")
    return G_sol



def remplir_trous_verticaux(G, classes_batiment=[6]):
    """
    Épaissit les murs en remplissant les trous verticaux entre voxels bâtiment.
    """

    nb_avant = len(G.nodes())

    G2 = G.copy()

    # --- Regrouper les voxels par colonne (x, y) ---
    colonnes = {}
    for n, d in G.nodes(data=True):
        x, y, z = d["coord"]
        colonnes.setdefault((x, y), []).append((z, d['class_maj']))

    # --- Parcourir chaque colonne ---
    for (x, y), lst in colonnes.items():

        # trier verticalement
        lst_sorted = sorted(lst, key=lambda t: t[0])
        Z = [z for z, c in lst_sorted]
        C = [c for z, c in lst_sorted]

        # trouver les indices où classe = bâtiment
        idx_bat = [i for i, c in enumerate(C) if c in classes_batiment]
        if len(idx_bat) < 2:
            continue  # rien à remplir

        # parcourir les paires successives de voxels bâtiment
        for i1, i2 in zip(idx_bat[:-1], idx_bat[1:]):
            z1 = Z[i1]
            z2 = Z[i2]

            # Trou vertical ?
            if z2 > z1 + 1:
                # prendre la classe du voxel supérieur
                classe = C[i2]

                # Remplir les z manquants
                for z_new in range(z1 + 1, z2):
                    node = (x, y, z_new)

                    if node not in G2:

                        G2.add_node(
                            node,
                            coord=(x, y, z_new),
                            class_maj=classe
                        )

                        # Connectivité verticale
                        if (x, y, z_new - 1) in G2:
                            G2.add_edge(node, (x, y, z_new - 1))

                        if (x, y, z_new + 1) in G2:
                            G2.add_edge(node, (x, y, z_new + 1))

    nb_apres = len(G2.nodes())
    print(f"Remplissage murs : {nb_apres - nb_avant} nœuds rajoutés (Total: {nb_apres} nœuds).")
    return G2



def graphe_voxel(G):
    """
    Reconstruit les tableaux counts et class_maj à partir d'un graphe voxelisé.

    Les nœuds du graphe doivent avoir les attributs :
        - 'coord' : tuple (x, y, z) des indices voxel
        - 'class_maj' : classe majoritaire du voxel

    Paramètres
    ----------
    G : networkx.Graph
        Graphe voxelisé.

    Retour
    ------
    counts : np.ndarray
        Tableau 3D avec le nombre de points par voxel.
    class_maj : np.ndarray
        Tableau 3D avec la classe majoritaire de chaque voxel.
    """

    # --- Récupération des coordonnées et classes depuis le graphe ---
    coords = np.array([ (data['coord'][1], data['coord'][0], data['coord'][2])  # inverser X/Y pour cohérence
                        for _, data in G.nodes(data=True) ], dtype=int)
    classes = np.array([ data['class_maj'] for _, data in G.nodes(data=True) ], dtype=int)

    # --- Dimensions du tableau voxel ---
    ny, nx, nz = coords.max(axis=0) + 1  # +1 car indices commencent à 0

    # --- Initialisation ---
    counts = np.zeros((ny, nx, nz), dtype=int)
    class_maj = np.zeros((ny, nx, nz), dtype=int)

    # --- Remplissage ---
    for (y, x, z), c in zip(coords, classes):
        counts[y, x, z] += 1
        # Priorité : si le voxel contient déjà un autre point non-classé (1), le remplacer
        if class_maj[y, x, z] == 0 or (class_maj[y, x, z] == 1 and c != 1):
            class_maj[y, x, z] = c

    nb_briques = np.count_nonzero(counts)
    print(f"Conversion Voxel : (Total: {nb_briques} briques)")

    return counts, class_maj






# === Lancement du script ===

if __name__ == "__main__":

    # === IMPORT DU FICHIER LIDAR_LDRAW ===
    from LIDAR_LDRAW import voxel_LDRAW_classif

    # === FICHIER D'ENTRÉE ===
    nom_fichier = "exemple.laz"   # Remplacer par le nom du fichier .laz souhaité
    file_path = DATA_DIR / nom_fichier
    output_path_test = OUTPUT_DIR 

    # Vérification de sécurité
    if not file_path.exists():
        print(f"ERREUR : Le fichier {nom_fichier} est introuvable dans {DATA_DIR}")
        print("Veuillez placer un fichier .laz dans le dossier 'data'.")
        sys.exit(1) 

    print(f"Traitement du fichier : {nom_fichier}\n")
    
    print("=== DÉBUT DU TEST DE TRAITEMENT LIDAR ===\n")
    
    # On prend une petite zone rectangulaire pour tester rapidement
    print(f"1. Chargement et échantillonnage de {nom_fichier}...")
    lidar_data = LIDAR_rectangle(
        file_path, 
        nb_points=500000, 
        x_min_coin=669680.0, 
        y_min_coin=6860143.0, 
        longueur_x=80, 
        longueur_y=80
    )

    # 2. VOXELISATION INITIALE
    # ------------------------
    print("2. Voxelisation initiale (numpy)...")
    # On utilise la fonction de LIDAR_couches pour obtenir la grille de base
    counts, class_maj = LIDAR_couches_LEGO_LDRAW(
        lidar_data, 
        taille_xy=1.0, 
        lego_ratio=1.2, 
        densite_min=1
    )
    print(f"   -> Grille obtenue : {counts.shape}\n")

    # 3. CRÉATION DU GRAPHE
    # ---------------------
    print("3. Conversion en Graphe 6-connexe...")
    G = voxel_graphe(counts, class_maj)

    # 4. TRAITEMENTS TOPOLOGIQUES
    # ---------------------------
    
    # A. Filtrage des composants volants (bruit)
    print("4A. Filtrage : Suppression des éléments non connectés au sol...")
    G_clean = graphe_filtre_sol(G, class_sol=2)
    print(f"    -> Reste {len(G_clean.nodes())} noeuds après nettoyage.\n")

    # B. Remplissage des murs (bâtiments)
    print("4B. Correction : Remplissage vertical des murs de bâtiments (classe 6)...")
    G_filled = remplir_trous_verticaux(G_clean, classes_batiment=[6])
    print(f"    -> {len(G_filled.nodes()) - len(G_clean.nodes())} voxels ajoutés.\n")

    # C. Ajout des fondations (Coque + Piliers)
    print("4C. Structure : Ajout d'une coque de sol et de piliers de soutènement...")
    # On définit class_bat=6 pour que le sol ne remplisse pas l'intérieur des bâtiments si nécessaire
    G_final = ajouter_sol_coque_pillier(G_filled, class_sol=2, class_bat=6, n_min=1, pillar_step=4, pillar_width=2)
    print(f"    -> Graphe final : {len(G_final.nodes())} noeuds.\n")

    # 5. RETOUR VERS NUMPY ET EXPORT
    # ------------------------------
    print("5. Conversion inverse (Graphe -> Numpy) et Export LDraw...")
    final_counts, final_class_maj = graphe_voxel(G_final)
    
    nom_sortie = "Resultat_Traitement_Structure.ldr"
    voxel_LDRAW_classif(final_counts, final_class_maj, nom_fichier=output_path_test / nom_sortie)
    
    print(f"\n=== TEST TERMINÉ AVEC SUCCÈS ===")
    print(f"Fichier généré : {nom_sortie}")
    print("Ouvrez ce fichier dans LDView ou stud.io pour voir le résultat avec piliers et corrections.")
    