"""
=== Création d'un échantillon d'un fichier LiDAR ===

Ce code permet de :
- Créer un tableau NumPy d'un échantillon d'un fichier LIDAR
- Régler les paramètres d'échantillonage via un nombre de points et/ou d'une zone prédéfinie rectangulaire avec choix de ses attributs.

Informations complémentaires :
- Ce code est surtout destiner à échantilloner un fichier LIDAR trop important ainsi que pour tester les données sur des zones restreintes.
- Il ne contribue pas directement à la finalité opérationnelle du projet, mais en constitue un support de test.

"""

# === Importations ===

import sys
import numpy as np
from pathlib import Path

# --- Configuration des chemins ---
BASE_DIR = Path(__file__).resolve().parent.parent 
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"

sys.path.append(str(SRC_DIR))

# --- Imports des modules du projet ---
from import_LIDAR import laz_to_las


# === Fonction principale ===

def LIDAR_carre_aleatoire(file_path, nb_points, taille_zone):
    """
    Génère un échantillon d'une zone aléatoire sous forme de tableau NumPy à partir d’un fichier LiDAR.
    
    Paramètres
    ----------
    file_path : str
        Chemin d’accès au fichier LiDAR voulant être échantillonné.
    nb_points : int
        Nombre maximum de points souhaités dans l’échantillon.
    taille_zone : float
        Taille (en mètres) du côté de la zone carrée sélectionnée aléatoirement dans l’emprise du fichier.

    Retour
    ------
    LIDAR_numpy_test : np.ndarray
        Tableau NumPy structuré contenant les champs :
        - 'x' : coordonnées X (float64)
        - 'y' : coordonnées Y (float64)
        - 'z' : altitude Z (float64)
        - 'classification' : code de classification LiDAR (uint8)

    """

    # Lecture du fichier LiDAR
    las = laz_to_las(file_path)

    # Extraction des attributs du fichier LIDAR
    x = las.x
    y = las.y
    z = las.z
    classification = las.classification

    # Sélection d’une zone carrée aléatoire 
    xmin, xmax = np.min(x), np.max(x)
    ymin, ymax = np.min(y), np.max(y)

    x0 = np.random.uniform(xmin, xmax - taille_zone)
    y0 = np.random.uniform(ymin, ymax - taille_zone)

    # Points dans la zone
    masque_zone = (x >= x0) & (x <= x0 + taille_zone) & (y >= y0) & (y <= y0 + taille_zone)
    indices_zone = np.where(masque_zone)[0]

    # Si trop de points, on échantillonne
    if len(indices_zone) > nb_points:
        indices_zone = np.random.choice(indices_zone, size=nb_points, replace=False)

    # Données finales
    x_final = x[indices_zone]
    y_final = y[indices_zone]
    z_final = z[indices_zone]
    classification_final = classification[indices_zone]

    # Construction du tableau Numpy 
    LIDAR_numpy_test = np.zeros(len(indices_zone), dtype=[
        ('x', np.float64),
        ('y', np.float64),
        ('z', np.float64),
        ('classification', np.uint8)
    ])
    LIDAR_numpy_test['x'] = x_final
    LIDAR_numpy_test['y'] = y_final
    LIDAR_numpy_test['z'] = z_final
    LIDAR_numpy_test['classification'] = classification_final

    return LIDAR_numpy_test



def LIDAR_rectangle(file_path, nb_points, x_min_coin, y_min_coin, longueur_x, longueur_y):
    """
    Génère un échantillon sous forme de tableau NumPy à partir d’un fichier LiDAR,
    limité à un rectangle défini par son coin Sud-Ouest et ses dimensions (en mètres).

    Paramètres
    ----------
    file_path : str
        Chemin d’accès au fichier LiDAR voulant être échantillonné.
    nb_points : int
        Nombre maximum de points souhaités dans l’échantillon.
    x_min_coin : float
        Coordonnée X du coin Sud-Ouest du rectangle (Ouest).
    y_min_coin : float
        Coordonnée Y du coin Sud-Ouest du rectangle (Sud).
    longueur_x : float
        Taille du rectangle selon l’axe Est-Ouest (en mètres).
    longueur_y : float
        Taille du rectangle selon l’axe Nord-Sud (en mètres).

    Retour
    ------
    LIDAR_numpy_test : np.ndarray
        Tableau NumPy structuré contenant les champs :
        - 'x' : coordonnées X (float64)
        - 'y' : coordonnées Y (float64)
        - 'z' : altitude Z (float64)
        - 'classification' : code de classification LiDAR (uint8)
    """

    # === Lecture du fichier LiDAR ===
    las = laz_to_las(file_path)

    # === Extraction des attributs ===
    x = las.x
    y = las.y
    z = las.z
    classification = las.classification

    # === Bornes globales ===
    xmin, xmax = np.min(x), np.max(x)
    ymin, ymax = np.min(y), np.max(y)

    # === Définition du rectangle ===
    x_max_coin = x_min_coin + longueur_x
    y_max_coin = y_min_coin + longueur_y

    # === Filtrage vectorisé des points dans le rectangle ===
    masque_zone = ((x >= x_min_coin) & (x <= x_max_coin) & (y >= y_min_coin) & (y <= y_max_coin))
    indices_zone = np.where(masque_zone)[0]

    # === Échantillonnage si trop de points ===
    if len(indices_zone) > nb_points:
        indices_zone = np.random.choice(indices_zone, size=nb_points, replace=False)

    # === Données finales ===
    x_final = x[indices_zone]
    y_final = y[indices_zone]
    z_final = z[indices_zone]
    classification_final = classification[indices_zone]

    # === Construction du tableau NumPy structuré ===
    LIDAR_numpy_test = np.zeros(len(indices_zone), dtype=[
        ('x', np.float64),
        ('y', np.float64),
        ('z', np.float64),
        ('classification', np.uint8)
    ])
    LIDAR_numpy_test['x'] = x_final
    LIDAR_numpy_test['y'] = y_final
    LIDAR_numpy_test['z'] = z_final
    LIDAR_numpy_test['classification'] = classification_final

    return LIDAR_numpy_test



# === Lancement du script ===

if __name__ == "__main__":

    # === Configuration du fichier de test ===
    nom_fichier = "sample.laz"   # Remplacer par le nom du fichier .laz souhaité
    file_path = DATA_DIR / nom_fichier

    # Vérification de sécurité
    if not file_path.exists():
        print(f"ERREUR : Le fichier {nom_fichier} est introuvable dans {DATA_DIR}")
        print("Veuillez placer un fichier .laz dans le dossier 'data'.")
        sys.exit(1) 

    print(f"Traitement du fichier : {nom_fichier}\n")

    # === TEST 1 : Échantillonnage aléatoire carré ===
    nb_points_test = 1000000000          # Nombre de points souhaités
    taille_zone_test = 100               # Taille (en mètres) du carré d’échantillonnage

    print("\n=== TEST 1 : LIDAR_carre_aleatoire (zone carrée aléatoire) ===")

    LIDAR_numpy_test = LIDAR_carre_aleatoire(file_path, nb_points_test, taille_zone_test)

    print(f"Nombre de points retenus : {len(LIDAR_numpy_test)}")
    print(f"Taille de la zone : {taille_zone_test}x{taille_zone_test} m")
    print(f"\n{LIDAR_numpy_test}\n")


    # === TEST 2 : Échantillonnage rectangulaire défini ===
    nb_points_rect = 1000000000           # Nombre de points souhaités
    x_min_coin = 669680.0                 # Exemple de coordonnée X du coin Sud-Ouest
    y_min_coin = 6860143.0                # Exemple de coordonnée Y du coin Sud-Ouest
    longueur_x = 150                      # Longueur (Est-Ouest)
    longueur_y = 100                      # Hauteur (Nord-Sud)

    print("\n=== TEST 2 : LIDAR_rectangle (zone rectangulaire définie) ===")

    LIDAR_numpy_rect = LIDAR_rectangle(file_path, nb_points_rect, x_min_coin, y_min_coin, longueur_x, longueur_y)

    print(f"Nombre de points retenus : {len(LIDAR_numpy_rect)}")
    print(f"Taille du rectangle : {longueur_x}x{longueur_y} m")
    print(f"\n{LIDAR_numpy_rect}\n")
    