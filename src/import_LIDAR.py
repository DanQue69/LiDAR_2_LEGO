"""
=== Importer un fichier .laz en .las ===

Ce code permet de :
- Convertir un fichier .laz en .las.

"""

# === Importations ===

import laspy



# === Fonction principale ===

def laz_to_las(file_path):
    """Retourne le fichier .laz dézippé en .las"""

    # Lecture du fichier LiDAR
    las = laspy.read(str(file_path), laz_backend=laspy.LazBackend.Laszip)

    return las
    