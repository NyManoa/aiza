# Rapport d'analyse — réseau de transport d'Antananarivo

_Généré par `analysis/stats.py` (règles déterministes, aucune IA)._

## 1. Rattachement lieux ↔ référentiel administratif

- Lieux uniques du corpus : **188** — rattachés : **157** (83.5 %)
- Occurrences (passages dans les trajets/liaisons) : **626** — rattachées : **470** (75.1 %)

| Statut | Lieux | Occurrences |
|---|---:|---:|
| exact_fokontany | 86 | 160 |
| sous_chaine_fokontany | 44 | 234 |
| commune | 7 | 14 |
| repere_ou_variante | 20 | 62 |
| non_resolu | 31 | 156 |

Lieux non résolus (priorité de complétion de `data/reference/manual_places.csv`) :

- Anosy — 28 occurrence(s), 17 ligne(s)
- Météo — 24 occurrence(s), 12 ligne(s)
- CNAPS — 21 occurrence(s), 3 ligne(s)
- Rasalama — 9 occurrence(s), 6 ligne(s)
- Tsimbazaza — 8 occurrence(s), 5 ligne(s)
- Mahazo — 8 occurrence(s), 2 ligne(s)
- Mascar — 7 occurrence(s), 3 ligne(s)
- Mausolée — 6 occurrence(s), 2 ligne(s)
- Antananandrano — 5 occurrence(s), 2 ligne(s)
- Coliseum — 5 occurrence(s), 2 ligne(s)
- Ste Akanjo — 4 occurrence(s), 1 ligne(s)
- Bel'air — 3 occurrence(s), 3 ligne(s)
- Bypass — 3 occurrence(s), 1 ligne(s)
- Fasan karana — 2 occurrence(s), 2 ligne(s)
- Ravitoto — 2 occurrence(s), 2 ligne(s)

## 2. Réseau et graphe

- 58 lignes urbaines, 85 variantes (dont 14 circulaires)
- 9 groupes suburbains, 85 liaisons Primus → Terminus
- Graphe : 188 nœuds, 458 arcs publiés + 322 arcs retour supposés
- Composantes faiblement connexes : [170, 13, 3, 2]
- Nœuds de correspondance (≥ 2 lignes) : 67

| Nœud | Lignes | Passages | Degré entrant | Degré sortant | Rattachement |
|---|---:|---:|---:|---:|---|
| Analakely | 26 | 31 | 12 | 18 | sous_chaine_fokontany (0.75) |
| 67ha | 22 | 35 | 11 | 15 | sous_chaine_fokontany (0.65) |
| Anosy | 17 | 28 | 10 | 16 | non_resolu (0.0) |
| Ambanidia | 14 | 16 | 10 | 10 | sous_chaine_fokontany (0.75) |
| Météo | 12 | 24 | 11 | 17 | non_resolu (0.0) |
| Ankorondrano | 10 | 12 | 11 | 8 | sous_chaine_fokontany (0.75) |
| Mahamasina | 10 | 10 | 6 | 3 | sous_chaine_fokontany (0.75) |
| Anosibe | 10 | 10 | 6 | 8 | sous_chaine_fokontany (0.65) |
| Antanimena | 9 | 13 | 6 | 6 | exact_fokontany (1.0) |
| Ankadimbahoaka | 7 | 10 | 5 | 8 | sous_chaine_fokontany (0.75) |
| Anosizato | 7 | 10 | 3 | 8 | sous_chaine_fokontany (0.75) |
| Rasalama | 6 | 9 | 5 | 6 | non_resolu (0.0) |
| Betongolo | 6 | 8 | 6 | 3 | exact_fokontany (1.0) |
| Ampefiloha | 6 | 6 | 2 | 1 | sous_chaine_fokontany (0.75) |
| Analamahitsy | 5 | 11 | 8 | 6 | sous_chaine_fokontany (0.75) |

## 3. Couverture des fokontany d'Analamanga

- 1660 fokontany ; cœur (Renivohitra + périphérie) : 920
- Couverture (tous) : {'direct': 78, 'faible': 95, 'passage': 59, 'commune': 142, 'aucune': 1286}
- Couverture (cœur) : {'direct': 78, 'faible': 93, 'passage': 59, 'commune': 142, 'aucune': 548}

| District / Arrondissement | Fokontany | Direct | Faible | Commune | Aucune | % fokontany desservis | % superficie desservie |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1er Arrondissement | 44 | 13 | 11 | 20 | 0 | 54.5 | 61.1 |
| 2e Arrondissement | 24 | 10 | 4 | 10 | 0 | 58.3 | 68.0 |
| 3e Arrondissement | 34 | 14 | 2 | 0 | 4 | 47.1 | 59.9 |
| 4e Arrondissement | 32 | 10 | 6 | 0 | 2 | 50.0 | 54.0 |
| 5e Arrondissement | 27 | 12 | 6 | 0 | 5 | 66.7 | 76.9 |
| 6e Arrondissement | 31 | 6 | 4 | 21 | 0 | 32.3 | 55.7 |
| Ambohidratrimo | 313 | 2 | 12 | 41 | 254 | 4.5 | 2.0 |
| Antananarivo Atsimondrano | 206 | 6 | 19 | 32 | 136 | 12.1 | 8.1 |
| Antananarivo Avaradrano | 209 | 5 | 29 | 18 | 147 | 16.3 | 18.3 |
| Andramasina | 112 | 0 | 0 | 0 | 112 | 0.0 | 0.0 |
| Anjozorobe | 175 | 0 | 0 | 0 | 175 | 0.0 | 0.0 |
| Ankazobe | 143 | 0 | 0 | 0 | 143 | 0.0 | 0.0 |
| Manjakandriana | 310 | 0 | 2 | 0 | 308 | 0.6 | 0.4 |

Plus grands fokontany sans desserte (cœur) :

- Mahitsitady (Ambato) — 95.79 km², à 5 voisin(s) du réseau
- Ambohimanatrika (Anjanadoria) — 58.92 km², éloigné du réseau
- Ambodimanga (Ambato) — 49.41 km², à 6 voisin(s) du réseau
- Ambohimarina (Anjanadoria) — 28.52 km², éloigné du réseau
- Ampanotokana (Ambato) — 27.03 km², éloigné du réseau
- Ambatoharanana (Ambato) — 23.52 km², éloigné du réseau
- Antanetimboahangy (Avaratsena) — 23.07 km², à 4 voisin(s) du réseau
- Ambohijorery (Ambato) — 21.03 km², à 6 voisin(s) du réseau
- Miorikampoza (Ankadinandriana) — 19.68 km², à 2 voisin(s) du réseau
- Vatovandana (Ambato) — 19.60 km², à 5 voisin(s) du réseau
- Manankasina (Anjanadoria) — 18.05 km², éloigné du réseau
- Mamory (Antsahafilo) — 17.20 km², à 4 voisin(s) du réseau
- Ambohidravaka (Antanetibe) — 16.72 km², à 6 voisin(s) du réseau
- Ambatomanana (Avaratsena) — 15.59 km², à 3 voisin(s) du réseau
- Soaloka (Ambato) — 15.34 km², éloigné du réseau

_Définitions : direct = au moins un lieu rattaché au fokontany et ≥ 2 lignes ; faible = 1 seule ligne ; passage = aucun arrêt publié mais ligne traversant probablement le fokontany ; commune = rattachement seulement au niveau communal ; aucune = aucun lieu._
