from flask import Flask, render_template, request #framework
import os   #interagir avec le système d'exploitation
from concurrent.futures import ProcessPoolExecutor # outil pour faire du parallélisme
import multiprocessing #naerfo shhal kayn coeurs fel pc 
import time #pour calculer le temps d'exécution
import tracemalloc #alternative plus rapide pour mesurer la mémoire

app = Flask(__name__, template_folder='interface', static_folder='interface')

# FONCTIONS POUR PARALLÉLISATION

def calc_tree_pair(args):
    """Calcule une paire pour l'arbre de somme (UP-SWEEP)"""
    i, niveau_courant = args #args = (0, [2, 3, -1, 5]) , args est un tuple 
    if i + 1 < len(niveau_courant):  #len([2, 3, -1, 5])=4 , i=0 => 0+1<4 
        return niveau_courant[i] + niveau_courant[i + 1] #nv_cr[0]+nv_cr[1]=2+3
    else:
        return niveau_courant[i] #tb9a nfs valeur 


def calc_down_sweep_pair(args):
    """Calcule une paire pour le DOWN-SWEEP (méthode du professeur)"""
    i, niveau_courant, niveau_somme = args
    # niveau_courant : valeurs du parent dans l'arbre descendant
    # niveau_somme : valeurs correspondantes dans l'arbre de somme
    pos = i * 2  # position dans le niveau de somme
    parent_val = niveau_courant[i]
    
    if pos + 1 < len(niveau_somme):
        # Gauche = parent - droite (méthode du professeur !)
        # exemple: si parent=53 et droite=49, alors gauche=53-49=4
        gauche = parent_val - niveau_somme[pos + 1]
        droite = parent_val
        return [gauche, droite]
    else:
        # Dernier élément impair reste seul
        return [parent_val]


# FONCTION PRINCIPALE AVEC UP-SWEEP ET DOWN-SWEEP PARALLÉLISÉS

def parallel_prefix_sum_prof(x): 
    n = len(x) #[2,3,-1,5] n=4
    if n == 0:
        return [], [], [] #ida kan x vide nrjaeo 3 tables vide (no data)
    
    if n == 1:
        # Si un seul élément, le prefix sum est lui-même
        return [x[0]], [x.copy()], [x.copy()]
    
    # Toujours utiliser le parallélisme (pas de cas séquentiel)
    num_workers = min(multiprocessing.cpu_count(), max(n // 2, 1))
    #multiprocessing.cpu_count() => nombre de coeurs disponibles sur le PC
    #n//2=chaque worker calcule une paire, donc pas besoin de plus de n//2 workers
    #max(n//2, 1) => minimum 1 worker même si n est très petit
    #PC avec 8 cœurs, n=200
    #min(8, 200//2) = min(8, 100) = 8 => On utilise 8 cœurs


# ========== PHASE 1: UP-SWEEP (ARBRE MONTANT) - PARALLÉLISÉ ========== 
    arbre_somme = [x.copy()]  #liste qui va contenir tous les niveaux de l'arbre "up-tree"
    niveau_courant = x.copy()  #tableau qu'on va réduire étape par étape pour construire les niveaux supérieurs
    #x = [2,3,-1,5]
    #arbre_somme = [[2,3,-1,5]]
    #niveau_courant = [2,3,-1,5]
    
    while len(niveau_courant) > 1: #ida kayn aktr mn element ndiro nv_suivant
        # Toujours en parallèle avec ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=num_workers) as executor: #ProcessPoolExecutor → outil de Python pour exécuter plusieurs fonctions en parallèle dans différents processus
            #max_workers=num_workers → nombre de processus simultanés, calculé avant en fonction du nombre de cœurs et de la taille du tableau
            #with ... as executor =>quand on sort du bloc, l'équipe est automatiquement fermée
            args = [(i, niveau_courant) for i in range(0, len(niveau_courant), 2)] #range(0, len(niveau_courant), 2): 0, 2, 4, 6, ... (tous les indices pairs) 
            #args = [(0, [2,3,-1,5]), (2, [2,3,-1,5])]
            niveau_suivant = list(executor.map(calc_tree_pair, args))
            #executor.map(fonction, arguments):applique la fonction à tous les arguments EN PARALLELE
            #calc_tree_pair((0, [2,3,-1,5])) = 2+3 = 5
            #calc_tree_pair((2, [2,3,-1,5])) = -1+5 = 4
            #niveau_suivant = [5,4] 
        
        arbre_somme.append(niveau_suivant) #on ajoute le niveau calculé à l'arbre
        niveau_courant = niveau_suivant #pour l'itération suivante, niveau_courant devient ce nouveau niveau
    
    # Exemple avec x = [-1, 3, 7, -5, 3, 17, 8, 21]:
    # arbre_somme = [
    #   [-1, 3, 7, -5, 3, 17, 8, 21],  # Niveau 0 (feuilles)
    #   [2, 2, 20, 29],                 # Niveau 1
    #   [4, 49],                        # Niveau 2
    #   [53]                            # Niveau 3 (racine = somme totale)
    # ]


# ========== PHASE 2: DOWN-SWEEP (ARBRE DESCENDANT) - PARALLÉLISÉ ========== 
    # Méthode du professeur : on part de la racine (somme totale) et on descend
    # À chaque niveau : valeur_gauche = parent - valeur_droite
    
    arbre_recon = []
    niveau_courant = [arbre_somme[-1][0]]  # On commence avec la racine (somme totale)
    arbre_recon.append(niveau_courant.copy())
    
    # Exemple: niveau_courant = [53]
    # On va descendre niveau par niveau en appliquant : gauche = parent - droite
    
    # Parcourir l'arbre de somme de haut en bas (en inversant l'ordre)
    for depth in range(len(arbre_somme) - 2, -1, -1):
        niveau_somme = arbre_somme[depth]  # Le niveau correspondant dans l'arbre de somme
        
        # Toujours parallélisation du down-sweep
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            args = [(i, niveau_courant, niveau_somme) for i in range(len(niveau_courant))]
            # Chaque worker calcule une paire [gauche, droite]
            resultats = list(executor.map(calc_down_sweep_pair, args))
            # Aplatir les résultats : [[g1,d1], [g2,d2]] -> [g1,d1,g2,d2]
            niveau_suivant = []
            for res in resultats:
                niveau_suivant.extend(res)
        
        arbre_recon.append(niveau_suivant)
        niveau_courant = niveau_suivant
    
    # Exemple avec x = [-1, 3, 7, -5, 3, 17, 8, 21]:
    # arbre_recon = [
    #   [53],                           # Niveau 0 (racine)
    #   [4, 53],                        # Niveau 1: 53-49=4, 53
    #   [2, 4, 24, 53],                 # Niveau 2: 4-2=2, 4, 53-29=24, 53
    #   [-1, 2, 9, 4, 7, 24, 32, 53]    # Niveau 3: 2-3=-1, 2, 4-(-5)=9, 4, 24-17=7, 24, 53-21=32, 53
    # ]
    
    # Le dernier niveau de arbre_recon contient le prefix sum final !
    somme_prefixe = niveau_suivant

    return somme_prefixe, arbre_somme, arbre_recon


# FONCTION POUR ANALYSE COMPLÈTE DE COMPLEXITÉ
def analyse_complexite_complete(x):
    """
    Analyse complète avec mesure du temps et de la mémoire EN UN SEUL APPEL
    (optimisation pour éviter de calculer l'algorithme 2 fois)
    Retourne: (résultats, métriques_complexité)
    """
    n = len(x)
    if n == 0:
        return ([], [], []), None
    
    num_workers = min(multiprocessing.cpu_count(), max(n // 2, 1))
    
    # ========== MESURE TEMPS + MÉMOIRE EN UN SEUL APPEL (optimisation importante!) ==========
    tracemalloc.start()  #démarre le traçage de mémoire
    start_time = time.perf_counter()  #temps de début (plus précis que time.time())
    
    # Un seul appel à l'algorithme principal
    somme_prefixe, arbre_somme, arbre_recon = parallel_prefix_sum_prof(x)
    
    end_time = time.perf_counter()  #temps de fin
    current, peak = tracemalloc.get_traced_memory()  #peak = pic de mémoire utilisée
    tracemalloc.stop()  #arrête le traçage
    
    # ========== CALCULS DE COMPLEXITÉ ==========
    temps_execution = end_time - start_time  #temps total en secondes
    memoire_mesuree_mb = peak / (1024 * 1024)  #conversion bytes -> MB
    
    # Profondeur de l'arbre = nombre de niveaux - 1
    profondeur_arbre = len(arbre_somme) - 1
    
    # Nombre total d'éléments stockés dans les deux arbres
    elements_arbre_somme = sum(len(niveau) for niveau in arbre_somme)
    elements_arbre_recon = sum(len(niveau) for niveau in arbre_recon)
    total_elements = elements_arbre_somme + elements_arbre_recon
    
    # Estimation théorique (série géométrique)
    # arbre_somme: n + n/2 + n/4 + ... ≈ 2n éléments
    # arbre_recon: 1 + 2 + 4 + ... + n ≈ 2n éléments
    # Total théorique: ≈ 4n éléments
    espace_theorique_elements = 4 * n
    
    # Calcul de la mémoire théorique basée sur les éléments réels mesurés
    # On calcule combien de bytes prend chaque élément en moyenne
    bytes_par_element = peak / total_elements if total_elements > 0 else 28
    memoire_theorique_mb = (espace_theorique_elements * bytes_par_element) / (1024 * 1024)
    
    # Construction du dictionnaire de résultats
    complexity = {
        'taille_entree': n,  #taille du tableau d'entrée
        'nombre_workers': num_workers,  #nombre de processeurs utilisés
        'temps_execution_ms': round(temps_execution * 1000, 3),  #temps en millisecondes
        'profondeur_arbre': profondeur_arbre,  #log(n) = nombre de niveaux
        'complexite_temps': f'O((n/p) × log n) = O(({n}/{num_workers}) × {profondeur_arbre})',
        'memoire_mesuree_mb': round(memoire_mesuree_mb, 4),  #mémoire réelle mesurée
        'memoire_theorique_mb': round(memoire_theorique_mb, 4),  #mémoire théorique estimée
        'nombre_elements_stockes': total_elements,  #nombre total d'éléments dans les arbres
        'elements_arbre_somme': elements_arbre_somme,  #éléments dans up-tree
        'elements_arbre_recon': elements_arbre_recon,  #éléments dans down-tree
        'complexite_espace': 'O(n)',  #complexité en espace
        'formule_espace': f'≈ 4n = 4 × {n} = {espace_theorique_elements} éléments'
    }
    
    return (somme_prefixe, arbre_somme, arbre_recon), complexity


# ROUTE FLASK
@app.route("/", methods=["GET", "POST"])
def index():
    input_numbers = ""
    somme_prefixe_resultat = []
    arbre_somme = []
    arbre_recon = []
    complexity = None
    error_message = None

    if request.method == "POST":
        input_numbers = request.form.get("numbers", "")
        try:
            # Parser les nombres (enlever les espaces et filtrer les vides)
            numbers = [int(num.strip()) for num in input_numbers.split(",") if num.strip()]
            
            if not numbers:
                error_message = "Erreur : veuillez entrer au moins un nombre"
            else:
                # Calculer avec analyse de complexité (un seul appel optimisé!)
                (somme_prefixe_resultat, arbre_somme, arbre_recon), complexity = \
                    analyse_complexite_complete(numbers)
                
        except ValueError:
            error_message = "Erreur : entrez des nombres entiers séparés par des virgules"
            somme_prefixe_resultat = arbre_somme = arbre_recon = []

    return render_template("index.html",
                           input_numbers=input_numbers,
                           S=somme_prefixe_resultat,
                           up_tree=arbre_somme,
                           down_tree=arbre_recon,
                           complexity=complexity,
                           error_message=error_message)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)