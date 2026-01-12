"""
=== cost_func_change.py ===
Fonctions de coût pour évaluer la solidité d'un assemblage LEGO.
Optimisé via Hash Map (Grille spatiale) pour une complexité O(N).
"""

def build_grid_map(bricks):
    """
    Crée un dictionnaire spatial pour accès O(1).
    Clé : (layer, x, y) -> Valeur : Référence vers l'objet Brick
    """
    grid = {}
    for b in bricks:
        # Cartographie de chaque voxel occupé par la brique vers la brique elle-même
        for dx in range(b.length):
            for dy in range(b.width):
                # Coordonnées absolues du voxel
                vx = b.x + dx
                vy = b.y + dy
                grid[(b.layer, vx, vy)] = b
    return grid

# ============================================================
#   P1 — PERPENDICULARITY PENALTY (Croisement des couches)
# ============================================================

def perpendicularity_penalty_fast(layer_bricks, grid, current_z):
    """
    Pénalise si une brique repose sur une brique de MÊME orientation.
    C'est la règle de base : il faut croiser les briques (H sur V, V sur H).
    """
    penalty = 0
    processed_pairs = set()

    for b in layer_bricks:
        x1, y1, x2, y2 = b.bbox()
        
        # Scan la surface de la brique courante
        for ix in range(x1, x2):
            for iy in range(y1, y2):

                brick_below = grid.get((current_z - 1, ix, iy))
                
                if brick_below:
                    # Identifiant unique de la paire
                    pair_id = (id(b), id(brick_below))
                    
                    if pair_id not in processed_pairs:
                        # Si même orientation => Pénalité (Pas de croisement)
                        if b.orientation == brick_below.orientation:
                            penalty += 1
                        processed_pairs.add(pair_id)
    return penalty

# ============================================================
#   P2 — VERTICAL BOUNDARY PENALTY (Coup de sabre)
# ============================================================

def vertical_boundary_penalty_fast(layer_bricks, grid, current_z):
    """
    Pénalise les joints verticaux alignés ("Coups de sabre").
    Si le bord d'une brique tombe exactement au-dessus du bord de la brique du dessous.
    """
    penalty = 0
    
    for b in layer_bricks:
        x1, y1, x2, y2 = b.bbox()
        
        # On vérifie les deux extrémités de la brique selon son orientation
        # Si b est Horizontal, ses bords pertinents sont à x1 et x2 (bords verticaux)
        # Si b est Vertical, ses bords pertinents sont à y1 et y2 (bords horizontaux dans le plan)
        
        # --- Cas Horizontal (Bords gauche/droite) ---
        if b.orientation == "H":
            # Vérif Bord Gauche (x1)
            b_below_in = grid.get((current_z - 1, x1, y1))      # Juste dessous
            b_below_out = grid.get((current_z - 1, x1 - 1, y1)) # Juste à gauche dessous
            
            # Si changement de brique dessous exactement ici => Joint aligné
            if b_below_in != b_below_out:
                penalty += 1
                
            # Vérif Bord Droit (x2)
            b_below_in = grid.get((current_z - 1, x2 - 1, y1))
            b_below_out = grid.get((current_z - 1, x2, y1))
            if b_below_in != b_below_out:
                penalty += 1

        # --- Cas Vertical (Bords haut/bas) ---
        elif b.orientation == "V":
            # Vérif Bord Bas (y1)
            b_below_in = grid.get((current_z - 1, x1, y1))
            b_below_out = grid.get((current_z - 1, x1, y1 - 1))
            if b_below_in != b_below_out:
                penalty += 1
                
            # Vérif Bord Haut (y2)
            b_below_in = grid.get((current_z - 1, x1, y2 - 1))
            b_below_out = grid.get((current_z - 1, x1, y2))
            if b_below_in != b_below_out:
                penalty += 1

    return penalty

# ============================================================
#   P3 — HORIZONTAL T-JUNCTION PENALTY (Jonctions en T)
# ============================================================

def horizontal_alignment_penalty_fast(layer_bricks, grid, current_z):
    """
    Pénalise les jonctions en T qui ne sont pas au centre (offset).
    Plus la jonction est proche du bord, moins c'est solide.
    """
    penalty = 0

    for b in layer_bricks:
        x1, y1, x2, y2 = b.bbox()
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        
        neighbors = set()
        
        if b.orientation == "H":
            # Voisins au-dessus (y-1) et au-dessous (y+1) localement
            # Scan tout le long de la brique
            for ix in range(x1, x2):
                n_top = grid.get((current_z, ix, y1 - 1))
                n_bot = grid.get((current_z, ix, y2))
                if n_top: neighbors.add(n_top)
                if n_bot: neighbors.add(n_bot)
                
        else: # Vertical
            # Voisins à gauche (x-1) et à droite (x+1)
            for iy in range(y1, y2):
                n_left = grid.get((current_z, x1 - 1, iy))
                n_right = grid.get((current_z, x2, iy))
                if n_left: neighbors.add(n_left)
                if n_right: neighbors.add(n_right)
        
        # Calcul de la pénalité pour chaque voisin identifié
        for n in neighbors:
            nx1, ny1, nx2, ny2 = n.bbox()
            
            # Si b est H, les voisins créent des jonctions par leurs bords verticaux (nx1, nx2)
            if b.orientation == "H":
                if x1 < nx1 < x2:
                    dist = abs(nx1 - center_x)
                    penalty += (dist / ((x2 - x1)/2.0)) 

                if x1 < nx2 < x2:
                    dist = abs(nx2 - center_x)
                    penalty += (dist / ((x2 - x1)/2.0))
                    
            # Si b est V, voisins créent jonctions par leurs bords horizontaux (ny1, ny2)
            elif b.orientation == "V":
                if y1 < ny1 < y2:
                    dist = abs(ny1 - center_y)
                    penalty += (dist / ((y2 - y1)/2.0))
                if y1 < ny2 < y2:
                    dist = abs(ny2 - center_y)
                    penalty += (dist / ((y2 - y1)/2.0))

    return penalty


# ============================================================
#   COST FUNCTION — TOTAL COST (Fonction Principale)
# ============================================================

def total_cost_function(bricks, C1=1.0, C2=1.0, C3=1.0):
    """
    Calcule le coût TOTAL du modèle LEGO.
    Plus le coût est bas, plus le modèle est solide.
    
    C1 : Poids Perpendicularité (Croisement)
    C2 : Poids Joints Verticaux (Coups de sabre)
    C3 : Poids Jonctions T
    """
    if not bricks:
        return 0.0

    # 1. Construction de la carte spatiale (O(N))
    grid = build_grid_map(bricks)
    
    # 2. Organisation par couches
    from collections import defaultdict
    layers = defaultdict(list)
    for b in bricks:
        layers[b.layer].append(b)

    total_cost = 0.0
    sorted_layers = sorted(layers.keys())
    
    for layer_idx in sorted_layers:
        current_bricks = layers[layer_idx]
        
        # P1 & P2 nécessitent une couche en dessous. 
        if (layer_idx - 1) in layers:
            P1 = perpendicularity_penalty_fast(current_bricks, grid, layer_idx)
            P2 = vertical_boundary_penalty_fast(current_bricks, grid, layer_idx)
        else:
            P1 = 0
            P2 = 0
            
        # P3 ne dépend que de la couche courante
        P3 = horizontal_alignment_penalty_fast(current_bricks, grid, layer_idx)

        total_cost += (C1 * P1) + (C2 * P2) + (C3 * P3)

    return total_cost