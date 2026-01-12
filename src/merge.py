"""
=== merge.py ===
Gestion des briques LEGO : Définition, Fusion et Contraintes physiques.
Ce module définit la classe Brick et les règles permettant de fusionner deux briques 1x1.
"""

# Catalogue simplifié des briques standard (Largeur, Longueur)
# Il faut que ca corresponde au catalogue de pièces LDraw dans solver.py
VALID_SIZES = {
    # --- Briques 1.x ---
    (1, 1), (1, 2), (1, 4), 
    
    # --- Briques 2.x ---
    (2, 2), (2, 4),
    
    # --- Inverses (pour la recherche) ---
    (2, 1), (4, 1),
    (4, 2)
}

class Brick:
    def __init__(self, layer, x, y, length, width, color, orientation="H"):
        """
        Représente une brique LEGO.
        
        Paramètres
        ----------
        layer : int
            Niveau Z (couche).
        x, y : int
            Coordonnées du coin inférieur gauche sur la grille.
        length : int
            Longueur (dimension selon l'axe X si horizontal).
        width : int
            Largeur (dimension selon l'axe Y si horizontal).
        color : int
            Code couleur LDraw (ex: 0=Noir, 4=Rouge, 7=Gris).
        orientation : str
            "H" (Horizontal) ou "V" (Vertical).
        """
        self.layer = layer
        self.x = x
        self.y = y
        self.length = length
        self.width = width
        self.color = color 
        self.orientation = orientation

    def bbox(self):
        """
        Retourne la bounding box (x1, y1, x2, y2).
        x2 et y2 sont exclusifs (comme range en python).
        """
        return (self.x, self.y, self.x + self.length, self.y + self.width)

    def __repr__(self):
        return f"Brick(L{self.layer}, x={self.x}, y={self.y}, {self.length}x{self.width}, col={self.color}, ori={self.orientation})"


# =======================================================
#          Fonctions de Validation & Voisinage
# =======================================================

def is_valid_lego_part(length, width):
    """
    Vérifie si la brique existe dans le catalogue LEGO physique.
    Ex: 1x4 existe, mais 1x5 n'existe pas.
    """
    return (length, width) in VALID_SIZES

def are_neighbors(b1, b2):
    """
    Deux briques sont voisines si :
    - Elles sont dans la même couche
    - Leur bounding box SE TOUCHENT EXACTEMENT sur une frontière
      (pas de chevauchement diagonal, pas éloigné)
    """

    if b1.layer != b2.layer:
        return False

    x1a, y1a, x2a, y2a = b1.bbox()
    x1b, y1b, x2b, y2b = b2.bbox()

    # --- 1) partage d'une frontière verticale (bords X se touchent)
    # L'un finit où l'autre commence, et il y a chevauchement en Y
    vertical_touch = (x2a == x1b or x2b == x1a) and not (y2a <= y1b or y2b <= y1a)

    # --- 2) partage d'une frontière horizontale (bords Y se touchent)
    # L'un finit où l'autre commence, et il y a chevauchement en X
    horizontal_touch = (y2a == y1b or y2b == y1a) and not (x2a <= x1b or x2b <= x1a)

    return vertical_touch or horizontal_touch


# =======================================================
#        Fonctions de Fusion (Merging)
# =======================================================

# --- FUSION LONGITUDINALE (1D) ---
def can_merge(b1, b2):
    """Fusion bout à bout (Allongement)."""
    if b1.layer != b2.layer or b1.color != b2.color or b1.orientation != b2.orientation:
        return False
    if not are_neighbors(b1, b2):
        return False

    if b1.orientation == "H": 
        return (b1.y == b2.y) and (b1.width == b2.width)
    if b1.orientation == "V":
        return (b1.x == b2.x) and (b1.length == b2.length)
    return False

def merge_bricks(b1, b2):
    """Crée une brique plus longue."""
    if not can_merge(b1, b2): return None
    
    if b1.orientation == "H":
        x = min(b1.x, b2.x)
        length = b1.length + b2.length
        if is_valid_lego_part(length, b1.width):
            return Brick(b1.layer, x, b1.y, length, b1.width, b1.color, "H")
            
    elif b1.orientation == "V":
        y = min(b1.y, b2.y)
        width = b1.width + b2.width 
        if is_valid_lego_part(b1.length, width):
            return Brick(b1.layer, b1.x, y, b1.length, width, b1.color, "V")
    return None

# --- FUSION LATÉRALE (2D) ---
def can_merge_side(b1, b2):
    """
    Fusion côte à côte (Élargissement).
    Exemple : Deux 1x4 côte à côte deviennent une 2x4.
    """
    if b1.layer != b2.layer or b1.color != b2.color or b1.orientation != b2.orientation:
        return False
    
    if not are_neighbors(b1, b2):
        return False

    if b1.orientation == "H":
        return (b1.x == b2.x) and (b1.length == b2.length)
    elif b1.orientation == "V":
        return (b1.y == b2.y) and (b1.width == b2.width)
    return False

def merge_bricks_side(b1, b2):
    """Crée une brique plus large (ex: 2xN)."""
    if not can_merge_side(b1, b2): return None
    
    if b1.orientation == "H":
        y = min(b1.y, b2.y)
        new_width = b1.width + b2.width
        if is_valid_lego_part(b1.length, new_width):
            return Brick(b1.layer, b1.x, y, b1.length, new_width, b1.color, "H")
            
    elif b1.orientation == "V":
        x = min(b1.x, b2.x)
        new_length = b1.length + b2.length
        if is_valid_lego_part(new_length, b1.width):
            return Brick(b1.layer, x, b1.y, new_length, b1.width, b1.color, "V")
            
    return None

def get_neighbors(brick, bricks):
    """
    Retourne tous les voisins mergeables d’une brique donnée dans une liste.
    Note : Cette fonction est linéaire O(N), pour l'optimisation on préférera
    passer par une grille spatiale (voir cost_func_change.py).
    """
    neigh = []
    for b in bricks:
        if b is brick:
            continue
        if can_merge(brick, b):
            neigh.append(b)
    return neigh