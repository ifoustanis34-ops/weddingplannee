# Audit de fidélité au prototype — Étape A

> **Statut : audit partiel (20 oct. 2026).** Le prototype `docs/prototype/wedivo-plateforme.html` est absent du dépôt et introuvable sur la machine. Cet audit compare le code actuel au **texte du complément** (`docs/specs/complement-prototype.md`, sections 2 à 17). Les écarts qui ne se voient que dans le prototype (espacements fins, ordre exact de certains blocs, icônes, textes absents du complément) seront ajoutés dès que le fichier sera fourni, avant l'Étape G.
>
> Rappel de la règle d'arbitrage : le prototype l'emporte pour l'apparence, les textes et l'organisation des écrans ; `CLAUDE.md` l'emporte pour la logique métier, la sécurité, le multi-tenant et l'architecture. Les conflits entre les deux sont signalés par ⚖️.

> **Avancement.** Étape B faite : sections 1 et 2 corrigées (tokens, styles de base, polices, icônes, composants W* et nouveaux composants, `WAreaChart`, pipeline sans ECharts). `WKanban` corrigé à l’Étape D.
> Étape D faite : sections 5 (tableau de bord), 6 (prospects), 7 (devis) et 8 (relances), avec les calculs de la section 16. Écarts gardés : avancement des mariages par les paiements tant que les tâches n’existent pas (étape 9) ; vue tableau, modèles de devis et actions reporter / annuler / envoyer maintenant conservés ; le catalogue d’exemple garde ses noms jusqu’à l’Étape F.
> Étape C faite : sections 3 (coquille) et 4 (connexion et inscription) corrigées, recherche serveur de la palette, offres en base. Écart gardé : le bloc entreprise ouvre le sélecteur d’espace quand l’utilisateur en a plusieurs ; sinon il mène à Paramètres (dès l’étape 8).

Priorités : **P1** = visible partout ou bloquant pour la suite · **P2** = écart visible sur un écran · **P3** = finition.

## 1. Tokens, polices, icônes

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Global | Tokens manquants : `--surface-3`, `--line-2`, `--violet-ink`, `--grey-soft`, `--hero-ink`, `--hero-muted`, `--shadow`, `--shadow-lg`, `--sidebar`. `--shadow-float` est maison | `frontend/src/design/tokens.css` | Copier le bloc de la section 3 tel quel ; remplacer `--shadow-float` par `--shadow` / `--shadow-lg` | P1 |
| Global | Thème sombre incomplet ou différent : `--muted`, `--line-2`, `--violet-ink`, `--surface-3`, `--grey-soft`, `--hero-muted`, `--shadow` absents ; valeurs écartées (`--fuchsia #F06BB0` au lieu de `#F06AB0`, `--coral #FF8A5C`/`#FF925F`, `--coral-soft`, `--gold #F4B444`/`#F4B54A`, `--gold-soft`, `--fuchsia-soft`) | `tokens.css` | Jeu sombre complet de la section 3, appliqué via `prefers-color-scheme` et `:root[data-theme="dark"]` | P1 |
| Global | Thème Tailwind : manque `surface-3`, `line-2`, `violet-ink`, `grey-soft`, `hero-muted`, ombres | `frontend/src/design/main.css` | Étendre `@theme inline` avec les nouveaux tokens | P1 |
| Global | Couleurs codées en dur hors tokens : `#17153b` (voiles, toasts), `#c9c5ea`, `#3dd3a0`, `#ff6f85` | `WDrawer.vue`, `WModal.vue`, `WCommandPalette.vue`, `WToast.vue`, `AuthLayout.vue` | Voile `rgba(13,12,32,.5)` + flou 2px ; toast `--hero` avec icônes `#5DE3B4` / `#FFB27A` ; textes du panneau en `--hero-muted` | P1 |
| Global | Styles de base : pas de règles `h1` 26px/600/1.2 (22px sous 960px), `h2` 17px, `h3` 15px ; pas de classe `.num` ; le `:focus-visible` n'a pas `border-radius: 6px` ; `line-height` 1.55 et graisse 500 du corps absents | `main.css` | Reprendre les règles de la section 3 dans `@layer base` ; ajouter l'utilitaire `num` | P1 |
| Global | Polices : Sora chargée sans la graisse 400 ; Cormorant Garamond absente | `frontend/index.html` | URL Google Fonts de la section 3 (Cormorant réservée aux invitations, Étape E) | P2 |
| Global | Icônes : `@lucide/vue` avec `stroke-width` 2 par défaut ; tailles variées (16, 20) | tous les composants | Régler `stroke-width` 1.8 globalement (wrapper ou attribut par défaut) ; tailles 18 / 22 (barre mobile) / 15 (petits boutons) | P2 |
| Logotype | Image JPEG du logo complet en 36px + « Wedivo » en `text-lg` ; pas de « ı » avec point doré | `AppLayout.vue`, `AuthLayout.vue` | Composant `WLogo` : symbole détouré 40px + « Wedivo » Sora 700 22px, −0,03em, « ı » + point `--gold-bright` 0,24em ; variante blanche | P1 |
| Rubans | Rubans SVG dessinés à la main dans la carte solde ; pas de symbole commun `#ribbons` / `gRib` | `BalanceCard.vue` | Symbole SVG unique de la section 3, réutilisé (carte solde, panneau de connexion) | P2 |

## 2. Composants (section 4)

| Composant | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| WButton | Bordure `--line` au lieu de `--line-2` ; texte 14,5px au lieu de 14px ; désactivé opacité .55 au lieu de .5 ; pas d'appui `translateY(1px)` ; `sm` padding 12 au lieu de 11 et rayon 10 au lieu de 8 ; pas de variante `icon` (carré 40/32) ; primaire sans `--violet-ink` | `WButton.vue` | Aligner sur la section 4 ; ajouter `variant="icon"` | P1 |
| WInput / WSelect / WTextarea | Hauteur 40 au lieu de 42 ; bordure `--line` au lieu de `--line-2` ; halo `violet/25` au lieu de 3px `--violet-soft` ; textarea à vérifier (min 84, padding 10 12) ; pas de groupe de saisie avec suffixe gris (« .wedivo.app », « % », « jours ») | `fieldClasses.ts`, `WInput.vue`, `WTextarea.vue` | Corriger les classes ; ajouter un slot `addon` rendu dans le même cadre | P1 |
| Libellés / aide / erreur | Aide 13px au lieu de 12,5px ; erreur 13px 600 au lieu de 13,5px 700 | `WField.vue` | Ajuster | P2 |
| WSwitch | 44×24 au lieu de 42×24 ; rail inactif `--line` au lieu de `--line-2` ; actif violet au lieu de `--green` ; bouton de 20px au lieu de 18 | `WSwitch.vue` | Aligner | P2 |
| WBadge | Hauteur et padding différents (py 2, px 10, 13px au lieu de hauteur 24, padding 0 9, 12px) ; ton `grey` à vérifier sur `--grey-soft`/`--muted` | `WBadge.vue`, `badgeTones.ts` | Aligner ; variante `plain` (= `dot=false`) | P2 |
| Étiquette de phase | Absente | — | Créer `WPhaseTag` (11px 700, padding 2 7, rayon 6, `--surface-3`) | P2 |
| WCard | Padding 20 / 24 selon la taille d'écran au lieu de 20 fixe | `WCard.vue` | Padding 20 partout | P3 |
| Tuile | Pas de composant : les tuiles de Finances et du tableau de bord sont faites à la main | `FinancePage.vue`, `DashboardPage.vue` | Créer `WTile` (rayon 18, padding 16 18, libellé 13px 600, valeur Sora 600 21px, variante `dark`), grille de 4 (2 sous 1000px), écart 14 | P1 |
| WTable | Largeur min 560 au lieu de 640 ; cellules padding 12 au lieu de 13 12 ; à vérifier : montants à droite en Sora tabulaire | `WTable.vue` | Aligner | P2 |
| WTabs | Padding 10 12 au lieu de 10 14 ; compteur en pastille (le prototype affiche le compteur muted à part, à confirmer) | `WTabs.vue` | Aligner | P3 |
| Puces de filtre | Pas de composant (catégories du catalogue, prestataires) | `CatalogPicker.vue` | Créer `WChips` : hauteur 32, pilule, `--line-2`, 13px 700, active `--ink`/`--surface` | P2 |
| WDrawer | Largeur 520 au lieu de 500 ; pas d'animation d'entrée (0,22s depuis 40px) ; en-tête padding 16 au lieu de 20 ; corps sans écart de 20 ; ombre `--shadow-float` | `WDrawer.vue` | Aligner | P2 |
| WModal | Largeurs `sm/md/lg` au lieu de min(560px, 100% − 24px) ; rayon 18 au lieu de 20 ; bottom-sheet sur mobile (le prototype : centrée) ; pas d'animation d'échelle .98 → 1 | `WModal.vue` | Aligner (garder `lg` pour l'import si nécessaire) | P2 |
| WToast | Centré en bas au lieu de bas à droite sur bureau ; rayon 12 OK ; bouton fermer en plus ; durée à vérifier (3,6 s) | `WToast.vue`, `useToast.ts` | Bas droite sur bureau, pleine largeur au-dessus de la barre d'onglets sur mobile | P2 |
| WProgress | Hauteur 8 au lieu de 6, rayon pilule au lieu de 6 | `WProgress.vue` | Aligner | P3 |
| Bloc date, icône de canal, avatar, note, bandeau d'alerte | Pas de composants dédiés ; réalisés au cas par cas | `DashboardPage.vue`, `ReminderCard.vue`, `RemindersPage.vue` | Créer `WDateBlock`, `WChannelIcon`, `WAvatar` (rond ruban / carré entreprise), `WNote`, `WAlert` | P1 |
| État vide | Icône + titre + texte, sans bordure pointillée | `WEmptyState.vue` | Variante conforme : bordure pointillée `--line-2`, rayon 12, padding 28, texte muted centré (garder les actions) | P2 |
| Palette Ctrl+K | Largeur 576 au lieu de min(600px, 100% − 24px) ; rayon 18 au lieu de 16 ; champ 56px au lieu de 54 ; résultats non groupés (« Pages », « Prospects et clients », « Devis ») ; pas de limite 12 | `WCommandPalette.vue`, `AppLayout.vue` | Grouper les résultats et brancher la recherche serveur (§7.10) | P2 |
| WAreaChart | Absent : le graphique utilise ECharts | `CashflowChart.vue`, `design/charts.ts` | Créer `WAreaChart` SVG (section 7) puis retirer `echarts` et `vue-echarts` | P1 |

## 3. Coquille (section 5)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Barre latérale | Ordre et contenu du menu différents : Calendrier sous « Pilotage » au lieu d'« Organisation » ; « Catalogue » dans le menu (prototype : dans Paramètres › Catalogue) ; libellés « Prospects », « Finances » au lieu de « Prospects & clients », « Paiements & finances » ; « Invitations » au lieu d'« Invitations & QR » | `app/navigation.ts`, `i18n/fr.ts` | Ordre exact de la section 5. Catalogue : garder la route, retirer l'entrée quand l'onglet Paramètres › Catalogue existe (Étape 8) | P1 |
| Barre latérale | Icônes : `LayoutDashboard`, `BellRing`, `Banknote`, `Gem`, `Store`, `CalendarDays` au lieu de home, refresh-cw, wallet, heart, briefcase, calendar | `navigation.ts` | Reprendre les icônes de la section 5 | P2 |
| Barre latérale | Pas de pastille fuchsia avec le nombre de relances du jour ; pas d'étiquettes P2/P3 | `AppLayout.vue`, `navigation.ts` | Pastille depuis `/reminders/summary` ; ⚖️ étiquettes P2/P3 : la règle « ne jamais afficher un module non construit » (`ready`) l'emporte, donc l'étiquette s'affiche seulement pour un module livré mais encore en phase de test, pilotée par un feature flag | P2 |
| Barre latérale | Actif : fond `--violet-soft` au lieu de `--surface-2` ; barre de 4px placée dans le lien au lieu d'être collée au bord gauche (left −14px, top/bottom 8px, rayon 0 4 4 0) ; liens padding 8 12 au lieu de 9 10, écart icône 12 au lieu de 11 ; padding de la barre 20 16 au lieu de 18 14 14 | `AppLayout.vue` | Aligner | P2 |
| Bloc entreprise | Sélecteur d'espace au lieu du bouton (avatar carré, nom 13,5px, `slug.wedivo.app`) qui mène à Paramètres › Entreprise | `OrganizationSwitcher.vue` | Bouton conforme ; ⚖️ garder le changement d'espace (multi-organisation, §5.8 de `CLAUDE.md`) dans ce bouton quand l'utilisateur a plusieurs espaces | P2 |
| Bas de la barre | Avatar `--hero` avec initiale au lieu du dégradé ruban et des initiales ; email au lieu du rôle ; bouton icône au lieu du bouton fantôme « Se déconnecter » | `AppLayout.vue` | Aligner | P2 |
| Barre supérieure | Padding 12 16/24 au lieu de 12 clamp(16px,3vw,32px) ; fond 90 % ; recherche max 384px au lieu de 420 et texte « Rechercher » au lieu de « Rechercher un client, un devis… » ; cloche ouvrant un panneau vide au lieu d'aller à Relances avec un point corail | `AppLayout.vue`, `fr.ts` | Aligner | P2 |
| Contenu | Padding 24 16-32 au lieu de 26 clamp() 48 ; pas de largeur max 1360 ; chaque page a sa propre largeur max | `AppLayout.vue`, pages | Largeur max 1360 dans la coquille ; composant `PageHeader` (h1 + sous-titre 64ch + actions, marge 22) | P1 |
| Mobile | Seuil 1024px (`lg`) au lieu de 960px ; tiroir du menu = `WDrawer` 520px au lieu de 282px avec voile `.45` ; barre d'onglets sans flou ni fond à 92 %, icônes 20 au lieu de 22, libellés 12 au lieu de 11 ; icône « Plus » `MoreHorizontal` au lieu de grid ; marge basse du contenu 112 au lieu de 110 ; pas de retour en haut au changement de page | `AppLayout.vue`, `router.ts` | Breakpoint personnalisé `nav: 960px` ; tiroir dédié de 282px ; `scrollBehavior` dans le routeur | P1 |

## 4. Connexion et création de compte (section 6)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Panneau de marque | Grille 5/7 au lieu de 44 % (min 360px) ; masqué sous 1024px au lieu d'être réduit sous 900px ; pas de slogan en `--hero-muted` (affiché en or) ; pas des trois cartes translucides ; pas de rubans | `AuthLayout.vue`, `fr.ts` | Refaire selon la section 6 avec les trois cartes et leurs textes | P1 |
| Formulaire | Pas de sélecteur segmenté « Se connecter » / « Créer un compte entreprise » (liens texte à la place) ; sélecteur de thème en haut, absent du prototype | `AuthLayout.vue`, `LoginPage.vue`, `SignupPage.vue` | Sélecteur segmenté ; thème : garder la préférence système | P1 |
| Connexion | « Connexion » / « Accédez à l'espace de votre agence. » au lieu de « Bon retour » / « Connectez-vous à l'espace de votre agence. » ; « Email » au lieu de « Email professionnel » ; « Mot de passe oublié ? » sous le champ au lieu d'à droite du libellé ; bouton 40px au lieu de 46 | `LoginPage.vue`, `fr.ts` | Aligner | P1 |
| Inscription | Sous-titre différent ; « Étape n sur 3 » au lieu des 3 barres libellées « 1. Entreprise », « 2. Votre compte », « 3. Votre espace » ; placeholder sans « Ex. » ; « Mariages par an » au lieu de « Mariages organisés par an » ; aide du mot de passe différente (« 8 caractères minimum. ») ; offres en liste au lieu de cartes radio avec prix ; aide de l'offre différente | `SignupPage.vue`, `fr.ts` | Aligner. ⚖️ prix des offres : lus depuis l'API (« prix en base, pas dans le code »), nécessite la table des offres de l'Étape 8 | P1 |
| Inscription | Listes Pays et Mariages par an à vérifier contre la section 6 (8 pays ; Moins de 10 / 10 à 30 / 30 à 60 / Plus de 60) | `SignupPage.vue` | Aligner | P2 |
| Messages | Erreurs génériques (« Ce champ est obligatoire. », « Saisissez un email valide. ») au lieu des messages par champ de la section 6 ; toast « Espace créé. Bienvenue sur Wedivo ! » au lieu de « Espace {slug}.wedivo.app créé » | `fr.ts`, schémas zod | Messages par champ | P2 |

## 5. Tableau de bord (section 7)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| En-tête | Sous-titre « Voici votre espace {organisation}. » au lieu de « {Jour date}. {n} relances à traiter et le mariage de {couple} dans {x} jours. » ; boutons « Nouveau prospect » / « Créer un devis » à vérifier | `DashboardPage.vue`, `fr.ts` | Aligner | P1 |
| Carte de démarrage | Titres différents (« Pour bien démarrer ») ; pas de cercle à cocher ni de texte barré ; pas de disparition avec le toast « Votre espace est prêt. Bon travail ! » | `DashboardPage.vue` | Aligner | P2 |
| Ligne 1 | Grille 3fr/2fr au lieu de 1,1fr/1fr (empilée sous 1100px) ; carte solde : rayon, hauteur min 248, montant clamp(32px,4.4vw,46px) et « FCFA » à .42em à vérifier ; libellé « Solde à recevoir » au lieu de « Solde à recevoir sur vos contrats » ; ⚖️ le bloc « dont x en retard » n'est pas dans le prototype (le garder : information métier utile) | `BalanceCard.vue` | Aligner | P1 |
| Indicateurs | 4 cartes séparées au lieu d'une carte 2×2 sans padding avec filets ; libellés différents (« Temps gagné estimé » au lieu de « Temps gagné ce mois ») ; pas de deltas (« +4 cette semaine », « +8 pts sur 3 mois ») | `DashboardPage.vue`, `finance/dashboard.py` | Carte 2×2 ; deltas calculés selon la section 16 | P1 |
| Calculs | Conversion sans fenêtre de 90 jours ni delta ; temps gagné = 100 min/devis + 5 min/relance (section 16 : 10 min/relance, arrondi à 0,5 h, sur le mois) ; prospects actifs sans delta 7 jours | `backend/finance/dashboard.py` | Appliquer la section 16 (le calcul reste côté serveur) | P1 |
| Encaissements | ECharts ; sous-titre « 6 derniers mois » au lieu de « Six derniers mois, en millions de FCFA » ; pas de badge de variation | `CashflowChart.vue`, `dashboard.py` | `WAreaChart` ; variation vs les 6 mois précédents calculée côté serveur | P1 |
| Pipeline | ECharts (barres) au lieu de lignes HTML (grille 120px / 1fr / 72px, barre 10px de la couleur du statut, total court) ; « Perdu » à exclure ; titre « Pipeline » au lieu de « Pipeline commercial » ; pas de bouton « Ouvrir » | `PipelineChart.vue` | Réécrire en HTML/CSS, sans ECharts | P1 |
| Ligne 2 / 3 | Grilles 1fr/1fr au lieu de 1,35fr/1fr ; relances du jour : icône de canal, motif, badge « Faite », vide « Toutes les relances du jour sont faites. » ; prochains mariages : bloc date, « lieu, J-x », barre ruban + pourcentage (aujourd'hui : avancement des paiements, faute de tâches, Étape 9) ; « Tout voir » au lieu de « Toutes les relances » | `DashboardPage.vue`, `fr.ts` | Aligner ; l'avancement passe aux tâches à l'Étape 9 | P2 |

## 6. Prospects & clients (section 8)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| En-tête | Titre « Prospects » au lieu de « Prospects & clients » ; sous-titre « {n} prospects dans votre pipeline » au lieu du texte de la section 8 | `ProspectsPage.vue`, `fr.ts` | Aligner | P1 |
| Barre d'outils | Placeholder « Nom, téléphone ou email… » au lieu de « Rechercher un nom, un besoin… » ; filtre « responsable » et bascule Kanban/Tableau en plus ⚖️ (exigés par `CLAUDE.md` §7.2, les garder en style discret) | `ProspectsPage.vue` | Aligner le texte ; garder les fonctions en plus | P2 |
| Kanban | Colonnes 280px au lieu de 258 min ; fond `surface-2/60` et rayon 18, padding 8 au lieu de 12 ; hauteur min 320 et total au format court dans l'en-tête à vérifier ; survol en glisser (contour 2px violet + violet-soft) ; « Aucun prospect » dans une colonne vide | `WKanban.vue` | Aligner | P2 |
| Carte | Couleurs de canal (`#25D366`, `#D62976`, `#1877F2`, `#8A87A6`, `#F4A62A`) et carré 8px à vérifier ; pastille corail « Relance aujourd'hui / demain » au lieu de « Relance en retard » / « Relance le {date} » | `ProspectCard.vue`, `fr.ts` | Aligner | P2 |
| Toasts | « {nom} : {statut}. » au lieu de « {nom} passe en « {statut} » » ; pas de second toast « Pensez à convertir son devis en contrat. » ; « Prospect ajouté. » au lieu de « {nom} ajouté aux prospects » | `fr.ts`, `ProspectsPage.vue` | Aligner | P2 |
| Tiroir | Pas d'avatar 44 ; grille 2 colonnes Téléphone / Date / Budget / Prochaine relance ; historique en frise verticale ; titre « Historique des échanges » au lieu de « Historique » ; aide « Les rappels automatiques arrivent avec le module Relances. » devenue fausse (module livré) | `ProspectDrawer.vue`, `fr.ts` | Aligner ; supprimer l'aide obsolète | P1 |
| Modale « Nouveau prospect » | Placeholders différents (« Awa et Moussa » au lieu de « Ex. Awa & Koffi Mensah ») ; pas de case « Me rappeler de le contacter demain » | `ProspectFormModal.vue`, `fr.ts` | Ajouter la case (pose `next_follow_up_at` = demain, ce qui planifie la relance existante) | P2 |
| Import | Pas de zone de dépôt « Déposez votre fichier ici » / « CSV ou XLSX, 5 Mo maximum » (bouton de choix de fichier) | `ImportModal.vue` | Zone de dépôt (garder l'étape de correspondance des colonnes) | P3 |

## 7. Devis (section 9)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Liste | Sous-titre différent ; pas de bouton « Gérer le catalogue » ; pas des 4 tuiles (« Temps moyen de création » dark, « Envoyés ce mois », « Taux d'acceptation », « Montant en attente ») | `QuotesPage.vue`, nouveau sélecteur backend | Tuiles + endpoint de statistiques (médiane, taux sur 90 jours, section 16) | P1 |
| Liste | Onglets « Expirés » et « Modèles » en plus ⚖️ (modèles exigés par `CLAUDE.md` §7.3 : les garder) ; actions par ligne (« Envoyer », « Marquer accepté », « Convertir en contrat », « Contrat créé ») à vérifier ; vide « Aucun devis dans cette catégorie. » | `QuotesPage.vue` | Aligner | P2 |
| Éditeur | Titre et sous-titre ; boutons « Annuler », « Enregistrer le brouillon », « Envoyer le devis » (aujourd'hui « Enregistrer ») | `QuoteEditorPage.vue`, `fr.ts` | Aligner | P1 |
| Éditeur | Grille 1fr/1fr au lieu de minmax(0,1fr) / minmax(340px,440px), empilée sous 1180px ; colonne d'aperçu collante à 96px au lieu de 84 | `QuoteEditorPage.vue` | Aligner | P1 |
| Éditeur | Catalogue intégré à la carte des lignes au lieu d'une carte « Catalogue » séparée (compteur, puces de catégories, liste de 340px max, bouton « Ajouter ») ; lignes sur une grille 1fr 84px 118px 32px ; « Conditions » regroupe remise, acompte, validité au lieu de « Remise (%) » et « Acompte à la signature (%) » sous les lignes | `QuoteEditorPage.vue`, `CatalogPicker.vue` | Réorganiser | P1 |
| Éditeur | Nouveau devis sans lignes par défaut (Planification complète, Décoration de salle, DJ et sonorisation, acompte 30 %) ; règles de quantité : Location de chaises = invités et Centre de table = invités ÷ 10 arrondi au-dessus non gérées ; réajouter une prestation crée une nouvelle ligne au lieu d'augmenter la quantité | `QuoteEditorPage.vue`, `modules/quotes/calculations.ts` | ⚖️ Les noms des prestations par défaut ne doivent pas être en dur : les lire comme prestations « par défaut » du catalogue (drapeau `is_default` sur `ServiceItem`) et la règle ÷ 10 comme une unité « table (10 invités) » | P2 |
| Aperçu | Pas de filet ruban de 4px en haut ; logo 36px (pastille d'initiale) au lieu du logo 46px ; « Valable 30 jours » ; tableau Prestation / Qté / Montant avec prix unitaire en sous-ligne ; totaux sur 250px ; pied de page de la section 9 ; rayon 18 au lieu de 14 | `QuotePreview.vue`, `backend/templates/pdf/quote.html` | Aligner l'aperçu et le PDF ensemble | P1 |
| Toasts | « {nom} ajouté. » avec point final ; « Devis enregistré. » au lieu de « Brouillon {n} enregistré » ; « Devis envoyé à {email}. » au lieu de « Devis {n} envoyé. Relance programmée le {date}. » ; « Contrat créé. Le client est confirmé. » au lieu de « Contrat, échéancier et fiche mariage créés » | `fr.ts`, `QuoteEditorPage.vue` | Aligner (la date de relance vient de la réponse de `/send`) | P2 |

## 8. Relances (section 10)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Mise en page | Onglets (Aujourd'hui / À venir / Faites / Règles) au lieu de deux colonnes : « Règles automatiques » à gauche, « File de relances » à droite avec « Faites récemment » | `RemindersPage.vue` | Deux colonnes (empilées sur mobile) | P1 |
| En-tête | Sous-titre différent ; pas de bouton « Nouvelle règle » ni de modale de création (on ne peut que modifier les règles existantes) | `RemindersPage.vue`, `RuleModal.vue`, `reminders/views.py` | Ajouter la création de règle (POST `/reminders/rules`, propriétaire/planner) avec les déclencheurs existants | P2 |
| Bandeau | Textes différents : « {n} prospects sans relance depuis plus de 7 jours » au lieu de « {n} prospects n'ont pas été relancés depuis plus de 7 jours » / « Wedivo peut leur envoyer un email de suivi demain à 9 h. » ; la modale de programmation groupée est en plus ⚖️ (choix de la date et du canal : la garder, préremplie à demain 9 h, email) ; bandeau sans carré blanc de 38px | `RemindersPage.vue`, `BulkScheduleModal.vue`, `fr.ts` | Aligner ; toast « {n} relances programmées pour demain à 9 h » | P2 |
| Règles | Pas de statistique par règle (« 18 relances ce mois, 6 devis signés ensuite ») ; pas de règle WhatsApp verrouillée avec « Connecter WhatsApp Business » (cadenas) ; note WhatsApp au texte différent ; interrupteur à droite au lieu d'à gauche | `RemindersPage.vue`, `reminders/selectors.py` | Statistiques calculées depuis les jobs ; règle WhatsApp affichée verrouillée tant que l'intégration n'existe pas | P2 |
| File | « Faite » au lieu de « Marquer faite » ; « À faire aujourd'hui » (corail) / « Prévue demain / dans n j » ; toast de copie « Message copié. Collez-le dans WhatsApp. » ; actions reporter / annuler / envoyer maintenant en plus ⚖️ (exigées par `CLAUDE.md` §7.4 : les garder dans un menu) | `ReminderCard.vue`, `fr.ts` | Aligner | P2 |
| Canaux | Le prototype a un canal « Appel » (icône gold) ; le modèle a email / tâche / WhatsApp | `reminders/models.py` | ⚖️ Pas de nouveau canal : afficher l'icône « Appel » pour une tâche interne dont le motif est un appel (champ `kind` dans le payload) | P3 |

## 9. Paiements & finances (section 12)

| Écran | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| En-tête | « Finances » au lieu de « Paiements & finances » ; sous-titre différent ; bouton « Exporter » à vérifier (menu CSV / Excel) | `FinancePage.vue`, `fr.ts` | Aligner | P1 |
| Tuiles | Libellés et variantes : « Solde à recevoir » en tuile dark, « Encaissé » en vert, montants complets | `FinancePage.vue` | `WTile` | P2 |
| Mise en page | Pas de colonnes 1,35fr / 1fr : manque « Échéances à venir » (6 lignes, « , en retard » en rouge) et « À payer aux prestataires » (dépend des prestataires, Étape 9) | `FinancePage.vue`, `finance/selectors.py` | Colonne droite : échéances maintenant, prestataires à l'Étape 9 | P1 |
| Tableau | Colonnes et barre de paiement (max 180px, verte à 100 %) à vérifier ; montants sans « FCFA » dans le tableau ; « Touchez une ligne pour le détail » | `FinancePage.vue` | Aligner | P2 |
| Tiroir | Note de marge plus courte que le texte de la section 12 ; marge « x FCFA (y %) » en vert à vérifier | `ContractDrawer.vue`, `fr.ts` | Aligner | P2 |
| Modale paiement | Libellés des contrats « {client}, solde {montant} » ; « Virement » au lieu de « Virement bancaire » ; aide « Un reçu PDF est envoyé au client et les rappels de cette échéance sont annulés. » ; toast « Paiement de {montant} enregistré pour {client} » ; référence et justificatif en plus ⚖️ (exigés par `CLAUDE.md` §7.5 : les garder) | `PaymentModal.vue`, `fr.ts` | Aligner | P2 |

## 10. Écrans construits à l’Étape E

> Étape E faite : Paiements & finances (§12), Paramètres (§15), Mariages et calendrier (§11), Prestataires (§13), construits directement selon le complément. Reste §14 Invitations & QR, traité avec l’étape 10.

### Notes d’origine

Mariages et calendrier (section 11), Prestataires (13), Invitations (14) et Paramètres (15) n'existent pas : ils seront construits directement conformes aux Étapes 8, 9 et 10. Rien à corriger aujourd'hui. Points à prévoir :

- Paramètres : onglets verticaux de 220px ; Catalogue déplacé dans Paramètres (voir coquille) ; offres en base avec prix (aujourd'hui `Organization.Plan` est une simple liste de choix, sans table ni prix).
- Mariages : les 12 tâches standard sont des données, pas du code (modèle de liste de tâches par organisation, créé au démarrage du compte).
- Invitations : Cormorant Garamond seulement dans l'aperçu et le PDF.

## 11. Données de démonstration (section 17)

| Sujet | Écart constaté | Fichier concerné | Correction proposée | Priorité |
|---|---|---|---|---|
| Commande | Pas d'options `--reset` ni `--anchor` ; pas de décalage des dates | `backend/*/management/commands/seed_demo.py` | Ajouter les options et le décalage (date du jour − 2026-10-19) | P1 |
| Équipe | Aïcha Koné, Yao Kouassi… avec `Wedivo-demo-2026` au lieu de Freddy Kouamé, Awa Sangaré, Didier Kra, Nadège Brou (`demo-wedivo`) | `seed_demo.py` | Jeu de la section 17 | P1 |
| Données | 8 prospects au lieu des 10 + 32 inactifs ; devis, contrats (5), échéanciers, paiements, historique d'encaissements (mai 3,2 M … oct. 6,3 M, +28 %), règles et file différents ; mariages, tâches, prestataires et invitations absents (modèles à venir) | `seed_demo.py` | Réécrire à l'Étape F, au fur et à mesure des modèles disponibles | P1 |
| Isolation | Pas d'organisation secondaire « Atelier Bassam Mariages » | `seed_demo.py` | L'ajouter (2 prospects, 1 devis) | P2 |
| Numérotation | Le prototype numérote sur 3 chiffres (`DV-2026-047`), le code sur 4 (`DV-2026-0048`) | `organizations/numbering.py` | ⚖️ Garder 4 chiffres (`CLAUDE.md` : `DV-2026-0048`) ; le seed reprend les numéros du prototype sur 4 chiffres | P3 |

## 12. Écarts que l'on garde

Ces écarts sont voulus : `CLAUDE.md` l'emporte, ou ils viennent de fonctions exigées par le premier prompt.

- Modules non construits absents du menu (`ready: false`) : pas d'entrée Mariages, Calendrier, Prestataires, Invitations, Paramètres tant qu'ils ne sont pas livrés.
- Vue tableau et filtre par responsable des prospects ; modèles de devis ; référence et justificatif de paiement ; actions reporter / annuler / envoyer maintenant des relances ; sélecteur d'espace pour les utilisateurs de plusieurs organisations.
- Bandeau de vérification d'email et bandeau d'essai sur le tableau de bord (envois bloqués tant que l'email n'est pas vérifié, `CLAUDE.md` §11).
- Numérotation sur 4 chiffres.

## Plan de correction

1. **Étape B — Design system** (P1 de la section 1 et 2) : tokens complets clair et sombre, styles de base, polices, `stroke-width` 1.8, mise en conformité des W*, nouveaux composants (`WLogo`, `WTile`, `WChips`, `WPhaseTag`, `WDateBlock`, `WChannelIcon`, `WAvatar`, `WNote`, `WAlert`, `WAreaChart`, symbole des rubans), page `/dev/ui` dans les deux thèmes. Retrait d'ECharts. Tests Vitest des nouveaux composants.
2. **Étape C — Coquille et authentification** : seuil 960px, ordre et icônes du menu, pastille des relances, étiquettes de phase (feature flag), barre supérieure, tiroir mobile 282px, barre d'onglets, `PageHeader`, largeur 1360 ; panneau de marque, sélecteur segmenté, textes et messages d'erreur de la section 6.
3. **Étape D — Écrans commerciaux** : tableau de bord (calculs de la section 16 côté serveur, carte 2×2, `WAreaChart`, pipeline HTML) ; Prospects (textes, carte, tiroir, case « Me rappeler demain ») ; Devis (tuiles et statistiques, éditeur réorganisé, prestations par défaut via le catalogue, aperçu et PDF identiques) ; Relances (deux colonnes, création de règle, statistiques, règle WhatsApp verrouillée).
4. **Étape 8 (spécification initiale), construite conforme à la section 15** : paramètres, équipe, offres en base avec prix. Le catalogue passe dans Paramètres.
5. **Étape E — Organisation** : Finances (colonne des échéances, textes) puis, avec l'Étape 9, Mariages, Calendrier, Prestataires ; puis Invitations (Étape 10).
6. **Étape F — Données fictives** : `seed_demo --reset --anchor`, jeu complet de la section 17 et organisation secondaire, avec des tests sur les totaux (solde, marge, encaissements par mois).
7. **Étape G — Contrôle visuel** : captures Playwright 1440×900 et 390×844, clair et sombre, comparées au prototype. **Il faut le fichier `docs/prototype/wedivo-plateforme.html`**, et compléter cet audit avant de commencer.
