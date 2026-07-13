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
# DONNÉES DES RAPPORTS OFFICIELS (rang premier / dernier intégré)
# ================================================================
# Source BCPST : concours-agro-veto.fr  (rapport PDF annuel)
# Source TB    : concours-agro-veto.fr  (rapport PDF annuel)
# Source G2E   : concoursg2e.univ-lorraine.fr (rapport PDF annuel)
#
# Format de chaque entrée :
#   "Nom SCEI exact" : {
#       "specs": [                          ← liste des spécialités (1 seule si pas de spécialité)
#           {"spec": None ou "libellé",
#            "premier": rang_premier_intégré,
#            "dernier": rang_dernier_intégré,
#            "n": nombre_intégrés}          ← facultatif
#       ]
#   }
#
# ⚠️  À mettre à jour chaque année (juin) en consultant les PDFs :
#   BCPST : https://www.concours-agro-veto.fr  (bilan_general_AAAA-cpge-bcpst.pdf)
#   TB    : https://www.concours-agro-veto.fr  (bilan_general_tb_AAAA.pdf)
#   G2E   : https://concoursg2e.univ-lorraine.fr (rapport-AAAA-1.pdf)

RANGS_OFFICIELS_BCPST = {
    # ── AGRO ──────────────────────────────────────────────────────────────────
    "AgroParisTech": {"specs": [
        {"spec": None, "premier": 19, "dernier": 721, "n": 274}
    ]},
    "Bordeaux Sciences Agro": {"specs": [
        {"spec": None, "premier": 810, "dernier": 1796, "n": 88}
    ]},
    "ENSAIA Nancy": {"specs": [
        {"spec": None, "premier": 767, "dernier": 2000, "n": 89}
    ]},
    "INP AgroToulouse": {"specs": [
        {"spec": None, "premier": 16, "dernier": 1768, "n": 88}
    ]},
    "ENSP Versailles": {"specs": [
        {"spec": None, "premier": 1984, "dernier": 1984, "n": 1}
    ]},
    "Institut Agro Dijon": {"specs": [
        {"spec": "Cursus agronome (civil)",        "premier": 296,  "dernier": 1824, "n": 30},
        {"spec": "Cursus agronome (fonctionnaire)","premier": 754,  "dernier": 2161, "n": 40},
        {"spec": "Cursus agroalimentaire",         "premier": 1094, "dernier": 2212, "n": 28},
    ]},
    "Institut Agro Montpellier": {"specs": [
        {"spec": "Cursus agronome",                "premier": 71,  "dernier": 1239, "n": 113},
        {"spec": "Cursus SAADS",                   "premier": 117, "dernier": 1240, "n": 11},
    ]},
    "Institut Agro Rennes-Angers (Rennes)": {"specs": [
        {"spec": "Cursus agronome",                "premier": 207,  "dernier": 1474, "n": 137},
    ]},
    "Institut Agro Rennes-Angers (Angers)": {"specs": [
        {"spec": "Cursus horticulture et paysage", "premier": 852,  "dernier": 2188, "n": 43},
    ]},
    "VetAgro Sup Clermont": {"specs": [
        {"spec": None, "premier": 997, "dernier": 2210, "n": 53}
    ]},
    "ONIRIS Nantes (alimentation)": {"specs": [
        {"spec": None, "premier": 489, "dernier": 2206, "n": 23}
    ]},
    # ── VETO ──────────────────────────────────────────────────────────────────
    "ENV Alfort": {"specs": [
        {"spec": None, "premier": 4,  "dernier": 282, "n": 68}
    ]},
    "VetAgro Sup Lyon": {"specs": [
        {"spec": None, "premier": 5,  "dernier": 306, "n": 68}
    ]},
    "ONIRIS Nantes (vétérinaire)": {"specs": [
        {"spec": None, "premier": 17, "dernier": 363, "n": 68}
    ]},
    "ENV Toulouse": {"specs": [
        {"spec": None, "premier": 11, "dernier": 295, "n": 68}
    ]},
    # ── PC BIO ────────────────────────────────────────────────────────────────
    "ENSMAC Bordeaux (agroalimentaire - génie biologique)": {"specs": [
        {"spec": None, "premier": None, "dernier": 684, "n": 9}
    ]},
    "ENSMAC Bordeaux (chimie - génie physique)": {"specs": [
        {"spec": None, "premier": None, "dernier": 453, "n": 5}
    ]},
    "ENSC Lille": {"specs": [
        {"spec": None, "premier": None, "dernier": 423, "n": 3}
    ]},
    "ENSC Montpellier": {"specs": [
        {"spec": None, "premier": None, "dernier": 197, "n": 2}
    ]},
    "Chimie ParisTech": {"specs": [
        {"spec": None, "premier": None, "dernier": 123, "n": 4}
    ]},
    "ESPCI Paris": {"specs": [
        {"spec": None, "premier": None, "dernier": 16, "n": 2}
    ]},
    "ENSIC Nancy": {"specs": [
        {"spec": None, "premier": None, "dernier": 522, "n": 3}
    ]},
    # ── POLYTECH BCPST ────────────────────────────────────────────────────────
    # (pas de rangs par école dans le rapport BCPST — voir Stats_BCPST SCEI)
    # ── X BIO ─────────────────────────────────────────────────────────────────
    "Ecole Polytechnique": {"specs": [
        {"spec": None, "premier": None, "dernier": None, "n": 13}
    ]},
}

RANGS_OFFICIELS_TB = {
    # ── TB AGRO ───────────────────────────────────────────────────────────────
    "AgroParisTech (TB)": {"specs": [
        {"spec": None, "premier": 8, "dernier": 47, "n": 12}
    ]},
    "Institut Agro Rennes-Angers (Rennes) TB": {"specs": [
        {"spec": "Cursus agronome", "premier": 1, "dernier": 30, "n": 4}
    ]},
    "Institut Agro Rennes-Angers (Angers) TB": {"specs": [
        {"spec": "Cursus horticulture et paysage", "premier": 93, "dernier": 102, "n": 2}
    ]},
    "Institut Agro Dijon TB": {"specs": [
        {"spec": "Cursus agroalimentaire", "premier": 23, "dernier": 99, "n": 3},
        {"spec": "Cursus agronome (civil)", "premier": 60, "dernier": 60, "n": 1},
    ]},
    "Bordeaux Sciences Agro TB": {"specs": [
        {"spec": None, "premier": 33, "dernier": 100, "n": 8}
    ]},
    "ENGEES TB": {"specs": [
        {"spec": None, "premier": 48, "dernier": 103, "n": 3}
    ]},
    "ENSAIA Nancy TB": {"specs": [
        {"spec": None, "premier": 38, "dernier": 97, "n": 10}
    ]},
    "INP AgroToulouse TB": {"specs": [
        {"spec": None, "premier": 15, "dernier": 55, "n": 8}
    ]},
    "Institut Agro Montpellier TB": {"specs": [
        {"spec": "Cursus agronome", "premier": 17, "dernier": 61, "n": 4},
        {"spec": "Cursus SAADS",    "premier": 52, "dernier": 101, "n": 6},
    ]},
    "ONIRIS Nantes (alimentation) TB": {"specs": [
        {"spec": None, "premier": 79, "dernier": 105, "n": 4}
    ]},
    "VetAgro Sup Clermont TB": {"specs": [
        {"spec": None, "premier": 31, "dernier": 98, "n": 5}
    ]},
    # ── TB VETO ───────────────────────────────────────────────────────────────
    "ENV Alfort (TB)": {"specs": [
        {"spec": None, "premier": 8, "dernier": 12, "n": 2}
    ]},
    "VetAgro Sup Lyon (TB)": {"specs": [
        {"spec": None, "premier": 5, "dernier": 10, "n": 2}
    ]},
    "ONIRIS Nantes (vétérinaire) TB": {"specs": [
        {"spec": None, "premier": 7, "dernier": 11, "n": 2}
    ]},
    "ENV Toulouse (TB)": {"specs": [
        {"spec": None, "premier": 2, "dernier": 6, "n": 3}
    ]},
}

RANGS_OFFICIELS_G2E = {
    # ── G2E (rangs sur classement G2E, différent du BCPST) ───────────────────
    "EIL Côte d'Opale": {"specs": [
        {"spec": None, "premier": 435, "dernier": 685, "n": 4}
    ]},
    "EIVP Civil": {"specs": [
        {"spec": None, "premier": 119, "dernier": 643, "n": 5}
    ]},
    "EIVP Apprenti": {"specs": [
        {"spec": None, "premier": 128, "dernier": 676, "n": 3}
    ]},
    "ENGEES Civil": {"specs": [
        {"spec": None, "premier": 51, "dernier": 383, "n": 8}
    ]},
    "ENGEES Fonctionnaire": {"specs": [
        {"spec": None, "premier": 36, "dernier": 441, "n": 18}
    ]},
    "ENM Fonctionnaire": {"specs": [
        {"spec": None, "premier": 200, "dernier": 473, "n": 6}
    ]},
    "ENSEGID Bordeaux": {"specs": [
        {"spec": None, "premier": 14, "dernier": 46, "n": 3}
    ]},
    "ENSG Nancy": {"specs": [
        {"spec": None, "premier": 132, "dernier": 499, "n": 20}
    ]},
    "ENSGéomatique civil": {"specs": [
        {"spec": None, "premier": 24, "dernier": 365, "n": 71}
    ]},
    "ENSGéomatique fonctionnaire": {"specs": [
        {"spec": None, "premier": 533, "dernier": 583, "n": 4}
    ]},
    "ENSIL-ENSCI (eau et environnement)": {"specs": [
        {"spec": None, "premier": 520, "dernier": 691, "n": 7}
    ]},
    "ENSIP (eau et génie civil)": {"specs": [
        {"spec": None, "premier": 557, "dernier": 678, "n": 7}
    ]},
    "ENSIP (génie de l'eau)": {"specs": [
        {"spec": None, "premier": 314, "dernier": 664, "n": 11}
    ]},
    "ENSIP (énergétique et environnement)": {"specs": [
        {"spec": None, "premier": 141, "dernier": 568, "n": 26}
    ]},
    "ENTPE Civil": {"specs": [
        {"spec": None, "premier": 215, "dernier": 581, "n": 20}
    ]},
    "ENTPE Fonctionnaire": {"specs": [
        {"spec": None, "premier": 8, "dernier": 353, "n": 14}
    ]},
    "EOST Strasbourg": {"specs": [
        {"spec": None, "premier": 441, "dernier": 686, "n": 3}
    ]},
    "ESGT": {"specs": [
        {"spec": None, "premier": 202, "dernier": 298, "n": 7}
    ]},
    "IMT Mines Albi": {"specs": [
        {"spec": None, "premier": 20, "dernier": 198, "n": 7}
    ]},
    "IMT Mines Alès": {"specs": [
        {"spec": None, "premier": 41, "dernier": 297, "n": 5}
    ]},
    "IMT Nord Europe": {"specs": [
        {"spec": None, "premier": 269, "dernier": 463, "n": 3}
    ]},
}

# Écoles Polytech/ISIFC/ENSTIB : pas de rapport jury officiel avec premier/dernier,
# mais présentes dans SCEI. On les stocke ici avec dernier=None pour n'afficher que le médian.
RANGS_OFFICIELS_POLYTECH = {
    "Enstib":                  {"specs": [{"spec": None, "dernier": None, "n": 13}]},
    "ESIAB":                   {"specs": [{"spec": "Microbiologie et Qualité / Production Biotechnologies", "dernier": None, "n": 5}]},
    "ESIR":                    {"specs": [{"spec": "Technologies de l'information pour la santé", "dernier": None, "n": 2}]},
    "ISIFC":                   {"specs": [{"spec": "Génie Biomédical", "dernier": None, "n": 13}]},
    "Polytech Angers":         {"specs": [{"spec": "Génie Biologique et Santé", "dernier": None, "n": 4}]},
    "Polytech Clermont":       {"specs": [{"spec": "Génie Biologique", "dernier": None, "n": 8}]},
    "Polytech Grenoble":       {"specs": [{"spec": "Géotechnique et génie civil", "dernier": None, "n": 2},
                                          {"spec": "Technologies de l'information pour la santé", "dernier": None, "n": 1}]},
    "Polytech Lille":          {"specs": [{"spec": "Génie biologique et alimentaire", "dernier": None, "n": 5}]},
    "Polytech Marseille":      {"specs": [{"spec": "Génie Biologique, Biotechnologie", "dernier": None, "n": 4},
                                          {"spec": "Génie Biomédical", "dernier": None, "n": 5}]},
    "Polytech Nantes":         {"specs": [{"spec": "Génie des Procédés et Bioprocédés", "dernier": None, "n": 3}]},
    "Polytech Nice":           {"specs": [{"spec": "Génie biologique", "dernier": None, "n": 12}]},
    "Polytech Orléans":        {"specs": [{"spec": "Génie industriel", "dernier": None, "n": 1}]},
    "Polytech Sorbonne":       {"specs": [{"spec": "Agroalimentaire", "dernier": None, "n": 5},
                                          {"spec": "Matériaux", "dernier": None, "n": 1},
                                          {"spec": "Sciences de la Terre", "dernier": None, "n": 2}]},
    "Polytech Tours":          {"specs": [{"spec": "Génie de l'aménagement et de l'environnement", "dernier": None, "n": 4}]},
    "EPISEN":                  {"specs": [{"spec": "Génie Biomédical et santé", "dernier": None, "n": 3}]},
    "ESBS":                    {"specs": [{"spec": None, "dernier": None, "n": 9}]},
}

# ================================================================
# Correspondance noms Excel → clés des tables de rangs
# ================================================================
# Seules les écoles présentes dans l'Excel ET dans les rapports
# sont listées ici. Compléter si de nouvelles écoles sont ajoutées.

CORRESPONDANCE_BCPST = {
    "AgroParisTech":                                 "AgroParisTech",
    "Bordeaux Sciences Agro":                        "Bordeaux Sciences Agro",
    "ENSAIA":                                        "ENSAIA Nancy",
    "ENSAT":                                         "INP AgroToulouse",
    "ENSP Versailles (Paysage)":                     "ENSP Versailles",
    "Institut Agro Dijon":                           "Institut Agro Dijon",
    "Institut Agro Montpellier":                     "Institut Agro Montpellier",
    "Institut Agro Rennes-Angers, campus Rennes":    "Institut Agro Rennes-Angers (Rennes)",
    "Institut Agro Rennes-Angers, campus d'Angers":  "Institut Agro Rennes-Angers (Angers)",
    "VetAgro Sup (campus Agro Clermont-Ferrand)":    "VetAgro Sup Clermont",
    "VetAgro Sup (campus Véto Lyon)":                "VetAgro Sup Lyon",
    "ONIRIS Nantes":                                 "ONIRIS Nantes (alimentation)",
    "ONIRIS Nantes Véto":                            "ONIRIS Nantes (vétérinaire)",
    "École Nationale Vétérinaire d'Alfort (ENVA)":  "ENV Alfort",
    "École Nationale Vétérinaire de Toulouse (ENVT)":"ENV Toulouse",
    "Bordeaux INP":                                  "ENSMAC Bordeaux (agroalimentaire - génie biologique)",
    "ENSC Lille":                                    "ENSC Lille",
    "ENSC Montpellier":                              "ENSC Montpellier",
    "Chimie ParisTech":                              "Chimie ParisTech",
    "ESPCI Paris":                                   "ESPCI Paris",
    "ENSIC":                                         "ENSIC Nancy",
    "École Polytechnique":                           "Ecole Polytechnique",
    # Polytech / ISIFC / ENSTIB (rang médian SCEI uniquement)
    "Enstib":                    "Enstib",
    "ESIR":                      "ESIR",
    "ESIAB":                     "ESIAB",
    "ISIFC":                     "ISIFC",
    "Polytech Angers":           "Polytech Angers",
    "Polytech Clermont":         "Polytech Clermont",
    "Polytech Tours":            "Polytech Tours",
    "Polytech Nice":             "Polytech Nice",
    "EPISEN":                    "EPISEN",
    "Polytech Lille":            "Polytech Lille",
    "ESBS":                      "ESBS",
    "Polytech Grenoble":         "Polytech Grenoble",
    "Polytech Marseille":        "Polytech Marseille",
    "Polytech Sorbonne":         "Polytech Sorbonne",
    "Polytech Orléans":          "Polytech Orléans",
    "Polytech Nantes":           "Polytech Nantes",
}

CORRESPONDANCE_TB = {
    "AgroParisTech":                                 "AgroParisTech (TB)",
    "Bordeaux Sciences Agro":                        "Bordeaux Sciences Agro TB",
    "ENSAIA":                                        "ENSAIA Nancy TB",
    "ENSAT":                                         "INP AgroToulouse TB",
    "Institut Agro Dijon":                           "Institut Agro Dijon TB",
    "Institut Agro Montpellier":                     "Institut Agro Montpellier TB",
    "Institut Agro Rennes-Angers, campus Rennes":    "Institut Agro Rennes-Angers (Rennes) TB",
    "Institut Agro Rennes-Angers, campus d'Angers":  "Institut Agro Rennes-Angers (Angers) TB",
    "VetAgro Sup (campus Agro Clermont-Ferrand)":    "VetAgro Sup Clermont TB",
    "VetAgro Sup (campus Véto Lyon)":                "VetAgro Sup Lyon (TB)",
    "ONIRIS Nantes":                                 "ONIRIS Nantes (alimentation) TB",
    "ONIRIS Nantes Véto":                            "ONIRIS Nantes (vétérinaire) TB",
    "École Nationale Vétérinaire d'Alfort (ENVA)":  "ENV Alfort (TB)",
    "École Nationale Vétérinaire de Toulouse (ENVT)":"ENV Toulouse (TB)",
    "ENGEES":                                        "ENGEES TB",
}

CORRESPONDANCE_G2E = {
    "EIVP Paris":             "EIVP Civil",
    "ENGEES":                 "ENGEES Civil",
    "ENSG Géologie Nancy":    "ENSG Nancy",
    "ENTPE Lyon":             "ENTPE Civil",
    "EOST Strasbourg":        "EOST Strasbourg",
    "IMT Mines Albi":         "IMT Mines Albi",
    "IMT Mines Alès":         "IMT Mines Alès",
    "IMT Nord-Europe (Mines)":"IMT Nord Europe",
}

def formater_specs(specs_data):
    """
    Convertit une entrée RANGS_OFFICIELS_* en liste sérialisable pour data.js.
    Retourne None si aucune donnée.
    """
    if not specs_data:
        return None
    return specs_data.get("specs")

# ================================================================
# LECTURE DES STATS SCEI (rang médian) — onglets collés depuis scei-concours.fr
# ================================================================
# Mode d'emploi (une fois par an) :
#   1. https://www.scei-concours.fr/stat[ANNEE]/bcpst.html  → Ctrl+A, Ctrl+C
#      Coller dans l'onglet "Stats_BCPST" (Excel) en A1
#   2. https://www.scei-concours.fr/stat[ANNEE]/tb.html → onglet "Stats_TB"
#   3. Relancer ce script

COL_ECOLE  = 0
COL_RG_MED = 13
COL_PLACES = 16

SKIP_PREFIXES = ('ecole - concours','nb','inscrits','concours ','cpge ','groupe ',
                 'statistiques','bcpst','tb -','les tableaux','pour les','x bio',
                 'ens ','centrale-','g2e','polytech bcpst',
                 'polytech tb','groupe insa','insa ')

MOTS_SPEC = ['cursus','spécialité','génie','biotechnologie','chimie','physique','alimentation',
             'biomédical','biologique','agroalimentaire','horticulture','paysage','fonctionnaire',
             'apprentissage','vivant','santé','matériaux','énergétique','géomatique','agronomie',
             'microbiologie','géotechnique','procédés','aménagement','ingénieur','technologies']

NOMS_COMPOSES = ['angers','rennes','dijon','montpellier','paris','lyon','bordeaux',
                 'toulouse','nantes','strasbourg','nancy','lille','géomatique','metz',
                 'enstib','ensic','ensmac','ensegid','esbs']

def contient_spec(t):
    tl = t.lower()
    return any(m in tl for m in MOTS_SPEC)

def est_nom_compose(_, droite):
    pd_low = droite.lower().strip()
    for v in NOMS_COMPOSES:
        if pd_low.startswith(v) and (len(pd_low)==len(v) or pd_low[len(v)] in ' -–(,'):
            return True
    return False

def extraire_nom_et_specialite(nom_complet):
    for m in re.finditer(r'\s*[-–]\s*', nom_complet):
        droite = nom_complet[m.end():]
        if est_nom_compose(nom_complet[:m.start()], droite):
            continue
        if contient_spec(droite):
            return nom_complet[:m.start()].strip(), droite.strip()
    mp = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', nom_complet)
    if mp and contient_spec(mp.group(2)):
        return mp.group(1).strip(), mp.group(2).strip()
    return nom_complet, None

def lire_stats_scei(excel_path, nom_onglet):
    try:
        df = pd.read_excel(excel_path, sheet_name=nom_onglet, header=None)
    except Exception as e:
        print(f"  ⚠️  Onglet '{nom_onglet}' absent ({e}) — rang médian ignoré.")
        return {}

    print(f"  📋 '{nom_onglet}' : {len(df)} lignes lues…")
    stats = {}

    for _, row in df.iterrows():
        nom = safe_str(row.iloc[COL_ECOLE]) if len(row) > COL_ECOLE else ""
        if not nom or len(nom) < 4:
            continue
        if any(nom.lower().startswith(p) for p in SKIP_PREFIXES):
            continue
        # Ignorer les lignes de totaux de concours : elles ont un nom très court
        # ou commencent par des mots-clés supplémentaires
        if len(nom) < 6 or nom.lower().startswith(('total','sous-total','dont','nb ')):
            continue

        try:
            rg = int(float(row.iloc[COL_RG_MED])) if not pd.isna(row.iloc[COL_RG_MED]) else None
            pl = int(float(row.iloc[COL_PLACES])) if not pd.isna(row.iloc[COL_PLACES]) else 0
        except (TypeError, ValueError, IndexError):
            continue

        if not rg:
            continue

        nom_base, spec = extraire_nom_et_specialite(nom)
        if nom_base not in stats:
            stats[nom_base] = []
        stats[nom_base].append({"spec": spec, "rg_median": rg, "places": pl})

    print(f"  ✅ {len(stats)} écoles (rang médian) dans '{nom_onglet}'")
    return stats

def rapprocher_medians(nom_excel, stats_scei, seuil=75):
    if not stats_scei:
        return None
    match = fuzz_process.extractOne(nom_excel, list(stats_scei.keys()))
    if match and match[1] >= seuil:
        return stats_scei[match[0]]
    return None

def fusionner_specs(specs_medians, specs_officiels):
    """
    Construit la liste finale des spécialités.
    - Source de vérité : specs_officiels (rapports PDF jury) pour premier/dernier/n
    - Le rang médian SCEI est associé par fuzzy matching sur le libellé de spécialité
    - Si specs_officiels est None mais specs_medians existe (cas Polytech/ISIFC),
      on retourne directement les données SCEI avec dernier=None
    - Ne conserve que 'dernier' et 'rg_median' (pas de 'premier')
    """
    # Cas Polytech/ISIFC : données SCEI uniquement, pas de rapport jury
    if not specs_officiels and specs_medians:
        return [{"spec": s.get("spec"), "dernier": None, "rg_median": s.get("rg_median"), "places": s.get("places")}
                for s in specs_medians]

    if not specs_officiels:
        return None

    # Index des médians SCEI par libellé (pour le matching)
    med_index = {}
    if specs_medians:
        for s in specs_medians:
            key = (s.get("spec") or "").strip()
            med_index[key] = s.get("rg_median")

    resultat = []
    for s in specs_officiels:
        spec_label = s.get("spec")
        dernier    = s.get("dernier")
        places     = s.get("n")

        # Rang médian SCEI : correspondance exacte d'abord, puis fuzzy
        rg_median = None
        if med_index:
            cle_pdf = (spec_label or "").strip()
            # Chercher aussi sous la clé None (école sans spécialité distincte)
            if cle_pdf in med_index:
                rg_median = med_index[cle_pdf]
            elif None in med_index and not cle_pdf:
                rg_median = med_index[None]
            elif "" in med_index and not cle_pdf:
                rg_median = med_index[""]
            elif not cle_pdf and len(med_index) == 1:
                # Une seule entrée dans le dict : c'est forcément la bonne
                rg_median = list(med_index.values())[0]
            else:
                match = fuzz_process.extractOne(cle_pdf, [k for k in med_index if k])
                if match and match[1] >= 80:
                    rg_median = med_index[match[0]]

        # Si 1 seule place : médian = dernier par définition
        if places == 1 and dernier is not None:
            rg_median = dernier

        resultat.append({
            "spec":      spec_label,
            "dernier":   dernier,
            "rg_median": rg_median,
            "places":    places,
        })

    resultat.sort(key=lambda x: (x.get("dernier") or x.get("rg_median") or 9999))
    return resultat if resultat else None


# Types d'écoles sans rapport officiel jury → pas de données de sélectivité
# Note : Polytech et ENSTIB ont des données SCEI (rang médian uniquement)
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

print("\n📊 Chargement des rangs médians SCEI…")
stats_bcpst_medians = lire_stats_scei(excel_path, "Stats_BCPST")
stats_tb_medians    = lire_stats_scei(excel_path, "Stats_TB")

donnees_web = []
avec_rang = sans_rang = 0

print("\n⚡ Traitement des écoles…")

for _, ecole in ecoles.iterrows():
    nom_ecole  = safe_str(ecole['Nom'])
    if not nom_ecole:
        continue
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

    # Rangs — uniquement pour les types avec rapport jury officiel
    specs_bcpst = specs_tb = specs_g2e = None

    if type_bcpst not in TYPES_SANS_RANG or type_tb not in TYPES_SANS_RANG:
        medians_bcpst = rapprocher_medians(nom_ecole, stats_bcpst_medians)
        medians_tb    = rapprocher_medians(nom_ecole, stats_tb_medians)

        cle_bcpst = CORRESPONDANCE_BCPST.get(nom_ecole)
        cle_tb    = CORRESPONDANCE_TB.get(nom_ecole)
        cle_g2e   = CORRESPONDANCE_G2E.get(nom_ecole)

        off_bcpst = (RANGS_OFFICIELS_BCPST.get(cle_bcpst, {}).get("specs")
                     or RANGS_OFFICIELS_POLYTECH.get(cle_bcpst, {}).get("specs")) if cle_bcpst else None
        off_tb    = RANGS_OFFICIELS_TB.get(cle_tb,    {}).get("specs") if cle_tb    else None
        off_g2e   = RANGS_OFFICIELS_G2E.get(cle_g2e,  {}).get("specs") if cle_g2e  else None

        if type_bcpst not in TYPES_SANS_RANG:
            specs_bcpst = fusionner_specs(medians_bcpst, off_bcpst)
        if type_tb not in TYPES_SANS_RANG:
            specs_tb = fusionner_specs(medians_tb, off_tb)
        specs_g2e = fusionner_specs(None, off_g2e)

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
