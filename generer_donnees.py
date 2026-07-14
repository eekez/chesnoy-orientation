import pandas as pd
import json
import math
import os
import re
from thefuzz import process as fuzz_process

def safe_isnan(val):
    return isinstance(val, float) and math.isnan(val)

def safe_str(val):
    return "" if pd.isna(val) else str(val).strip()

# ================================================================
# LECTURE DES STATISTIQUES DEPUIS L'ONGLET "Stats"
# ================================================================
# Toutes les données de sélectivité viennent d'un seul onglet Excel.
#
# Colonnes de l'onglet (ligne 2 = en-tête, ligne 3 = descriptions) :
#   Nom_Excel   → nom de l'école tel qu'il apparaît dans l'onglet "Ecoles"
#   Filiere     → BCPST, TB ou G2E
#   Specialite  → libellé de la spécialité (laisser vide si pas de spécialité)
#   Rg_median   → rang médian des intégrés (source : scei-concours.fr)
#   Dernier     → rang du dernier intégré  (source : rapport jury PDF)
#   N_integres  → nombre d'intégrés
#   Concours    → classement de référence (BCPST, TB, Polytech Réseau, Concours ENSTIB…)
#
# ── MISE À JOUR ANNUELLE (juin, ~30 min) ──────────────────────────
# 1. Ouvrir anciens_eleves.xlsx → onglet "Stats"
# 2. Mettre à jour colonne "Rg_median" depuis :
#    https://www.scei-concours.fr/stat[ANNEE]/bcpst.html  (BCPST)
#    https://www.scei-concours.fr/stat[ANNEE]/tb.html     (TB)
# 3. Mettre à jour colonne "Dernier" depuis les rapports PDF :
#    BCPST/TB : concours-agro-veto.fr  (bilan_general_[ANNEE]-cpge-bcpst.pdf)
#    G2E      : concoursg2e.univ-lorraine.fr (rapport-[ANNEE]-1.pdf)
# 4. Ajuster "N_integres" si nécessaire
# 5. Ajouter des lignes pour les nouvelles écoles / supprimer les absentes
# 6. Relancer ce script

def lire_stats(excel_path):
    """
    Lit l'onglet Stats et retourne un dict :
      { nom_excel : { "BCPST": [...], "TB": [...], "G2E": [...] } }
    où chaque liste contient :
      { "spec": str|None, "rg_median": int|None, "dernier": int|None,
        "n": int, "concours": str }
    """
    try:
        df = pd.read_excel(excel_path, sheet_name="Stats", header=1, skiprows=[2])
    except Exception as e:
        print(f"  ⚠️  Onglet 'Stats' absent ({e}) — sélectivité ignorée.")
        return {}

    cols_req = {"Nom_Excel", "Filiere"}
    if not cols_req.issubset(set(df.columns)):
        print(f"  ⚠️  Colonnes manquantes dans 'Stats' : {cols_req - set(df.columns)}")
        return {}

    rangs = {}
    for _, row in df.iterrows():
        nom     = safe_str(row.get("Nom_Excel", ""))
        fil     = safe_str(row.get("Filiere", "")).upper()
        spec    = safe_str(row.get("Specialite", "")) or None
        concours= safe_str(row.get("Concours", "")) or fil

        if not nom or not fil:
            continue

        def to_int(v):
            try: return int(float(v)) if not pd.isna(v) else None
            except: return None

        rg_med  = to_int(row.get("Rg_median"))
        dernier = to_int(row.get("Dernier"))
        n_int   = to_int(row.get("N_integres")) or 0

        if rg_med is None and dernier is None:
            continue  # ligne vide → ignorer

        if nom not in rangs:
            rangs[nom] = {}
        if fil not in rangs[nom]:
            rangs[nom][fil] = []

        # 1 seul intégré → médian = dernier
        if n_int == 1 and dernier is not None:
            rg_med = dernier

        rangs[nom][fil].append({
            "spec":      spec,
            "rg_median": rg_med,
            "dernier":   dernier,
            "n":         n_int,
            "concours":  concours,
        })

    print(f"  ✅ Sélectivité : {len(rangs)} écoles lues dans l'onglet 'Stats'")
    return rangs


def construire_specs(specs_list):
    """
    Prend la liste brute de l'onglet Stats pour une école+filière
    et retourne la liste formatée pour data.js, triée par rang dernier.
    """
    if not specs_list:
        return None
    resultat = []
    for s in specs_list:
        resultat.append({
            "spec":      s["spec"],
            "rg_median": s["rg_median"],
            "dernier":   s["dernier"],
            "places":    s["n"],
            "concours":  s["concours"],
        })
    resultat.sort(key=lambda x: (x.get("dernier") or x.get("rg_median") or 9999))
    return resultat


# Types d'écoles sans données de sélectivité pertinentes
TYPES_SANS_RANG = {'Fac', 'INSA', 'ENS', 'Centrale', 'Centrale-Supélec', 'Mines-Pont', 'X-BIO', ''}

# ================================================================
# SCRIPT PRINCIPAL
# ================================================================
excel_path = "anciens_eleves.xlsx"

if not os.path.exists(excel_path):
    print(f"❌ Erreur : Le fichier {excel_path} est introuvable.")
    exit()

print("📖 Lecture du fichier Excel…")
eleves_BCPST = pd.read_excel(excel_path, sheet_name="Elèves_BCPST")
eleves_TB    = pd.read_excel(excel_path, sheet_name="Elèves_TB")
ecoles       = pd.read_excel(excel_path, sheet_name="Ecoles")

if 'Nom' in eleves_BCPST.columns and 'NOM' not in eleves_BCPST.columns:
    eleves_BCPST = eleves_BCPST.rename(columns={'Nom': 'NOM'})
if 'Nom' in eleves_TB.columns and 'NOM' not in eleves_TB.columns:
    eleves_TB = eleves_TB.rename(columns={'Nom': 'NOM'})

for col in ['Lien_Video', 'Lien_Fiche_Poste', 'Fonctionnaire']:
    if col not in eleves_BCPST.columns: eleves_BCPST[col] = ""
    if col not in eleves_TB.columns:    eleves_TB[col]    = ""

eleves = pd.concat([eleves_BCPST, eleves_TB], ignore_index=True)

print("\n📊 Chargement des statistiques de sélectivité…")
stats = lire_stats(excel_path)

donnees_web = []
avec_rang = sans_rang = 0

print("\n⚡ Traitement des écoles…")

for _, ecole in ecoles.iterrows():
    nom_ecole  = safe_str(ecole['Nom'])
    if not nom_ecole: continue
    type_bcpst = safe_str(ecole.get('Type_BCPST'))
    type_tb    = safe_str(ecole.get('Type_TB'))

    # GPS
    coords_raw = ecole.get("coords", "[0,0]")
    if isinstance(coords_raw, str):
        try:
            cleaned = re.sub(r'[‑–—−]', '-', coords_raw).replace(',', '.')
            nombres = re.findall(r'-?\d+\.\d+|-?\d+', cleaned)
            coords  = [float(nombres[0]), float(nombres[1])] if len(nombres) >= 2 else [0, 0]
        except:
            coords = [0, 0]
    else:
        coords = list(coords_raw) if isinstance(coords_raw, (list, tuple)) else [0, 0]

    # Anciens
    eleves_ecole  = eleves[eleves['École intégrée'] == nom_ecole]
    liste_anciens = []
    for _, eleve in eleves_ecole.iterrows():
        liste_anciens.append({
            "nom":              safe_str(eleve.get('NOM')),
            "prenom":           safe_str(eleve.get('Prénom')),
            "initiale_nom":     safe_str(eleve.get('Initiale NOM')),
            "annee":            int(eleve.get('Année')) if not safe_isnan(eleve.get('Année')) else 0,
            "classe":           safe_str(eleve.get('Classe')),
            "lien_video":       safe_str(eleve.get('Lien_Video')),
            "lien_fiche_poste": safe_str(eleve.get('Lien_Fiche_Poste')),
            "fonctionnaire":    safe_str(eleve.get('Fonctionnaire')),
        })

    # Sélectivité
    ecole_stats = stats.get(nom_ecole, {})
    specs_bcpst = construire_specs(ecole_stats.get('BCPST')) if type_bcpst not in TYPES_SANS_RANG else None
    specs_tb    = construire_specs(ecole_stats.get('TB'))    if type_tb    not in TYPES_SANS_RANG else None
    specs_g2e   = construire_specs(ecole_stats.get('G2E'))

    if specs_bcpst or specs_tb or specs_g2e:
        avec_rang += 1
    else:
        sans_rang += 1

    donnees_web.append({
        "nom":          nom_ecole,
        "ville":        safe_str(ecole.get('Ville')),
        "coords":       coords,
        "type_bcpst":   type_bcpst,
        "type_tb":      type_tb,
        "banque_bcpst": safe_str(ecole.get('Banque_BCPST')),
        "banque_tb":    safe_str(ecole.get('Banque_TB')),
        "descriptif":   safe_str(ecole.get('Descriptif')),
        "lien_site":    safe_str(ecole.get('Lien')),
        "image":        safe_str(ecole.get('image')),
        "specs_bcpst":  specs_bcpst,
        "specs_tb":     specs_tb,
        "specs_g2e":    specs_g2e,
        "anciens":      liste_anciens,
    })

with open('data.js', 'w', encoding='utf-8') as f:
    f.write("const ecolesData = " + json.dumps(donnees_web, ensure_ascii=False, indent=4) + ";")

total = sum(len(e['anciens']) for e in donnees_web)
print(f"\n✅ data.js généré : {len(donnees_web)} écoles, {total} anciens")
print(f"   ↳ {avec_rang} avec données de sélectivité  |  {sans_rang} sans")
