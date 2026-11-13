# Analyse des billets de référence — Étape R1

> Images analysées (1080 × 720 px sauf mention, JPEG WhatsApp) :
>
> | Fichier | Modèle | Palette |
> |---|---|---|
> | `billets/billet-or-noir.jpg` | Ticket détachable | Noir & Or (David & Grâce) |
> | `billets/billet-bleu-royal.jpg` | Ticket détachable | Bleu royal (Daniel & Estelle) |
> | `billets/billet-emeraude.jpg` | Ticket détachable, avec monogramme | Émeraude & Or (Samuel & Chimène) |
> | `billets/billet-emeraude-manuscrit.jpg` | **Variante non décrite dans le prompt** : prénoms tous deux manuscrits, bande verticale | Émeraude & Or |
> | `billets/billet-portrait-emeraude.jpg` (720 × 1080) | **Variante non décrite** : ticket portrait | Émeraude & Or |
>
> Échelle (paysage) : le billet occupe x 8 → 1062 px et y 45 → 668 px de l’image, soit **200 × 118 mm** (1 px = 0,19 mm). Positions en mm depuis le coin haut gauche du billet.

## 1. Format

- Paysage **200 × 118 mm** (le prompt indique 200 × 117 : écart de mesure). Recto seul.
- Ligne pointillée verticale à **x = 139 mm** : partie principale 139 mm, talon 61 mm. Deux encoches demi-cercle ⌀ 4 mm en haut et en bas de la ligne.
- Contour : liseré or 0,5 mm (#DFBD75) ; coins du talon coupés en biais 3,5 mm ; coin haut gauche de la partie principale arrondi 4 mm.
- Fond du billet : crème (Noir & Or #FBF7EF environ, Émeraude #F5F3E9, Bleu #F0F6FB), voile d’ombre très léger sous le billet (fond de l’image, non reproduit).

## 2. Partie principale (Noir & Or)

| Zone | Position (mm) | Contenu et style | Fixe / variable |
|---|---|---|---|
| Photo d’ambiance | 0, 0 — 50 × 118 | Bouquet de roses blanches et gypsophile, alliances or ; fondu vers la droite | Variable : `ticket_design.photo` (série de la palette) |
| Panneau sombre haut gauche | 0, 0 — 37 × 43 | #0F0E0E, bord bas droit en courbe, ruban or ; icône alliances or (10 × 9 mm) ; « DEUX CŒURS / UNE MÊME / HISTOIRE » capitales Montserrat 500 ≈ 7 pt interlettrage 0,2 em, blanc ; filet or 5 mm | Texte variable : `ticket_design.panel_text` |
| Bande sombre basse | 0, 103 — 78 × 15 | Courbe, ruban or ; « Amour • Engagement • Éternité » Great Vibes or ≈ 13 pt (image : « Engagment », faute) | Variable : `ticket_design.bottom_slogan` |
| Titre | 52, 9 — 87 × 4 | « INVITATION OFFICIELLE » Montserrat 500 ≈ 11 pt, interlettrage 0,25 em, #17153B ; filets or de part et d’autre | Variable : `ticket_design.title` |
| Sous-titre | 74, 14 | « À NOTRE MARIAGE » ≈ 8,5 pt, interlettrage 0,2 em | Variable : `ticket_design.subtitle` |
| Introduction | 55, 20 — 82 × 11 | 3 lignes centrées Montserrat 400 ≈ 9,5 pt | Variable : `ticket_design.intro` |
| Premier prénom | 64, 33 — 58 × 11 | « David » **Playfair Display Black** ≈ 44 pt, #111 | Variable : `wedding.partner_1` |
| « & » | 83, 45 — 15 × 9 | Great Vibes or #B37827 ≈ 32 pt + petit cœur | Fixe |
| Second prénom | 70, 54 — 46 × 13 | « Grâce » Great Vibes ≈ 46 pt, noir | Variable : `wedding.partner_2` |
| Ornement | 80, 68 | Filet or avec cœur | Fixe |
| Trois colonnes | 55, 72 — 82 × 20 | Filets verticaux à x 72 et 106 ; icône or 5 mm, libellé capitales 6,5 pt (DATE, LIEU, CODE VESTIMENTAIRE), valeur 9,5 pt sur 2 à 3 lignes | Variables : date + heure, lieu, `ticket_design.dress_code` |
| Phrase | 62, 97 — 62 × 9 | Filet + cœur au-dessus ; « Votre présence est un bonheur pour nous ! » Great Vibes ≈ 18 pt | Variable : `ticket_design.script_line` |
| Feuillages | 123, 10 — 15 × 27 et 120, 96 — 15 × 19 | Or au trait | Fixe (SVG, couleur d’accent) |

## 3. Talon (Noir & Or)

| Zone | Position (mm, x depuis le bord gauche du billet) | Contenu | Fixe / variable |
|---|---|---|---|
| En-tête | 141, 1 — 57 × 17 | Bande #141618 coins coupés, cœur or, « BILLET D’INVITATION » blanc ≈ 9 pt interlettrage 0,15 em, « ÉVÉNEMENT MARIAGE » or 6,5 pt | Variable : `ticket_design.stub_title` |
| Numéro | 159, 19 — 25 × 5 | Badge or #E7C67E rayon 1 mm, « N° 000248 » Montserrat 700 ≈ 10 pt sombre | Variable : `ticket.code` |
| **Ajout : invité** | sous le badge, 3 mm | « Famille Kouassi · 4 places » Montserrat 600 ≈ 7,5 pt (style des valeurs de la carte) — absent des images, obligatoire (§2b) | `guest.name`, `ticket.seats` |
| QR | 155, 25 — 29 × 26 | Cadre or rayon 2 mm, QR noir sur blanc ; zone utile ≈ 25 mm | `ticket.token` (URL signée) |
| Consigne | 156, 52 — 37 × 6 | Icône téléphone or + « Scannez ce code QR pour valider votre entrée » 7 pt | Fixe |
| Carte infos | 144, 61 — 45 × 34 | Fond #F3F0EC bordure fine, rayon 2 mm ; DATE / LIEU / CODE VESTIMENTAIRE (icône or, libellé 6 pt capitales, valeur 7,5 pt) | Variables |
| Merci | 151, 96 — 31 × 7 | « Merci de confirmer votre présence » Great Vibes ≈ 12 pt + filet et cœur | Variable : `ticket_design.stub_script` |
| Pied | 141, 107 — 57 × 10 | Bande #131415, cœur or, « ENSEMBLE POUR TOUJOURS » 6,5 pt interlettrage 0,25 em | Variable : `ticket_design.stub_footer` |
| Code-barres | 193, 28 — 6 × 56 | Vertical, noir | `ticket.code` (Code 128) |
| Numéro vertical | 195, 88 — 3 × 15 | « N° 000248 » or ≈ 8 pt | `ticket.code` |

## 4. Différences entre palettes et variantes

| Élément | Noir & Or | Bleu royal | Émeraude & Or | Émeraude manuscrit | Portrait |
|---|---|---|---|---|---|
| Sombre | #0F0E0E / #141618 | #0D284A / #022C5B | #03251D | #03251D | #03251D |
| Accent | Or #B37827, liseré #DFBD75, badge #E7C67E | Bleu #5190CF (« & », cœurs), alliances argent, badge #D2E4FA | Or #CD992E, badge #D2BC84 | Or | Or |
| Fond / carte talon | #FBF7EF / #F3F0EC | #F0F6FB / #E2ECFB | #F5F3E9 / #F6F3EE | crème | crème |
| Panneau haut gauche | « DEUX CŒURS / UNE MÊME / HISTOIRE » | « UN AMOUR / UNE VIE / ENSEMBLE » | aucun (ruban or courbe sur la photo) | bande verticale pleine hauteur « AMOUR • ENGAGEMENT • POUR TOUJOURS » | — |
| Bas de la partie principale | « Amour • Engagment • Éternité » or | « Bienvenue à notre histoire » manuscrit blanc + cœur | « UNION ♡ AMOUR ♡ POUR LA VIE » capitales | aucun | bande sombre courbe sous la photo |
| Prénoms | Serif noir + manuscrit | Serif bleu nuit + manuscrit | Serif + manuscrit | **les deux manuscrits** | les deux manuscrits |
| Monogramme | non | non | **oui** (« SC » dans un cercle or, 14 mm, en haut à droite des prénoms) | non | non |
| Icône au-dessus du titre | non | non | non | alliances or | alliances-cœurs |
| Pied du talon | « ENSEMBLE POUR TOUJOURS » | idem | idem | « UNION POUR LA VIE » | « UNION POUR LA VIE » (pastille) |
| Phrase | « … un bonheur pour nous ! » | « … un honneur pour nous ! » | « … un honneur pour nous ! » | « … un honneur pour nous ! » | « … un honneur pour nous ! » |

**Billet portrait** (720 × 1080, ≈ 117 × 176 mm si même largeur de talon) : partie principale à gauche (≈ 66 %), talon à droite séparé par une ligne pointillée verticale avec encoches ; date en ligne « SAMEDI | 24 | MAI 2025 À 15H00 » (chiffre en serif 30 pt), lieu avec repère, photo en bas ; talon : en-tête, N°, QR, consigne, liste DATE / LIEU / CODE (sans carte), « UNION POUR LA VIE », **code-barres horizontal** en bas avec le numéro.

## 5. Points incertains

1. **Deux variantes non prévues** (manuscrit et portrait) : les intégrer comme modèles supplémentaires (« Ticket manuscrit », « Ticket portrait ») ou les ignorer ? Proposition : les traiter comme 2 modèles de plus dans R4b, après le modèle principal.
2. Place du **nom de l’invité et du nombre de places** : sous le badge du numéro, ce qui demande 3 mm ; le QR passe de 26 à 24 mm de cadre (zone utile ≥ 22 mm). Le prompt exige ≥ 25 mm imprimés : il faudra soit réduire l’espace entre la consigne et la carte, soit accepter 25 mm de cadre en rognant 1 mm sur la carte. À valider.
3. Polices : titres en capitales espacées proches de Montserrat 500 ; prénoms serif = Playfair Display Black ; manuscrit = Great Vibes (prénoms) et Allura (phrases) — correspondances approximatives.
4. Photos (bouquets, alliances, arche) propres aux images : à remplacer par des séries libres de droits par palette ; recadrages réservés au test de fidélité.
5. Faute « Engagment » (Noir & Or) → « Engagement ».
6. Le code-barres des images n’encode pas de donnée lisible ; il encodera `ticket.code`.
7. Résolution faible (1080 px de large) : tailles de police ± 1 pt, positions ± 1 mm.

## 6. Décisions validées (20 oct. 2026)

1. Les variantes « manuscrit » et « portrait » deviennent deux modèles supplémentaires, réalisés à l’étape R4b après le modèle principal.
2. Nom de l’invité et nombre de places sous le badge du numéro ; le QR garde un cadre de **25 mm** en prenant 1 à 2 mm sur l’espace entre la consigne et la carte d’informations.
