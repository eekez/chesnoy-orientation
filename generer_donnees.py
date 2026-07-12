import pandas as pd
import json
import ast
import math
import os
import re


def safe_isnan(val):
    return isinstance(val, float) and math.isnan(val)

def safe_str(val):
    return "" if pd.isna(val) else str(val).strip()

# Configuration du nom de votre fichier Excel
excel_path = "anciens_eleves.xlsx"

if not os.path.exists(excel_path):
    print(f"❌ Erreur : Le fichier {excel_path} est introuvable dans ce dossier.")
    exit()

print("📖 Lecture du fichier Excel...")

eleves_BCPST = pd.read_excel(excel_path, sheet_name="Elèves_BCPST")
eleves_TB    = pd.read_excel(excel_path, sheet_name="Elèves_TB")
ecoles       = pd.read_excel(excel_path, sheet_name="Ecoles")

# --- Normalisation des noms de colonnes ---
# L'onglet BCPST peut avoir 'Nom' (minuscule) selon la version Excel
if 'Nom' in eleves_BCPST.columns and 'NOM' not in eleves_BCPST.columns:
    eleves_BCPST = eleves_BCPST.rename(columns={'Nom': 'NOM'})
if 'Nom' in eleves_TB.columns and 'NOM' not in eleves_TB.columns:
    eleves_TB = eleves_TB.rename(columns={'Nom': 'NOM'})

# --- Colonnes optionnelles (créées vides si absentes) ---
for col in ['Lien_Video', 'Lien_Fiche_Poste', 'Fonctionnaire']:
    if col not in eleves_BCPST.columns:
        eleves_BCPST[col] = ""
    if col not in eleves_TB.columns:
        eleves_TB[col] = ""

# Fusion des deux listes d'élèves
eleves = pd.concat([eleves_BCPST, eleves_TB], ignore_index=True)

donnees_web = []

print("⚡ Traitement des écoles et association des élèves...")

for index, ecole in ecoles.iterrows():
    nom_ecole = safe_str(ecole['Nom'])
    if not nom_ecole:
        continue

# Gestion ultra-sécurisée des coordonnées GPS
    coords_raw = ecole.get("coords", "[0,0]")
    if isinstance(coords_raw, str):
        try:
            # 1. Remplacer tous les types de tirets (insécable, cadratin, moins mathématique) par un tiret standard
            cleaned_coords = re.sub(r'[‑–—−]', '-', coords_raw)

            # 2. Remplacer les virgules par des points (pour gérer la saisie décimale française)
            cleaned_coords = cleaned_coords.replace(',', '.')

            # 3. Extraire tous les nombres (positifs ou négatifs, entiers ou décimaux)
            nombres = re.findall(r'-?\d+\.\d+|-?\d+', cleaned_coords)

            if len(nombres) >= 2:
                coords = [float(nombres[0]), float(nombres[1])]
            else:
                print(f"⚠️ Coordonnées incomplètes pour {nom_ecole}: {coords_raw}")
                coords = [0, 0]
        except Exception as e:
            print(f"⚠️ Erreur de parsing GPS pour {nom_ecole}: {e}")
            coords = [0, 0]
    else:
        coords = list(coords_raw) if isinstance(coords_raw, (list, tuple)) else [0, 0]

    eleves_ecole = eleves[eleves['École intégrée'] == nom_ecole]
    liste_anciens = []

    for _, eleve in eleves_ecole.iterrows():
        liste_anciens.append({
            "nom":              safe_str(eleve.get('NOM')),
            "prenom":           safe_str(eleve.get('Prénom')),
            "initiale_nom":     safe_str(eleve.get('Initiale NOM')),
            "annee":            int(eleve.get('Année')) if not safe_isnan(eleve.get('Année')) else 0,
            "classe":           safe_str(eleve.get('Classe')),
            "lien_video":       safe_str(eleve.get('Lien_Video')),        # URL YouTube (témoignage vidéo)
            "lien_fiche_poste": safe_str(eleve.get('Lien_Fiche_Poste')), # URL PDF fiche de poste
            "fonctionnaire":    safe_str(eleve.get('Fonctionnaire')),     # "fonctionnaire" ou ""
        })

    donnees_web.append({
        "nom":          nom_ecole,
        "ville":        safe_str(ecole.get('Ville')),
        "coords":       coords,
        "type_bcpst":   safe_str(ecole.get('Type_BCPST')),
        "type_tb":      safe_str(ecole.get('Type_TB')),
        "banque_bcpst": safe_str(ecole.get('Banque_BCPST')),
        "banque_tb":    safe_str(ecole.get('Banque_TB')),
        "descriptif":   safe_str(ecole.get('Descriptif')),
        "lien_site":    safe_str(ecole.get('Lien')),
        "image":        safe_str(ecole.get('image')),
        "anciens":      liste_anciens,
    })

with open('data.js', 'w', encoding='utf-8') as f:
    f.write("const ecolesData = " + json.dumps(donnees_web, ensure_ascii=False, indent=4) + ";")

total = sum(len(e['anciens']) for e in donnees_web)
print(f"✅ data.js généré : {len(donnees_web)} écoles, {total} anciens")
