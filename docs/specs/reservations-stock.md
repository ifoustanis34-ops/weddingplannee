# Réservations, stock, finances, personnel et tableau de bord — Wedivo

> Source : prompt « Réservations, stock, finances, personnel et tableau de bord » (texte collé le 12 nov. 2026). Complète `CLAUDE.md`, le complément (`docs/specs/complement-prototype.md`) et `docs/specs/devis-billets.md`.

## 1. Objectif

- Ajouter cinq ensembles de fonctionnalités : réservations et événements, stock et matériel, gestion financière et commerciale, gestion du personnel, tableau de bord de gestion.
- Refaire entièrement le tableau de bord : élégant, charismatique, lisible en un coup d’œil, fidèle au design system Wedivo (encre, violet, ruban dégradé, or, Sora et Manrope).
- Retirer complètement le système de relances et la prospection : ces fonctions sont gérées par une autre plateforme.
- Fournir des données fictives complètes et cohérentes pour que chaque écran soit démontrable.

**Priorité.** Ce prompt remplace les parties des prompts précédents qui concernent les relances, la prospection (pipeline de prospects) et le contenu du tableau de bord. Le reste (multi-tenant, design system, devis, billets, FreeMoPay, emails, coffre de clés) reste valable.

## 2. Retrait des relances et de la prospection

### À supprimer
- **Relances** : l’entrée de menu, l’écran (règles, file, bandeau « prospects non relancés »), la pastille de compteur, la cloche qui y renvoie, les modèles `ReminderRule` et `ReminderJob`, les endpoints `/reminders/*`, les tâches Celery associées (`dispatch_due_jobs`, `flag_stale_prospects`), les règles créées au signup, les données de démo, les tests et toute mention dans les textes.
- **Prospection** : le kanban de statuts (nouveau, contacté, devis envoyé, négociation, confirmé, perdu), les canaux d’origine, la programmation de relances, l’import de prospects, le taux de conversion et l’indicateur « Temps gagné » qui en dépendait.
- Les emails automatiques de relance de devis et de rappel d’échéance envoyés aux clients.

### À conserver et à adapter
- « Prospects & clients » devient « Clients » : une fiche par client, sans pipeline (section 4.4). Migration : les prospects confirmés deviennent des clients ; les autres sont archivés, pas supprimés.
- La cloche de la barre supérieure devient le centre d’alertes internes (stock bas, retours en retard, soldes impayés, maintenance) : ce sont des notifications pour l’équipe, jamais des messages envoyés aux clients.
- Les rappels liés aux billets (confirmation de présence des invités) restent dans le module Billets.
- Les migrations suppriment les tables retirées proprement, après sauvegarde, et l’application ne garde aucun lien mort.

## 3. Nouvelle navigation

| Groupe | Entrées (icône lucide) |
|---|---|
| Pilotage | Tableau de bord (home) |
| Activité | Réservations (calendar-check) · Calendrier (calendar) · Clients (users) · Devis & factures (file-text) |
| Matériel | Stock & matériel (package) · Mouvements (arrow-left-right) |
| Finances | Finances (wallet) · Rapports (bar-chart-3) |
| Équipe | Personnel (user-cog) · Présences & paie (clock) |
| Événementiel | Mariages (heart) · Prestataires (briefcase) · Invitations & QR (mail) |
| Espace | Paramètres (settings) |

Barre d’onglets mobile : Accueil, Réservations, Stock, Finances, Plus. Même style que le prototype (indicateur ruban, pastilles, tiroirs, modales).

## 4. Réservations et événements

### 4.1 Réservation
- Une réservation regroupe tout ce qu’un client commande pour une date : location de matériel, vente de matériel, prestations (décoration, coordination…), ou un mélange. Elle peut être liée à une fiche mariage.
- Champs : numéro (`RES-2026-0142`), client, type (location, vente, prestation, mixte), titre de l’événement, lieu et adresse, nombre d’invités, responsable, notes, lignes, documents.
- Dates logistiques : livraison, installation, début et fin de l’événement, démontage, récupération, retour à l’entrepôt. La période de blocage du matériel va de la sortie de l’entrepôt à son retour, plus un délai de remise en état configurable par catégorie (ex. nappes : 1 jour de pressing).
- Statuts : brouillon, devis envoyé, en attente d’acompte, confirmée, en préparation, livrée, installée, en cours, récupérée, clôturée, annulée. Badges de couleur cohérents avec le design system.
- Lignes : article du stock (quantité, période, prix de location ou de vente, caution), pack, prestation du catalogue, ligne libre. Remise, transport, frais d’installation.
- Paiements : acompte requis (montant ou %), paiements enregistrés (espèces, virement, Mobile Money, FreeMoPay), solde calculé, caution encaissée puis restituée ou retenue.
- Documents générés avec l’identité de l’agence : devis, facture, reçu, bon de sortie (liste du matériel à charger), bon de retour (quantités revenues, état, manquants).
- Au retour : saisie des quantités rendues, abîmées ou manquantes ; les manquants et la casse génèrent automatiquement une ligne « Casse et pertes » facturable et un mouvement de stock.
- Annulation : libère le matériel, applique la politique d’acompte définie dans les paramètres.

### 4.2 Écran Réservations
- En-tête : « Réservations », sous-titre « Toutes vos commandes, de la confirmation au retour du matériel. », boutons « Exporter » et « Nouvelle réservation ».
- Tuiles : Confirmées ce mois, En attente d’acompte, À livrer cette semaine, Soldes à encaisser.
- Onglets par statut, recherche, filtres (type, responsable, période). Tableau : numéro, client, événement, date, statut, montant, payé, solde, prochaine étape logistique.
- Assistant de création en tiroir large : client (ou création rapide), dates logistiques, ajout de matériel avec disponibilité affichée en direct pour la période (« 180 disponibles sur 250 »), packs, prestations, récapitulatif et acompte. Si une quantité dépasse la disponibilité : alerte rouge, suggestion d’articles équivalents, ou location complémentaire chez un prestataire.
- Fiche réservation : frise des étapes logistiques, lignes, paiements, documents, équipe affectée, historique.

### 4.3 Calendrier centralisé
- Vues mois, semaine, jour, liste, et planning logistique : une ligne par jour avec les livraisons, installations, récupérations, l’équipe et le véhicule affectés.
- Couleurs : événements (dégradé ruban), livraisons (violet), installations (fuchsia), récupérations (corail), maintenance (gris), paiements attendus (or).
- Filtres par membre de l’équipe, type d’opération, statut. Glisser une réservation pour changer sa date, avec revérification de la disponibilité du matériel.

### 4.4 Clients
- Fiche : nom ou couple, entreprise, téléphones, email, adresse, notes, préférences.
- Historique : toutes ses réservations, devis, factures, paiements ; indicateurs : nombre de commandes, chiffre d’affaires total, solde dû, dernière commande, matériel le plus loué.
- Liste avec recherche, tri par chiffre d’affaires ou par solde dû.

## 5. Stock et matériel

### 5.1 Articles
- Champs : nom, référence, catégorie (mobilier, linge de table, vaisselle, décoration, structures et tentes, éclairage, sonorisation, énergie, divers), photo, description, emplacement à l’entrepôt, quantité totale, prix de location (par jour ou par événement), prix de vente, coût d’achat, caution, seuil d’alerte, délai de remise en état, actif ou non.
- Mode de suivi : par quantité (chaises, assiettes) ou par unité avec numéro de série (sono, groupe électrogène, projecteurs), avec état de chaque unité.
- Statuts : disponible, réservé, loué (sorti), vendu, en maintenance, hors service ou perdu. Une vente retire définitivement les quantités du stock.
- Packs : ensembles prêts à réserver (ex. « Pack réception 100 invités » : 100 chaises, 10 tables rondes, 10 nappes, 100 housses), disponibles si tous leurs composants le sont.

### 5.2 Disponibilité et doubles locations
- Disponible sur une période = quantité totale − quantités réservées ou sorties sur des périodes qui se chevauchent (délais de remise en état compris) − maintenance − hors service.
- Le contrôle se fait côté serveur, sous verrou, à la confirmation d’une réservation : deux réservations simultanées ne peuvent jamais dépasser le stock.
- Vue « Disponibilité » : grille articles × jours sur 30 jours, cases colorées selon le taux d’occupation, clic pour voir les réservations concernées.

### 5.3 Mouvements
- Journal immuable de chaque entrée et sortie : achat, sortie pour réservation, retour, vente, casse, perte, envoi et retour de maintenance, ajustement d’inventaire. Chaque mouvement a un auteur, une date, une quantité, un motif et une référence (réservation, facture d’achat).
- Sortie et retour par scan : étiquettes QR imprimables par article ou par lot ; le magasinier scanne avec l’écran de scan existant, en mode « Sortie » ou « Retour », depuis le bon de sortie.
- Inventaire : comptage physique par catégorie, écarts affichés, validation qui crée les ajustements.

### 5.4 Alertes
- Stock insuffisant pour une réservation à venir, article sous son seuil, retour en retard, unité en maintenance depuis trop longtemps, matériel abîmé non traité.
- Affichées dans le centre d’alertes, sur le tableau de bord et sur la fiche de l’article ; résumé quotidien par email au propriétaire (désactivable).

### 5.5 Écran Stock & matériel
- Tuiles : Articles, Valeur du stock (coût d’achat), Taux d’utilisation du mois, Alertes en cours.
- Vue grille (cartes avec photo, barre « disponible / réservé / loué / maintenance », quantité disponible aujourd’hui) et vue tableau ; filtres par catégorie et statut ; onglets Articles, Packs, Disponibilité, Inventaire.
- Fiche article : photo, stock par statut (anneau), calendrier d’occupation, réservations à venir, historique des mouvements, revenus générés et rentabilité (section 6.4).

## 6. Gestion financière et commerciale

### 6.1 Enregistrement automatique
- Chaque facture émise crée une recette attendue ; chaque paiement enregistré (manuel ou FreeMoPay) crée une recette encaissée, rattachée au client, à la réservation, à la catégorie (location, vente, prestation, transport, casse).
- Chaque achat de matériel, fiche de paie validée, frais de mission ou dépense saisie crée une dépense.

### 6.2 Recettes et dépenses
- Catégories de dépenses : achat de matériel, maintenance et réparation, transport et carburant, salaires et journaliers, sous-traitance, loyer de l’entrepôt, électricité et eau, marketing, frais bancaires et Mobile Money, divers. Catégories modifiables.
- Saisie rapide avec photo du justificatif, rattachement facultatif à une réservation (pour la rentabilité), mode de paiement, fournisseur.
- Vue « Trésorerie » : encaissé, à encaisser, dépensé, solde de la période, courbe mensuelle.

### 6.3 Devis, factures, reçus
- Chaîne devis → facture d’acompte → facture finale → reçus, avec avoirs en cas d’annulation. Numérotation sans trou par type et par année.
- Les documents reprennent les modèles et palettes du prompt « Devis et billets ».

### 6.4 Rentabilité
- Par réservation ou événement : recettes − coûts directs (personnel affecté au prorata des heures, transport, consommables, sous-traitance, casse non refacturée) = marge, en montant et en %.
- Par prestation : chiffre d’affaires, nombre de ventes, marge moyenne.
- Par article de stock : revenus de location cumulés, taux d’utilisation, coût d’achat, délai de rentabilisation (« Rentabilisé à 78 % »).

### 6.5 Rapports
- Période au choix (mois, trimestre, année, personnalisée) avec comparaison à la période précédente.
- Rapports : chiffre d’affaires par mois et par catégorie, activités les plus rentables, prestations les plus demandées, articles les plus loués, clients principaux, dépenses par catégorie, marge par événement, soldes impayés.
- Export PDF (aux couleurs de l’agence) et Excel. Graphiques sobres aux couleurs du design system.

## 7. Gestion du personnel

- Fiches : nom, photo, téléphone, poste (chef d’équipe, magasinier, livreur, installateur, décorateur, serveur, hôtesse, chauffeur…), type (salarié, journalier, freelance), compétences, mode de rémunération (mensuel, journalier, à la mission, horaire) et taux, Mobile Money, contact d’urgence, documents. Un membre du personnel n’a pas forcément de compte de connexion.
- Affectations : sur chaque réservation ou étape logistique, choix des personnes et de leur rôle, avec alerte si une personne est déjà affectée au même moment ou absente.
- Tâches et interventions : liste par personne et par événement, statut, commentaire, photo de fin d’installation.
- Espace « Mes missions » (mobile) pour les membres avec compte : missions du jour, adresse avec lien de navigation, liste du matériel, pointage.
- Présences : pointage arrivée et départ par mission (par le membre ou par le chef d’équipe), absences, retards, heures calculées.
- Rémunérations : calcul de la période à partir des présences et missions, plus primes, moins avances ; validation par le propriétaire ; enregistrement du paiement (espèces, Mobile Money) qui crée la dépense ; relevé de rémunération PDF par personne. Mention claire : ce relevé ne remplace pas une fiche de paie légale ni les déclarations sociales.
- Écran Personnel : tuiles (effectif, missions cette semaine, heures du mois, masse salariale du mois), liste des membres avec disponibilité du jour, planning de l’équipe sur la semaine.

## 8. Tableau de bord : refonte complète

Objectif : en ouvrant Wedivo, le propriétaire comprend en dix secondes comment va son entreprise et ce qu’il doit faire aujourd’hui. Design élégant et affirmé, sans surcharge : une seule zone forte, des chiffres nets, des graphiques sobres.

### En-tête
- « Bonjour {prénom} » et une phrase de synthèse générée à partir des données (« 3 livraisons aujourd’hui, 2 retours attendus et 1 alerte de stock. »).
- Sélecteur de période en segments : Aujourd’hui, Cette semaine, Ce mois, Ce trimestre, Cette année, Personnalisé. Toutes les tuiles et graphiques suivent la période.
- Boutons : « Nouvelle réservation » (principal), « Enregistrer une dépense ».

### Ligne 1 : la zone signature
- Grande carte sur fond encre avec les rubans du logo : Chiffre d’affaires réalisé sur la période en très grand (Sora 600, 46 px), variation par rapport à la période précédente (pastille verte ou rouge), mini courbe des 12 derniers mois en dégradé ruban, puis trois chiffres : Encaissé, À encaisser, Bénéfice estimé.
- À droite, carte Performance en 2 × 2 : Taux d’utilisation du matériel, Marge moyenne, Panier moyen par réservation, Taux de confirmation des devis, chacun avec sa variation.

### Ligne 2 : activité
- Réservations : anneau confirmées / en attente / annulées sur la période, avec chiffres cliquables qui ouvrent la liste filtrée.
- Matériel aujourd’hui : barre empilée par catégorie (disponible, réservé, loué, maintenance) et nombre total d’articles disponibles.
- Prestations les plus demandées : classement des 5 premières en barres horizontales, avec chiffre d’affaires.

### Ligne 3 : argent
- Recettes et dépenses : histogramme mensuel (recettes en violet, dépenses en corail) avec courbe du bénéfice en or, sur 6 ou 12 mois.
- Dépenses par catégorie : anneau et légende avec montants.
- Soldes à encaisser : les 5 plus gros soldes avec date d’échéance et bouton « Enregistrer un paiement ».

### Ligne 4 : aujourd’hui et alertes
- Planning logistique des 7 prochains jours : frise par jour avec livraisons, installations, événements, récupérations, chacun avec l’équipe affectée.
- Alertes : stock insuffisant, retours en retard, maintenance, factures en retard, triées par urgence, chacune avec son action.
- Équipe du jour : avatars des personnes en mission, avec statut de pointage.

### Règles de design
- Grille de 12 colonnes, espacement de 18 px, cartes de rayon 18 ; la carte signature occupe 7 colonnes, la carte Performance 5.
- Graphiques en SVG maison ou ECharts configuré sur les tokens : pas de grille épaisse, étiquettes en Manrope 12 px, couleurs uniquement du design system, info-bulle sombre arrondie.
- Animation discrète à l’arrivée (montée de 8 px et fondu, décalée de 40 ms par carte ; chiffres qui défilent jusqu’à leur valeur en 600 ms), désactivée si l’utilisateur préfère réduire les animations.
- États de chargement en squelettes à la forme des cartes ; état vide engageant pour un compte neuf (« Créez votre première réservation pour voir votre activité ici »).
- Mobile : carte signature en premier, puis Alertes et Planning, puis le reste en une colonne ; graphiques défilables horizontalement si nécessaire.
- Thème sombre soigné : la carte signature garde son fond encre plus lumineux, les graphiques adaptent leurs contrastes.
- Un seul endpoint `/dashboard/summary?period=`, mis en cache Redis 60 s, invalidé à chaque réservation, paiement, dépense ou mouvement de stock.

## 9. Modèle de données

| Modèle | Champs principaux |
|---|---|
| Client | name, company, phones, email, address, notes, preferences, archived |
| Reservation | number, client, wedding (nullable), kind, title, venue, address, guests, status, owner, delivery_at, setup_at, event_start, event_end, teardown_at, pickup_at, return_at, discount, transport_fee, setup_fee, deposit_required, total, paid, balance, deposit_held, notes |
| ReservationLine | reservation, item / pack / service (un seul), label, quantity, unit_price, period_days, deposit, amount, quantity_out, quantity_returned, quantity_damaged, quantity_missing |
| ItemCategory · Item | name, cleaning_days · reference, name, category, photo, location, tracking (quantity, unit), total_quantity, rent_price, rent_unit (day, event), sale_price, purchase_cost, deposit, alert_threshold, active |
| ItemUnit | item, serial_number, status, condition, notes |
| Pack · PackComponent | name, price, description · pack, item, quantity |
| StockMovement | item, unit (nullable), kind, quantity, reason, reservation, author, occurred_at (immuable) |
| Maintenance | item, unit, quantity, reason, started_at, expected_end, ended_at, cost |
| Inventory · InventoryLine | date, status, author · item, expected, counted, difference |
| Invoice · InvoiceLine · CreditNote | number, kind (deposit, final), reservation, client, issued_at, due_at, total, status · … · … |
| Revenue · Expense · ExpenseCategory | amount, date, category, reservation, client, payment, method · amount, date, category, supplier, reservation, receipt, method · name |
| StaffMember | name, photo, phone, position, kind, skills, pay_mode, pay_rate, mobile_money, user (nullable), active |
| Assignment · StaffTask | staff, reservation, step, role, start, end · staff, reservation, title, status, comment, photo |
| Attendance | staff, assignment, check_in, check_out, hours, status (présent, retard, absent), recorded_by |
| PayPeriod · PayLine | start, end, status · staff, base, bonuses, advances, total, paid_at, method |
| Alert | kind, severity, target, message, resolved_at |

Tous héritent de `TenantModel` (isolation par agence et RLS). Montants en entiers FCFA.

## 10. API

| Méthode | Endpoint |
|---|---|
| CRUD | /clients · /reservations · /reservations/{id}/lines |
| POST | /reservations/{id}/confirm · /cancel · /checkout · /return · /payments |
| GET | /availability?items=&from=&to= · /calendar?from=&to=&view= |
| CRUD | /items · /items/{id}/units · /packs · /item-categories |
| GET, POST | /stock-movements · /maintenance · /inventories · /inventories/{id}/validate |
| CRUD | /invoices · /credit-notes · /expenses · /expense-categories |
| GET | /finance/treasury · /finance/profitability?by=event\|service\|item · /reports/{type}?period= (json, pdf, xlsx) |
| CRUD | /staff · /assignments · /staff-tasks · /attendance · /pay-periods |
| GET | /me/missions · /alerts · /dashboard/summary?period= |

## 11. Données fictives

Étends `seed_demo` (dates décalées par rapport au jour d’exécution, comme les données précédentes) pour Maison Élégance Events, qui organise des mariages et loue du matériel. Retire les prospects non confirmés, les 32 prospects inactifs et les données de relances.

### Stock (extrait à compléter jusqu’à 30 articles)
`[catégorie, article, quantité, location FCFA, unité, vente FCFA, coût d’achat, caution, seuil]`

```
["Mobilier","Chaise Napoléon dorée",400,1500,"événement",null,9000,500,50]
["Mobilier","Chaise Chiavari transparente",250,2000,"événement",null,14000,500,40]
["Mobilier","Table ronde 10 personnes",45,5000,"événement",null,35000,5000,6]
["Mobilier","Table rectangulaire 2 m",30,4000,"événement",null,28000,5000,5]
["Mobilier","Table d’honneur modulable",4,25000,"événement",null,180000,20000,1]
["Mobilier","Canapé VIP blanc",6,30000,"événement",null,250000,25000,2]
["Linge de table","Nappe ronde blanche",60,2500,"événement",6000,4500,0,10]
["Linge de table","Chemin de table doré",80,1000,"événement",3000,1500,0,10]
["Linge de table","Housse de chaise lycra",500,500,"événement",1500,900,0,60]
["Vaisselle","Assiette de présentation dorée",400,500,"événement",2500,1800,200,50]
["Vaisselle","Verre à pied",500,300,"événement",1500,900,100,60]
["Vaisselle","Couverts (ménagère 1 pers.)",400,400,"événement",null,1500,100,50]
["Décoration","Arche florale ronde",3,60000,"événement",null,280000,30000,1]
["Décoration","Chandelier 5 branches",40,4000,"événement",15000,9000,2000,8]
["Décoration","Centre de table fleurs artificielles",50,7500,"événement",20000,12000,2000,8]
["Décoration","Tapis rouge 10 m",5,15000,"événement",null,60000,10000,1]
["Structures","Chapiteau 10 × 20 m",2,250000,"événement",null,2500000,100000,1]
["Structures","Tente pagode 5 × 5 m",6,60000,"événement",null,600000,30000,1]
["Éclairage","Guirlande guinguette 20 m",20,10000,"événement",25000,15000,3000,4]
["Éclairage","Projecteur LED (unité suivie)",16,8000,"jour",null,45000,5000,3]
["Sonorisation","Sono complète 2 × 1000 W (unité suivie)",3,75000,"jour",null,900000,50000,1]
["Énergie","Groupe électrogène 20 kVA (unité suivie)",2,90000,"jour",null,4500000,100000,1]
```

### Packs
- Pack réception 100 invités : 100 chaises Napoléon, 10 tables rondes, 10 nappes, 100 housses, 10 centres de table — 290 000 FCFA
- Pack réception 250 invités : 250 chaises Chiavari, 25 tables rondes, 25 nappes, 25 chemins de table, 25 centres de table — 760 000 FCFA
- Pack cérémonie : arche florale, tapis rouge, 2 chandeliers, 60 chaises Napoléon — 180 000 FCFA
- Pack lumière & son : sono complète, 6 projecteurs LED, 5 guirlandes, groupe électrogène (1 jour) — 260 000 FCFA

### Réservations (12, sur 6 semaines autour du jour d’exécution)
- Statuts répartis : 2 clôturées, 1 récupérée en attente de bon de retour, 1 en cours aujourd’hui, 1 installée, 2 en préparation (livraison dans 1 et 3 jours), 3 confirmées, 1 en attente d’acompte, 1 annulée.
- Types : 5 mariages complets (liés aux fiches mariage existantes : Mariam & Idriss, Aïcha & Serge, Estelle & Hervé, Christelle & Marc), 4 locations seules (anniversaire, baptême, séminaire d’entreprise, dot), 2 ventes (nappes et chandeliers à une autre agence), 1 mixte.
- Au moins une réservation qui crée une alerte de stock insuffisant (Chaise Chiavari, 280 demandées pour 250), un retour en retard et un retour avec 6 verres cassés et 2 housses manquantes facturés.
- Montants de 150 000 à 4 200 000 FCFA, acomptes et paiements cohérents.

### Clients (15)
Reprendre les clients des données précédentes et ajouter : Société Orange Events (séminaire), Famille Ekotto (dot), Mme Ngo Bassong (anniversaire), Paroisse Saint-Joseph (baptême), Agence Lumière Douala (achat de nappes), etc.

### Personnel (10)
- Awa Sangaré — Wedding planner (salariée, 250 000/mois)
- Didier Kra — Chef d’équipe (salarié, 200 000/mois)
- Nadège Brou — Comptable (salariée, 220 000/mois)
- Joël Mbarga — Magasinier (salarié, 150 000/mois)
- Serge Atangana — Chauffeur livreur (salarié, 140 000/mois)
- Brice Ndzana — Installateur (journalier, 8 000/jour)
- Mireille Fotso — Décoratrice (freelance, 40 000/mission)
- Carine Essomba — Hôtesse (journalière, 10 000/jour)
- Patrick Nkolo — Installateur (journalier, 8 000/jour)
- Linda Abena — Serveuse (journalière, 7 000/jour)

Affectations sur toutes les réservations à venir, présences pointées sur les réservations passées (dont 2 retards et 1 absence), une période de paie du mois précédent validée et payée, une en cours.

### Finances
- 12 mois d’historique : recettes cohérentes avec les réservations et une saisonnalité (pics en décembre, avril et août), dépenses mensuelles par catégorie (loyer entrepôt 150 000, carburant, maintenance, salaires calculés, achats de matériel ponctuels, marketing).
- Marge globale de l’ordre de 25 à 35 %, une réservation volontairement déficitaire (transport lointain) pour illustrer la rentabilité par événement.
- Factures : 2 en retard de paiement, 1 avoir après l’annulation.

### Maintenance et alertes
- 1 groupe électrogène en maintenance (vidange, retour prévu dans 4 jours), 3 projecteurs hors service.
- Alertes actives à l’ouverture : stock insuffisant (Chiavari), seuil atteint (verres à pied après casse), retour en retard, 2 factures en retard.

## 12. Rôles et sécurité

| Rôle | Accès |
|---|---|
| Propriétaire | Tout, y compris paie, rentabilité et rapports |
| Wedding planner | Clients, réservations, calendrier, devis, stock en lecture, affectations |
| Comptable | Finances, factures, dépenses, rapports, paie ; réservations en lecture |
| Magasinier (nouveau) | Stock, mouvements, sorties et retours, inventaires, maintenance ; aucun montant |
| Chef d’équipe (nouveau) | Ses missions, le matériel de ses missions, pointage de son équipe |
| Personnel avec compte | « Mes missions » et son propre pointage uniquement |

- Permissions vérifiées côté serveur ; les montants et salaires ne sont jamais envoyés à un rôle qui ne doit pas les voir.
- Mouvements de stock, paiements, paie et avoirs : jamais supprimés, seulement annulés avec motif ; journal d’audit.
- Contrôle de disponibilité sous verrou de base de données ; aucun dépassement possible par des requêtes simultanées.

## 13. Tests

- Retrait : plus aucune route, table, tâche ou texte lié aux relances et à la prospection ; migration des prospects confirmés en clients.
- Disponibilité : chevauchements, délais de remise en état, maintenance, packs, deux confirmations simultanées sur le dernier stock.
- Retours : quantités abîmées et manquantes créant mouvements et lignes de casse ; ventes retirant le stock.
- Finances : recettes et dépenses créées automatiquement, rentabilité par événement, prestation et article sur des données connues, rapports PDF et Excel.
- Personnel : conflits d’affectation, calcul des heures, calcul de la paie, droits du magasinier et du chef d’équipe.
- Tableau de bord : chaque chiffre vérifié contre un calcul direct sur les données de démonstration ; captures bureau et mobile, clair et sombre.
