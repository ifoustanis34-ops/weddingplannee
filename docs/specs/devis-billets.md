# Devis, billets, QR et scan — Wedivo

> Source : « wedivo-prompt-devis-billets.html ». Complète `CLAUDE.md` et le complément (`docs/specs/complement-prototype.md`). Images de référence : `devis/` et `billets/` à la racine.

## 1. Objectif
1. Le **devis** et le **billet** générés par Wedivo doivent être **identiques aux images de référence** placées dans les dossiers `devis/` et `billets/` : même mise en page, mêmes proportions, mêmes typographies, mêmes couleurs, mêmes éléments, au même endroit.
2. Ce rendu est le même dans les trois sorties : l’aperçu à l’écran quand on clique sur « Générer », le **PDF** téléchargé, et l’**email** envoyé.
3. Wedivo est multi-entreprise : chaque agence crée son compte et renseigne son **logo et ses informations**. Sur ses devis et ses billets, ce sont son logo et ses informations qui apparaissent, jamais ceux d’une autre agence, ni ceux visibles sur l’image de référence.
4. Le système des billets est complet : un QR code unique et signé par billet, une application de scan par caméra pour l’entrée, le refus des billets déjà utilisés, annulés ou faux, et le suivi des arrivées en direct.

## 2. Images de référence

Les images dans `devis/` et `billets/` sont la source de vérité visuelle. Elles sont décrites en détail dans les sections 2b à 2g ; ton analyse doit compléter ces descriptions avec des mesures précises, pas les contredire.

### Analyse obligatoire avant de coder

Ouvre chaque image et rédige `docs/rendus/analyse-devis.md` et `docs/rendus/analyse-billet.md` avec :
- Le format du document : A4 portrait, A5, format billet (ex. 210 × 99 mm), recto seul ou recto-verso, marges mesurées en mm.
- Le découpage en zones (en-tête, bloc client, tableau, totaux, pied, talon détachable, zone QR…), avec la position et la taille de chaque zone en mm.
- Chaque élément visible : texte, filet, forme, image, dégradé, motif, avec sa police (ou la police Google la plus proche), sa taille en pt, sa graisse, sa couleur hexadécimale relevée sur l’image, son alignement.
- Pour chaque élément : **fixe** (fait partie du design) ou **variable** (donnée de l’entreprise, du client, du mariage, de l’invité). Indique la donnée Wedivo correspondante.
- Les éléments propres à l’entreprise visible sur l’image (logo, nom, coordonnées, couleurs de marque) : ils deviennent des variables et seront remplacés par ceux de chaque agence.
- Les points incertains (police introuvable, texte illisible, élément ambigu) : liste-les en fin de fichier.

Crée aussi `docs/rendus/donnees-exemple.json` qui contient exactement les données visibles sur chaque image. Ce jeu sert à vérifier que le rendu généré se superpose à l’image (section 12).

## 2b. Modèles fournis : 4 devis, 1 billet, plusieurs couleurs

Les images ne sont pas un seul design : ce sont des **modèles**. Chaque agence choisit un modèle de devis et une palette de couleurs ; chaque mariage choisit la palette de ses billets. **Chaque modèle doit exister dans toutes les palettes** (section 2c) : la mise en page reste identique, seules les couleurs, les dégradés dorés et les photos d’ambiance changent.

Renomme les fichiers de référence ainsi (si ce n’est pas déjà fait) pour que le code et les tests s’y réfèrent :

| Fichier | Modèle | Palette d’origine |
|---|---|---|
| devis/devis-A-prestige.png | Devis A « Prestige » : colonne « Pourquoi nous choisir ? » à droite | Nuit & Or |
| devis/devis-B-elegance.png | Devis B « Élégance » : colonne d’informations à gauche avec photo arrondie | Nuit & Or |
| devis/devis-C-classique.png | Devis C « Classique » : titre à empattements, tableau pleine largeur | Nuit & Or |
| devis/devis-D-partenariat.png | Devis D « Partenariat » : deux entreprises, deux signatures, modalités en anneaux | Prune & Or |
| billets/billet-or-noir.png | Billet « Ticket détachable » | Noir & Or |
| billets/billet-bleu-royal.png | Billet « Ticket détachable » | Bleu royal |
| billets/billet-emeraude.png | Billet « Ticket détachable » | Émeraude & Or |

> **Image du devis D en basse résolution.** C’est une capture d’écran de téléphone (498 × 1080 px). Utilise-la pour la structure ; pour les tailles et couleurs fines, appuie-toi sur les devis A, B et C, qui partagent la même grammaire visuelle.

### Grammaire commune des devis (A4 portrait, 210 × 297 mm)
- Fond blanc cassé avec voiles dorés très légers et fines courbes or dans les coins ; motif floral or au trait en bas à gauche (A, C, D).
- Couleur sombre de la palette pour les en-têtes de tableau, les cartes « Conditions » et le pied de page ; dégradé métallique or pour les filets, les icônes, les montants mis en valeur et les courbes décoratives.
- Typographies : sans-serif géométrique (Montserrat) pour l’interface du document ; « DEVIS » en Montserrat ExtraBold (A, B, D) ou en serif à fort contraste (Playfair Display Black, modèle C) ; écriture manuscrite (Great Vibes ou Allura) pour les phrases d’accroche et la signature de l’équipe.
- En-tête : logo de l’agence, nom de l’agence en capitales grasses, activité en petites capitales espacées, slogan manuscrit doré souligné d’une courbe.
- Tableau : colonnes N°, Désignation (icône au trait + titre gras + description en petit), Quantité, Prix unitaire (FCFA), Montant (FCFA) ; lignes alternées très légèrement teintées ; coins arrondis 8 px.
- Pied de page sombre pleine largeur : téléphone et email, adresse, réseaux sociaux avec identifiant, phrase manuscrite dorée, séparés par des filets verticaux.

### Devis A « Prestige »
- Haut : logo et nom à gauche ; au centre, filet vertical or et liste de 4 activités avec icônes (Mariages, Anniversaires, Soirées privées, Événements professionnels) ; à droite, photo d’ambiance coupée en diagonale avec un liseré or.
- « DEVIS » très grand, numéro dessous, filet vertical or, accroche sur 3 lignes à droite.
- Barre d’informations sur fond gris très clair, 4 colonnes séparées par des filets : Client ; Téléphone + email ; Événement (type, date, lieu) ; Nombre d’invités. Icônes pleines sombres.
- Tableau sur 74 % de la largeur ; à droite, carte « Pourquoi nous choisir ? » : 4 pastilles rondes or avec icône blanche et texte sur 2 lignes, puis phrase manuscrite inclinée « Votre satisfaction est notre plus belle réussite ! » soulignée d’une courbe or.
- Totaux : « TOTAL À PAYER » (bande claire dorée à gauche, partie sombre en biais à droite avec le montant en blanc), « Remise commerciale » (bande grise), « Montant final après remise » (bande dégradé or, montant en gras sombre).
- Carte sombre « CONDITIONS DE PAIEMENT » (liste numérotée) avec icône or ; à droite « Merci pour votre confiance ! » manuscrit, « L’équipe {agence} », signature.

### Devis B « Élégance »
- Haut gauche : logo, nom, slogan. Haut droite : photo d’ambiance prolongée par un panneau sombre en biais listant les activités (texte blanc) et la phrase manuscrite or « Chaque détail compte ! ».
- Colonne gauche (≈ 25 %) : « DEVIS », numéro, accroche en italique couleur sombre, puis liste séparée par des filets : Date d’émission, Client, Lieu, Nombre d’invités ; phrase manuscrite « Votre événement, notre priorité ! » ; photo d’ambiance en bas de colonne avec bord droit en courbe et liseré or.
- Colonne droite : tableau (icônes or au trait, titres en couleur sombre, descriptions en or).
- Totaux : « TOTAL À PAYER » (gauche dégradé or avec icône pièces, droite sombre en biais), remise, puis « Montant final après remise » sur bande sombre pleine avec libellé manuscrit blanc et montant en or.
- Deux cartes claires côte à côte : « Conditions de paiement » et « Merci pour votre confiance ! » avec texte et signature.
- Bandeau de 4 engagements (icône or + 2 lignes) séparés par des filets ; pied sombre avec courbe or et blanche, nom de l’agence et slogan manuscrits à droite.

### Devis C « Classique »
- Haut : logo et nom à gauche, photo d’ambiance à droite avec courbe or, activités en blanc sur la photo séparées par des points or.
- « DEVIS » en serif noir très gras, petit carré or devant le numéro, accroche en italique.
- Carte d’informations à deux colonnes : Client (nom en grand, téléphone, email) | Événement, Date, Lieu, Nombre d’invités, chacun avec icône.
- Tableau pleine largeur.
- Rangée basse : carte photo avec dégradé sombre et texte manuscrit « Chaque détail compte… » + 2 lignes ; à droite carte claire Sous-total / Remise puis carte sombre « TOTAL À PAYER » avec icône portefeuille or et montant en dégradé or.
- Bandeau « NOS ENGAGEMENTS » (étoile or) à 4 colonnes, carte sombre « Conditions de paiement », remerciement manuscrit et signature, pied sombre.

### Devis D « Partenariat »
- Haut : logo et nom de l’agence, filet vertical, « En partenariat avec » + nom du partenaire en capitales + activité du partenaire en italique ; photo d’ambiance à droite.
- « DEVIS », numéro, accroche ; carte d’informations Client / Événement.
- Tableau compact (8 à 10 lignes sur une page), montants suivis de « FCFA ».
- Rangée : carte photo avec « Chaque détail compte… » | carte Sous-total, Remise, bande dorée « TOTAL À PAYER ».
- Carte « MODALITÉS DE PAIEMENT » : deux anneaux de progression (acompte et solde en %, calculés depuis l’échéancier) avec montant et échéance de chacun.
- Carte « CONDITIONS DU DEVIS » (liste numérotée) ; « Merci pour votre confiance ! » et **deux signatures** : « Pour {agence} / {fonction} » et « Pour {partenaire} / {fonction} ».
- Pied : ligne de contacts (adresse, téléphone, email, réseaux, site) puis ligne de mots-clés en petites capitales (« ÉVÉNEMENTS • MARIAGES • CÉRÉMONIES • ENTREPRISES ») et vague sombre avec liseré or.

### Billet « Ticket détachable » (paysage, 200 × 117 mm)
- Deux parties séparées par une ligne pointillée verticale avec deux encoches demi-cercle (haut et bas) : partie principale ≈ 137 mm, talon ≈ 62 mm. Coins du talon et de la partie principale coupés en biais, liseré or fin sur tout le contour.
- **Partie principale, à gauche** : photo d’ambiance (bouquet, alliances) fondue vers la droite ; panneau sombre en haut à gauche en courbe avec icône d’alliances or et phrase en capitales espacées sur 3 lignes (« DEUX CŒURS / UNE MÊME / HISTOIRE ») + petit filet or ; bande sombre courbe en bas avec slogan manuscrit or ou capitales espacées (« Amour • Engagement • Éternité »).
- **Partie principale, au centre** : « INVITATION OFFICIELLE » en capitales très espacées entre deux filets, « À NOTRE MARIAGE » ; texte d’introduction sur 3 lignes ; premier prénom en serif très gras (Playfair Display Black), « & » or en écriture, second prénom en grande écriture manuscrite ; ornement cœur ; trois colonnes séparées par des filets : DATE (icône calendrier), LIEU (icône repère), CODE VESTIMENTAIRE (icône robe) ; phrase manuscrite « Votre présence est un bonheur pour nous ! » entre deux ornements ; feuillages or au trait en haut et en bas à droite ; monogramme facultatif (initiales des mariés dans un cercle or).
- **Talon** : bandeau sombre « BILLET D’INVITATION / ÉVÉNEMENT MARIAGE » avec cœur or ; badge or « N° 000248 » ; QR code dans un cadre or arrondi ; « Scannez ce code QR pour valider votre entrée » avec icône téléphone ; carte claire DATE / LIEU / CODE VESTIMENTAIRE ; « Merci de confirmer votre présence » manuscrit ; bandeau sombre bas « ENSEMBLE POUR TOUJOURS » ; à droite, code-barres vertical (Code 128 du numéro) et numéro vertical en or.
- **Ajout obligatoire** absent des images : le nom de l’invité et le nombre de places, sous le badge du numéro (« Famille Kouassi · 4 places »), dans le même style que le texte de la carte. Un billet sans nom d’invité ne peut pas être contrôlé correctement.
- Le code-barres encode le même identifiant que le code lisible ; l’application de scan sait aussi le lire.

## 2c. Palettes de couleurs

Chaque gabarit utilise uniquement des variables de palette, jamais de couleur écrite en dur. Une palette définit :

```
--doc-dark        couleur sombre principale (en-têtes, pied, bandeaux)
--doc-dark-2      variante plus claire pour les dégradés du sombre
--doc-accent      couleur d’accent (or, argent, bleu clair…)
--doc-accent-grad dégradé métallique de l’accent (filets, montants, icônes)
--doc-paper       fond du document
--doc-soft        fonds de cartes et lignes alternées
--doc-text        texte principal      --doc-muted   texte secondaire
--doc-photo-set   série de photos d’ambiance assortie
```

| Palette | Sombre | Accent | Fond |
|---|---|---|---|
| Nuit & Or (devis A, B, C) | #0F1B3D | #C9A24A, dégradé #9C7428 → #F1D48A → #B88A35 | #FBFAF7 |
| Prune & Or (devis D) | #3B1E5A | #C9A24A | #FBF9FB |
| Noir & Or (billet) | #121212 | #C8A048, dégradé #8F6A22 → #F3D57E → #B98C33 | #FBF7EF |
| Bleu royal (billet) | #0E2A5C | #3D7BD9 (cœurs, « & »), alliances argent | #F7F9FD |
| Émeraude & Or (billet) | #0D3B2E | #C9A24A | #FBF8F0 |
| Bordeaux & Or | #5A1426 | #C9A24A | #FCF8F6 |
| Rose poudré & Or | #7A3B4A | #D8B26E | #FDF8F7 |
| Terracotta & Sable | #6B2E1C | #D9A066 | #FCF7F1 |
| Couleurs de l’agence | Calculée depuis la couleur principale et secondaire de l’identité de l’agence, avec contrôle du contraste (AA) ; si le contraste est insuffisant, l’accent est assombri ou éclairci automatiquement |  |  |

- Les 4 modèles de devis et le billet sont disponibles dans toutes les palettes. Les valeurs ci-dessus sont des points de départ à affiner à partir des images lors de l’analyse.
- Les icônes, liserés, ornements et feuillages sont en SVG et prennent la couleur ou le dégradé de la palette. Les photos d’ambiance ne se recolorent pas : chaque palette a sa série de photos assorties (bouquets blancs et or, roses bleues, verdure…), et l’agence ou le couple peut téléverser ses propres photos.
- Les photos par défaut sont fournies par Wedivo en haute définition (dossier `backend/documents/assets/photos/{palette}/`, droits d’usage vérifiés). Pour les tests de fidélité seulement, on peut utiliser des recadrages des images de référence.

## 2d. Plusieurs entreprises sur un devis
- Un devis peut associer l’agence émettrice à un ou deux **partenaires** (ex. « En partenariat avec SAGUIE ETEMO »).
- Partenaire interne : une autre agence inscrite sur Wedivo, invitée à valider le partenariat ; son logo, son nom et son signataire viennent alors de son identité. Partenaire externe : saisi à la main (nom, activité, logo, signataire, fonction, signature), visible uniquement dans l’organisation qui l’a créé.
- Le devis reste la propriété de l’agence émettrice (numérotation, paiements, données). Un partenaire interne peut consulter le devis partagé en lecture et le co-signer, sans accès aux autres données de l’agence.
- Le modèle D est conçu pour ce cas ; les modèles A, B et C affichent le partenaire en ligne sous le nom de l’agence (« En partenariat avec … ») et ajoutent sa signature à côté de celle de l’agence.

## 2e. Corrections à ne pas reproduire
- **Les totaux des images sont faux** : les 8 lignes font 1 250 000 FCFA, alors que les images affichent 1 150 000 ou 1 200 000. Dans Wedivo, sous-total, remise, total et montants des modalités sont toujours calculés. Pour le test de fidélité, utilise les montants calculés : seule la valeur change, pas la mise en page.
- Fautes : « inoubliole » (devis A) → « inoubliable » ; « Engagment » (billet noir et or) → « Engagement ».
- Icônes mal choisies dans les images (cloche de service pour « Fleurs & accessoires ») : chaque prestation du catalogue reçoit une icône choisie dans une bibliothèque d’icônes au trait (table, chaise, fleur, bouquet, arche, appareil photo, caméra, haut-parleur, micro, lumière, gâteau, assiette, verre, voiture, calendrier, coordination…).
- Toutes les données visibles (M'PLANNER, contacts, slogans, clients, noms des mariés) sont des exemples : elles viennent de l’identité de l’agence, du devis ou du mariage.

## 2f. Textes personnalisables

| Où | Texte modifiable (valeur par défaut) |
|---|---|
| Identité de l’agence | Slogan (« Vos rêves, notre organisation »), activité (« Gestion & organisation d’événements »), 4 activités avec icônes, accroche du devis, 4 engagements avec icônes (« Qualité du matériel et décoration haut de gamme », « Une équipe expérimentée et à votre écoute », « Respect des délais et du planning », « Un accompagnement personnalisé »), phrases manuscrites (« Votre satisfaction est notre plus belle réussite ! », « Chaque détail compte… », « Merci pour votre confiance ! », « Ensemble, rendons vos événements uniques ! »), conditions de paiement, signataire et fonction, réseaux sociaux, mots-clés du pied de page |
| Devis | Modèle, palette, accroche (surcharge), conditions (surcharge), partenaires, photo d’ambiance |
| Mariage (billets) | Palette, photo principale, phrase du panneau (« Deux cœurs, une même histoire »), slogan bas, titre, sous-titre, texte d’introduction, prénoms, date et heure, lieu, code vestimentaire, phrase manuscrite, pied du talon (« Ensemble pour toujours »), monogramme (initiales calculées, désactivable) |

Chaque zone de texte a une longueur maximale indiquée dans le formulaire et un ajustement automatique de taille (section 3) pour ne jamais casser la mise en page.

## 2g. Choix du modèle dans l’interface
- Paramètres › Identité des documents › **Modèles** : galerie des 4 modèles de devis et du billet, rendus avec les vraies données de l’agence, sélecteur de palette en pastilles, bouton « Définir par défaut ».
- Éditeur de devis : menu « Modèle » (vignettes) et pastilles de palette au-dessus de l’aperçu ; le changement met à jour l’aperçu serveur en moins d’une seconde.
- Écran Billets du mariage : pastilles de palette, choix de la photo, champs de texte de la section 2f, aperçu du billet d’un invité réel.

## 3. Un gabarit, trois sorties identiques

Pour garantir que l’écran, le PDF et l’email montrent exactement la même chose, il n’existe **qu’un seul rendu par document**, produit côté serveur.  **1**Gabarit HTML/CSS par document dans `backend/documents/templates/documents/quote.html` et `ticket.html`, mis en page en millimètres avec `@page` (taille, marges, numéros de page). Polices embarquées dans le dépôt (`backend/documents/fonts/`), jamais chargées depuis Internet. **2**WeasyPrint transforme ce gabarit en **PDF**. C’est la sortie maîtresse. **3**Le PDF est converti en **image PNG** (pypdfium2, 2× pour l’écran et l’email, 300 dpi pour l’impression) pour l’aperçu et l’email. **4****Aperçu à l’écran** : l’éditeur envoie les données à `POST /documents/preview` (anti-rebond 400 ms) et affiche l’image PNG renvoyée. On voit donc exactement le futur PDF. Le résultat est mis en cache Redis par empreinte des données pendant 10 minutes. **5**« Générer » ou « Télécharger le PDF » renvoie le PDF ; « Envoyer » envoie l’email décrit en section 9 avec ce même PDF.
- Le PDF final est stocké (stockage objet, préfixe de l’organisation) avec son empreinte SHA-256 et la version du gabarit. Un document envoyé n’est jamais regénéré en silence : une modification crée une nouvelle version.
- Le `url_fetcher` de WeasyPrint n’accepte que les fichiers du stockage de l’organisation et les ressources du gabarit : aucune requête réseau externe.
- Textes longs : réduction automatique de la taille de police jusqu’à un minimum défini, puis retour à la ligne, puis troncature avec « … » ; jamais de débordement hors de la zone.
- Devis de plusieurs pages : en-tête répété, tableau qui se poursuit avec la mention « Suite », totaux et signature uniquement sur la dernière page, « Page x sur y ».
- Génération en tâche Celery (file `pdf`) pour les envois et les lots ; l’aperçu reste synchrone et rapide (objectif : moins de 800 ms).

## 4. Identité de chaque entreprise

Ajoute dans Paramètres un onglet **« Identité des documents »** (propriétaire uniquement), avec aperçu en direct du devis et du billet remplis de données d’exemple.

| Champ | Détail |
|---|---|
| Logo | PNG, JPG ou SVG, 5 Mo max. Le serveur supprime les marges vides, crée une version transparente si le fond est uni, génère les tailles utiles et vérifie le contraste sur fond clair et foncé. Recadrage proposé à l’envoi |
| Nom commercial et raison sociale | Le nom commercial s’affiche en grand ; la raison sociale dans les mentions |
| Coordonnées | Adresse, ville, pays, téléphone(s), WhatsApp, email, site web, réseaux sociaux |
| Mentions légales | RCCM, NIF / NCC / numéro contribuable selon le pays, régime de TVA (assujetti ou non, taux) |
| Paiement | Coordonnées bancaires, numéros Mobile Money affichés sur le devis |
| Couleurs de marque | Couleur principale et secondaire, proposées automatiquement à partir du logo, modifiables. Option « Utiliser les couleurs du modèle » ou « Utiliser mes couleurs » : la mise en page reste celle de l’image de référence, seules les couleurs d’accent changent |
| Signature et cachet | Images facultatives placées dans la zone de signature du devis |
| Textes | Conditions générales, conditions de paiement, validité par défaut, message de pied de page, préfixe de numérotation |

- Sans logo : un monogramme (initiales du nom commercial sur la couleur principale) remplace le logo, à la même taille.
- Champ vide : la ligne correspondante disparaît proprement, sans laisser d’espace ni de libellé orphelin.
- La carte de démarrage du tableau de bord ajoute l’étape « Ajouter votre logo », et l’envoi du premier devis rappelle de compléter l’identité si elle est incomplète.
- Chaque document stocke une copie figée des informations de l’entreprise au moment de sa génération : modifier son adresse plus tard ne change pas les devis déjà envoyés.
- Les fichiers (logo, cachet, signature) sont stockés sous `org/{organization_id}/branding/`, servis par URL signée à durée limitée, et jamais accessibles par une autre organisation.
- La mention « Généré avec Wedivo » en pied de document est discrète et peut être retirée selon l’offre (option de l’offre Agence).

## 5. Devis
- Le gabarit `quote.html` reproduit l’image de `devis/`. Toutes les données variables viennent du devis : numéro, dates d’émission et de validité, client (nom, téléphone, email), mariage (date, lieu, nombre d’invités), lignes (désignation, description, quantité, unité, prix unitaire, montant), sous-total, remise, TVA le cas échéant, total, acompte, solde, conditions, signature et cachet, informations de l’entreprise.
- Si l’image de référence comporte un QR code, il pointe vers la page publique du devis (consultation, acceptation en ligne, paiement Mobile Money si FreeMoPay est connecté). Sinon, ajoute ce QR uniquement si l’analyse montre un emplacement naturel, et signale-le.
- Filigrane diagonal « BROUILLON » sur les brouillons, « ACCEPTÉ » discret sur un devis accepté, rien sur un devis envoyé.
- Montants au format FCFA de la section 6 du prompt principal ; montant total aussi écrit en toutes lettres en français si l’image le prévoit (« Un million cinq cent mille francs CFA »).
- Dans l’éditeur de devis, l’aperçu actuel (section 9 du complément) est remplacé par l’image PNG renvoyée par le serveur, dans le même cadre. Bouton « Générer le PDF » et menu « Télécharger », « Envoyer par email », « Copier le lien ».
- Même gabarit pour les documents dérivés : contrat et reçu de paiement reprennent l’en-tête et le pied du devis (identité de l’entreprise).

## 6. Billets
- Le gabarit `ticket.html` reproduit l’image de `billets/`. Un billet par invitation (une personne ou un groupe avec un nombre de places).
- Données variables : identité de l’agence (logo), titre de l’événement, prénoms des mariés, date, heure, lieu et adresse, nom de l’invité ou de la famille, nombre de places, catégorie (ex. VIP, Famille, Standard), table si renseignée, code lisible (`WDV-XX-0001`), QR code, message, et toute autre donnée visible sur l’image.
- Les couleurs et éléments décoratifs propres à un mariage (couleurs du thème choisies dans l’éditeur d’invitation) s’appliquent aux zones identifiées comme variables dans l’analyse ; la mise en page reste celle de l’image.
- **Écran « Billets »** du mariage :
  - Formulaire des informations communes (événement, date, lieu, catégories, message) avec aperçu PNG serveur à droite.
  - Liste des invités (ajout, import CSV/XLSX, nombre de places, catégorie, table, email, téléphone) avec statut du billet : non généré, généré, envoyé, ouvert, confirmé, entré, annulé.
  - Actions : « Générer » (un billet ou une sélection), « Générer tous les billets », « Télécharger » (PDF individuel, ou PDF unique de toutes les pages, ou archive ZIP d’un PDF par invité), « Envoyer par email », « Copier le lien », « Copier le message WhatsApp » avec le lien du billet, « Annuler le billet », « Réémettre ».
- Génération en lot dans Celery avec barre de progression ; 500 billets doivent être générés en moins de 3 minutes.
- Page publique du billet `/t/{token}` : l’invité voit son billet (image), peut le télécharger en PDF, l’ajouter à son calendrier (.ics), confirmer ou décliner sa présence. Cette page n’enregistre jamais d’entrée.

## 7. QR codes
- Le QR encode l’URL `https://{slug}.wedivo.app/t/{token}`. Ainsi, un téléphone ordinaire ouvre le billet de l’invité, et l’application de scan reconnaît le même QR pour le contrôle.
- `token` = identifiant aléatoire du billet (16 octets) + signature HMAC-SHA256 tronquée à 10 octets, le tout en base64url. La clé HMAC est dérivée (HKDF) de la clé maîtresse du coffre (prompt FreeMoPay, section 5) avec un sel propre à l’organisation. Aucune clé écrite dans le code.
- Génération avec `segno` en SVG vectoriel dans le PDF : correction d’erreur niveau Q, zone de silence de 4 modules, taille au moins égale à celle de l’image de référence et jamais sous 25 mm imprimés.
- Réémettre un billet crée un nouveau token : l’ancien QR devient « Annulé » au scan.
- Le code lisible (`WDV-KS-0001`) permet la saisie manuelle si le QR est abîmé.

## 8. Scan à l’entrée

### Accès
- Écran `/scan` (application web installable, plein écran, pensée pour le téléphone) accessible aux membres de l’agence.
- Pour le personnel externe (sécurité, hôtesses) : « Lien contrôleur » créé par événement avec un code PIN à 6 chiffres, valable de la veille au lendemain du mariage, révocable, limité au scan de cet événement. Chaque appareil enregistré apparaît dans la liste et peut être déconnecté.

### Fonctionnement
- Caméra arrière par défaut, bascule avant/arrière, lampe torche si disponible. Lecture avec l’API `BarcodeDetector` quand le navigateur la propose, sinon `zxing-wasm`. Scan continu, anti-doublon de 3 s sur le même code.
- Saisie manuelle du code en secours.
- Résultat plein écran, lisible à distance, avec son et vibration :
  - **Valide** (vert) : nom, nombre de places, catégorie, table. Pour un groupe, choix du nombre de personnes qui entrent maintenant (ex. 2 sur 4) ; les places restantes pourront entrer plus tard.
  - **Déjà utilisé** (rouge) : heure du premier passage, appareil ou contrôleur, places déjà entrées.
  - **Annulé** (gris), **Autre événement** (orange, nom de l’événement), **Pas encore ouvert** ou **Événement terminé** (orange), **Billet invalide** (rouge, signature fausse ou code inconnu).
  - **Invité ayant décliné** (orange) : entrée possible après confirmation du contrôleur.
- Compteur en haut : « 142 / 320 personnes entrées », avec historique des derniers scans.

### Hors connexion
- Bouton « Préparer le mode hors ligne » avant l’événement : télécharge dans IndexedDB la liste des empreintes (SHA-256) des tokens valides de l’événement, avec nom, places et catégorie. Aucune clé de signature n’est envoyée à l’appareil.
- Sans réseau, le scan est validé contre cette liste ; les entrées sont mises en file et synchronisées dès le retour du réseau. En cas d’entrée du même billet sur deux appareils hors ligne, la première heure l’emporte et l’agence reçoit une alerte de doublon.
- Un bandeau indique clairement « Hors ligne, 12 entrées en attente de synchronisation ».

### Côté serveur
- `POST /checkin` vérifie la signature HMAC, l’organisation, l’événement, la fenêtre horaire, le statut, puis enregistre l’entrée sous verrou (`select_for_update`) : deux scans simultanés du même billet ne donnent jamais deux entrées. Chaque scan porte un identifiant unique pour être idempotent.
- Tableau de bord de l’événement : arrivées en direct (mise à jour toutes les 10 s), courbe des arrivées par quart d’heure, répartition par catégorie, liste des absents, export CSV.

## 9. Emails
- Expéditeur affiché : le nom commercial de l’agence ; adresse d’envoi sur le domaine Wedivo (SPF, DKIM, DMARC configurés) ; `Reply-To` = email de l’agence.
- Corps HTML compatible avec les clients mail (tableaux, CSS en ligne, largeur 600 px, pas de JavaScript ni de police web obligatoire), aux couleurs de l’agence, avec son logo en en-tête.
- **Devis** : objet « Devis {numéro} de {agence} pour votre mariage » ; image PNG de la première page du devis (identique au PDF), montant total, validité, bouton « Voir et accepter le devis » (page publique), PDF en pièce jointe.
- **Billet** : objet « Votre billet pour le mariage de {prénoms} » ; image PNG du billet complet (identique au PDF), bouton « Ouvrir mon billet », bouton « Confirmer ma présence », fichier .ics, PDF en pièce jointe. Le QR est lisible directement depuis l’image de l’email.
- Version texte brut systématique ; images avec texte alternatif.
- Envoi par Celery, une tentative par destinataire, suivi de délivrance et d’ouverture via les webhooks du fournisseur email, statut visible dans la liste (envoyé, ouvert, échec avec motif).
- Limite d’envoi par organisation et par heure (configurable) pour protéger la réputation du domaine.

## 10. Modèle de données et API

| Modèle | Champs |
|---|---|
| OrganizationBranding | organization (1-1), logo, logo_on_dark, monogram_color, primary_color, secondary_color, use_brand_colors, legal_name, trade_name, address, phones, whatsapp, email, website, socials, tax_ids (JSON par pays), vat_rate, bank_details, mobile_money_numbers, signature_image, stamp_image, quote_terms, payment_terms, footer_text, show_wedivo_mention |
| DocumentTemplate | kind (quote, ticket, contract, receipt), version, path, page_size, is_default. Les versions permettent de faire évoluer le design sans changer les documents déjà envoyés |
| GeneratedDocument | organization, kind, object (devis, billet…), template_version, data_snapshot (JSON), pdf_file, png_file, sha256, created_by, created_at |
| Ticket | organization, wedding, guest, token_hash, code, seats, category, table, status (active, cancelled, reissued), issued_at, sent_at, opened_at, rsvp_status, document (FK GeneratedDocument) |
| CheckIn | organization, ticket, seats_entered, scanned_at, device, scanner (user ou lien contrôleur), scan_id (unique), offline (bool), synced_at |
| ScannerAccess | organization, wedding, pin_hash, valid_from, valid_until, revoked_at, devices (JSON) |
| EmailDelivery | organization, kind, object, recipient, provider_id, status, error, opened_at |

| Méthode | Endpoint |
|---|---|
| GET, PATCH | /organization/branding · POST /organization/branding/logo |
| POST | /documents/preview (kind, données ou id) → PNG |
| POST, GET | /quotes/{id}/generate · /quotes/{id}/pdf · /quotes/{id}/send |
| CRUD | /weddings/{id}/tickets · POST /weddings/{id}/tickets/generate · /send · /export (pdf, zip) |
| POST | /tickets/{id}/cancel · /tickets/{id}/reissue |
| GET | /public/t/{token} · /public/t/{token}/pdf · /public/t/{token}/ics · POST /public/t/{token}/rsvp |
| POST, GET | /weddings/{id}/scanner-access · /scan/session (PIN) · /scan/offline-pack · POST /checkin · POST /checkin/sync |
| GET | /weddings/{id}/attendance (arrivées en direct) |

## 11. Sécurité
- Isolation stricte : logos, documents, billets et entrées d’une agence ne sont jamais accessibles par une autre (RLS + préfixe de stockage + tests).
- Fichiers envoyés : vérification du type réel (pas seulement l’extension), SVG nettoyé (suppression des scripts et liens externes) ou converti en PNG, taille limitée.
- Pages publiques des devis et billets : tokens non devinables, en-tête `noindex`, `Referrer-Policy: no-referrer`, limite de débit, aucune donnée d’un autre invité visible.
- Scan : PIN haché, 5 essais puis blocage 15 min, sessions de contrôleur limitées à un événement et à une période.
- Aucune clé dans le code : la clé HMAC des billets est dérivée de la clé maîtresse du coffre.
- Journal d’audit : génération et envoi de lots, annulation et réémission de billets, création et révocation des liens contrôleur, entrées forcées.

## 12. Tests
- **Fidélité visuelle** : avec `donnees-exemple.json`, générer le devis et le billet, convertir en PNG à la résolution de l’image de référence, et comparer (SSIM ≥ 0,90 sur chaque zone, revue côte à côte et carte des différences enregistrée dans `docs/rendus/diff/`). Le test échoue en dessous du seuil.
- **Parité des sorties** : l’image d’aperçu, l’image de l’email et le PDF converti doivent être identiques pixel pour pixel pour les mêmes données.
- **Multi-entreprise** : deux agences avec des logos et couleurs différents génèrent chacune un devis et un billet ; vérifier sur le PNG que le logo est le bon, et qu’aucune ne peut lire les fichiers de l’autre.
- **Cas limites** : sans logo, logo très large ou très haut, noms très longs, 40 lignes de devis (plusieurs pages), champs vides, caractères accentués et apostrophes typographiques.
- **QR** : décoder chaque QR généré (pyzbar ou zxing) et retrouver le bon token ; QR avec signature modifiée refusé.
- **Scan** : billet valide, déjà utilisé, annulé, réémis, autre événement, hors fenêtre, groupe en plusieurs fois, deux scans simultanés, synchronisation hors ligne avec conflit.
- **Emails** : rendu HTML validé, pièces jointes présentes, texte brut présent, en-têtes corrects.
- Playwright : générer et télécharger un devis, envoyer un billet, scanner un billet (flux vidéo simulé avec une image de QR).

## 13. Définition de terminé
- Le devis et le billet générés avec les données d’exemple se superposent aux images de `devis/` et `billets/` (test de fidélité vert).
- L’aperçu écran, le PDF et l’email montrent le même rendu.
- Une nouvelle agence qui crée son compte et ajoute son logo obtient immédiatement des devis et billets à son nom, sans aucune intervention technique.
- Un billet peut être généré, envoyé, ouvert par l’invité, confirmé, scanné à l’entrée une seule fois, y compris sans réseau.
- Tous les tests passent, et `docs/rendus/` contient l’analyse, les données d’exemple et les captures de comparaison.

## Prompts d’exécution par étape

À lancer dans l’ordre. Relire l’analyse produite à l’étape R1 avant de passer à R2.

- **Étape R1 — Analyse des images de référence.** Lis la section « Devis, billets, QR et scan » de CLAUDE.md. Renomme les images selon la section 2b puis ouvre-les toutes. Sans écrire de code applicatif, rédige docs/rendus/analyse-devis.md, docs/rendus/analyse-billet.md et docs/rendus/donnees-exemple.json selon la section 2 : format, zones mesurées en mm, chaque élément avec police, taille, couleur hexadécimale, position, et son caractère fixe ou variable avec la donnée Wedivo correspondante. Termine par la liste des points incertains et attends ma validation.
- **Étape R2 — Identité des entreprises.** Implémente la section 4 : modèle OrganizationBranding, traitement du logo (rognage, transparence, tailles, monogramme de secours), extraction des couleurs, nettoyage des SVG, stockage par organisation avec URL signées, onglet Paramètres › Identité des documents avec aperçu, étape « Ajouter votre logo » dans la carte de démarrage. Mets à jour seed_demo avec l’identité complète de Maison Élégance Events et une identité différente pour Atelier Bassam Mariages. Tests d’isolation.
- **Étape R3 — Moteur de rendu et devis.** Implémente la section 3 (gabarit unique, WeasyPrint, conversion PNG, endpoint de preview avec cache, url_fetcher restreint, polices embarquées, gestion des textes longs et des pages multiples, GeneratedDocument et DocumentTemplate versionnés), puis les gabarits des 4 modèles de devis A, B, C et D (sections 2b, 2c, 2d, 2e), pilotés uniquement par les variables de palette, avec le cas des partenaires et des deux signatures. Remplace l’aperçu de l’éditeur de devis par l’image serveur. Ajoute le test de fidélité visuelle et de parité de la section 12 pour le devis, et itère jusqu’à SSIM ≥ 0,90.
- **Étape R4 — Billets.** Implémente la section 6 et la section 7 : modèle Ticket, tokens signés HMAC dérivés de la clé maîtresse, QR segno vectoriel, gabarit ticket.html fidèle à la section 2b dans toutes les palettes (noir et or, bleu royal, émeraude et or et les autres), nom de l’invité et nombre de places sur le talon, code-barres Code 128, écran Billets du mariage (liste des invités, génération unitaire et en lot avec progression, exports PDF et ZIP, annulation, réémission), page publique /t/{token} avec PDF, .ics et confirmation de présence. Test de fidélité visuelle du billet jusqu’à SSIM ≥ 0,90 et décodage des QR.
- **Étape R4b — Galerie des modèles et palettes.** Implémente les sections 2c, 2f et 2g : palettes en base (modifiables par le super-admin), palette « Couleurs de l’agence » calculée avec contrôle du contraste, séries de photos par palette et téléversement de photos par l’agence ou par mariage, textes personnalisables avec longueurs maximales, galerie Paramètres › Identité des documents › Modèles, sélecteurs de modèle et de palette dans l’éditeur de devis et dans l’écran Billets. Génère une planche de contrôle docs/rendus/planche.png avec chaque modèle dans chaque palette.
- **Étape R5 — Emails.** Implémente la section 9 pour le devis et le billet : HTML compatible clients mail aux couleurs de l’agence, image PNG identique au PDF, boutons, pièces jointes, .ics, version texte, envoi Celery, suivi de délivrance et d’ouverture, limites d’envoi. Tests de la section 12 pour les emails.
- **Étape R6 — Scan et contrôle à l’entrée.** Implémente la section 8 : écran /scan installable avec BarcodeDetector et repli zxing-wasm, résultats plein écran avec son et vibration, entrées partielles pour les groupes, saisie manuelle, liens contrôleur avec PIN, mode hors ligne avec IndexedDB et synchronisation, endpoint /checkin sous verrou et idempotent, tableau des arrivées en direct et export. Tous les tests de scan de la section 12, puis vérifie chaque point de la section 13 et rends un rapport.
