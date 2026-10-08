// Coefficients des concours (session 2026), regroupés par banque puis par concours.
// Sources : notices SCAV Agro-Véto (BCPST/TB), notice G2E 2026, tableaux ENS (banque BCPST) publiés par les prépas.
// À VÉRIFIER chaque année sur les sites des concours. Mettre null / [] quand un barème n'est pas connu.
// types : type(s) d'école (colonnes Type_BCPST / Type_TB de l'onglet Ecoles) ; noms : restreint à ces écoles.
const AN = (lib) => ['Anglais (écrit, compté à l\'admission)', lib];
const CONCOURS = {
  BCPST: [
    { banque: 'Agro-Véto', titre: 'Concours Agro', types: ['Agro'],
      ecrit: [['Biologie (synthèse)', 4], ['SVT (documents)', 4], ['Méthodes de calcul', 4], ['Modélisation math. et info.', 4], ['Physique', 4], ['Chimie', 4], ['Humanités', 4]],
      adm: [['Pratique de biologie', 3], ['Oral de biologie', 3], ['Maths pratiques et info.', 4], ['Physique-chimie', 4], ['Géographie', 3], ['Entretien TIPE', 4], AN(3)] },
    { banque: 'Agro-Véto', titre: 'Concours Véto', types: ['Véto'],
      ecrit: [['Biologie (synthèse)', 5], ['SVT (documents)', 5], ['Méthodes de calcul', 2], ['Modélisation math. et info.', 2], ['Physique', 4], ['Chimie', 4], ['Humanités', 4]],
      adm: [['Pratique de biologie', 4], ['Oral de biologie', 4], ['Maths pratiques et info.', 2], ['Physique-chimie', 4], ['Géographie', 2], ['Entretien TIPE', 4], AN(2)] },
    { banque: 'Agro-Véto', titre: 'Concours PC-BIO', types: ['PC-BIO'],
      ecrit: [['Biologie (synthèse)', 2], ['SVT (documents)', 2], ['Méthodes de calcul', 4], ['Modélisation math. et info.', 4], ['Physique', 4], ['Chimie', 4], ['Humanités', 4]],
      adm: [['Pratique de biologie', 3], ['Maths pratiques et info.', 4], ['Physique-chimie', 5], ['Entretien TIPE', 4], AN(3)] },
    { banque: 'Agro-Véto', titre: 'Concours Polytech', types: ['Polytech'],
      ecrit: [['Biologie (synthèse)', 4], ['Modélisation math. et info.', 4], ['Physique', 1.5], ['Chimie', 1.5], ['Humanités', 3], ['Anglais', 2]],
      adm: [['Entretien TIPE', 4]] },
    { banque: 'Agro-Véto', titre: 'Concours ENSTIB', types: ['ENSTIB'],
      ecrit: [['Biologie (synthèse)', 2], ['SVT (documents)', 2], ['Méthodes de calcul', 1], ['Modélisation math. et info.', 2], ['Physique', 1.5], ['Chimie', 1.5], ['Humanités', 2], ['Anglais', 2]],
      adm: [['Entretien spécifique (60 min)', 14]] },
    { banque: 'Agro-Véto', titre: 'Concours X-BIO', types: ['X-BIO'],
      ecrit: [['Biologie (synthèse)', 4], ['SVT (documents)', 4], ['Méthodes de calcul', 8], ['Modélisation math. et info.', 4], ['Physique', 4], ['Humanités', 4], ['Anglais', 4]],
      adm: [['Biologie', 18], ['Mathématiques', 28], ['Analyse de documents mathématiques', 16], ['Physique', 18], ['Français', 8], ['Langue vivante', 8], ['Sport', 4]],
      note: 'Barème d\'admission publié en 2022 (oraux et épreuves sportives spécifiques à l\'École polytechnique).' },
    { banque: 'Agro-Véto', titre: 'CentraleSupélec (campus de Metz)', types: ['Centrale-Supélec'], ecrit: null, adm: null,
      note: 'Barème non renseigné : les sources consultées sont contradictoires.' },

    { banque: 'G2E', titre: 'ENGEES', types: ['G2E'], noms: ['ENGEES'], ecrit: 'g2e',
      adm: [['Mathématiques', 4], ['Physique', 5], ['Informatique', 1], ['Géologie pratique', 3], ['TIPE', 8], ['Anglais', 5]], note: 'LV2 facultative (coef. 2).' },
    { banque: 'G2E', titre: 'EILCO · ENSG · ENSIL-ENSCI · ENSIP · ENSEGID', types: ['G2E'], noms: ['ENSG Géologie Nancy'], ecrit: 'g2e',
      adm: [['Mathématiques', 4], ['Physique', 4], ['Informatique', 2], ['Géologie pratique', 4], ['TIPE', 5], ['Anglais', 5]], note: 'LV2 facultative (coef. 2).' },
    { banque: 'G2E', titre: 'EOST · Géodata Paris · ESGT', types: ['G2E'], noms: ['EOST Strasbourg', 'Géodata Paris'], ecrit: 'g2e',
      adm: [['Mathématiques', 6], ['Physique', 6], ['Informatique', 2], ['Géologie pratique', 3], ['TIPE', 4], ['Anglais', 3]], note: 'LV2 facultative (coef. 2).' },
    { banque: 'G2E', titre: 'EIVP · ENTPE · ENM · IMT Mines', types: ['G2E'], noms: ['EIVP Paris', 'ENTPE Lyon', 'IMT Mines Albi', 'IMT Mines Alès', 'IMT Nord-Europe (Mines)'], ecrit: 'g2e',
      adm: [['Mathématiques', 6], ['Physique', 6], ['Informatique', 1], ['Géologie pratique', 3], ['TIPE', 5], ['Anglais', 3]] },

    { banque: 'ENS · Ponts · Mines · Centrale', titre: 'ENS Ulm', types: ['ENS'], noms: ['ENS Ulm'],
      blocs: [{ titre: 'Option Biologie', ecrit: [['Biologie', 7], ['Sciences de la Terre', 2], ['Physique', 3], ['Chimie', 3]], note: 'Admission : écrits 31 + oraux 100 (total général 146).' },
              { titre: 'Option Sciences de la Terre', ecrit: [['Biologie', 4], ['Sciences de la Terre', 5], ['Physique', 3], ['Chimie', 3]] }] },
    { banque: 'ENS · Ponts · Mines · Centrale', titre: 'ENS Lyon', types: ['ENS'], noms: ['ENS Lyon'],
      blocs: [{ titre: 'Option Biologie', ecrit: [['Biologie', 8], ['Sciences de la Terre', 4], ['Physique', 4], ['Chimie', 4]] },
              { titre: 'Option Sciences de la Terre', ecrit: [['Biologie', 4], ['Sciences de la Terre', 8], ['Physique', 5], ['Chimie', 3]] }] },
    { banque: 'ENS · Ponts · Mines · Centrale', titre: 'ENS Paris-Saclay', types: ['ENS'], noms: ['ENS Paris Saclay'],
      ecrit: [['Biologie', 8], ['Sciences de la Terre', 2], ['Physique', 4], ['Chimie', 5]], adm: null, note: 'Admission : écrits 9 + oraux 37 (total général 65).' },
    { banque: 'ENS · Ponts · Mines · Centrale', titre: 'École des Ponts ParisTech', types: ['Mines-Pont'], noms: ['Ecole nationale des ponts et des chaussées'],
      ecrit: [['Biologie', 4], ['Sciences de la Terre', 3], ['Physique', 5], ['Chimie', 3]], adm: null },
    { banque: 'ENS · Ponts · Mines · Centrale', titre: 'Mines Paris · Centrales (Lyon, Méditerranée, Nantes)', types: ['Mines-Pont', 'Centrale'], noms: ['Mines Paris', 'Centrale Lyon', 'Centrale Méditerranée', 'Centrale Nantes'], ecrit: null, adm: null,
      note: 'Barème non renseigné.' },

    { banque: 'Groupe INSA', titre: 'Recrutement groupe INSA', types: ['INSA'], ecrit: null, adm: null,
      note: 'Recrutement sur dossier : pas de barème par matière.' }
  ],
  TB: [
    { banque: 'Agro-Véto', titre: 'Concours TB Agro', types: ['Agro'],
      ecrit: [['SVT', 3], ['Biotechnologies', 3], ['Méthodes de calcul', 3], ['Algorithmique et informatique', 1], ['Physique-chimie (résolution de problème)', 3], ['Composition de français', 2]],
      adm: [['Oral de SVT', 3], ['Oral de biotechnologies', 3], ['Pratique biologie / biotechnologies', 3], ['Oral de mathématiques', 3], ['Oral de physique-chimie', 3], ['Oral de géographie', 2], ['Entretien TIPE', 4], AN(2)] },
    { banque: 'Agro-Véto', titre: 'Concours TB Véto', types: ['Véto'],
      ecrit: [['SVT', 3], ['Biotechnologies', 3], ['Méthodes de calcul', 2], ['Algorithmique et informatique', 1], ['Physique-chimie (résolution de problème)', 3], ['Composition de français', 2]],
      adm: [['Oral de SVT', 4], ['Oral de biotechnologies', 3], ['Pratique biologie / biotechnologies', 3], ['Oral de mathématiques', 2], ['Oral de physique-chimie', 3], ['Oral de géographie', 1], ['Entretien TIPE', 4], AN(2)] },
	{ banque: 'Agro-Véto', titre: 'Concours TB ENSTIB', types: ['ENSTIB'],
      ecrit: [['SVT', 3], ['Biotechnologies', 1], ['Méthodes de calcul', 2], ['Algorithmique et informatique', 1], ['Physique-chimie (résolution de problème)', 3], ['Composition de français', 2], ['Anglais', 2]],
      adm: null, note: 'Admission : entretien spécifique de 30 min (coefficient non renseigné).' },
    { banque: 'Polytech', titre: 'Concours TB Polytech', types: ['Polytech'],
      ecrit: [['SVT', 2], ['Biotechnologies', 3], ['Méthodes de calcul', 3], ['Algorithmique et informatique', 1], ['Physique-chimie (résolution de problème)', 3], ['Composition de français', 2], ['Anglais', 2]],
      adm: null, note: 'Barème d\'admission non renseigné (oral de biotechnologies : coef. 3).' },
    { banque: 'ENS', titre: 'Concours TB ENS Paris-Saclay', types: ['ENS'], noms: ['ENS Paris Saclay'],
      ecrit: [['Biologie (épreuve du concours ENS BCPST)', 3], ['Méthodes de calcul', 2], ['Algorithmique et informatique', 1], ['Physique-chimie (résolution de problème)', 1], ['Composition de français', 1], ['Anglais', 1]],
      adm: null, note: 'Oraux gérés par l\'ENS Paris-Saclay (barème non renseigné).' },
    { banque: 'Groupe INSA', titre: 'Recrutement groupe INSA', types: ['INSA'], ecrit: null, adm: null,
      note: 'Recrutement sur dossier : pas de barème par matière.' }
  ]
};
const ECRIT_G2E = [['Mathématiques', 5], ['Chimie', 4], ['Biologie', 3], ['Composition française', 5], ['Physique', 4], ['Géologie', 3]];
CONCOURS.BCPST.forEach(s => { if (s.ecrit === 'g2e') s.ecrit = ECRIT_G2E; });
