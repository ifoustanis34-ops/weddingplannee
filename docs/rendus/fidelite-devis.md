# Fidélité des devis et des billets — Étapes R3 et R4

Mesure : `python manage.py fidelity_report --out docs/rendus/diff` (planches rendu | référence | carte des différences dans `diff/`). Le devis d’exemple (`donnees-exemple.json`) est rendu avec chaque modèle ; la référence 2:3 est ramenée au format A4 (décision R1), puis chaque zone sans photo ni logo est comparée (SSIM, fenêtre 7 × 7).

## Résultats (21 oct. 2026)

SSIM par zone, niveau glyphes (720 px de large) / niveau composition (zones réduites 4 fois).

| Modèle | Zones (glyphes / composition) | Minimum |
|---|---|---|
| A Prestige | titre 0,45 / 0,71 · informations 0,67 / 0,69 · tableau 0,66 / 0,77 · pourquoi 0,59 / 0,74 · totaux 0,65 / 0,75 · conditions 0,53 / 0,64 · pied 0,62 / 0,58 | 0,45 |
| B Élégance | colonne 0,54 / 0,48 · tableau 0,62 / 0,58 · totaux 0,17 / 0,16 · cartes 0,56 / 0,57 · engagements 0,52 / 0,64 · pied 0,58 / 0,45 | 0,17 |
| C Classique | titre 0,29 / 0,59 · informations 0,63 / 0,68 · tableau 0,63 / 0,75 · totaux 0,45 / 0,68 · engagements 0,72 / 0,78 · conditions 0,48 / 0,46 · pied 0,64 / 0,55 | 0,29 |
| D Partenariat | titre 0,57 / 0,59 · informations 0,65 / 0,65 · tableau 0,63 / 0,69 · totaux 0,72 / 0,75 · modalités 0,65 / 0,65 · conditions 0,51 / 0,47 · pied 0,49 / 0,35 | 0,49 |

**Le seuil du prompt (SSIM ≥ 0,90 par zone) n’est pas atteint.** Les blocs sont alignés à ± 3 mm (mesuré : décalage optimal de chaque zone), mais la similarité au niveau des glyphes plafonne vers 0,8 même avec un alignement parfait, pour des raisons qui ne relèvent pas de la mise en page :

1. **Valeurs volontairement différentes** : les totaux des images sont faux (§2e) ; le rendu affiche 1 250 000 / 1 200 000 FCFA au lieu de 1 150 000 / 1 100 000. La zone « totaux » de B est la plus touchée (la bande dorée et la bande sombre portent ces montants en gros).
2. **Écriture manuscrite** dessinée par l’IA qui a produit les images : aucune police libre ne la reproduit ; Great Vibes et Allura en sont proches mais pas identiques (titres manuscrits, « Merci pour votre confiance ! », pied).
3. **Icônes** : pleines et dessinées à la main sur les références, au trait (bibliothèque lucide) dans Wedivo, comme demandé au §2e.
4. **Logo** « M couronné » de l’exemple : ce n’est pas un fichier d’agence ; le monogramme le remplace (zone exclue de la mesure).
5. **Résolution** : JPEG WhatsApp de 720 px (D : capture de 462 px utiles), d’où ± 1 pt sur les tailles et ± 1 mm sur les positions.

## Temps de rendu

Mesuré sur la machine de développement (un cœur, devis d’exemple) : HTML 2 ms, PDF 0,42 à 0,69 s, image PNG 0,13 à 0,15 s, soit **0,55 à 0,81 s** par aperçu (objectif du §3 : 800 ms). Deux réglages y ont contribué : la configuration des polices de WeasyPrint est réutilisée d’un rendu à l’autre, et les mises en page à hauteur fixe utilisent des tableaux et des positions absolues plutôt que flex, quatre à cinq fois plus lent dans WeasyPrint. Un aperçu déjà calculé revient du cache Redis (10 min).

## Ce que garantit le test

`documents/tests/test_fidelity.py` fixe le niveau actuel de chaque zone (moins 0,05) : toute régression de mise en page fait échouer la suite. Le seuil sera relevé si des références plus fidèles sont fournies (gabarits sources, polices exactes, totaux corrects).

## Pour atteindre 0,90

Il faudrait des références produites avec les mêmes polices et les mêmes données que Wedivo (par exemple un export PDF des maquettes d’origine, avec les montants calculés). Dans ce cas, la comparaison se ferait directement et l’écart restant viendrait seulement de la mise en page.

## Billets « Ticket détachable » (R4)

Mêmes mesures sur les zones sans photo du billet (200 × 118 mm), contre `billets/billet-{or-noir,bleu-royal,emeraude}.jpg`. Glyphes / composition :

| Palette | Zones | Minimum |
|---|---|---|
| Noir & Or | titre 0,60 / 0,74 · prénoms 0,60 / 0,53 · colonnes 0,53 / 0,64 · talon haut 0,34 / 0,53 · carte du talon 0,48 / 0,56 · talon bas 0,53 / 0,60 | 0,34 |
| Bleu royal | titre 0,54 / 0,77 · prénoms 0,51 / 0,39 · colonnes 0,52 / 0,58 · talon haut 0,29 / 0,31 · carte du talon 0,47 / 0,61 · talon bas 0,56 / 0,48 | 0,29 |
| Émeraude & Or | titre 0,63 / 0,78 · prénoms 0,53 / 0,35 · colonnes 0,48 / 0,53 · talon haut 0,36 / 0,56 · carte du talon 0,44 / 0,59 · talon bas 0,52 / 0,58 | 0,36 |

Seuil de 0,90 non atteint, pour les mêmes raisons que les devis, plus deux propres au billet : le QR code et le code-barres encodent un vrai jeton (les motifs ne peuvent pas être ceux des images), et le talon porte en plus le nom de l’invité et ses places (§2b, ajout obligatoire). Les blocs sont à moins de 2 mm de la référence.

**Lecture des codes** : le QR (segno, niveau Q, zone de silence de 4 modules, 25 mm imprimés) et le Code 128 sont décodés par zxing-cpp sur l’image rendue, dans les tests (`invitations/tests/test_tickets.py`).

**Temps** : environ 0,3 s par billet avec son image, moins sans image (la génération en lot ne fait que le PDF ; l’image est tirée du PDF à la demande). Le test vérifie le budget de 500 billets en moins de 3 minutes.
