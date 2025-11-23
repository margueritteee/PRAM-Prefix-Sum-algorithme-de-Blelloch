from flask import Flask, render_template, request #framework
import os   #interagir avec le système d'exploitation
from concurrent.futures import ProcessPoolExecutor # outil pour faire du parallélisme
import multiprocessing #naerfo shhal kayn coeurs fel pc 

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
    
    #utiliser parallèle seul ida kan n>100 
    use_parallel = n >= 100
    num_workers = min(multiprocessing.cpu_count(), n // 2) if use_parallel else 1
    #multiprocessing.cpu_count() => nombre de coeurs disponibles sur le PC
    #n//2=chaque worker calcule une paire, donc pas besoin de plus de n//2 workers
    #if use_parallel else 1 => si parallélisme désactivé, on utilise 1 seul processus (sequentiel)
    #PC avec 8 cœurs, n=200
    #min(8, 200//2) = min(8, 100) = 8 => On utilise 8 cœurs


# ========== PHASE 1: UP-SWEEP (ARBRE MONTANT) - PARALLÉLISÉ ========== 
    arbre_somme = [x.copy()]  #liste qui va contenir tous les niveaux de l'arbre "up-tree"
    niveau_courant = x.copy()  #tableau qu'on va réduire étape par étape pour construire les niveaux supérieurs
    #x = [2,3,-1,5]
    #arbre_somme = [[2,3,-1,5]]
    #niveau_courant = [2,3,-1,5]
    
    while len(niveau_courant) > 1: #ida kayn aktr mn element ndiro nv_suivant
        #cas parallele
        if use_parallel and len(niveau_courant) >= 100: #use_parallel boolean variable => true si la liste x est assez grande (≥100)
            #len(niveau_courant) = fait pas de parallélisme si le tableau est petit
            #ida kano les conditions f zouj kayn ndiro parallele
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
        else: #cas sequentiel nrml
            niveau_suivant = []
            for i in range(0, len(niveau_courant), 2): #parcours les i 2 b 2 (0,2,4,...)
                #Exemple [2,3,-1,5] :
                #i=0 → paire [2,3]
                #i=2 → paire [-1,5]
                if i + 1 < len(niveau_courant): #verifie ida kayn element suiv
                    #i=0 , 1<4 
                    niveau_suivant.append(niveau_courant[i] + niveau_courant[i + 1]) #nv_suiv=nv_cr[0]+nv_cr[1] >> [5,4]
                else:
                    niveau_suivant.append(niveau_courant[i]) #ida mknsh yb9a
        
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
        
        if use_parallel and len(niveau_courant) >= 50:
            # Parallélisation du down-sweep
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                args = [(i, niveau_courant, niveau_somme) for i in range(len(niveau_courant))]
                # Chaque worker calcule une paire [gauche, droite]
                resultats = list(executor.map(calc_down_sweep_pair, args))
                # Aplatir les résultats : [[g1,d1], [g2,d2]] -> [g1,d1,g2,d2]
                niveau_suivant = []
                for res in resultats:
                    niveau_suivant.extend(res)
        else:
            # Version séquentielle du down-sweep
            niveau_suivant = []
            for i in range(len(niveau_courant)):
                pos = i * 2  # position dans le niveau de somme
                parent_val = niveau_courant[i]
                
                if pos + 1 < len(niveau_somme):
                    # Calcul selon la méthode du professeur :
                    # gauche = parent - droite
                    gauche = parent_val - niveau_somme[pos + 1]
                    droite = parent_val
                    niveau_suivant.append(gauche)
                    niveau_suivant.append(droite)
                else:
                    # Dernier élément impair
                    niveau_suivant.append(parent_val)
        
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



# ROUTE FLASK
@app.route("/", methods=["GET", "POST"])
def index():
    input_numbers = ""
    somme_prefixe_resultat = []
    arbre_somme = []
    arbre_recon = []

    if request.method == "POST":
        input_numbers = request.form.get("numbers", "")
        try:
            numbers = [int(num.strip()) for num in input_numbers.split(",")]
            somme_prefixe_resultat, arbre_somme, arbre_recon = parallel_prefix_sum_prof(numbers)
        except ValueError:
            somme_prefixe_resultat = arbre_somme = arbre_recon = ["Erreur : entrez des nombres séparés par des virgules"]

    return render_template("index.html",
                           input_numbers=input_numbers,
                           S=somme_prefixe_resultat,
                           up_tree=arbre_somme,
                           down_tree=arbre_recon)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)