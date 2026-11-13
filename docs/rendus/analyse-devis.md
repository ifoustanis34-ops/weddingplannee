# Analyse des devis de référence — Étape R1

> Images analysées : `devis/devis-A-prestige.jpg`, `devis-B-elegance.jpg`, `devis-C-classique.jpg` (720 × 1080 px, JPEG WhatsApp) et `devis-D-partenariat.jpg` (capture de téléphone 498 × 1080 px, page utile 462 × 695 px). Un 5e fichier reçu était un doublon exact du devis B (même MD5) : supprimé.
>
> Échelle : la largeur de la page vaut 210 mm. A, B, C : **1 px = 0,292 mm** ; D : 1 px = 0,455 mm. Positions données en mm depuis le coin haut gauche de la page (x, y, largeur × hauteur), arrondies au mm. Couleurs relevées par médiane des pixels (JPEG compressé : ± 3 %). Tailles de police déduites de la hauteur des capitales (capitale ≈ 0,7 × corps).

## 0. Format — point à valider avant R3

Les quatre images sont au rapport **2:3** (210 × 315 mm), pas A4 (210 × 297 mm, rapport 1:1,414). Deux options :

1. **A4 portrait** (recommandé, imprimable partout) : même largeur, même ordre et mêmes proportions horizontales ; les blocs verticaux sont réduits de 5,7 % (marges internes et hauteur des lignes du tableau d’abord). Le test de fidélité compare **zone par zone** après remise à l’échelle de chaque zone.
2. Page sur mesure 210 × 315 mm : superposition directe, mais impression sur A4 réduite (≈ 94 %) ou rognée.

Marges : aucune marge blanche externe (fonds et pied pleine page, à fond perdu). Contenu à **8 mm** des bords gauche et droit (A, C) ou 6 mm (B, D).

## 1. Grammaire commune (confirmée sur les 4 images)

| Élément | Constat | Fixe / variable |
|---|---|---|
| Fond | Blanc légèrement bleuté #F5F6FA à #FEFEFE, voiles or très légers aux coins, fine courbe or en bas de l’en-tête | Fixe (palette `--doc-paper`, `--doc-soft`) |
| Couleur sombre | A #152232, B #0E254A, C #141543 (toutes « nuit ») ; D prune #291141 (en-tête) / #351648 (pied) | Palette `--doc-dark` |
| Or | Pastilles A #BF8B3D ; icônes B #CAA05B ; dégradés de bande #E7C590 (clair) → #BF8B3D ; montant C #DBA95C | Palette `--doc-accent`, `--doc-accent-grad` |
| Police d’interface | Sans-serif géométrique : **Montserrat** (400 texte, 600 libellés, 700 titres de ligne) | Fixe |
| « DEVIS » | A, B, D : Montserrat ExtraBold 800 ; C : **Playfair Display Black** 900 | Fixe |
| Manuscrit | Slogan, « Chaque détail compte… », « Merci pour votre confiance ! », signatures d’équipe : **Great Vibes** (proche) ; « Vos rêves, notre organisation » : **Allura** (proche) | Police fixe, texte variable |
| Logo | Monogramme « M » couronné + nom « M’PLANNER » en capitales | **Variable** : logo et nom commercial de l’agence |
| Activité | « GESTION & ORGANISATION D’ÉVÉNEMENTS », petites capitales espacées (≈ 5,5 pt, interlettrage 0,12 em) | Variable : `branding.activity` |
| Slogan | « Vos rêves, notre organisation », manuscrit or + courbe or dessous | Variable : `branding.slogan` |
| Tableau | Colonnes N°, Désignation (icône au trait + titre gras + description 6 pt), Quantité, Prix unitaire (FCFA), Montant (FCFA) ; en-tête sombre texte blanc capitales 6,5 pt ; lignes alternées #FBFBFD / #F5F6FA ; coins arrondis 8 px (2,3 mm) | Structure fixe ; lignes variables (`quote.lines`) |
| Pied | Bande sombre pleine largeur avec courbe or et blanche au-dessus ; 4 groupes séparés par des filets verticaux : téléphone + email, adresse, réseaux (Facebook, Instagram, TikTok / WhatsApp) + identifiant, phrase manuscrite or | Variables : `branding.phones`, `email`, `address`, `socials`, `footer_script` |
| Ornement floral | Fleur or au trait en bas à gauche (A, C, D) | Fixe (SVG, couleur d’accent) |

## 2. Devis A « Prestige »

| Zone | Position (mm) | Contenu et style | Variable |
|---|---|---|---|
| Logo | 9, 9 — 26 × 23 | Logo de l’agence | `branding.logo` |
| Nom | 37, 16 — 58 × 9 | « M’PLANNER » Montserrat 800 ≈ 22 pt, #0B1C2F | `branding.trade_name` |
| Activité | 37, 26 — 58 × 3 | Petites capitales | `branding.activity` |
| Slogan | 44, 32 — 52 × 8 | Allura ≈ 16 pt, or #D3B78D, courbe or dessous | `branding.slogan` |
| Filet vertical | 103, 13 → 44 | Or 0,4 mm | Fixe |
| Activités | 106, 14 — 32 × 30 | 4 lignes icône au trait + texte 6,5 pt (Mariages, Anniversaires, Soirées privées, Événements professionnels) | `branding.activities[4]` |
| Photo d’ambiance | 125, 0 — 85 × 79 | Coupée en diagonale côté gauche, liseré or | `quote.photo` ou série de la palette |
| « DEVIS » | 8, 50 — 47 × 13 | Montserrat 800 ≈ 52 pt, #0B1C2F | Fixe |
| Numéro | 8, 64 | « N° DE-2025-0048 » Montserrat 500 ≈ 12 pt | `quote.number` |
| Filet vertical | 63, 52 → 68 | Or | Fixe |
| Accroche | 69, 53 — 51 × 14 | 3 lignes Montserrat 400 ≈ 10 pt #4A4769 | `branding.quote_tagline` (surcharge `quote.tagline`) |
| Barre d’informations | 6, 74 — 198 × 25 | Fond #ECEFF4, rayon 3 mm, 4 colonnes séparées par des filets à x 53, 98, 160 : Client (icône pleine) ; Téléphone + email ; Événement (type, date, lieu) ; Nombre d’invités | `quote.client`, `quote.wedding_date`, `wedding.venue`, `quote.guest_count` |
| Tableau | 6, 103 — 146 × 115 | En-tête 10,5 mm #152232 ; 8 lignes de 13 mm ; colonnes N° 10 mm, Désignation 63 mm, Qté 21 mm, PU 27 mm, Montant 25 mm | `quote.lines` |
| Carte « Pourquoi nous choisir ? » | 156, 103 — 48 × 117 | Fond #FBFBFB, bordure fine ; titre Montserrat 700 ≈ 9 pt ; 4 pastilles or ⌀ 11 mm (#BF8B3D, icône blanche) + texte 2 lignes 6 pt ; phrase manuscrite inclinée (≈ −8°) « Votre satisfaction est notre plus belle réussite ! » + courbe or | `branding.engagements[4]`, `branding.script_satisfaction` |
| TOTAL À PAYER | 6, 221 — 146 × 12 | Gauche : bande claire dorée #F4EEE6, icône calculatrice, libellé Montserrat 800 ≈ 11 pt ; droite (≈ 45 %) : partie sombre en biais, montant blanc ≈ 15 pt | ⚠ voir § 6 |
| Remise commerciale | 6, 235 — 146 × 10 | Bande #F2F4F7, montant « - 50 000 FCFA » | `quote.discount_amount` |
| Montant final après remise | 6, 247 — 146 × 11 | Bande dégradé or #E7C590 → #C49A5A, montant sombre gras ≈ 15 pt | `quote.total` |
| Conditions de paiement | 7, 261 — 115 × 30 | Carte sombre #1E3146 rayon 3 mm, icône document or, titre capitales blanches, liste numérotée 6 pt | `quote.payment_terms` (liste) |
| Remerciement | 128, 255 — 76 × 33 | « Merci pour votre confiance ! » Great Vibes ≈ 20 pt incliné, « L’équipe M’PLANNER » 6,5 pt, signature | `branding.signatory`, `branding.signature_image` |
| Pied | 0, 295 — 210 × 20 | #112236 ; colonnes à x 13 / 69 / 113 / 147 ; phrase « Ensemble, rendons vos événements uniques ! » or + petit cœur | `branding.*` |

## 3. Devis B « Élégance »

| Zone | Position (mm) | Contenu et style | Variable |
|---|---|---|---|
| Logo + nom + slogan | 10, 12 — 80 × 30 | Comme A, nom ≈ 20 pt | `branding.*` |
| Photo | 88, 0 — 75 × 51 | Bouquet et bougies | photo |
| Panneau sombre en biais | 152, 7 — 58 × 46 | #070F21 ; 4 activités en blanc 7 pt, filet or, « Chaque détail compte ! » Great Vibes or | `branding.activities`, `branding.script_detail` |
| Colonne gauche | 6, 51 — 49 × 241 | Fond #F9F8F7 rayon 4 mm | Fixe |
| « DEVIS » + numéro | 8, 54 — 40 × 16 | Montserrat 800 ≈ 30 pt ; numéro ≈ 10 pt | `quote.number` |
| Accroche | 8, 75 — 46 × 13 | Italique couleur sombre ≈ 8,5 pt | tagline |
| Liste d’infos | 8, 94 — 46 × 49 | 4 entrées icône pleine + libellé gras + valeur, séparées par des filets : Date d’émission, Client, Lieu, Nombre d’invités | `quote.issue_date`, client, lieu, invités |
| Phrase manuscrite | 8, 152 — 46 × 20 | « Votre événement, notre priorité ! » Great Vibes ≈ 17 pt + courbe or | `branding.script_priority` |
| Photo de colonne | 0, 163 — 52 × 126 | Bord droit en courbe, liseré or | photo |
| Tableau | 61, 58 — 144 × 121 | En-tête #0E254A ; 8 lignes de 13,7 mm ; icônes or #CAA05B, titres sombres, descriptions or | `quote.lines` |
| TOTAL À PAYER | 61, 184 — 144 × 13 | Gauche dégradé or #EFCA8E avec icône pièces ; droite sombre #0C162C en biais, montant blanc ≈ 16 pt | ⚠ § 6 |
| Remise | 61, 199 — 144 × 8 | Icône, libellé, montant | `discount_amount` |
| Montant final | 61, 209 — 144 × 16 | Bande sombre #091834, libellé Great Vibes blanc, montant or #E6C080 ≈ 18 pt | `quote.total` |
| Conditions de paiement | 61, 231 — 76 × 41 | Carte claire #F2F5F9 bordure, icône portefeuille | `payment_terms` |
| Merci | 140, 231 — 65 × 41 | Carte claire : titre manuscrit, 3 lignes, « L’équipe M’PLANNER », signature | signatory |
| Engagements | 6, 274 — 198 × 13 | 4 colonnes icône or + 2 lignes 6 pt, filets verticaux | `branding.engagements` |
| Pied | 0, 289 — 210 × 26 | #0C1D3B, courbe or et blanche ; nom et slogan manuscrits à droite | `branding.*` |

## 4. Devis C « Classique »

| Zone | Position (mm) | Contenu et style | Variable |
|---|---|---|---|
| Logo + nom + slogan | 11, 7 — 92 × 33 | Comme A | `branding.*` |
| Photo | 111, 0 — 99 × 44 | Courbe or à gauche ; activités en blanc séparées par des points or (2 lignes, 7 pt) | photo, activités |
| « DEVIS » | 11, 49 — 41 × 12 | **Playfair Display Black** ≈ 46 pt #05032B | Fixe |
| Numéro | 11, 63 | Petit carré or 2 mm + « N° DE-2025-0048 » 9 pt | `quote.number` |
| Accroche | 11, 70 — 55 × 10 | Italique 8,5 pt | tagline |
| Carte d’informations | 71, 47 — 129 × 40 | Fond #F7F7F9, 2 colonnes séparées à x 128 : Client (nom ≈ 10 pt, téléphone, email) ; Événement, Date, Lieu, Nombre d’invités (icône chacun) | client, mariage |
| Tableau | 11, 90 — 189 × 99 | Pleine largeur, en-tête #141543, 8 lignes de 11 mm | `quote.lines` |
| Carte photo | 11, 192 — 99 × 40 | Dégradé sombre à droite, « Chaque détail compte… » Great Vibes blanc + 2 lignes | photo, `script_detail` |
| Sous-total / Remise | 112, 192 — 88 × 18 | Carte or clair #FBEBD7 | `subtotal`, `discount_amount` |
| TOTAL À PAYER | 112, 211 — 88 × 21 | Carte sombre #0F1033, icône portefeuille or, montant dégradé or #DBA95C ≈ 24 pt | `quote.total` |
| Nos engagements | 11, 236 — 189 × 20 | Étoile or + titre capitales, 4 colonnes | engagements |
| Conditions de paiement | 11, 258 — 108 × 29 | Carte sombre #171744 | `payment_terms` |
| Merci + signature | 128, 257 — 73 × 32 | Manuscrit, « L’équipe M’PLANNER » | signatory |
| Pied | 0, 290 — 210 × 25 | #111441, courbes | `branding.*` |

## 5. Devis D « Partenariat » (structure ; tailles fines reprises de A à C)

| Zone | Contenu | Variable |
|---|---|---|
| En-tête gauche | Logo, nom, activité, slogan | agence |
| Bloc partenaire | Filet vertical ; « En partenariat avec » (7 pt), « SAGUIE ETEMO » capitales ≈ 12 pt, « Wedding Planner & Event Design » italique 7 pt, petit ornement | `quote.partners[0]` (nom, activité) |
| Photo | Haut droit avec liseré or | photo |
| « DEVIS » + numéro + accroche | Montserrat 800 couleur prune #251A38 | `quote.number` |
| Carte infos | Client (nom, téléphone, email) ; Événement, Date, Lieu, Nombre d’invités | client, mariage |
| Tableau | En-tête prune #291141, 8 lignes compactes, montants suivis de « FCFA » | lignes |
| Carte photo | « Chaque détail compte… » + « Nous créons des instants uniques, à votre image. » | photo |
| Totaux | Sous-total, Remise commerciale, bande dorée #D2B08C « TOTAL À PAYER » | montants |
| Modalités de paiement | Deux anneaux de progression : « 50 % — Acompte à la réservation — 575 000 FCFA (à la signature du devis) » et « 50 % — Solde restant — 575 000 FCFA (au plus tard 7 jours avant l’événement) » | échéancier : % et montants calculés |
| Conditions du devis | Liste de 5 points (validité 30 jours, prix en FCFA, annulation par écrit 15 jours avant, solde 7 jours avant, frais en cas de modification) | `quote.terms` |
| Signatures | « Merci pour votre confiance ! » ; « Pour M’PLANNER / La Gestionnaire » et « Pour SAGUIE ETEMO / La Responsable », chacune avec signature manuscrite | `branding.signatory`, `partner.signatory` |
| Pied | Ligne de contacts (« M’PLANNER – Cameroun », téléphone, email, réseaux, « mplanner.cm ») ; ligne de mots-clés « ÉVÉNEMENTS • MARIAGES • CÉRÉMONIES • ENTREPRISES » ; vague prune #351648 avec liseré or | `branding.*`, `branding.footer_keywords` |

## 6. Données et corrections

- **Totaux faux** (comme annoncé §2e) : les 8 lignes font **1 250 000 FCFA**. Les images affichent 1 200 000 (sous-total C, D) et 1 150 000 / 1 100 000. Avec une remise de 50 000 FCFA (= 4 %), Wedivo calculera : sous-total 1 250 000, remise − 50 000, total 1 200 000, acompte et solde 600 000 chacun (D).
- **Libellés de totaux incohérents entre modèles** : dans A et B, « TOTAL À PAYER » est affiché **avant** la remise, puis « Montant final après remise » ; dans C et D, « TOTAL À PAYER » est le montant **après** remise. Proposition : dans A et B, la première bande devient « TOTAL DES PRESTATIONS » (valeur : sous-total), la mise en page est inchangée. À valider.
- Faute « inoubliole » (A) → « inoubliable ».
- Icônes mal choisies : « Fleurs & accessoires » montre une cloche de service (B, C) ; « Installation & démontage » un haut-parleur (A). Chaque prestation recevra une icône de la bibliothèque au trait (§2e).
- La date d’émission de B (« 14 Février 2027 ») est la date du mariage : donnée d’exemple incohérente, sans effet sur le gabarit.
- Aucun QR code ni montant en toutes lettres sur les images : non ajoutés (§5).

## 7. Points incertains

1. **Format A4 ou 210 × 315 mm** (§ 0) — décision nécessaire avant R3.
2. **Libellé de la première bande des totaux A et B** (§ 6).
3. Résolution faible (720 px de large, JPEG WhatsApp ; D en 462 px) : positions ± 1 mm, tailles de police ± 1 pt, couleurs ± 3 %. Les textes de 5 à 6 pt (descriptions, conditions de D) sont lus mais pas mesurables précisément.
4. Polices manuscrites : Great Vibes et Allura sont les plus proches parmi les polices libres ; la police exacte des images n’est pas identifiable (rendu probablement généré par IA).
5. Photos d’ambiance : propres aux images, sans droits connus ; elles ne serviront qu’au test de fidélité (recadrages). Il faut une série de photos libres de droits par palette pour la production.
6. Le logo « M couronné » fait partie de l’exemple ; sans logo, le monogramme de l’agence le remplace (§4).
7. Le test de fidélité à SSIM ≥ 0,90 n’est atteignable que si les photos et le logo d’exemple sont ceux des images (recadrages) ; avec d’autres photos, seules les zones sans photo sont comparables.

## 8. Décisions validées (20 oct. 2026)

1. **Format A4 portrait** : blocs verticaux réduits de 5,7 %, test de fidélité zone par zone.
2. **A et B** : la première bande des totaux s’intitule « TOTAL DES PRESTATIONS » (sous-total) ; « Montant final après remise » = total.
