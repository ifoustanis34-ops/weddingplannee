# Complément Wedivo — fidélité au prototype et données fictives

> Source : « wedivo-prompt-complement.html ». Complète `CLAUDE.md` (spécifications initiales).
> Référence visuelle : `docs/prototype/wedivo-plateforme.html`. Logo : `docs/brand/`.

## 1. Source de vérité visuelle

Le fichier `docs/prototype/wedivo-plateforme.html` est la référence visuelle et ergonomique de Wedivo. L’application Vue doit le reproduire à l’identique : mêmes couleurs, polices, tailles, espacements, rayons, ombres, textes, icônes, ordre des éléments, comportements et adaptations mobiles.

**Règle d’arbitrage.** Pour l’apparence, les textes et l’organisation des écrans, le prototype l’emporte sur le premier prompt. Pour la logique métier, la sécurité, l’isolation multi-tenant et l’architecture, le premier prompt l’emporte. Les données du prototype sont codées en dur : dans l’application, tout vient de l’API.

- Avant de coder un écran, ouvrir le prototype, lire son CSS (balise `<style>`) et la fonction JavaScript de la vue correspondante (`vDash`, `vProspects`, `vBuilder`…).
- Reprendre les valeurs CSS telles quelles. Ne pas arrondir, ne pas remplacer une couleur par la palette par défaut de Tailwind.
- Pour se connecter au prototype : bouton « Se connecter » (identifiants préremplis). Le menu donne accès à tous les écrans.

## 2. Corrections du premier prompt

| Sujet | Premier prompt | À appliquer |
|---|---|---|
| Polices | Sora + Manrope | Sora (titres, montants), Manrope (interface) et **Cormorant Garamond** uniquement dans l’aperçu et le PDF des invitations |
| Graphique des encaissements | Apache ECharts | Composant SVG maison `WAreaChart` qui reproduit exactement la courbe du prototype (section 7). ECharts n’est pas nécessaire |
| Tailwind | Preset sur les tokens | Les tokens sont des variables CSS (section 3). Tailwind ne fait que les référencer (`bg-[var(--surface)]` ou thème étendu). Aucune couleur Tailwind par défaut (gray, indigo…) |
| Icônes | lucide-vue-next | lucide-vue-next avec `stroke-width` 1.8, taille 18 px (22 px dans la barre mobile, 15 px dans les petits boutons) |
| Thème sombre | Jeu partiel | Jeu complet de la section 3, y compris les couleurs « soft » |
| Badges de phase | Non mentionnés | Le menu affiche « P2 » et « P3 » à droite des modules concernés. Les piloter par un feature flag pour les retirer à la mise en production du module |
| Liste de tâches standard | Non détaillée | Les 12 tâches de la section 11 |
| Page « Architecture technique » | — | Documentation, pas un écran du produit. Ne pas la développer |
| Indicateurs | — | Valeurs fixes dans le prototype ; règles de calcul réelles en section 16 |
| Données de démonstration | Une phrase | Jeu complet de la section 17, identique au prototype |

## 3. Tokens complets (à copier tels quels)

```css
/* frontend/src/design/tokens.css */
:root{
  --bg:#F5F4FA; --surface:#FFFFFF; --surface-2:#F1EFF8; --surface-3:#E9E6F4;
  --ink:#17153B; --ink-2:#4A4769; --muted:#85829F; --line:#E5E2F0; --line-2:#D6D2E6;
  --violet:#5126C2; --violet-ink:#FFFFFF; --violet-soft:#EEE8FD;
  --fuchsia:#C42C7E; --fuchsia-soft:#FCE6F1;
  --coral:#E3622F; --coral-soft:#FEEBE2;
  --gold:#B97A0E; --gold-soft:#FDF2DC; --gold-bright:#F4A62A;
  --green:#0E8F69; --green-soft:#DFF4EC;
  --red:#D23A50; --red-soft:#FCE6EA;
  --grey-soft:#EEEDF3;
  --hero:#17153B; --hero-ink:#FFFFFF; --hero-muted:#A9A5CC;
  --ribbon:linear-gradient(118deg,#4A22B5 0%,#8E2BA8 42%,#E03E7D 70%,#F68A45 100%);
  --shadow:0 1px 2px rgba(23,21,59,.05),0 8px 24px -12px rgba(23,21,59,.12);
  --shadow-lg:0 24px 60px -20px rgba(23,21,59,.35);
  --r-sm:8px; --r:12px; --r-lg:18px; --sidebar:252px;
  color-scheme:light;
}
/* Sombre : appliqué via prefers-color-scheme ET :root[data-theme="dark"] (choix mémorisé) */
:root[data-theme="dark"]{
  --bg:#0D0C20; --surface:#16152E; --surface-2:#1E1C3A; --surface-3:#28264A;
  --ink:#F2F1FA; --ink-2:#C6C3DE; --muted:#8C89AD; --line:#29274A; --line-2:#36345A;
  --violet:#9F82FF; --violet-ink:#120F2C; --violet-soft:#29225A;
  --fuchsia:#F06AB0; --fuchsia-soft:#3A1830; --coral:#FF925F; --coral-soft:#3A2016;
  --gold:#F4B54A; --gold-soft:#36290F; --green:#3DD3A0; --green-soft:#10302A;
  --red:#FF6F85; --red-soft:#3B1822; --grey-soft:#24223F;
  --hero:#221F4C; --hero-muted:#ABA7D6;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px -12px rgba(0,0,0,.5);
  color-scheme:dark;
}
body{background:var(--bg);color:var(--ink);font:500 14.5px/1.55 Manrope,"Segoe UI",system-ui,sans-serif}
h1,h2,h3{font-family:Sora,Manrope,sans-serif;letter-spacing:-.015em}
h1{font-size:26px;font-weight:600;line-height:1.2}   /* 22px sous 960px */
h2{font-size:17px;font-weight:600}
h3{font-size:15px;font-weight:600}
.num{font-family:Sora;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
:focus-visible{outline:2px solid var(--violet);outline-offset:2px;border-radius:6px}
```

Google Fonts : `Sora:wght@400;500;600;700`, `Manrope:wght@400;500;600;700;800`, `Cormorant Garamond:ital,wght@0,500;0,600;1,500`.

### Rubans décoratifs (symbole SVG réutilisé)

```html
<linearGradient id="gRib" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#5A2BD0"/><stop offset=".45" stop-color="#A12FA4"/>
  <stop offset=".75" stop-color="#E5407B"/><stop offset="1" stop-color="#F7934A"/>
</linearGradient>
<symbol id="ribbons" viewBox="0 0 400 300">
  <path d="M20 40 C 70 30, 110 120, 150 210 C 175 265, 220 270, 250 230 C 290 170, 300 90, 380 60"
        fill="none" stroke="url(#gRib)" stroke-width="38" stroke-linecap="round" opacity=".9"/>
  <path d="M120 20 C 170 20, 210 110, 235 170 C 255 220, 300 250, 370 240"
        fill="none" stroke="url(#gRib)" stroke-width="14" stroke-linecap="round" opacity=".45"/>
  <path d="M318 26 l7 15 15 7 -15 7 -7 15 -7 -15 -15 -7 15 -7z" fill="#F4A62A"/>
</symbol>
```

Logotype : symbole du logo détouré (fond transparent) à 40 px de large + texte « Wedivo » en Sora 700, 22 px, interlettrage −0,03em. Le « i » est un i sans point (`ı`) surmonté d’un point rond `--gold-bright` de 0,24em.

## 4. Spécifications des composants

| Composant | Spécification exacte |
|---|---|
| WButton | Hauteur 40, padding 0 16, rayon 10, bordure 1px `--line-2`, fond `--surface`, Manrope 700 14px, écart icône 8. Survol : `--surface-2`. Appui : translateY(1px). **primary** : fond et bordure `--violet`, texte `--violet-ink`, survol brightness(1.08). **ghost** : transparent. **sm** : hauteur 32, padding 0 11, 13px, rayon 8. **icon** : carré 40 (ou 32 en sm). Désactivé : opacité .5 |
| WInput / WSelect | Hauteur 42, padding 0 12, rayon 10, bordure `--line-2`. Focus : bordure `--violet` + halo 3px `--violet-soft`. Textarea : min 84px, padding 10 12 |
| Libellés | 13px 700 `--ink-2`, écart 6px avec le champ. Aide : 12,5px `--muted`. Erreur : 13,5px 700 `--red` |
| Groupe de saisie | Champ + suffixe gris (`--surface-2`, texte `--muted`) dans un même cadre arrondi : « .wedivo.app », « % », « jours » |
| WSwitch | 42×24, rail `--line-2`, bouton blanc 18px avec ombre ; activé : rail `--green`. `role="switch"` |
| WBadge | Pilule hauteur 24, padding 0 9, 12px 700, point de 6px de la couleur du texte (variante **plain** sans point). Fond « soft » + texte de la couleur : violet, fuchsia, coral, gold, green, red, grey (`--grey-soft`/`--muted`) |
| Étiquette de phase | 11px 700, padding 2 7, rayon 6, fond `--surface-3`, texte `--ink-2` |
| WCard | Fond `--surface`, bordure 1px `--line`, rayon 18, padding 20. En-tête : titre h2 + sous-titre 13px `--muted` à gauche, action (bouton sm) à droite, marge basse 16 |
| Tuile | Rayon 18, padding 16 18 ; libellé 13px 600 muted ; valeur Sora 600 21px, interlettrage −.02em. Variante **dark** : fond `--hero`, texte blanc, libellé `--hero-muted`. Grille de 4 (2 sous 1000px), écart 14 |
| WTable | En-têtes 12,5px 700 muted, padding 10 12, filet bas ; cellules padding 13 12 ; largeur minimale 640 et défilement horizontal dans la carte ; lignes cliquables : survol `--surface-2`. Montants alignés à droite en Sora tabulaire |
| WTabs | Boutons texte 700 muted, padding 10 14 ; actif : texte ink + soulignement 2px violet ; filet bas 1px |
| Puces de filtre | Hauteur 32, pilule, bordure `--line-2`, 13px 700 ; active : fond `--ink`, texte `--surface` |
| WDrawer | À droite, largeur min(500px, 100%), ombre `--shadow-lg`, entrée 0,22s depuis 40px. En-tête padding 20 avec bouton fermer ; corps padding 20, écart 20 ; pied avec boutons, filet haut |
| WModal | Centrée, largeur min(560px, 100% − 24px), rayon 20, en-tête / corps / pied séparés par des filets, apparition 0,18s (échelle .98 → 1). Pied : « Annuler » + action principale à droite |
| Voile | `rgba(13,12,32,.5)` + flou 2px ; clic ou Échap ferme |
| WToast | Bas droite (mobile : pleine largeur au-dessus de la barre d’onglets), fond `--hero`, texte blanc 600 14px, rayon 12, icône coche `#5DE3B4` ou alerte `#FFB27A`, durée 3,6 s, pile verticale |
| WProgress | Hauteur 6, rayon 6, fond `--surface-2` ; remplissage violet, ou dégradé ruban pour les mariages |
| Bloc date | Largeur 46, fond `--surface-2`, rayon 10 ; jour Sora 600 17px ; mois abrégé 11px 700 muted (« oct. ») |
| Icône de canal | 36×36, rayon 10, fond soft : Email violet (mail), Appel gold (phone), WhatsApp green, Tâche interne grey (check) |
| Avatar | Rond 34, fond dégradé ruban, initiales blanches 12,5px 800. Avatar entreprise : carré rayon 9, fond `--hero`, Sora 600 13px |
| Note | Fond `--surface-2`, rayon 12, padding 12 14, icône info violette, texte 13,5px `--ink-2` |
| Bandeau d’alerte | Fond `--coral-soft`, rayon 14, padding 14 16 ; icône alerte corail dans un carré blanc 38 rayon 10 ; titre gras + texte 13,5px ; bouton principal à droite |
| État vide | Bordure pointillée `--line-2`, rayon 12, padding 28, texte centré muted |
| Palette Ctrl+K | En haut à 12vh, largeur min(600px, 100% − 24px), rayon 16 ; champ 54px de haut, 16px ; résultats groupés « Pages », « Prospects et clients », « Devis », 12 maximum, premier sélectionné, Entrée ouvre |

## 5. Coquille de l’application

### Bureau (plus de 960 px)
- Grille : barre latérale 252px + contenu. Barre latérale collante pleine hauteur, fond `--surface`, bordure droite, padding 18 14 14.
- Haut de la barre : logotype (padding 4 8 18), puis bloc entreprise (bouton fond `--surface-2`, rayon 12, padding 10) : avatar entreprise, nom (13,5px gras, tronqué), adresse `slug.wedivo.app` (12px muted, tronquée). Clic → Paramètres › Entreprise.
- Navigation, dans cet ordre exact (titres de groupe 12px 700 muted, padding 14 10 6) :
  - **Pilotage** : Tableau de bord (home)
  - **Commercial** : Prospects & clients (users) · Devis (file-text) · Relances (refresh-cw, pastille fuchsia avec le nombre de relances du jour) · Paiements & finances (wallet)
  - **Organisation** : Mariages (heart, P2) · Calendrier (calendar, P2) · Prestataires (briefcase, P2) · Invitations & QR (mail, P3)
  - **Espace** : Paramètres (settings)
- Lien : padding 9 10, rayon 10, Manrope 600 14px `--ink-2`, écart icône 11. Survol et actif : fond `--surface-2`, texte ink. Actif : barre verticale de 4px en dégradé ruban collée au bord gauche de la barre latérale (left −14px, top/bottom 8px, rayon 0 4 4 0).
- Bas : filet haut, avatar, nom (13,5px gras), rôle (12px muted), bouton fantôme « Se déconnecter » (logout).
- Barre supérieure collante : padding 12 clamp(16px,3vw,32px), fond `--bg` à 86 % + flou 10px, filet bas. À gauche, bouton de recherche (hauteur 40, max 420px, fond surface, icône loupe, texte « Rechercher un client, un devis… », touche « Ctrl K » à droite). À droite : bouton thème (lune), bouton cloche avec point corail 8px → Relances.
- Zone de contenu : padding 26 clamp(16px,3vw,32px) 48, largeur max 1360.
- En-tête de page : h1 + sous-titre muted (max 64 caractères par ligne) à gauche, boutons à droite (passent à la ligne si besoin), marge basse 22.

### Mobile (960 px et moins)
- Barre latérale en tiroir de 282px depuis la gauche, voile `rgba(13,12,32,.45)`, bouton menu (≡) à gauche de la recherche ; « Ctrl K » masqué ; h1 22px.
- Barre d’onglets fixe en bas, 5 colonnes : Accueil (home), Prospects (users), Devis (file-text), Finances (wallet), Plus (grid → ouvre le tiroir). Icônes 22px, libellés 11px 700, actif violet, fond surface à 92 % + flou, marge de sécurité iOS en bas. Le contenu garde 110px de marge basse.
- Changer de page ferme le tiroir et remonte en haut.

## 6. Connexion et création de compte

- Grille : panneau de marque 44 % (min 360px) + formulaire. Sous 900px : une colonne, panneau réduit (padding 28 22, titre 24px, cartes et rubans masqués).
- Panneau de marque : fond `--hero`, padding 48 clamp(28px,5vw,64px) ; logotype blanc ; titre « Moins d’administratif, plus de mariages réussis. » (Sora 600, clamp(28px,3.2vw,40px), max 13 caractères de large par ligne) ; slogan « Planifiez · Gérez · Célébrez » en `--hero-muted` ; trois cartes translucides (fond blanc 6 %, bordure blanche 10 %, rayon 14, icône dans un carré 30 rayon 9) :
  - « Un devis en 20 minutes » — « Catalogue, calculs et PDF générés pour vous. »
  - « Aucune relance oubliée » — « Devis, paiements et rendez-vous suivis automatiquement. »
  - « Votre trésorerie, en clair » — « Encaissé, solde à recevoir et marge par mariage. »

  Rubans SVG en bas à droite (560px, décalés −120px / −60px).
- Formulaire centré, largeur max 460. Sélecteur segmenté (fond surface-2, padding 4, rayon 12 ; onglet actif surface + ombre) : « Se connecter » | « Créer un compte entreprise ».
- Connexion : h1 « Bon retour », sous-titre « Connectez-vous à l’espace de votre agence. », Email professionnel, Mot de passe (lien « Mot de passe oublié ? » à droite du libellé), bouton principal pleine largeur 46px « Se connecter ».
- Inscription : h1 « Créer l’espace de votre agence », sous-titre « Trois étapes, environ deux minutes. », indicateur de 3 barres de 4px (violettes une fois atteintes) libellées « 1. Entreprise », « 2. Votre compte », « 3. Votre espace ». Boutons « Retour » et « Continuer » / « Créer mon espace » (46px).
- Étape 1 : Nom de l’entreprise (placeholder « Ex. Maison Élégance Events »), Ville, Pays (Côte d’Ivoire, Sénégal, Cameroun, Bénin, Togo, Burkina Faso, Mali, Gabon), Mariages organisés par an (Moins de 10, 10 à 30, 30 à 60, Plus de 60).
- Étape 2 : Nom complet, Email professionnel, Téléphone (WhatsApp), Mot de passe (aide « 8 caractères minimum. »).
- Étape 3 : Adresse de votre espace (suffixe « .wedivo.app », proposée depuis le nom sans accents), offres en cartes radio (nom, description, prix à droite « 35 000 FCFA / mois » ; sélection : bordure violette + halo), aide « 14 jours d’essai gratuit, sans moyen de paiement. ».
- Messages d’erreur : « Indiquez le nom de votre entreprise. », « Indiquez votre nom complet. », « Cette adresse email n’est pas valide. », « Le mot de passe doit contenir au moins 8 caractères. », « L’adresse doit contenir au moins 3 caractères. ». Succès : toast « Espace {slug}.wedivo.app créé ».

## 7. Tableau de bord

- h1 « Bonjour {prénom} ». Sous-titre : « {Jour date complète}. {n} relances à traiter et le mariage de {couple} dans {x} jours. » Boutons : « Nouveau prospect » (+), « Créer un devis » (principal, icône fichier).
- **Carte de démarrage** (comptes neufs uniquement) : « Bienvenue sur Wedivo, votre espace est prêt. » / « Trois étapes pour envoyer votre premier devis. » + trois boutons avec cercle à cocher : « Compléter votre catalogue », « Ajouter vos prospects », « Inviter votre équipe ». Étape faite : coche verte et texte barré. Quand tout est fait, la carte disparaît avec le toast « Votre espace est prêt. Bon travail ! ».
- **Ligne 1** (1,1fr / 1fr, empilée sous 1100px) :
  - Carte solde : fond `--hero`, rayon 22, padding 26 26 24, hauteur min 248, rubans SVG en haut à droite (340px, décalés −70 / −40). Libellé « Solde à recevoir sur vos contrats » ; montant Sora 600 clamp(32px,4.4vw,46px), interlettrage −.035em, suivi de « FCFA » à .42em en hero-muted ; trois chiffres : « Déjà encaissé », « Contrats signés », « Marge prévisionnelle » (format court « 7,67 M ») ; boutons blanc « Enregistrer un paiement » et translucide « Voir l’échéancier ».
  - Carte indicateurs 2×2 sans padding, cases séparées par des filets : « Prospects actifs » (« +4 cette semaine » vert), « Taux de conversion » (« +8 pts sur 3 mois »), « Devis en attente » (« 9,35 M en jeu » muted), « Temps gagné ce mois » (« Estimation devis + relances » muted). Valeur Sora 600 24px.
- **Ligne 2** (1,35fr / 1fr) :
  - « Encaissements » / « Six derniers mois, en millions de FCFA » + badge vert « +28 % vs période précédente ». **WAreaChart** : viewBox 600×230, marges latérales 34, courbe lissée (points de contrôle au milieu horizontal de chaque segment), trait 3,5px dégradé ruban, aire dégradée `#8E2BA8` 28 % → 0, lignes de grille à 0 (pleine), 2, 4, 6 (pointillés 3/5), graduations à gauche, mois en bas (« mai, juin, juil., août, sept., oct. »), points de 3,5 (fond surface, contour `#A12FA4`), dernier point 6 rempli `#E5407B` avec étiquette sombre 72×28 rayon 8 « 6,3 M ».
  - « Pipeline commercial » / « Prospects par étape et budget estimé » + bouton « Ouvrir ». Une ligne par statut sauf « Perdu » : grille 120px / 1fr / 72px ; nom gras + « n prospects » ; barre 10px de la couleur du statut ; total au format court à droite.
- **Ligne 3** (deux colonnes égales) : « Relances du jour » / « Générées par vos règles automatiques » + « Tout voir » (icône canal, nom, motif, bouton « Marquer faite » ou badge « Faite » ; vide : « Toutes les relances du jour sont faites. ») et « Prochains mariages » / « Avancement de la préparation » + « Tout voir » (bloc date, couple, « lieu, J-x », barre ruban, pourcentage ; clic → tiroir du mariage).

## 8. Prospects & clients

- h1 « Prospects & clients ». Sous-titre « Toutes vos demandes au même endroit, quel que soit le canal. Glissez une carte pour changer son statut. » Boutons « Importer », « Nouveau prospect ».
- Barre d’outils : recherche (icône loupe, « Rechercher un nom, un besoin… », max 340px) et liste « Tous les canaux ».
- Kanban de 6 colonnes (largeur min 258, défilement horizontal) : Nouveau (violet), Contacté (gold), Devis envoyé (fuchsia), Négociation (coral), Client confirmé (green), Perdu (muted). Colonne : fond `--surface-2`, rayon 18, padding 12, hauteur min 320 ; en-tête : point 9px, nom, compteur en pilule, total au format court à droite. Survol en glisser : contour intérieur 2px violet et fond violet-soft. Colonne vide : « Aucun prospect ».
- Carte : fond surface, bordure, rayon 12, padding 12 13 ; nom 14px 800 ; besoins 12,5px muted sur 2 lignes maximum ; bas : canal (carré coloré 8px + nom 11,5px) et budget Sora à droite ; pastille corail « Relance aujourd’hui / demain » si la relance est dans moins d’un jour. Couleurs de canal : WhatsApp `#25D366`, Instagram `#D62976`, Facebook `#1877F2`, Téléphone `#8A87A6`, Recommandation `#F4A62A`.
- Toasts : « {nom} passe en « {statut} » », puis si confirmé « Pensez à convertir son devis en contrat. ».
- Tiroir : avatar 44, nom, badge de statut et canal ; liste « Statut » ; grille 2 colonnes Téléphone / Date du mariage / Budget annoncé / Prochaine relance (« Aucune » ou « date (demain) ») ; « Besoins » ; « Programmer une relance » (date + « Programmer ») ; « Historique » en frise verticale (filet 2px, ronds 12px bordés de violet, date en dessous) ; pied « Appeler » (lien tel:) et « Créer un devis » (ouvre l’éditeur avec le client prérempli).
- Modale « Nouveau prospect » : Nom ou couple (« Ex. Awa & Koffi Mensah »), Téléphone, Canal, Date du mariage, Budget annoncé (FCFA), Besoins (« Nombre d’invités, lieu, prestations souhaitées… »), case « Me rappeler de le contacter demain » ; bouton « Ajouter le prospect » ; toast « {nom} ajouté aux prospects ».
- Modale « Importer des prospects » : texte explicatif + zone de dépôt « Déposez votre fichier ici » / « CSV ou XLSX, 5 Mo maximum ».

## 9. Devis

### Liste
- h1 « Devis », sous-titre « Préparez un devis à partir de votre catalogue, envoyez-le et suivez la réponse du client. » Boutons « Gérer le catalogue », « Nouveau devis ».
- 4 tuiles (la première en variante dark) : « Temps moyen de création », « Envoyés ce mois », « Taux d’acceptation », « Montant en attente ».
- Carte avec onglets « Tous, Brouillons, Envoyés, Acceptés, Refusés » + compteur muted. Tableau : Numéro, Client, Date, Montant, Statut, Action. Badges : Brouillon grey, Envoyé violet, Accepté green, Refusé red, Expiré grey. Actions : brouillon → « Envoyer » ; envoyé → « Marquer accepté » ; accepté → « Convertir en contrat » (principal) puis texte « Contrat créé » ; refusé → « — ». Vide : « Aucun devis dans cette catégorie. ».

### Éditeur
- h1 « Nouveau devis », sous-titre « Choisissez les prestations : les montants, la remise et l’acompte se calculent tout seuls. » Boutons « Annuler », « Enregistrer le brouillon », « Envoyer le devis ».
- Deux colonnes : minmax(0,1fr) / minmax(340px,440px), empilées sous 1180px. À gauche : carte Client / Date du mariage / Nombre d’invités ; carte « Catalogue » (compteur à droite, puces de catégories, liste défilante de 340px max : nom, « catégorie, prix / unité », bouton « Ajouter ») ; carte « Lignes du devis » (grille 1fr 84px 118px 32px : libellé et prix unitaire, quantité centrée 36px, montant Sora à droite, corbeille ; vide « Ajoutez des prestations depuis le catalogue. »), puis Remise (%) et Acompte à la signature (%).
- À droite, collant à 84px : « Aperçu du PDF » + « Télécharger le PDF ». La feuille reste **blanche avec texte encre même en thème sombre** : rayon 14, padding 28 26, filet ruban de 4px en haut ; logo 46px, nom et ville de l’entreprise ; à droite « Devis » Sora 20, numéro, « Émis le », « Valable 30 jours » ; filet encre 2px ; « Pour » / client et « Mariage » / date, invités ; tableau Prestation / Qté / Montant (prix unitaire en sous-ligne) ; totaux sur 250px : Sous-total, Remise (x %) en négatif, Total (filet 2px, Sora 15px), Acompte (x %) ; pied « Paiement par virement, espèces ou Mobile Money. Le solde est dû 7 jours avant la date du mariage. Bon pour accord, date et signature du client. ». Le PDF WeasyPrint reprend exactement cette mise en page.
- Nouveau devis : lignes par défaut Planification complète, Décoration de salle, DJ et sonorisation ; remise 0 ; acompte 30 %. Quantité à l’ajout : unité « invité » et Location de chaises = nombre d’invités ; Centre de table = invités ÷ 10 arrondi au-dessus ; sinon 1. Réajouter une prestation augmente sa quantité.
- Toasts : « {prestation} ajouté », « Indiquez le nom du client avant de continuer. », « Ajoutez au moins une prestation. », « Brouillon {n} enregistré », « Devis {n} envoyé. Relance programmée le {date}. », « Contrat, échéancier et fiche mariage créés ».

## 10. Relances

- h1 « Relances », sous-titre « Wedivo prépare les relances selon vos règles. Vous gardez la main sur chaque envoi. » Bouton « Nouvelle règle ».
- Bandeau : « {n} prospects n’ont pas été relancés depuis plus de 7 jours » / « Wedivo peut leur envoyer un email de suivi demain à 9 h. » + « Programmer leur relance » → toast « {n} relances programmées pour demain à 9 h ».
- Colonne gauche « Règles automatiques » / « Activez celles qui correspondent à votre façon de travailler » : titre 800, description muted, badge du canal + statistique, interrupteur à droite. Règle WhatsApp désactivée avec bouton « Connecter WhatsApp Business » (cadenas). Note : « Les emails partent automatiquement. Les messages WhatsApp exigent l’API WhatsApp Business et des modèles validés par Meta : en attendant, Wedivo vous propose le message à envoyer vous-même. »
- Colonne droite « File de relances » / « x à faire, y faites récemment » : icône, nom, motif, puis « À faire aujourd’hui » (corail) ou « Prévue demain / dans n j » (muted) ; bouton « Faite », ou « Copier le message » pour WhatsApp (toast « Message copié. Collez-le dans WhatsApp. ») ; section « Faites récemment ».
- Modale « Nouvelle règle de relance » : Quand (Un devis est envoyé, Une échéance de paiement approche, Un prospect reste sans échange, Un rendez-vous est prévu), Délai (jours), Canal (Email, Tâche interne, WhatsApp grisé « connexion requise »), Message avec aide « Variables : {prenom}, {date_mariage}, {montant}, {numero_devis} » ; bouton « Créer la règle ».

## 11. Mariages et calendrier

### Mariages
- h1 « Mariages », sous-titre « Une fiche par mariage : client, budget, prestataires et tâches de l’équipe. » Boutons « Calendrier », « Nouveau mariage ».
- Grille auto (min 290px) de cartes : bloc date, couple (Sora 600 16px), lieu muted, badge « J-x » à droite (coral si 14 jours ou moins, sinon violet) ; encadré `--surface-2` à 3 colonnes Invités / Budget / Prestataires ; « n tâches restantes » + pourcentage ; barre ruban.
- Tiroir : bloc date, « Mariage de {couple} », « {lieu}, {n} invités » ; « Préparation » avec barre ruban ; Contrat / Solde à recevoir ; « Tâches » : case 22px rayon 7 (faite = verte remplie + texte barré), tri non faites d’abord puis par échéance, sous-ligne « Awa, 22 oct. », badges « En retard » (red) et « Bientôt » (coral, 3 jours ou moins) ; ligne d’ajout « Ajouter une tâche… » + membre + bouton + ; « Prestataires » avec bouton d’appel ; pied « Invitations », « Voir les paiements ».
- Modale « Nouveau mariage » : Couple, Date, Invités, Lieu, case « Ajouter la liste de tâches standard (12 tâches) ».
- Tâches standard (échéance = jours avant le mariage) : Rendez-vous de lancement (−180), Valider le budget global (−170), Réserver la salle (−160), Choisir le traiteur et organiser la dégustation (−120), Réserver photographe et vidéaste (−120), Réserver DJ ou orchestre (−100), Définir la décoration et la palette (−90), Envoyer les invitations (−60), Finaliser la liste des invités (−30), Établir le plan de table (−10), Briefing équipe jour J (−2), Répétition de la cérémonie (−1). Une échéance déjà passée est ramenée à aujourd’hui + 3 jours.

### Calendrier
- h1 « Calendrier », sous-titre « Mariages, tâches et échéances de paiement de toute l’équipe. » Boutons « Aujourd’hui », mois précédent, mois suivant.
- Titre du mois (« Octobre 2026 », 20px) + légende : Mariage (ruban), Tâche (violet-soft), Paiement attendu (gold-soft).
- Grille 7 colonnes commençant le lundi (Lun … Dim), 6 semaines, bordure et rayon 18 ; cases min 108px ; jours hors mois sur `--surface-2` muted ; aujourd’hui : numéro dans un rond violet ; 3 éléments maximum puis « +n ». Éléments 11,5px 700 : mariage fond ruban texte blanc « Mariage {couple} », tâche violet-soft, paiement gold-soft « {montant court} de {prénom} ».
- Sous 700px : cases de 58px, éléments réduits à des points de 7px centrés, « +n » masqué.
- Dessous : carte « Agenda du mois » (bloc date avec jour de semaine abrégé, titre, badge Mariage fuchsia / Paiement gold / Tâche violet ; vide « Rien de prévu ce mois-ci. »).

## 12. Paiements & finances

- h1 « Paiements & finances », sous-titre « Ce que vos clients vous doivent, ce que vous devez à vos prestataires et la marge de chaque mariage. » Boutons « Exporter », « Enregistrer un paiement ».
- Tuiles en montants complets : « Montant des contrats », « Encaissé » (vert), « Solde à recevoir » (dark), « Marge prévisionnelle ».
- Colonnes 1,35fr / 1fr. « Contrats » / « Touchez une ligne pour le détail » : Client (nom, « Mariage le … », barre de paiement max 180px, verte à 100 %), Contrat, Encaissé, Solde (gras, ou badge « Soldé »), Marge est. — montants sans « FCFA » dans le tableau.
- « Échéances à venir » / « Les clients sont prévenus 2 jours avant » : 6 lignes (bloc date, client, libellé, « , en retard » en rouge, montant court) ; puis « À payer aux prestataires » (avatar gold, nom, catégorie, montant).
- Tiroir du contrat : liste clé/valeur (Montant du contrat, Dépenses estimées, Marge prévisionnelle en vert « x FCFA (y %) », Montant déjà encaissé, Solde à recevoir), note « La marge prévisionnelle compare le contrat aux dépenses saisies pour ce mariage. Ce n’est pas le bénéfice net comptable de l’entreprise. », « Échéancier » avec badge « Payé » ou bouton « Marquer payé ».
- Modale « Enregistrer un paiement » : Contrat (« {client}, solde {montant} », seulement les contrats non soldés), Montant (FCFA), Date, Mode de paiement (Virement bancaire, Espèces, Orange Money, MTN MoMo, Wave, Chèque), aide « Un reçu PDF est envoyé au client et les rappels de cette échéance sont annulés. » ; toast « Paiement de {montant} enregistré pour {client} ».

## 13. Prestataires

- h1 « Prestataires », sous-titre « Votre carnet d’adresses de confiance, avec l’historique des collaborations et les montants dus. » Bouton « Ajouter un prestataire ».
- Puces de catégories (« Tous » + catégories existantes). Tableau : Prestataire (avatar carré 40 rayon 11 violet-soft avec initiales, nom, catégorie), Téléphone, Collaborations, Évaluation (étoiles `--gold-bright`, étoiles vides à 25 % d’opacité), Montant dû (« — » si nul), bouton d’appel.

## 14. Invitations & QR codes

- h1 « Invitations & QR codes », sous-titre « Créez l’invitation, envoyez-la par email et contrôlez les entrées le jour J. » Actions : étiquette « Phase 3 », « Contrôle à l’entrée » (icône scan), « Envoyer les invitations ».
- Colonnes minmax(0,1fr) / minmax(300px,400px). Carte « Contenu » : Prénom 1, Prénom 2, Date, Heure, Lieu, Message, « Couleurs » : 4 pastilles rondes 34px coupées en diagonale — `#2A2440/#FFFDF9`, `#5126C2/#F7F3FF`, `#8A3B12/#FFF6EC`, `#0E5B47/#F1FAF6` (texte / fond).
- Carte « Réponses des invités » / « Mariage d’Aïcha & Serge » + « Ajouter » : 4 cases (Envoyées, Confirmées en vert, Déclinées, En attente), tableau Invité / Code / Réponse (Confirmé green, Décliné red, En attente gold) / Entrée (« Entré » violet).
- Aperçu collant : carte rayon 18, padding 30 26, centrée, cadre intérieur 1px couleur du texte à 25 % (inset 10px, rayon 12). « Ont la joie de vous convier à leur mariage » Cormorant italique 17 ; prénoms Cormorant 600 36px avec « & » seul sur sa ligne en 24px ; date en majuscules Sora 13px, interlettrage .04em (« SAMEDI 14 NOVEMBRE 2026 À 15H00 ») ; lieu 13,5px ; message Cormorant 16px (30 caractères de large) ; QR de 118px dans un cadre blanc rayon 10 ; ligne Sora 11px interlettrage .08em « WDV-KS-0001, FAMILLE KOUASSI (4) ».
- Modale « Contrôle à l’entrée » : « Scannez le QR code avec la caméra, ou saisissez le code imprimé sous le QR. », champ + « Vérifier ». Résultats : vert « Bienvenue {nom}. Entrée enregistrée. », rouge « Déjà utilisé : {nom} est déjà entré. », gold « {nom} avait décliné l’invitation. », rouge « Code inconnu : cette invitation n’existe pas. ».

## 15. Paramètres

- h1 « Paramètres », sous-titre « Espace {nom de l’entreprise} ». Onglets verticaux de 220px (horizontaux défilants sous 860px) : Entreprise, Équipe & rôles, Catalogue, Abonnement, Intégrations. Actif : fond surface + ombre.
- Entreprise : « Profil de l’entreprise » / « Ces informations apparaissent sur vos devis, contrats et invitations. » ; Nom commercial, Adresse de votre espace (suffixe .wedivo.app, aide « Vos clients et votre équipe se connectent à cette adresse. »), Ville, Pays, Devise (FCFA XOF, FCFA XAF, EUR), Fuseau horaire, Mentions sur les devis ; « Enregistrer les modifications » → « Modifications enregistrées ».
- Équipe : « Membres de l’équipe » / « Chaque rôle ne voit que ce dont il a besoin » + « Inviter un membre » ; tableau Membre / Rôle (liste modifiable sauf propriétaire) / Statut (« Actif » green, « Invitation envoyée » gold) ; puis « Ce que chaque rôle peut faire » (coches vertes, tirets muted).
- Catalogue : « Catalogue de prestations » / « Utilisé pour composer vos devis en quelques clics » + « Ajouter une prestation ».
- Abonnement : 3 cartes (offre actuelle : bordure violette, halo, badge « Offre actuelle », bouton désactivé) ; prix Sora 24 + « FCFA / mois » ; liste à coches vertes ; bouton « Passer à {offre} » ; mention « Tarifs indicatifs à valider. Paiement par carte ou Mobile Money, facture mensuelle. ».
- Intégrations : Email d’envoi (Connecté, « Gérer »), WhatsApp Business (Non connecté, « Connecter »), Mobile Money (Bientôt), Google Agenda (Non connecté, « Connecter »).

## 16. Calcul des indicateurs

| Indicateur | Calcul |
|---|---|
| Solde à recevoir | Σ montants des contrats actifs − Σ paiements non annulés |
| Marge prévisionnelle | Σ contrats − Σ dépenses estimées des mariages liés |
| Prospects actifs | Prospects hors « confirmé » et « perdu » ; delta = créés depuis 7 jours |
| Taux de conversion | Confirmés ÷ (confirmés + perdus) sur 90 jours ; delta en points vs les 90 jours précédents |
| Devis en attente | Devis au statut « envoyé » ; « en jeu » = somme de leurs montants |
| Temps gagné ce mois | (devis envoyés × 100 min + relances automatiques envoyées × 10 min) ÷ 60, arrondi à 0,5 h. Libellé « Estimation » |
| Temps moyen de création | Médiane entre la création du brouillon et l’envoi, sur 30 jours |
| Taux d’acceptation | Acceptés ÷ (acceptés + refusés + expirés) sur 90 jours |
| Encaissements | Σ paiements par mois sur les 6 derniers mois ; badge = variation vs les 6 mois précédents |
| Avancement d’un mariage | Tâches faites ÷ tâches totales |

## 17. Données fictives de démonstration

Commande `python manage.py seed_demo [--reset] [--anchor YYYY-MM-DD]` et cible `make seed`. Le jeu ci-dessous est celui du prototype, daté autour du **19 octobre 2026**. Toutes les dates sont décalées de (date du jour − 2026-10-19) pour que la démonstration reste cohérente quel que soit le jour d’exécution ; `--anchor` fixe une autre date de référence. La commande ne s’exécute jamais en production (vérifier `settings.DEBUG` ou un drapeau dédié).

### Organisation et équipe

```json
{
 "organization": {"name":"Maison Élégance Events","slug":"maison-elegance","city":"Abidjan","country":"Côte d’Ivoire",
   "currency":"XOF","timezone":"Africa/Abidjan","plan":"Pro","quote_prefix":"DV",
   "legal_mentions":"RCCM CI-ABJ-2023-B-12345. Paiement par virement, espèces ou Mobile Money."},
 "members": [
  {"full_name":"Freddy Kouamé","email":"freddy@maison-elegance.ci","role":"owner","password":"demo-wedivo"},
  {"full_name":"Awa Sangaré","email":"awa@maison-elegance.ci","role":"planner","password":"demo-wedivo"},
  {"full_name":"Didier Kra","email":"didier@maison-elegance.ci","role":"assistant","password":"demo-wedivo"},
  {"full_name":"Nadège Brou","email":"nadege@maison-elegance.ci","role":"accountant","password":"demo-wedivo"}
 ],
 "plans": [
  {"name":"Essentiel","monthly_price":15000,"max_users":1,"modules":["crm","quotes","reminders_email"]},
  {"name":"Pro","monthly_price":35000,"max_users":5,"modules":["crm","quotes","reminders_email","finance","events","calendar","vendors"]},
  {"name":"Agence","monthly_price":75000,"max_users":null,"modules":["*"]}
 ]
}
```

Seconde organisation minimale, « Atelier Bassam Mariages » (slug `atelier-bassam`, 2 prospects, 1 devis), pour vérifier l’isolation des données.

### Prospects

```json
[
 {"name":"Grâce Bamba","phone":"+225 07 48 21 33 10","source":"instagram","status":"new","budget":2500000,"wedding_date":"2027-04-17","needs":"Mariage civil + réception 180 invités, thème ivoire et or","next_follow_up":"2026-10-19","history":[["2026-10-11","Demande reçue via Instagram"]]},
 {"name":"Ibrahim Coulibaly","phone":"+225 05 66 90 12 47","source":"whatsapp","status":"new","budget":3200000,"wedding_date":"2027-02-13","needs":"Planification complète, dégustation traiteur à prévoir","next_follow_up":"2026-10-20","history":[["2026-10-17","Message WhatsApp reçu"]]},
 {"name":"Nadia Kambou","phone":"+225 01 02 77 45 19","source":"facebook","status":"contacted","budget":1800000,"wedding_date":"2027-03-06","needs":"Coordination jour J uniquement","next_follow_up":"2026-10-22","history":[["2026-10-09","Demande via Facebook"],["2026-10-12","Appel découverte de 20 min"]]},
 {"name":"Jean-Marc Yao","phone":"+225 07 11 34 82 50","source":"phone","status":"quote_sent","budget":2900000,"wedding_date":"2027-01-30","needs":"Décoration + DJ + photographe, 220 invités","next_follow_up":"2026-10-19","history":[["2026-10-05","Appel entrant"],["2026-10-14","Devis DV-2026-044 envoyé"]]},
 {"name":"Patricia Ouattara","phone":"+225 05 74 63 28 91","source":"whatsapp","status":"negotiation","budget":4500000,"wedding_date":"2027-05-22","needs":"Mariage traditionnel et civil sur deux jours","next_follow_up":"2026-10-19","history":[["2026-09-28","Demande WhatsApp"],["2026-10-03","Devis envoyé"],["2026-10-15","Demande de remise de 10 %"]]},
 {"name":"Yannick Touré","phone":"+225 01 45 66 70 23","source":"instagram","status":"quote_sent","budget":2200000,"wedding_date":"2027-02-27","needs":"Réception 150 invités à Grand-Bassam","next_follow_up":"2026-10-21","history":[["2026-10-08","DM Instagram"],["2026-10-16","Devis DV-2026-046 envoyé"]]},
 {"name":"Estelle & Hervé Konan","phone":"+225 07 98 12 54 66","source":"referral","status":"confirmed","budget":2800000,"wedding_date":"2026-12-12","needs":"Planification complète","history":[["2026-08-20","Contrat signé"]]},
 {"name":"Aïcha & Serge Kouassi","phone":"+225 05 23 47 81 09","source":"facebook","status":"confirmed","budget":1500000,"wedding_date":"2026-11-14","needs":"Coordination + décoration","history":[["2026-09-02","Acompte reçu"]]},
 {"name":"Rachel Assi","phone":"+225 07 66 45 02 18","source":"facebook","status":"lost","budget":1200000,"wedding_date":"2026-12-19","needs":"Budget insuffisant pour la date","lost_reason":"A choisi un autre prestataire","history":[["2026-09-30","A choisi un autre prestataire"]]},
 {"name":"Kevin & Sarah Gnahoré","phone":"+225 01 20 30 40 55","source":"phone","status":"contacted","budget":3800000,"wedding_date":"2027-06-12","needs":"Mariage destination à Assinie","next_follow_up":"2026-10-23","history":[["2026-10-13","Appel entrant"]]}
]
```

Ajouter aussi 32 prospects anciens au statut « contacté », sans échange depuis plus de 7 jours, pour alimenter le bandeau « 32 prospects n’ont pas été relancés » (noms ivoiriens variés générés par Faker `fr_FR` avec numéros +225).

> Statuts du prototype → modèle : `confirmed` = `won` (« Client confirmé »).

### Catalogue

```json
[
 ["Coordination","Planification complète",1200000,"forfait"],["Coordination","Coordination jour J",450000,"forfait"],
 ["Coordination","Accompagnement partiel (3 mois)",650000,"forfait"],["Décoration","Décoration de salle",800000,"forfait"],
 ["Décoration","Arche florale",250000,"unité"],["Décoration","Centre de table",15000,"unité"],
 ["Restauration","Traiteur, menu complet",12000,"invité"],["Restauration","Gâteau de mariage",180000,"unité"],
 ["Animation","DJ et sonorisation",300000,"soirée"],["Animation","Orchestre live",650000,"soirée"],
 ["Image","Photographe",350000,"journée"],["Image","Vidéaste",400000,"journée"],
 ["Logistique","Location de chaises",1500,"unité"],["Logistique","Voiture des mariés",150000,"journée"],
 ["Invitations","Invitations électroniques + QR",75000,"forfait"]
]
```

### Devis

```json
[
 {"number":"DV-2026-047","client":"Patricia Ouattara","date":"2026-10-15","total":4350000,"status":"sent"},
 {"number":"DV-2026-046","client":"Yannick Touré","date":"2026-10-16","total":2140000,"status":"sent"},
 {"number":"DV-2026-045","client":"Nadia Kambou","date":"2026-10-18","total":520000,"status":"draft"},
 {"number":"DV-2026-044","client":"Jean-Marc Yao","date":"2026-10-14","total":2860000,"status":"sent"},
 {"number":"DV-2026-042","client":"Christelle Aka & Marc Dosso","date":"2026-09-21","total":3600000,"status":"accepted","converted":true},
 {"number":"DV-2026-040","client":"Rachel Assi","date":"2026-09-18","total":1450000,"status":"refused"},
 {"number":"DV-2026-038","client":"Estelle & Hervé Konan","date":"2026-08-12","total":2800000,"status":"accepted","converted":true},
 {"number":"DV-2026-035","client":"Aïcha & Serge Kouassi","date":"2026-08-25","total":1500000,"status":"accepted","converted":true}
]
```

Chaque devis reçoit des lignes cohérentes tirées du catalogue dont la somme (après remise éventuelle) donne exactement le total indiqué. La numérotation suivante démarre à DV-2026-048.

### Contrats, échéanciers et paiements

```json
[
 {"client":"Aïcha & Serge Kouassi","wedding_date":"2026-11-14","total":1500000,"expenses":900000,
  "schedule":[["Acompte à la signature",500000,"2026-09-02",true],["Deuxième versement",500000,"2026-10-21",false],["Solde",500000,"2026-11-07",false]]},
 {"client":"Mariam Traoré & Idriss Koné","wedding_date":"2026-10-31","total":4200000,"expenses":2750000,
  "schedule":[["Acompte",1260000,"2026-06-10",true],["Deuxième versement",1890000,"2026-09-15",true],["Solde",1050000,"2026-10-24",false]]},
 {"client":"Estelle & Hervé Konan","wedding_date":"2026-12-12","total":2800000,"expenses":1700000,
  "schedule":[["Acompte",840000,"2026-08-20",true],["Deuxième versement",980000,"2026-11-10",false],["Solde",980000,"2026-12-05",false]]},
 {"client":"Christelle Aka & Marc Dosso","wedding_date":"2027-01-23","total":3600000,"expenses":2300000,
  "schedule":[["Acompte",1080000,"2026-09-25",true],["Deuxième versement",1260000,"2026-12-15",false],["Solde",1260000,"2027-01-15",false]]},
 {"client":"Fatou Diabaté & Moussa Sylla","wedding_date":"2026-10-10","total":2100000,"expenses":1380000,
  "schedule":[["Acompte",630000,"2026-05-02",true],["Solde",1470000,"2026-10-03",true]]}
]
```

Chaque échéance payée crée un paiement du même montant à sa date (mode : alterner Virement bancaire, Orange Money, Wave, Espèces). Le contrat Kouassi reproduit l’exemple de référence : 1 500 000 / 900 000 / 600 000 / 500 000 / 1 000 000 FCFA.

**Historique pour le graphique** : ajouter des contrats de mariages déjà passés (statut terminé, entièrement payés) et répartir leurs paiements pour que le total encaissé par mois soit exactement : mai 3,2 M · juin 4,1 M · juil. 2,8 M · août 5,6 M · sept. 4,9 M · oct. 6,3 M (paiements des contrats ci-dessus inclus), et environ 21 M sur les 6 mois précédents pour obtenir le badge « +28 % ».

### Mariages et tâches

```json
[
 {"title":"Mariam & Idriss","contract":"Mariam Traoré & Idriss Koné","date":"2026-10-31","venue":"Sofitel Hôtel Ivoire, Cocody","guests":320,"budget":4200000,
  "vendors":["Fleurs d’Ébène","Saveurs du Plateau","Studio Lumière","Sofitel Hôtel Ivoire"],
  "tasks":[["Confirmer le plan de table final","Awa","2026-10-22",false],["Valider le menu avec le traiteur","Freddy","2026-10-20",true],
   ["Répétition de la cérémonie","Awa","2026-10-30",false],["Briefing équipe jour J","Didier","2026-10-29",false],
   ["Réception des alliances","Freddy","2026-10-15",true],["Livraison décoration","Didier","2026-10-30",false],
   ["Envoi du programme aux invités","Awa","2026-10-18",true],["Essayage robe final","Awa","2026-10-24",true]]},
 {"title":"Aïcha & Serge","contract":"Aïcha & Serge Kouassi","date":"2026-11-14","venue":"Espace Latrille, Cocody","guests":180,"budget":1500000,
  "vendors":["Fleurs d’Ébène","DJ Kevin Sound","Pâtisserie Ama"],
  "tasks":[["Choisir la palette de décoration","Awa","2026-10-12",true],["Réserver le DJ","Didier","2026-10-20",false],
   ["Envoyer les invitations électroniques","Awa","2026-10-25",false],["Visite technique de la salle","Freddy","2026-10-28",false],
   ["Valider le gâteau","Awa","2026-11-02",false]]},
 {"title":"Estelle & Hervé","contract":"Estelle & Hervé Konan","date":"2026-12-12","venue":"Jardins de Grand-Bassam","guests":240,"budget":2800000,
  "vendors":["Saveurs du Plateau","Studio Lumière","Prestige Location"],
  "tasks":[["Signer le contrat du traiteur","Freddy","2026-10-30",false],["Repérage photo","Didier","2026-11-08",false],
   ["Choisir la voiture des mariés","Awa","2026-11-15",false],["Liste des invités finalisée","Awa","2026-10-15",true]]},
 {"title":"Christelle & Marc","contract":"Christelle Aka & Marc Dosso","date":"2027-01-23","venue":"Salle Prestige, Riviera 3","guests":280,"budget":3600000,
  "vendors":["Fleurs d’Ébène","Ciné Moments"],
  "tasks":[["Premier rendez-vous de cadrage","Freddy","2026-10-02",true],["Proposer trois traiteurs","Awa","2026-11-05",false],
   ["Moodboard décoration","Awa","2026-11-12",false]]}
]
```

### Prestataires

```text
// nom, catégorie, téléphone, collaborations, note, montant dû
["Fleurs d’Ébène","Décoration","+225 07 22 18 90 45",14,5,450000],["Saveurs du Plateau","Traiteur","+225 05 31 64 77 02",9,4,1200000],
["Studio Lumière","Photographe","+225 01 88 40 15 63",11,5,175000],["DJ Kevin Sound","DJ","+225 07 55 02 39 81",7,4,0],
["Pâtisserie Ama","Gâteau","+225 05 49 17 60 22",6,5,90000],["Sofitel Hôtel Ivoire","Salle","+225 27 22 48 26 26",4,5,0],
["Prestige Location","Location matériel","+225 01 63 28 44 70",12,4,260000],["Ciné Moments","Vidéaste","+225 07 03 91 56 38",5,4,0]
```

### Règles et file de relances

```text
rules: [
 {"title":"Relancer les devis sans réponse","channel":"email","active":true,"trigger":"quote_sent","delays":[3,7],
  "description":"Email au client 3 jours après l’envoi, puis 7 jours après. S’arrête dès que le devis est accepté ou refusé."},
 {"title":"Rappeler les prospects non recontactés","channel":"internal_task","active":true,"trigger":"prospect_stale","delays":[7],
  "description":"Crée une tâche pour le planner quand un prospect reste 7 jours sans échange."},
 {"title":"Prévenir avant une échéance de paiement","channel":"email","active":true,"trigger":"payment_due","delays":[-2,0],
  "description":"Email au client 2 jours avant l’échéance, puis le jour même si le paiement n’est pas enregistré."},
 {"title":"Rappeler les rendez-vous","channel":"email","active":false,"trigger":"appointment","delays":[-1],
  "description":"Email au client la veille à 18 h pour les dégustations, essayages et visites."},
 {"title":"Relances par WhatsApp","channel":"whatsapp","active":false,"locked":true,
  "description":"Envoi automatique de modèles approuvés via l’API WhatsApp Business."}
]
jobs: [
 ["Jean-Marc Yao","Devis DV-2026-044 envoyé il y a 5 jours, sans réponse","email","2026-10-19","pending"],
 ["Grâce Bamba","Nouveau prospect, pas encore contacté","call","2026-10-19","pending"],
 ["Patricia Ouattara","Négociation : répondre à la demande de remise","whatsapp","2026-10-19","pending"],
 ["Aïcha & Serge Kouassi","Deuxième versement de 500 000 FCFA attendu le 21 oct.","email","2026-10-19","pending"],
 ["Ibrahim Coulibaly","Premier rendez-vous à proposer","call","2026-10-20","pending"],
 ["Mariam Traoré","Rappel du solde avant le mariage du 31 oct.","email","2026-10-22","pending"],
 ["Fatou Diabaté","Demande d’avis après le mariage","email","2026-10-17","done"],
 ["Nadia Kambou","Relance après l’appel découverte","email","2026-10-15","done"]
]
```

Statistiques affichées sous les règles : calculées depuis les jobs ; seed d’un historique du mois donnant « 18 relances ce mois, 6 devis signés ensuite », « 11 tâches créées ce mois », « 7 rappels, 5 paiements reçus à temps ».

### Invitations (mariage d’Aïcha & Serge)

```text
template: {"title":"Ont la joie de vous convier à leur mariage","first_name_1":"Aïcha","first_name_2":"Serge",
  "date":"2026-11-14","time":"15h00","venue":"Espace Latrille, Cocody",
  "message":"Votre présence sera notre plus beau cadeau. Merci de confirmer avant le 1er novembre.",
  "text_color":"#2A2440","background":"#FFFDF9"}
guests (code WDV-KS-0001 à 0008) : [
 ["Famille Kouassi",4,"confirmed",checked_in=true], ["Bintou Cissé",1,"confirmed"], ["Hervé Gbané",1,"declined"],
 ["Famille Ahoua",3,"confirmed"], ["Marcelle Yapi",1,"pending"], ["Rodrigue N’Dri",1,"confirmed"],
 ["Clarisse Ehui",1,"pending"], ["Famille Brou",5,"confirmed"]
]
```

## 18. Contrôle de fidélité

- Tests Playwright de capture d’écran pour chaque écran, à 1440×900 et 390×844, en thème clair et sombre, avec les données `seed_demo --anchor 2026-10-19`.
- Mêmes captures du prototype (`docs/prototype/wedivo-plateforme.html`, après « Se connecter »), comparées côte à côte. Lister chaque écart (couleur, taille, espacement, texte, ordre) et le corriger.
- Écarts acceptés uniquement s’ils sont dus à des données réelles (noms plus longs, listes vides) ; ils respectent alors troncature et états vides du prototype.

## Prompts d’exécution par étape

Le développement ayant commencé : d’abord l’audit, puis les corrections dans l’ordre.

- **Étape A — Audit des écarts.** Lire ce complément et ouvrir `docs/prototype/wedivo-plateforme.html`. Sans rien modifier, comparer le code actuel au prototype et au complément : tokens et polices, composants, coquille (barre latérale, barre supérieure, mobile), chaque écran, textes, toasts, données de démonstration. Produire `docs/audit-fidelite.md` avec un tableau : écran, écart constaté, fichier concerné, correction proposée, priorité. Terminer par un plan de correction en étapes.
- **Étape B — Design system.** Remplacer les tokens par ceux de la section 3 (clair et sombre complets), charger Sora, Manrope et Cormorant Garamond, configurer Tailwind pour n’utiliser que ces variables, régler lucide-vue-next à stroke-width 1.8. Mettre chaque composant W* en conformité avec la section 4 (dimensions, rayons, états). Ajouter `WAreaChart` en SVG selon la section 7 et le symbole des rubans. Créer une page de développement `/dev/ui` qui montre tous les composants dans les deux thèmes.
- **Étape C — Coquille et authentification.** Mettre la barre latérale, la barre supérieure, la palette Ctrl+K, la barre d’onglets mobile et le tiroir mobile en conformité avec la section 5 (ordre du menu, badges P2/P3 pilotés par feature flag, pastille du nombre de relances, indicateur ruban). Refaire les écrans de connexion et de création de compte selon la section 6, textes et messages d’erreur compris.
- **Étape D — Écrans commerciaux.** Mettre en conformité, un écran à la fois, le tableau de bord (section 7, avec la carte de démarrage), Prospects (section 8), Devis liste et éditeur avec la feuille PDF toujours blanche (section 9) et Relances (section 10). Brancher les indicateurs sur les calculs de la section 16. Vérifier chaque écran à 1440 px et 390 px contre le prototype avant de passer au suivant.
- **Étape E — Écrans organisation et paramètres.** Mettre en conformité Mariages et Calendrier avec les 12 tâches standard (section 11), Paiements & finances (section 12), Prestataires (section 13), Invitations avec l’aperçu Cormorant Garamond et le contrôle à l’entrée (section 14) et Paramètres (section 15). Le gabarit PDF du devis et de l’invitation doit reproduire l’aperçu à l’écran.
- **Étape F — Données fictives.** Écrire la commande `seed_demo` de la section 17 (options `--reset` et `--anchor`, décalage des dates, interdite en production) avec l’organisation Maison Élégance Events, ses 4 membres, les prospects (plus les 32 prospects inactifs), le catalogue, les devis avec lignes cohérentes, les contrats, échéanciers et paiements, l’historique d’encaissements du graphique, les mariages et tâches, les prestataires, les règles et la file de relances, l’invitation et ses 8 invités, ainsi que l’organisation secondaire Atelier Bassam Mariages. Ajouter `make seed` et des tests qui vérifient les totaux attendus (solde, marge, encaissements par mois).
- **Étape G — Contrôle visuel final.** Ajouter les tests Playwright de capture de la section 18 pour tous les écrans, en bureau et mobile, clair et sombre. Comparer avec le prototype, corriger les derniers écarts et mettre à jour `docs/audit-fidelite.md` en marquant chaque point comme corrigé ou justifié.
