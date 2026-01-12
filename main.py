# ==========================================
# ===  CONFIGURATION DE L'ENVIRONNEMENT  ===
# ==========================================

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
sys.path.append(str(SRC_DIR))

try:
    from affichage_LIDAR import (afficher_bornes_zone, 
        afficher_coordonnees_systeme, 
        afficher_header, 
        afficher_infos_fichier, 
        afficher_conversion, 
        afficher_attributs_points
    )
    from import_LIDAR import laz_to_las
    from LIDAR_numpy import LIDAR_numpy_utile
    from donnees_echantillonnees_LIDAR import LIDAR_rectangle, LIDAR_carre_aleatoire
    from LIDAR_couches import LIDAR_couches_LEGO_LDRAW
    from LIDAR_LDRAW import voxel_LDRAW, voxel_LDRAW_classif
    from LIDAR_traitement import (
        voxel_graphe, 
        corriger_voxels_non_classes_iteratif, 
        graphe_filtre_classes, 
        graphe_filtre_sol,
        ajouter_sol_coque_pillier,
        ajouter_sol_coque,   
        ajouter_sol_rempli,  
        remplir_trous_verticaux, 
        graphe_voxel
    )
    import brique_merge
    import merge 
    from merge import Brick
    from cost_function import total_cost_function
    from brique_merge import bricks_from_ldr, bricks_from_numpy
    from solver import solve_greedy_stripe, export_to_ldr, print_brick_stats

except ImportError as e:
    print(f"\n[ERREUR] Impossible d'importer les modules : {e}")
    print(f"Vérifiez que le dossier 'src' contient bien tous les fichiers .py nécessaires.\n")
    sys.exit(1)



# ==========================================
# ===      PARAMÈTRES UTILISATEUR        ===
# ==========================================

# 1. FICHIER D'ENTRÉE
# -------------------
NOM_FICHIER = "exemple.laz"      # Nom du fichier .laz à traiter (doit être dans le dossier 'data')

# 2. MODE D'IMPORT
# ---------------------------
# "AFFICHAGE_INFO_LIDAR" :          Affichage des informations du fichier LIDAR
# "COMPLET" :                       Chargement complet du fichier LIDAR
# "ECHANTILLON_CARRE_ALEATOIRE" :   Chargement d'un échantillon aléatoire en zone carrée
# "ECHANTILLON_RECTANGLE" :         Chargement d'un échantillon dans une zone rectangulaire définie
MODE_IMPORT = "ECHANTILLON_RECTANGLE"

# Si MODE_IMPORT = "ECHANTILLON_CARRE_ALEATOIRE" :
# Renseignez ici les paramètres
NB_POINTS_ALEATOIRE = 1000000000    # Nombre de points max à récupérer
TAILLE_ZONE_ALEATOIRE = 50          # Taille de la zone carrée en mètres
   
# Si MODE_IMPORT = "ECHANTILLON_RECTANGLE" :
# Renseignez ici les paramètres
NB_POINTS_RECTANGLE = 1000000000    # Nombre de points max à récupérer
X_MIN_RECTANGLE = 669680.0          # Coordonnée X du coin bas gauche du rectangle échantillonné
Y_MIN_RECTANGLE = 6860143.0         # Coordonnée Y du coin bas gauche du rectangle échantillonné
LONGUEUR_X_RECTANGLE = 150          # Longueur en x dans la direction Est-Ouest en mètres
LONGUEUR_Y_RECTANGLE = 100          # Longueur en y dans la direction Nord-Sud en mètres

# 3. WORKFLOW DE GÉNÉRATION
# -------------------------
# "ETAPE_PAR_ETAPE" : Génère 3 dossiers (1_Apres_Voxelisation, 2_Apres_Traitement_Structurel, 3_Resultat_Final) avec les exports intermédiaires.
# "DIRECT"          : Ne génère que le résultat final optimisé dans un dossier 'Resultat_Final'.
MODE_WORKFLOW = "ETAPE_PAR_ETAPE"

# 4. OPTIONS DE VISUALISATION
# ---------------------------
# "COULEUR" : Maquette avec briques colorées selon la classification LiDAR 
# "GRIS"    : Maquette monochrome (Gris standard)
VISUALISATION = "COULEUR"

# Si VISUALISATION = "COULEUR", choisir le mode de rendu :
# "STANDARD" : Couleurs proches de la palette officielle LEGO 
# "HEX"      : Couleurs en Hexadécimal réglables à la ligne 173 de ce script
MODE_COULEUR = "STANDARD"

# 5. PARAMÈTRES DE VOXELISATION
# -----------------------------
TAILLE_VOXEL = 1.0    # Résolution des voxels en mètres
LDRAW_RATIO = 1.2     # Ratio de conversion LEGO (résolution/hauteur)
DENSITE_MIN = 1       # Densité minimale de points par voxel pour être pris en compte  

# 6. INVENTAIRE DES BRIQUES AUTORISÉES 
# ------------------------------------
# Définissez ici les tailles de briques qui vont être utilisées (Largeur, Longueur)
INVENTAIRE_BRIQUES = {
    # --- Briques 1.x ---
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (1, 8),
    
    # --- Briques 2.x ---
    (2, 2), (2, 3), (2, 4), (2, 6),
    
    # --- Inverses (nécessaire pour la logique de rotation) ---
    (2, 1), (3, 1), (4, 1), (6, 1), (8, 1),
    (3, 2), (4, 2), (6, 2)
}

# 7. CONFIGURATION DES TRAITEMENTS STRUCTURELS
# --------------------------------------------
# Activez (True) ou désactivez (False) les étapes et réglez leurs paramètres

# A. Correction des voxels non classés 
ACTIVER_CORRECTION_NC = True
PARAM_CORRECTION = {
    "class_non_classe": 1, 
    "classes_a_propager": [6], # Propager le Bati (6) sur le non-classé
    "class_sol": 2, 
    "max_iter": 5
}

# B. Filtrage des classes 
ACTIVER_FILTRE_CLASSES = True
PARAM_FILTRE_CLASSES = {
    # 1:Non Classé, 2:Sol, 3:Végétation basse, 4:Végétation moyenne, 5:Végétation haute, 6:Bati, 9:Eau, 17:Tablier de pont, 64:Sursol pérenne, 66:Points virtuels, 67:Divers - bâtis
    "classes_gardees": [1, 2, 3, 4, 5, 6, 9, 17, 64, 66, 67] 
}

# C. Suppression du bruit volant 
ACTIVER_FILTRE_SOL = True
PARAM_FILTRE_SOL = {
    "class_sol": 2
}

# D. Consolidation du sol 
# Choix : "PILIERS" (Recommandé), "COQUE" (Économique), "REMPLI" (Massif), "AUCUN"
TYPE_CONSOLIDATION = "PILIERS" 
PARAM_CONSOLIDATION = {
    "class_sol": 2, 
    "class_bat": 6, 
    "n_min": 2,
    "pillar_step": 4,  # Uniquement utilisé si mode PILIERS
    "pillar_width": 2  # Uniquement utilisé si mode PILIERS
}

# E. Remplissage des murs 
ACTIVER_REMPLISSAGE_MURS = True
PARAM_REMPLISSAGE = {
    "classes_batiment": [6]
}

# 8. CALCUL DE LA SOLIDITÉ STRUCTURELLE
# --------------------------------------------
# Activez (True) ou désactivez (False) cette étape.
# Calculer le score de solidité (peut être long sur gros modèles)
CALCULER_COUT_STRUCTUREL = True



# ==========================================
# ===    CONFIGURATION DYNAMIQUE         ===
# ==========================================

def configurer_couleurs():
    """Injecte la palette de couleur choisie dans le module brique_merge."""
    if VISUALISATION == "GRIS":
        return 

    if MODE_COULEUR == "HEX":
        MAP_HEX = {
            1: 0x2000000,   # Noir
            2: 0x28B4513,   # Marron 
            3: 0x27CFC00,   # Vert pelouse 
            4: 0x2008000,   # Vert 
            5: 0x2006400,   # Vert Sombre 
            6: 0x2808080,   # Gris 
            9: 0x20000FF,   # Bleu 
            17:0x2FF0000,   # Rouge
            64:0x2FFA500,   # Orange
            66:0x2FFFFFF,   # Blanc
            67:0x2FFFF00,   # Jaune
        }
        brique_merge.LIDAR_TO_LEGO_COLORS = MAP_HEX
        
    else:
        MAP_STD = {
            1: 0,   # Black
            2: 6,   # Brown
            3: 10,  # Bright Green
            4: 2,   # Green
            5: 288, # Dark Green
            6: 7,   # Light Gray
            9: 1,   # Blue
            17: 4,  # Red
            64: 14, # Yellow
            66: 15, # White
            67: 8,  # Dark Gray
        }
        brique_merge.LIDAR_TO_LEGO_COLORS = MAP_STD

def configurer_inventaire():
    """Injecte l'inventaire utilisateur dans le module merge."""
    merge.VALID_SIZES = INVENTAIRE_BRIQUES



# ==========================================
# ===      FONCTIONS UTILITAIRES         ===
# ==========================================

def exporter_modele(counts, class_maj, chemin_sortie):
    """Fonction utilitaire pour gérer le choix Couleur/Gris"""
    if VISUALISATION == "COULEUR":
        voxel_LDRAW_classif(counts, class_maj, nom_fichier=str(chemin_sortie))
    else:
        voxel_LDRAW(counts, nom_fichier=str(chemin_sortie))




# ==========================================
# ===       EXECUTION PRINCIPALE         ===
# ==========================================

if __name__ == "__main__":

    # === A. Initialisation ===
    fichier_entree = DATA_DIR / NOM_FICHIER

    # Configuration des modules dynamiques
    configurer_couleurs()
    configurer_inventaire()
    
    # Gestion des dossiers de sortie selon le Workflow
    dossiers = {}
    if MODE_WORKFLOW == "ETAPE_PAR_ETAPE":
        dossiers["1"] = OUTPUT_DIR / "1_Apres_Voxelisation"
        dossiers["2"] = OUTPUT_DIR / "2_Apres_Traitement_Structurel"
        dossiers["3"] = OUTPUT_DIR / "3_Resultat_Final"
    else:
        dossiers["FINAL"] = OUTPUT_DIR / "Resultat_Final"

    # Création des dossiers
    for path in dossiers.values():
        os.makedirs(path, exist_ok=True)

    if not fichier_entree.exists():
        print(f"[ERREUR] Le fichier {NOM_FICHIER} est introuvable dans {DATA_DIR}")
        sys.exit(1) 

    print(f"\n=== DÉMARRAGE DU TRAITEMENT : {NOM_FICHIER} ===")
    print(f"   Mode d'import : {MODE_IMPORT}")
    if MODE_IMPORT != "AFFICHAGE_INFO_LIDAR":
        print(f"   Mode workflow : {MODE_WORKFLOW}")
        print(f"   Visuel        : {VISUALISATION}")
        if VISUALISATION == "COULEUR":
            print(f"   Mode couleur  : {MODE_COULEUR}")



    print("\n==================================================================\n")



    # === B. Import et Chargement des Données ===
    print("1. Chargement des données...")

    if MODE_IMPORT == "AFFICHAGE_INFO_LIDAR":
        # Affichage des informations du fichier LIDAR
        las = laz_to_las(str(fichier_entree))
        afficher_header(las)
        afficher_coordonnees_systeme(las)
        afficher_bornes_zone(las)
        afficher_infos_fichier(las)
        afficher_conversion(las)
        afficher_attributs_points(las)
        print("\nNombre total de points :", len(las.points))  
        sys.exit(0)

    elif MODE_IMPORT == "COMPLET":
        # Chargement complet
        las = laz_to_las(str(fichier_entree))
        lidar_data = LIDAR_numpy_utile(las)
        suffixe = "COMPLET"

    elif MODE_IMPORT == "ECHANTILLON_CARRE_ALEATOIRE": 
        # Chargement échantillonné (Zone Carrée Aléatoire)
        lidar_data = LIDAR_carre_aleatoire(
            str(fichier_entree), 
            nb_points=NB_POINTS_ALEATOIRE,
            taille_zone=TAILLE_ZONE_ALEATOIRE
        )
        suffixe = "ECHANTILLON-CARRE-ALEATOIRE"

    elif MODE_IMPORT == "ECHANTILLON_RECTANGLE": 
        # Chargement échantillonné (Zone Rectangle)
        lidar_data = LIDAR_rectangle(
            str(fichier_entree), 
            nb_points=NB_POINTS_RECTANGLE, 
            x_min_coin=X_MIN_RECTANGLE,
            y_min_coin=Y_MIN_RECTANGLE,
            longueur_x=LONGUEUR_X_RECTANGLE,
            longueur_y=LONGUEUR_Y_RECTANGLE
        )
        suffixe = "ECHANTILLON-RECTANGLE"

    if len(lidar_data) == 0:
        print(f"[STOP] Aucun point récupéré (vérifiez les coordonnées du mode ECHANTILLON_RECTANGLE).")
        sys.exit(1)       
    print(f"   -> {len(lidar_data)} points chargés.")



    print("\n==================================================================\n")



    # === C. Voxelisation Initiale ===
    print(f"2. Voxelisation...")
    counts, class_maj = LIDAR_couches_LEGO_LDRAW(
        lidar_data, 
        taille_xy=TAILLE_VOXEL, 
        lego_ratio=LDRAW_RATIO, 
        densite_min=DENSITE_MIN
    )

    # Export visuel AVANT traitement (seulement si étape par étape)
    if MODE_WORKFLOW == "ETAPE_PAR_ETAPE":
        print("   -> Exportation du modèle brut (Voxels)...")
        nom_brut = f"01_BRUT_{NOM_FICHIER}_{suffixe}_{VISUALISATION}.ldr"
        exporter_modele(counts, class_maj, dossiers["1"] / nom_brut)



    print("\n==================================================================\n")



    # === D. Traitements Structurels (Graphes) ===
    print("3. Analyse et Traitement Structurel...")
    
    # 1. Création du graphe
    G = voxel_graphe(counts, class_maj)

    # 2. Correction voxels 
    if ACTIVER_CORRECTION_NC:
        print("   -> Correction des voxels non classés...")
        G = corriger_voxels_non_classes_iteratif(G, **PARAM_CORRECTION)
    
    # 3. Filtrage
    if ACTIVER_FILTRE_CLASSES:
        print("   -> Filtrage des classes indésirables...")
        G = graphe_filtre_classes(G, **PARAM_FILTRE_CLASSES)
    
    # 4. Supression bruit volant
    if ACTIVER_FILTRE_SOL:
        print("   -> Suppression du bruit volant (Filtrage Sol)...")
        G = graphe_filtre_sol(G, **PARAM_FILTRE_SOL)
    
    # 5. Consolidation du sol 
    if TYPE_CONSOLIDATION != "AUCUN":
        print(f"   -> Consolidation du sol (Mode: {TYPE_CONSOLIDATION})...")
        
        p_sol = PARAM_CONSOLIDATION["class_sol"]
        p_bat = PARAM_CONSOLIDATION["class_bat"]
        p_nmin = PARAM_CONSOLIDATION["n_min"]

        if TYPE_CONSOLIDATION == "PILIERS":
            step = PARAM_CONSOLIDATION.get("pillar_step")
            pillar_width = PARAM_CONSOLIDATION.get("pillar_width")
            G = ajouter_sol_coque_pillier(G, class_sol=p_sol, class_bat=p_bat, n_min=p_nmin, pillar_step=step, pillar_width=pillar_width)
        
        elif TYPE_CONSOLIDATION == "COQUE":
            G = ajouter_sol_coque(G, class_sol=p_sol, class_bat=p_bat, n_min=p_nmin)
            
        elif TYPE_CONSOLIDATION == "REMPLI":
            G = ajouter_sol_rempli(G, class_sol=p_sol, class_bat=p_bat, n_min=p_nmin)

    # 6. Remplissage des murs 
    if ACTIVER_REMPLISSAGE_MURS:
        print("   -> Consolidation : Remplissage des murs...")
        G = remplir_trous_verticaux(G, **PARAM_REMPLISSAGE)

    # 7. Conversion inverse (Graphe -> Grille)
    counts_traite, class_maj_traite = graphe_voxel(G)

    # Export visuel APRES traitement (seulement si étape par étape)
    if MODE_WORKFLOW == "ETAPE_PAR_ETAPE":
        print("   -> Exportation du modèle structuré (Voxels traités)...")
        nom_struct = f"02_STRUCTURE_{NOM_FICHIER}_{suffixe}_{VISUALISATION}.ldr"
        exporter_modele(counts_traite, class_maj_traite, dossiers["2"] / nom_struct)



    print("\n==================================================================\n")



    # === E. Optimisation & Merging ===
    print("4. Optimisation & Merging...")

    # 1. Conversion des voxels traités en objets Brick 
    print("   -> Conversion : Voxels -> Briques unitaires...")
    raw_bricks = bricks_from_numpy(counts_traite, class_maj_traite, visualisation=VISUALISATION)
    print(f"      ({len(raw_bricks)} briques à optimiser)")

    # Coût structurel avant l'algorithme
    if CALCULER_COUT_STRUCTUREL:
        c_init = total_cost_function(raw_bricks)
        print(f"   -> Score de solidité initial : {c_init:.1f}")

    # 2. Exécution du Solver Glouton (Greedy Stripe)
    print("   -> Exécution de l'algorithme d'assemblage...")
    final_bricks = solve_greedy_stripe(raw_bricks)

    # Coût structurel après l'algorithme
    if CALCULER_COUT_STRUCTUREL:
        c_final = total_cost_function(final_bricks)
        gain = c_init - c_final
        print(f"   -> Score de solidité final   : {c_final:.1f}")
        print(f"   -> Gain de solidité          : +{gain:.1f} points")

    # 3. Statistiques finales
    print(f"   -> Statistiques finales des briques...")
    print_brick_stats(final_bricks)

    # 4. Export Final
    nom_final = f"03_FINAL_{NOM_FICHIER}_{suffixe}_{VISUALISATION}.ldr"
    
    if MODE_WORKFLOW == "ETAPE_PAR_ETAPE":
        chemin_final = dossiers["3"] / nom_final
    else:
        chemin_final = dossiers["FINAL"] / nom_final

    print(f"   -> Génération du fichier : {chemin_final}")
    export_to_ldr(final_bricks, str(chemin_final))



    print("\n==================================================================\n")
    


    print(f"=== TRAITEMENT TERMINÉ ===")
    if MODE_WORKFLOW == "ETAPE_PAR_ETAPE":
        print(f"1. Voxelisation : {dossiers['1']}")
        print(f"2. Structure    : {dossiers['2']}")
        print(f"3. Final Lego   : {dossiers['3']}")
    else:
        print(f"Résultat final  : {dossiers['FINAL']}")