import warnings
# Messages sans gravité : openpyxl signale qu'il ne sait pas lire les listes déroulantes du classeur (il ne fait que LIRE, l'Excel n'est jamais modifié),
# et pandas annonce un changement futur sur la fusion des deux onglets d'élèves.
warnings.filterwarnings("ignore", message="Data Validation extension is not supported")
warnings.filterwarnings("ignore", category=FutureWarning)
import pandas as pd
import json
import math
import os
import re
import sys
import datetime
from thefuzz import process as fuzz_process

def safe_isnan(val):
    return isinstance(val, float) and math.isnan(val)

def safe_str(val):
    return "" if pd.isna(val) else str(val).strip()

DATES_INVALIDES = []   # valeurs de « Date_ajout » illisibles, signalées par le contrôle qualité

def date_iso(val):
    """Colonne facultative « Date_ajout » (date d'ajout d'un témoignage) -> « AAAA-MM-JJ », ou « » si absente."""
    if pd.isna(val) or str(val).strip() == '':
        return ""
    if hasattr(val, 'strftime'):                      # cellule Excel au format date
        return val.strftime('%Y-%m-%d')
    brut = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.datetime.strptime(brut, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    DATES_INVALIDES.append(brut)
    return ""

def liste_mots_cles(val):
    """Colonne « Mots_cles » de l'onglet Ecoles : « A ; B ; C. » -> ["A", "B", "C"]"""
    mots = [m.strip().rstrip('.').strip() for m in safe_str(val).split(';')]
    return [m for m in mots if m]

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
# CONTRÔLE QUALITÉ (exécuté avant l'écriture de data.js)
# ================================================================
# - ERREURS      : problèmes bloquants -> data.js N'EST PAS réécrit (l'ancien reste en place) et le script
#                  s'arrête avec un code d'erreur (visible dans GitHub Actions).
# - AVERTISSEMENTS : données incomplètes ou suspectes -> data.js est écrit, mais la liste s'affiche.
def controle_qualite(donnees_web, hors_carte, stats):
    erreurs, avert = [], []
    annee_max = datetime.date.today().year + 1
    ANNEE_MIN = 2011                      # le classeur commence en 2011
    CLASSES = {'BCPST', 'TB'}
    noms = [e['nom'] for e in donnees_web]

    def lien_ok(v):
        return v.lower().startswith(('http://', 'https://'))

    # ---------- Erreurs bloquantes ----------
    if not donnees_web:
        erreurs.append("Aucune école lue : onglet « Ecoles » vide, renommé ou colonne « Nom » absente ?")
    elif sum(len(e['anciens']) for e in donnees_web) == 0:
        erreurs.append("Aucun ancien rattaché à une école : colonne « École intégrée » ou onglets Elèves_* modifiés ?")
    doubles = sorted({n for n in noms if noms.count(n) > 1})
    if doubles:
        erreurs.append(f"École(s) en double dans l'onglet Ecoles : {doubles}")
    for e in donnees_web:
        lat, lon = e['coords']
        if (lat, lon) == (0, 0) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            erreurs.append(f"Coordonnées invalides pour « {e['nom']} » : {e['coords']} (colonne « coords »)")

    # ---------- Avertissements : écoles ----------
    def groupe(titre, liste):
        if liste:
            avert.append((titre, liste))

    groupe("École sans mots-clés (colonne « Mots_cles »)",  [e['nom'] for e in donnees_web if not e['mots_cles']])
    groupe("École sans descriptif",                          [e['nom'] for e in donnees_web if not e['descriptif']])
    groupe("École sans lien vers son site (colonne « Lien »)", [e['nom'] for e in donnees_web if not e['lien_site']])
    groupe("École sans image (colonne « image »)",           [e['nom'] for e in donnees_web if not e['image']])
    groupe("Lien de site cassé (ne commence pas par http) ou image illisible (ni http ni data:image)",
           [f"{e['nom']} : « {(e['lien_site'] if e['lien_site'] and not lien_ok(e['lien_site']) else e['image'])[:40]} »"
            for e in donnees_web
            if (e['lien_site'] and not lien_ok(e['lien_site']))
            or (e['image'] and not (lien_ok(e['image']) or e['image'].startswith('data:image')))])
    groupe("Mot-clé avec une virgule (séparateur attendu : « ; ») ou de plus de 60 caractères",
           [f"{e['nom']} : « {m[:60]} »" for e in donnees_web for m in e['mots_cles'] if ',' in m or len(m) > 60])
    inconnues_stats = sorted(n for n in stats if n not in set(noms))
    groupe("Nom de l'onglet « Stats » absent de l'onglet Ecoles (faute de frappe ?)", inconnues_stats)

    # ---------- Avertissements : anciens ----------
    tous = [(e['nom'], a) for e in donnees_web for a in e['anciens']] + \
           [(a.get('categorie', 'Hors carte'), a) for a in hors_carte]
    def ident(a):
        return f"{a.get('prenom', '?')} {a.get('initiale_nom', '')}. ({a.get('annee')} {a.get('classe')})"

    groupe("Année hors de la plage attendue (%d-%d)" % (ANNEE_MIN, annee_max),
           [f"{ident(a)} → {ec}" for ec, a in tous if not (ANNEE_MIN <= a.get('annee', 0) <= annee_max)])
    groupe("Classe inattendue (attendu : BCPST ou TB)",
           [f"{ident(a)} → {ec}" for ec, a in tous if a.get('classe') not in CLASSES])
    groupe("Lien vidéo ou fiche de poste qui ne commence pas par http(s)",
           [f"{ident(a)} → {ec}" for ec, a in tous
            if (a.get('lien_video') and not lien_ok(a['lien_video'])) or (a.get('lien_fiche_poste') and not lien_ok(a['lien_fiche_poste']))])
    vus, doublons = {}, []
    for ec, a in tous:
        cle = (a.get('prenom', '').lower(), a.get('initiale_nom', ''), a.get('annee'), a.get('classe'))
        if a.get('prenom') != 'Inconnu':
            if cle in vus:
                doublons.append(f"{ident(a)} → {vus[cle]} et {ec}" if vus[cle] != ec else f"{ident(a)} → {ec}")
            vus[cle] = ec
    groupe("Doublon possible (même prénom, initiale, année et classe)", doublons)
    n_inconnus = sum(1 for _, a in tous if a.get('prenom') == 'Inconnu')
    if n_inconnus:
        avert.append((f"{n_inconnus} ancien(s) sans prénom (affichés « Inconnu »)", []))

    # ---------- Dates d'ajout des vidéos (colonne facultative « Date_ajout ») ----------
    groupe("Date_ajout illisible (formats acceptés : 03/11/2026 ou 2026-11-03)", sorted(set(DATES_INVALIDES)))
    demain = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    groupe("Date_ajout dans le futur",
           [f"{ident(a)} → {ec} ({a['date_ajout']})" for ec, a in tous if a.get('date_ajout', '') > demain])
    groupe("Date_ajout renseignée mais pas de lien vidéo",
           [f"{ident(a)} → {ec}" for ec, a in tous if a.get('date_ajout') and not a.get('lien_video')])

    # ---------- Confidentialité ----------
    n_noms = sum(1 for e in donnees_web for a in e['anciens'] if a.get('nom'))
    if n_noms:
        avert.append((f"🔒 data.js est public et contient le NOM DE FAMILLE COMPLET de {n_noms} ancien(s)", []))

    return erreurs, avert


def afficher_controle(erreurs, avert, limite=8):
    print("\n🔎 Contrôle qualité")
    if not erreurs and not avert:
        print("   ✅ Aucun problème détecté")
    for titre, liste in avert:
        print(f"   ⚠️  {titre}" + (f" ({len(liste)})" if liste else ""))
        for x in liste[:limite]:
            print(f"        - {x}")
        if len(liste) > limite:
            print(f"        … et {len(liste) - limite} autre(s)")
    for err in erreurs:
        print(f"   ❌ {err}")

# ================================================================
# SCRIPT PRINCIPAL
# ================================================================
def norm(x):
    import unicodedata
    return unicodedata.normalize('NFD', str(x)).encode('ascii', 'ignore').decode().strip().lower() if not pd.isna(x) else ''

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

    # Destinations « Hors carte » (BUT, fac non précisée, sans nouvelles) : comptées dans les stats, jamais sur la carte
    if type_bcpst == 'Hors carte' or type_tb == 'Hors carte':
        continue

    # Anciens (comparaison insensible à la casse / aux accents)
    eleves_ecole  = eleves[eleves['École intégrée'].map(norm) == norm(nom_ecole)]
    liste_anciens = []
    for _, eleve in eleves_ecole.iterrows():
        liste_anciens.append({
            # Confidentialité : data.js est PUBLIC -> jamais le nom de famille complet, seulement l'initiale
            "prenom":           safe_str(eleve.get('Prénom')) or "Inconnu",
            "initiale_nom":     safe_str(eleve.get('NOM'))[:1].upper(),   # calculée depuis le nom (indépendante de la colonne B)
            "annee":            int(eleve.get('Année')) if not safe_isnan(eleve.get('Année')) else 0,
            "classe":           safe_str(eleve.get('Classe')),
            "lien_video":       safe_str(eleve.get('Lien_Video')),
            "date_ajout":       date_iso(eleve.get('Date_ajout')),        # facultatif : sert à signaler les nouvelles vidéos sur le site
            "lien_fiche_poste": safe_str(eleve.get('Lien_Fiche_Poste')),
            "fonctionnaire":    safe_str(eleve.get('Fonctionnaire')),
            "apres_ecole":      safe_str(eleve.get("Après l'école")),
            "cinq_demi":        safe_str(eleve.get('CinqDemi')).lower().startswith('oui'),
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
        "mots_cles":    liste_mots_cles(ecole.get('Mots_cles')),
        "specs_bcpst":  specs_bcpst,
        "specs_tb":     specs_tb,
        "specs_g2e":    specs_g2e,
        "anciens":      liste_anciens,
    })

# Étudiants hors carte : agrégés pour les stats ; jamais le nom de famille complet (le site est public)
hors_noms = {norm(e['Nom']): safe_str(e['Nom']) for _, e in ecoles.iterrows()
             if 'Hors carte' in (safe_str(e.get('Type_BCPST')), safe_str(e.get('Type_TB')))}
# « Sans nouvelles » reste anonyme ; les autres destinations hors carte apparaissent dans l'onglet Promotions
CATEGORIES_VISIBLES_PROMOS = None   # toutes les destinations hors carte apparaissent (prénom + initiale) dans Promotions
hors_carte = []
for _, el in eleves.iterrows():
    cat = hors_noms.get(norm(el.get('École intégrée')))
    if cat:
        d = {"annee": int(el.get('Année')) if not safe_isnan(el.get('Année')) else 0,
             "classe": safe_str(el.get('Classe')), "categorie": cat,
             "cinq_demi": safe_str(el.get('CinqDemi')).lower().startswith('oui')}
        if True:      # identité réduite (prénom + initiale), comme pour les étudiants de la carte
            d.update({"prenom": safe_str(el.get('Prénom')) or "Inconnu", "initiale_nom": safe_str(el.get('NOM'))[:1].upper(),
                      "fonctionnaire": safe_str(el.get('Fonctionnaire')), "lien_video": safe_str(el.get('Lien_Video')),
                      "lien_fiche_poste": safe_str(el.get('Lien_Fiche_Poste')), "apres_ecole": safe_str(el.get("Après l'école"))})
        hors_carte.append(d)
connus = {norm(e['nom']) for e in donnees_web} | set(hors_noms)
inconnus = sorted({safe_str(v) for v in eleves['École intégrée'] if norm(v) not in connus})
if inconnus:
    print("\n⚠️  'École intégrée' absente de l'onglet Ecoles (non affichée) :", inconnus)

erreurs_qc, avert_qc = controle_qualite(donnees_web, hors_carte, stats)
afficher_controle(erreurs_qc, avert_qc)
if erreurs_qc:
    print("\n⛔ Génération interrompue : data.js n'a PAS été modifié. Corrige les erreurs ci-dessus puis relance le script.")
    sys.exit(1)

with open('data.js', 'w', encoding='utf-8') as f:
    f.write("const ecolesData = " + json.dumps(donnees_web, ensure_ascii=False, indent=4) + ";\n")
    f.write("const etudiantsHorsCarte = " + json.dumps(hors_carte, ensure_ascii=False) + ";")

total = sum(len(e['anciens']) for e in donnees_web)
print(f"\n✅ data.js généré : {len(donnees_web)} écoles, {total} anciens")
print(f"   ↳ {avec_rang} avec données de sélectivité  |  {sans_rang} sans")
print(f"   ↳ {len(hors_carte)} étudiants hors carte (stats uniquement)")
