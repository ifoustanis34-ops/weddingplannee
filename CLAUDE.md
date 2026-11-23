# Spécifications Wedivo — prompt de développement

> Source : « Wedivo — Prompt de développement pour IA.html ». Ce fichier fait foi pour toutes les sessions.
> Logo : `backend/image/` (copie dans `frontend/src/assets/logo.jpeg`).

## Avancement

- [x] Étape 1 — Socle du projet
- [x] Étape 2 — Multi-tenant et comptes entreprises
- [x] Étape 3 — Design system et coquille de l’application
- [x] Étape 4 — Prospects et clients
- [x] Étape 5 — Catalogue et devis
- [x] Étape 6 — Relances programmées
- [x] Étape 7 — Paiements, finances et tableau de bord
- [x] Étape 8 — Paramètres, équipe et abonnement
- [x] Étape 9 — Phase 2 : mariages, calendrier, prestataires
- [ ] Étape 10 — Phase 3 : invitations, QR codes, déploiement

### Complément « fidélité au prototype » (texte intégral : `docs/specs/complement-prototype.md`)

- [x] Étape A — Audit des écarts (`docs/audit-fidelite.md`) — partiel : fait sur le texte du complément, à compléter quand `docs/prototype/wedivo-plateforme.html` sera fourni
- [x] Étape B — Design system (tokens complets, composants, `WAreaChart`, page `/dev/ui`)
- [x] Étape C — Coquille et authentification
- [x] Étape D — Écrans commerciaux (tableau de bord, prospects, devis, relances)
- [x] Étape E — Écrans organisation et paramètres (sauf §14 Invitations, traité avec l’étape 10)
- [ ] Étape F — Données fictives (`seed_demo --reset --anchor`)
- [ ] Étape G — Contrôle visuel final (captures Playwright vs prototype)

**Règle d’arbitrage.** Apparence, textes et organisation des écrans : le prototype `docs/prototype/wedivo-plateforme.html` l’emporte sur ce fichier. Logique métier, sécurité, isolation multi-tenant, architecture : ce fichier l’emporte. Les données du prototype sont en dur ; dans l’application, tout vient de l’API. Avant de coder un écran, lire la section correspondante du complément (§5 coquille, §6 auth, §7 tableau de bord, §8 prospects, §9 devis, §10 relances, §11 mariages/calendrier, §12 finances, §13 prestataires, §14 invitations, §15 paramètres, §16 indicateurs, §17 données de démo) et la vue du prototype (`vDash`, `vProspects`, `vBuilder`…).

Corrections qui remplacent des points ci-dessous : graphique des encaissements en SVG maison `WAreaChart` (pas ECharts) ; tokens complets du §3 du complément (dont `--surface-3`, `--line-2`, `--violet-ink`, `--grey-soft`, `--hero-muted`, ombres) ; Tailwind ne référence que ces variables (aucune couleur Tailwind par défaut) ; icônes lucide `stroke-width` 1.8 (18 px, 22 px barre mobile, 15 px petits boutons) ; Cormorant Garamond seulement pour l’aperçu et le PDF des invitations ; badges « P2 »/« P3 » dans le menu pilotés par feature flag ; la page « Architecture technique » du prototype n’est pas à développer ; feuille d’aperçu et PDF du devis toujours blancs, même en thème sombre.

### Devis, billets, QR et scan (texte intégral : `docs/specs/devis-billets.md`)

Images de référence : `devis/` (4 modèles A Prestige, B Élégance, C Classique, D Partenariat) et `billets/` (« Ticket détachable » en 3 palettes), à la racine. L’étape R1 ne commence qu’avec ces images.

- [x] Étape R1 — Analyse des images (`docs/rendus/analyse-devis.md`, `analyse-billet.md`, `donnees-exemple.json`) — validée (A4 ; « TOTAL DES PRESTATIONS » en A et B ; billets manuscrit et portrait en R4b ; QR 25 mm)
- [x] Étape R2 — Identité des entreprises (`OrganizationBranding`, logo, couleurs, onglet Paramètres › Identité des documents)
- [x] Étape R3 — Moteur de rendu unique (HTML → PDF WeasyPrint → PNG) et 4 modèles de devis — SSIM ≥ 0,90 non atteint (voir `docs/rendus/fidelite-devis.md`) : le test garde le niveau mesuré
- [x] Étape R4 — Billets (Ticket, jeton HMAC, QR segno, Code 128, écran Billets, page publique `/t/{token}`) — SSIM ≥ 0,90 non atteint (même raison que R3)
- [ ] Étape R4b — Galerie des modèles et palettes
- [ ] Étape R5 — Emails du devis et du billet
- [ ] Étape R6 — Scan à l’entrée (`/scan`, liens contrôleur, hors ligne, `/checkin`)

**Adaptations à la plateforme existante (font foi en cas de conflit).**
- Ce prompt remplace, pour les documents : l’aperçu HTML du devis du complément §9 (l’éditeur affichera l’image PNG rendue par le serveur, même cadre) et l’invitation Cormorant du complément §14 (le billet « Ticket détachable » est le document de l’invité). Le reste du complément s’applique toujours. Les modèles `Guest` / `CheckIn` du §8 deviennent `Guest` (l’invité) + `Ticket` (son billet) + `CheckIn` (section 10 de ce prompt).
- « Clé maîtresse du coffre (prompt FreeMoPay) » : ce prompt n’existe pas dans le projet. La clé HMAC des billets est dérivée (HKDF-SHA256) d’une variable d’environnement `DOCUMENTS_MASTER_KEY` (obligatoire en production, refus de démarrer sinon), sel = identifiant de l’organisation. FreeMoPay / Mobile Money n’est pas intégré : aucun QR ni bouton de paiement n’est affiché tant que ce n’est pas le cas (§2 : ne jamais promettre).
- QR des billets : `https://{slug}.wedivo.app/t/{token}` en production, `FRONTEND_URL/t/{token}` en développement.
- Polices des documents embarquées dans `backend/documents/fonts/` (Montserrat, Playfair Display, Great Vibes ; licences OFL), jamais chargées depuis Internet. Les gabarits des documents utilisent les palettes `--doc-*`, pas les tokens de l’interface.
- Photos d’ambiance : il faut des photos HD libres de droits par palette ; tant qu’elles ne sont pas fournies, un fond dégradé de la palette les remplace (signalé dans l’analyse). Les recadrages des images de référence ne servent qu’aux tests de fidélité.
- Choix de l’espace en production (14/11/2026) : sous-domaine s’il y en a un, sinon en-tête `X-Organization` (`TENANT_HEADER_ENABLED`, défaut vrai en prod) ; Wedivo fonctionne sur une seule adresse, l’appartenance (`IsTenantMember`) et le RLS restent la protection.
- Matériel des partenaires (14/11/2026, besoin client) : `stock.PartnerSupply` (article + partenaire `vendors.Vendor` kind partner, quantité qu’il peut prêter, `unit_cost` facturé à l’agence, RLS). Un article est à nous (`total_quantity`), chez des partenaires, ou les deux. Ligne de location : `partner_supply`, `partner_quantity`, `partner_unit_cost` (figé) ; seule notre part sort du stock (`needs`, `commitments.spans`, `checkout`), la part partenaire est bornée par sa capacité sur la période (`reservations.partners` : `committed`, `offers`, `assign`, `check` appelé par `check_availability` à la confirmation, la modification et le déplacement) ; modifier les lignes garde la part partenaire par article. Coût partenaire dans `finance.profitability.by_event` (`partner_costs`). API : `/partner-supplies` (+ `/{id}`, création avec `new_item_*` pour un article qu’on n’a pas), `/items?source=own|partner` + `partner_quantity`, `/reservations/{id}/shortages` (+ `line`, `partners` libres), `POST /reservations/{id}/lines/{line}/partner`, `/reservations/{id}/partner-orders`, `/reservations/{id}/document?type=partner&vendor=` (bon de commande PDF). Import des deux listes (`stock.imports`, une feuille, colonnes Type Interne/Partenaire…, aperçu `?dry_run=true`, tout ou rien, quantités internes alignées exactement par ajustement tracé) : `POST /stock/import` (propriétaire), `GET /stock/import/template`. Coûts : propriétaire et comptable seulement. Front : onglet Stock › « Matériel des partenaires » (`PartnersTab`, `PartnerSupplyModal`, `ImportListsModal`), filtre Notre matériel / Chez les partenaires, fiche réservation « Compléter chez un partenaire » (`ReservationPartners`). Démo : `demo_partners.py`. Parcours `e2e/partner-equipment.spec.ts`.
- Cameroun et abonnements (15/11/2026) : l’inscription part du Cameroun (pays présélectionné, liste CEMAC puis UEMOA, exemple de téléphone +237) ; la monnaie et le fuseau de l’agence suivent le pays (`organizations.services.COUNTRY_DEFAULTS` : CM → XAF, Africa/Douala). Aucun prix ni choix d’offre à l’inscription (offre Pro par défaut, tout inclus) ; Paramètres › Abonnement dit « Toutes les fonctionnalités incluses », sans prix ; plus de compte à rebours d’essai sur le tableau de bord (`SUBSCRIPTIONS_ENABLED`). Les abonnements et leur paiement viendront avec une mise à jour future (la table `SubscriptionPlan` et `POST /organization/plan` restent en place).
- « Super-admin » = l’admin Django (`is_staff`).
- Console plateforme (14/11/2026) : app `platform_admin`, réservée à `is_staff` (`IsPlatformAdmin`, jamais liée à un espace ; le front n’envoie pas `X-Organization` sur `/auth/*`, `/platform/*`, `/plans`). API `/platform/overview`, `/platform/agencies` (+ `/{id}`, `/members` ; création avec propriétaire et mot de passe provisoire), `/platform/users` (+ `/{id}`, `/password`, `/memberships`), `/platform/memberships/{id}`, `/platform/journal`. `Organization.lifetime_access` (« accès à vie » : pas de fin d’essai, offre changeable à tout moment via `can_change_plan_freely`), suspension = `is_active` + `suspended_at`, `suspension_reason`, `admin_note` (jamais montrée à l’agence). Un seul propriétaire actif : nommer un propriétaire rétrograde l’ancien en planner ; le dernier ne peut être retiré. Désactiver un compte (`User.is_active`) coupe la connexion partout ; on ne se désactive pas soi-même. Journal `PlatformAuditLog` (non tenant). `User.last_login` mis à jour à la connexion. Front : module `platform` (`/plateforme`, layout `platform` ; pas `/admin`, envoyé à Django par Nginx), lien « Console plateforme » dans la barre latérale ; un super-admin sans espace arrive sur la console. Admin Django : `DJANGO_ADMIN_URL` (vide = coupée, défaut `admin/` en debug), comptes, agences (actions accès à vie, suspension), journal en lecture ; suppression d’agences et de comptes interdite (RLS). Compte : `python manage.py create_platform_admin --email … --name …`. Parcours `e2e/platform-console.spec.ts`.
- Identité (R2) : app `documents`, `OrganizationBranding` (une par organisation, créée à la demande par `documents.services.get_branding()`), `GET/PATCH /organization/branding` et `POST/DELETE /organization/branding/files` (propriétaire, audité). Fichiers sous `org/{id}/branding/<uuid>.<ext>`, type réel vérifié (Pillow), SVG nettoyé (`documents.images.sanitize_svg` : DOCTYPE refusé, scripts, `on*`, liens externes retirés), fond uni rendu transparent, rognage, contraste WCAG sur papier et sur sombre (avertissement < 3), couleurs proposées depuis le logo. Fichiers privés servis seulement par URL signée `core.signed_files` (`/api/v1/files/<jeton>`, 1 h), jamais sous `/media/`.
- Le logo de l’organisation **est** celui de l’identité : `Organization.logo` n’est plus modifiable (`GET /organization` renvoie l’URL signée) ; les PDF l’intègrent en data URI (`documents.services.logo_data_uri`, tout stockage). Carte de démarrage : étape « Ajouter votre logo » (`starter.has_logo`, cache invalidé par `finance.signals`).
- `seed_demo` : identité de Maison Élégance Events et seconde agence « Atelier Bassam Mariages » (`koffi.nguessan@atelier-bassam.ci`), logos SVG générés (`documents/demo.py`) faute de logos fournis.
- Rendu (R3) : `documents.rendering` (gabarit → PDF WeasyPrint → PNG pypdfium2 à 2×, aperçu de toutes les pages empilées, cache Redis 10 min `org:{id}:preview:…`). `url_fetcher` restreint aux schémas `wedivo-asset:` (polices et décors du dossier `documents/`) et `wedivo-file:` (fichiers sous `org/{id}/` seulement) ; tout le reste est bloqué. Polices des documents dans `backend/documents/fonts/` (Montserrat, Playfair Display, Great Vibes, Allura, OFL). Palettes en code (`documents/palettes.py`, variables `--doc-*`) en attendant R4b ; icônes au trait (`documents/icons.py`, filtre `tint` : le SVG de WeasyPrint ignore `currentColor`).
- Devis : `documents.quote_document` (instantané figé + contexte, ajustement des textes longs `fit`), gabarits `documents/templates/documents/quote_{A,B,C,D}.html` sur `quote_base.html` (pied en élément « running », en-tête réduit et « Page x sur y » au-delà d’une page, filigrane BROUILLON/ACCEPTÉ). Champs du devis : `design` (A–D), `palette`, `tagline`, `event_type`, `venue`, partenaires externes `QuotePartner` (2 au plus) ; valeurs par défaut de l’agence `OrganizationBranding.quote_design` / `quote_palette`. Icône par prestation (`ServiceItem.icon`, sinon devinée du libellé par `icons.guess`).
- Versions : `documents.generation.generate` crée un `GeneratedDocument` (instantané, PDF, PNG de la page 1, SHA-256, `DocumentTemplate` versionné) seulement si les données ont changé ; l’envoi joint cette version figée, la page publique la montre (`/public/quotes/{jeton}/preview`, `noindex`, `no-referrer`). `GET /quotes/{id}/pdf` sert la dernière version si rien n’a changé, sinon un rendu non stocké. `POST /documents/preview` (brouillon de l’éditeur ou devis enregistré), `GET /documents/designs`. L’éditeur affiche l’image serveur (`ServerPreview`, anti-rebond 400 ms) ; l’ancien aperçu HTML `QuotePreview` est supprimé.
- Performance WeasyPrint : pas de `display: flex` dans les zones répétées ou à hauteur fixe (tableaux, cartes, pied) — tableaux CSS et positions absolues, 4 à 5 fois plus rapides ; configuration des polices réutilisée par thread. Aperçu mesuré entre 0,55 et 0,81 s.
- Fidélité : `python manage.py fidelity_report --out docs/rendus/diff` (SSIM par zone, recadrages des photos de référence pour le test seulement) et `render_sample --template A|B|C|D [--lines N]`. Les dossiers `docs/`, `devis/`, `billets/` sont montés en lecture dans les conteneurs de dev.
- Reçus et contrats gardent leur gabarit `backend/templates/pdf/` (logo de l’identité) : leur passage sur l’en-tête et le pied du devis (§5 du prompt) reste à faire.
- Parcours Playwright : `e2e/fixtures.ts` bloque Google Fonts (pas de dépendance au réseau) ; importer `test`/`expect` depuis `./fixtures`.
- Billets (R4) : app `invitations` — `TicketDesign` (1 par mariage, créé depuis le titre « A & B », la date à 15 h et le lieu), `Guest` (nom ou famille, places 1–50, catégorie, table, réponse), `Ticket` (`token_id` aléatoire + `token_hash` SHA-256, jamais le jeton ; `number` par mariage sous verrou, code `WDV-{initiales}-{NNNN}` ; un seul billet actif par invité ; annuler garde le billet, réémettre crée un nouveau numéro et un nouveau jeton). Jeton = base64url(16 octets ‖ HMAC-SHA256 tronqué à 10 octets), clé HKDF de `DOCUMENTS_MASTER_KEY` salée par l’organisation (`invitations.tokens`). QR : `documents.qr` (segno), Code 128 maison `documents.barcodes` (sous-ensemble B). Gabarit `documents/templates/documents/ticket.html` (200 × 118 mm, positions absolues).
- Génération : `invitations.services.generate` (document figé, PDF seul, image tirée du PDF à la demande) ; lots Celery `invitations.tasks.generate_tickets` (file `pdf`, progression en cache `org:{id}:ticket-batch:{id}`). API : `/weddings/{id}/ticket-design` (champ `starts_at_local` dans le fuseau de l’agence), `/weddings/{id}/guests` (+ `/import` CSV/XLSX par nom de colonne), `/weddings/{id}/tickets/generate|export?type=pdf|zip`, `/ticket-batches/{id}`, `/tickets/{id}/pdf|cancel|reissue`, `/tickets/preview`. Public : `/public/tickets/{jeton}` (+ `/image`, `/pdf`, `/ics`, `POST /rsvp`), jamais d’entrée enregistrée, `noindex`. Front : `/mariages/:id/billets` (lien dans le tiroir du mariage), `/t/:token`. Message WhatsApp à copier, jamais envoyé. L’envoi par email vient avec R5, le statut « Entré » avec R6.
- `seed_demo` : 8 invités et 5 billets pour le mariage « Nadia & Koffi » (palette Émeraude & Or).
- Les étapes R s’insèrent avant l’Étape F (données fictives) et l’Étape 10 (déploiement) ; les invitations de l’Étape 10 sont traitées par R4, R5 et R6.

### Réservations, stock, finances, personnel, tableau de bord (texte intégral : `docs/specs/reservations-stock.md`)

Ce prompt **remplace** tout ce qui concerne les relances, la prospection (pipeline, canaux, import, conversion, « Temps gagné ») et le contenu du tableau de bord, y compris dans les sections 7.1, 7.2, 7.4 et 10 ci-dessous et dans le complément (§7, §8, §10, §16). Les décisions plus bas qui parlent de relances ou de prospects sont caduques une fois l’étape S1 terminée.

- [x] Étape S1 — Retrait des relances et de la prospection ; « Prospects » devient « Clients » (§2, §4.4)
  - Sauvegardes avant retrait : `backups/db-avant-S1-20261112.dump` (pg_dump -Fc) et `backups/code-avant-S1-20261112.tgz`.
  - `crm.Prospect` renommé `crm.Client` (table `crm_client`, politique RLS conservée) : `company`, `phone_alt`, `address`, `notes` (reprend `needs`), `preferences`, `is_archived`, `is_deleted`. Migration `crm.0002` : supprime les tables `reminders_*` et `crm_interaction`, archive tout prospect non « won » (jamais supprimé). Les FK `prospect` deviennent `client` (devis, contrats, mariages). Convertir un devis sort le client des archives (`crm.services.ensure_active`).
  - API : `/clients` (liste sans archives par défaut, `?archived=true`, `?search=`, tri `name`, `revenue`, `balance_due`, `last_order_at`), `/clients/{id}`, `/clients/{id}/history` (devis, contrats, paiements). Indicateurs par sous-requêtes (`crm.selectors.with_metrics`, commandes = contrats non annulés en attendant les réservations). Montants à `null` et tri par montant ignoré (`ClientOrdering`, aussi pour la pagination) pour les rôles sans `can_see_balances`.
  - App `reminders` supprimée (modèles, routes, tâches beat, file Celery `reminders`, règles du signup) ; plus d’`Interaction` ni de statut, canal, import de prospects, conversion, « Temps gagné », `next_reminder_at`. Lecture CSV/XLSX générique : `core.spreadsheets.read_table`. Fuseau : `organizations.timezones.org_tz`.
  - Front : module `crm` = page `/clients` (liste, recherche, tri, archives), `ClientDrawer`, `ClientFormModal` ; `/prospects` redirige vers `/clients`, `/relances` vers l’accueil. `WKanban` et les teintes de statut de prospect retirés ; la cloche est masquée jusqu’au centre d’alertes (S2). `useMembers` dans `@/composables/useMembers`. Libellés communs dans `common.fields`. Tableau de bord provisoire (solde, devis en attente, clients actifs, encaissements, mariages) jusqu’à S8.
- [x] Étape S2 — Navigation (§3), rôles magasinier et chef d’équipe (§12), centre d’alertes (`Alert`)
  - Menu en 7 groupes (`app/navigation.ts` : Pilotage, Activité, Matériel, Finances, Équipe, Événementiel, Espace) ; Réservations, Stock, Mouvements, Rapports, Personnel, Présences sont déclarés `ready: false` jusqu’à leur étape. Onglets mobiles `mobileTabItems` : Accueil, Réservations, Stock, Finances ; tant que Réservations et Stock n’existent pas, Clients et Devis (`mobileFallback`) prennent leur place.
  - Rôles `storekeeper` (Magasinier), `team_lead` (Chef d’équipe), `staff` (Personnel) : `core.permissions.IsTenantMember` refuse toute vue qui ne déclare pas `open_to_field_roles = True` (aujourd’hui : organisation en lecture, membres, tableau de bord sans montants, alertes) ; côté front, menu réduit au tableau de bord et garde de route. Leurs écrans arrivent avec S3 (stock) et S7 (missions, pointage). Invitables depuis Paramètres › Équipe.
  - App `alerts` : `Alert` (une ligne par situation, `dedupe_key`, `resolved_at` automatique, `dismissed_at` = « Marquer comme traitée », reste masquée tant que la situation dure). Conditions dans `alerts/conditions.py` (échéance en retard, urgente au-delà de 7 j ; tâches en retard ; mariage à J-7 avec tâches ouvertes), rafraîchies au plus toutes les 5 min (`refresh_if_stale`) et aussitôt après un changement d’argent ou de tâche (`finance.signals` efface `org:{id}:alerts:refreshed`). Visibilité par rôle (`alerts.services.visible_to`) : argent pour les rôles « soldes », tâches pour le chef d’équipe, rien encore pour magasinier et personnel. `GET /alerts`, `POST /alerts/{id}/dismiss`. Résumé quotidien par email au propriétaire à 7 h 30 (`alerts.tasks.send_daily_digests`), désactivable : `Organization.alert_digest` (Paramètres › Entreprise). Le tableau de bord lit les mêmes alertes. Front : cloche `modules/alerts/components/AlertCenter.vue` (pastille rouge si urgent), formulation partagée `modules/alerts/format.ts`.
- [x] Étape S3 — Stock et matériel : articles, unités, packs, mouvements, maintenance, inventaires, disponibilité sous verrou (§5)
  - App `stock` (9 tables sous RLS) : `ItemCategory` (délai de remise en état ; 9 catégories par défaut à l’inscription et par migration), `Item` (référence auto `MOB-007` par préfixe de catégorie, suivi `quantity` ou `unit`, `total_quantity` = quantité possédée tenue par les mouvements, prix de location / vente, coût d’achat, caution, seuil, délai propre facultatif, photo privée `org/{id}/stock/…` servie par URL signée), `ItemUnit` (n° de série, statut `available|maintenance|out_of_service|lost|sold`, état `good|worn|damaged`), `Pack`/`PackComponent`, `StockMovement` (journal immuable : `delta` signé sur la quantité possédée ; jamais supprimé, annulé avec motif et audité ; un achat avec coût crée la dépense « Achat de matériel », annulée avec lui), `Maintenance` (bloque du départ à la veille du retour ; en retard = bloque jusqu’à clôture ; le coût à la clôture crée la dépense « Maintenance et réparation »), `Inventory`/`InventoryLine` (articles suivis par quantité ; la validation transforme les écarts en ajustements).
  - Disponibilité : `stock.availability.compute(items, start, end, today)` = possédé − maintenance (pic sur la période) − unités hors service − réservé − sorti (ces deux derniers à 0 jusqu’à S4, qui les branchera ici). Packs : min des composants. `lock_items` (verrous dans un ordre fixe) prêt pour la confirmation des réservations. Toute écriture de quantité passe par `stock.services` sous `select_for_update` ; une vente, une casse ou une perte ne prend jamais plus que le disponible du jour.
  - API : `/item-categories`, `/items` (`?search=&category=&status=available|low|maintenance|out_of_service`, stock du jour par état), `/items/{id}` (+ `/photo`, `/activity` = occupation 30 j, unités, maintenances, derniers mouvements, `/labels?count=` PDF d’étiquettes QR `WDV1:ITEM:<réf>` / `WDV1:UNIT:<réf>:<série>`), `/units/{id}`, `/packs?from=&to=`, `/availability?items=&from=&to=`, `/availability/grid?from=&days=&category=`, `/stock-movements` (+ `/cancel`), `/maintenance` (+ `/close`), `/inventories` (+ `PATCH` comptage, `/validate`), `/stock/stats`.
  - Rôles : lecture propriétaire, planner, assistant, comptable, magasinier ; écriture propriétaire et magasinier ; le magasinier ne reçoit ni ne saisit aucun montant (`stock.permissions.can_see_prices`), coûts et valeur du stock pour propriétaire et comptable seulement. Alertes de stock : article sous son seuil, maintenance en retard, unité abîmée laissée disponible (visibles du magasinier).
  - Front : module `stock` (`/stock` onglets Articles grille/tableau, Packs, Disponibilité 30 j en dégradé violet, Inventaire ; fiche `?article=<id>` ; `/mouvements` journal avec annulation), barre empilée `StockBar` (disponible vert, réservé violet, sorti corail, maintenance gris §4.3), carte « Matériel aujourd’hui » du tableau de bord. Le magasinier voit Tableau de bord, Stock, Mouvements.
  - `seed_demo` : `core/management/commands/demo_stock.py` (30 articles du §11, 4 packs, groupe électrogène en vidange retour J+4, 3 projecteurs hors service).
  - Divers : test `tests/unit/i18n.spec.ts` (toute clé `t('…')` du code existe) ; jetons de billet acceptés seulement sous leur forme base64 canonique (`invitations.tokens.parse`).
- [x] Étape S4 — Réservations : lignes, statuts, confirmation, sortie, retour et casse, paiements, bons de sortie et de retour (§4.1, §4.2)
  - App `reservations` (4 tables sous RLS) : `Reservation` (numéro `RES-AAAA-NNNN` par `next_number`, client, mariage facultatif, type location/vente/prestation/mixte, responsable, dates logistiques livraison → installation → début → fin → démontage → récupération → retour, vérifiées dans cet ordre ; remise, transport, installation, acompte requis, caution, `security_status`), `ReservationLine` (location, vente, pack, prestation, ligne libre, `damage` = « Casse et pertes » créée au retour ; quantités sorties / rendues / abîmées / manquantes), `ReservationPayment` (paiement, caution, restitution ; jamais supprimé, annulé avec motif et audité), `ReservationLog` (historique).
  - Statuts : brouillon → devis envoyé → en attente d’acompte → confirmée → en préparation → livrée → installée → en cours → récupérée → clôturée, ou annulée (`services.TRANSITIONS`). `confirm` verrouille les articles (`stock.availability.lock_items`) et refuse tout manque (`shortages`, équivalents libres proposés par `alternatives`) ; sans acompte payé la réservation reste « en attente d’acompte » (le matériel est déjà bloqué), le paiement qui atteint l’acompte la confirme. `checkout` (bon de sortie : mouvements de stock, les ventes quittent le stock), `process_return` (rendu + abîmé + manquant = sorti ; casse et pertes facturées au prix de remplacement, mouvements de casse/perte, clôture), `cancel` (libère le matériel ; acompte gardé ou à rembourser selon `Organization.deposit_kept_on_cancel`, Paramètres › Entreprise), `record_payment` (jamais au-delà du solde), `settle_security` (restitution moins la retenue).
  - Engagements du stock : `reservations.commitments` (`RESERVED` = en attente d’acompte, confirmée, en préparation ; `OUT` = livrée → récupérée ; `SOLD` = commandes, de la confirmation à la clôture) ; `stock.availability.compute` les déduit sur la fenêtre livraison → retour + délai de remise en état ; `/availability?exclude=<id>` pour éditer une réservation sans se compter soi-même. Alertes `stock_shortage` (réservation à venir en manque) et `late_return`.
  - API : `/reservations` (`?tab=&search=&kind=&owner=&from=&to=`), `/reservations/stats`, `/reservations/export?type=csv|xlsx`, `/reservations/{id}` (+ `/confirm`, `/status`, `/checkout`, `/return`, `/cancel`, `/payments`, `/security`, `/shortages`, `/document?type=checkout|return` PDF), `/reservation-payments` (+ `/cancel`). Droits (`reservations.permissions`) : lecture propriétaire, planner, assistant, comptable, magasinier ; création et confirmation propriétaire et planner ; logistique (étapes, sortie, retour) + magasinier ; argent propriétaire et comptable. Montants retirés pour les rôles sans `can_see_balances`.
  - Tableau de bord : CA réalisé = contrats signés + réservations confirmées sur la période ; anneau « Réservations » (confirmées / en attente / annulées) ; utilisation du matériel = pièces-jours louées ÷ possédées ; soldes à encaisser contrats + réservations (`reservation` ouvre la fiche) ; planning avec livraisons (violet), installations (fuchsia), récupérations et retours (corail), heure et tri chronologique ; phrase du jour avec livraisons, retours, événements en cours.
  - Fiche client (§4.4) : commandes, CA, encaissé et dernière commande comptent les réservations `SOLD` (caution exclue) ; `/clients/{id}/history` renvoie aussi `reservations` et des paiements unifiés (`origin` contrat/réservation, `kind`).
  - Front : module `reservations` (`/reservations`, onglets `?onglet=`, fiche `?reservation=<id>`, assistant `?nouvelle=1` en 5 étapes avec disponibilité en direct ; `ReservationDrawer` : étapes, commande, paiements, caution, documents, historique, modales sortie / retour / paiement / caution / annulation). `WDrawer wide`. Menu et onglet mobile « Réservations » (magasinier compris).
  - `seed_demo` : `core/management/commands/demo_reservations.py` (14 réservations à tous les statuts ; à aligner sur le §11 en S9). Parcours Playwright `e2e/reservations.spec.ts` (article → réservation → confirmation → paiement → sortie → retour avec casse).
- [x] Étape S5 — Calendrier centralisé et planning logistique (§4.3)
  - Flux unique `events.calendar.build(start, end, member=, kinds=, statuses=, with_money=, movable=)` : étapes des réservations (`event` sur plusieurs jours via `end_date`, `delivery`, `setup`, `teardown`, `pickup`, `return`, avec l’heure dans le fuseau de l’agence), mariages sans réservation vivante (une réservation liée les représente), tâches ouvertes, maintenance (`maintenance`, jusqu’à aujourd’hui si en retard), paiements attendus (échéances de contrat + solde de réservation attendu le jour de l’événement — hypothèse). Tri : jour, heure, type. Le filtre `member` garde ses réservations (responsable, équipe en S7) et ses tâches, sans maintenance ni argent ; `statuses` ne garde que les réservations.
  - `GET /calendar?from=&to=&member=&kinds=a,b&statuses=a,b` (62 jours au plus ; ouvert au magasinier, jamais de montant ; chef d’équipe et personnel refusés jusqu’à S7). L’ancien `events.selectors.calendar` est supprimé ; le type `wedding` devient `event` (avec `wedding`). Le planning 7 jours du tableau de bord lit ce même flux (`PLANNING_KINDS`, brouillons exclus).
  - Déplacer : `POST /reservations/{id}/move {days}` (`reservations.services.move`, propriétaire et planner) décale toutes les dates via `update_reservation` (stock revérifié sous verrou pour une réservation engagée, refus `stock_insufficient`), refusé dans le passé ou après la sortie (`reservation_locked`), journalisé. `Reservation.vehicle` (texte libre, en attendant une flotte).
  - Front : `/calendrier?vue=mois|semaine|jour|liste|logistique&jour=AAAA-MM-JJ` (`month.ts` : `viewDays`, `shiftAnchor`, `groupByDay`, testés), légende = filtres par type, filtres membre et statut ; couleurs `calendar/kinds.ts` (§4.3) ; glisser-déposer HTML5 (`CalendarChip` + `useDropDay`, seulement les réservations `movable`), alternative clavier = fiche de réservation (dates modifiables) ouverte sur place (`?reservation=`). Le magasinier voit le Calendrier.
  - Fuseau : l’assistant de réservation lit et affiche les heures dans le fuseau de l’agence (`useDate.fromZonedInput` / `toZonedInput`, `composables/useOrgTimezone`), plus celui du navigateur.
  - Parcours Playwright `e2e/calendar.spec.ts` (étapes dans la semaine, véhicule dans le planning, glisser au lendemain).
- [x] Étape S6 — Finances : factures, avoirs, recettes, dépenses, trésorerie, rentabilité, rapports PDF/Excel (§6)
  - Recettes (§6.1) : `finance.Revenue` (montant, date, catégorie `rental|sale|service|transport|damage`, client, réservation ou contrat, paiement d’origine, `is_cancelled`). Chaque paiement de réservation (`ReservationPayment` « paiement », jamais la caution) ou de contrat crée ses recettes, réparties au prorata de ce que le client a commandé (lignes + transport + installation, remise répartie), au franc près (`finance.revenues.split`, plus forts restes) ; annuler le paiement annule ses recettes. Appels explicites dans `reservations.services` et `contracts.services`. Reprise des paiements antérieurs : `finance.revenues.backfill()` (idempotent, exécuté en dev).
  - Factures et avoirs (§6.3) : `Invoice` (`deposit` | `final`, figée à l’émission : lignes `InvoiceLine` + instantané du document), `CreditNote`. Numéros sans trou par type et par année, réservés dans la transaction : `FA-AAAA-NNNN`, `AV-AAAA-NNNN` (`DocumentSequence` `invoice`, `credit_note`). `finance.invoicing.issue` : acompte = acompte demandé (une seule fois, avant toute autre facture) ; finale = tout ce qui n’est pas encore facturé, lignes de la réservation + remise, transport, installation, « Déjà facturé — FA-… » en négatif (une seconde finale facture la casse ajoutée au retour) ; échéance = émission + 7 j, solde au plus tard 7 j avant l’événement. Statut calculé, jamais stocké (`invoicing.states`) : paiements de la réservation affectés aux factures dans l’ordre d’émission, nets des avoirs → `paid|partial|issued|overdue|cancelled`. Avoir manuel ≤ ce que la facture réclame encore ; à l’annulation d’une réservation, avoirs automatiques sur tout sauf l’acompte reçu que l’agence garde (politique `deposit_kept_on_cancel`). PDF : les 4 modèles du devis et la palette de l’agence (`finance.invoice_documents`, titre `doc_label` « FACTURE » / « AVOIR » dans `quote_{A..D}.html`). Alerte `overdue_invoice` (argent : rôles « soldes »).
  - Dépenses (§6.2) : `Expense.reservation` (rentabilité ; sans catégorie → « Sous-traitance ») et `Expense.receipt` (photo redimensionnée ou PDF, privé `org/{id}/finance/receipts/…`, URL signée). `POST/DELETE /expenses/{id}/receipt`.
  - Trésorerie, rentabilité, rapports : `finance.treasury` (encaissé = recettes, à encaisser, dépensé, solde, période précédente, 12 mois, par catégorie, factures en retard), `finance.profitability` (par événement : recettes − dépenses rattachées, le personnel s’y ajoutera en S7 ; par prestation : ventes, CA, marge moyenne = marge des événements pondérée par la prestation (hypothèse) ; par article : revenus de location cumulés, packs répartis au prix de location des composants, utilisation, coût d’achat × quantité, « Rentabilisé à x % »), `finance.reports` (8 rapports en tableaux colonnes/lignes/totaux + chiffre clé comparé : `revenue`, `profitable`, `services`, `items`, `clients`, `expenses`, `margins`, `unpaid` ; PDF paysage aux couleurs et au logo de l’agence `finance/templates/finance/report.html`, Excel openpyxl). Période commune `finance.periods.from_params`.
  - API (`finance/billing.py`) : `/invoices` (GET `?reservation=&client=&status=&search=`, POST `{reservation, kind}`), `/invoices/{id}` (+ `/pdf`, `/credit`), `/credit-notes` (+ `/{id}/pdf`), `/revenues?period=`, `/finance/treasury`, `/finance/profitability?by=event|service|item`, `/reports/{type}?period=&from=&to=&output=json|pdf|xlsx` (export audité). Lecture des factures et recettes : rôles « soldes » ; émission, avoirs : propriétaire et comptable ; trésorerie, rentabilité, rapports : propriétaire et comptable.
  - Front : Finances en onglets `?onglet=tresorerie|factures|recettes|depenses|rentabilite|contrats` (le planner voit Factures, Recettes, Contrats), sélecteur de période du tableau de bord, `ReportTable` générique, `CreditModal`, `ExpenseModal` (réservation liée, justificatif), section Factures de la fiche réservation (`ReservationInvoices` : facture d’acompte, facture finale, PDF). Page `/rapports` (menu « Rapports », propriétaire et comptable). `finance.expenseList.*` (la clé `finance.expenses` sert à la fiche contrat).
  - `seed_demo` : `core/management/commands/demo_invoices.py` (acomptes et finales des réservations, factures en retard, 1 avoir) ; alignement exact sur §11 (2 en retard, avoir après annulation) en S9.
- [x] Étape S7 — Personnel : fiches, affectations, missions, présences, paie (§7)
  - App `staff` (6 tables sous RLS) : `StaffMember` (poste libre, type salarié / journalier / freelance, compétences, rémunération `monthly|daily|mission|hourly` + taux, Mobile Money, contact d’urgence, photo privée, `user` facultatif = compte « Mes missions », jamais supprimé : `is_active`), `Assignment` (réservation + étape `all|delivery|setup|event|teardown|pickup|return`, rôle, créneau calculé par `services.step_window` : heure de l’étape + 2 à 4 h, l’événement du début à la fin, « toute la réservation » de la livraison au retour ; suit les dates quand la réservation est modifiée ou glissée, `follow_reservation`), `StaffTask` (statut, commentaire, photo de fin d’installation), `Attendance` (une par affectation : arrivée, départ, heures, `present|late|absent` ; en retard au-delà de 15 min), `PayPeriod` / `PayLine`.
  - Conflits (§7) : `services.conflicts` (déjà affecté au même moment, absent ce jour-là) — l’affectation est permise et l’alerte renvoyée (`conflicts`), affichée en rouge dans la fiche réservation.
  - Paie : base = mensuel × mois entiers (sinon jours ÷ 30), journalier × jours pointés, mission × réservations pointées, horaire × heures ; + primes − avances ; recalcul tant que la période est « En cours », validation par le propriétaire seul, puis paiement par ligne (propriétaire, comptable) qui crée la dépense « Salaires et journaliers » ; période « Payée » quand tout est versé. Relevé PDF par personne (`staff/templates/staff/statement.html`) avec la mention « ne remplace pas une fiche de paie légale ni les déclarations sociales ».
  - Coût du personnel par événement (§6.4) : `services.reservation_cost` (heures pointées sinon prévues × coût horaire ; journalier une fois par jour ; mission une fois) ajouté aux coûts directs de `finance.profitability.by_event` (`staff_costs`). Calendrier : `team` par étape et filtre `member` qui inclut les affectations. Tableau de bord : « Équipe du jour » = missions et pointage (`absent`, `late`), sinon les tâches.
  - API : `/staff` (+ `/{id}`, `/photo`, `/stats`, `/planning?from=`), `/assignments` (`?reservation=&staff=`, POST → `conflicts`), `/assignments/{id}` (DELETE tant que personne n’a pointé) + `/check-in`, `/check-out`, `/absent`, `/staff-tasks` (+ `/{id}`, `/photo`), `/me/missions`, `/pay-periods` (+ `/refresh`, `/validate`), `/pay-lines/{id}` (PATCH primes, avances ; `/pay`, `/statement`). Droits : annuaire lu par propriétaire, planner, assistant, comptable, écrit par propriétaire et planner ; taux et paie pour propriétaire et comptable seulement (jamais envoyés aux autres, le planner ne fixe aucun salaire) ; pointage : propriétaire et planner pour tous, chef d’équipe pour les personnes de ses réservations, personnel pour lui-même (pas d’absence) ; « Mes missions » ouvert aux rôles de terrain (adresse, lien Google Maps, matériel sans prix, tâches, équipe pour le chef).
  - Front : module `staff` — `/personnel` (tuiles effectif, missions de la semaine, heures du mois, masse salariale ; membres avec disponibilité du jour ; planning de la semaine), `/presences` (pointage du jour, paie), `/mes-missions` (mobile, onglet « Missions » des rôles de terrain), `ReservationTeam` dans la fiche réservation. Menu « Équipe » : Personnel, Présences & paie, Mes missions (chef d’équipe, personnel).
  - `seed_demo` : `core/management/commands/demo_staff.py` — les 10 personnes du §11, comptes `didier.kra@maison-elegance.ci` (chef d’équipe) et `linda.abena@maison-elegance.ci` (personnel), affectations sur toutes les réservations vivantes, pointages passés (2 retards, 1 absence), paie du mois précédent validée et payée, mois en cours en préparation. Parcours Playwright `e2e/staff.spec.ts`.
- [x] Étape S8 — Refonte du tableau de bord (§8) — faite avant S2 à la demande de l’utilisateur ; les blocs liés au stock, aux réservations et au personnel se branchent en S3, S4, S7
  - `GET /dashboard/summary?period=today|week|month|quarter|year|custom&from=&to=` (`finance/dashboard.py`, périodes et période précédente dans `finance/periods.py`). Cache 60 s par période et par jour ; `finance.dashboard.invalidate` change un numéro de version (`org:{id}:dashboard:version`) : toutes les périodes tombent d’un coup (signaux sur paiements, contrats, devis, dépenses, catégories, clients, mariages, tâches).
  - Définitions (en attendant réservations et factures) : CA réalisé = contrats signés sur la période ; encaissé = paiements de la période ; à encaisser = solde de tous les contrats vivants ; bénéfice estimé = CA − coûts directs de ces contrats − dépenses générales datées de la période ; marge moyenne, panier moyen, confirmation des devis (acceptés ÷ décidés), taux d’encaissement des échéances (remplace l’utilisation du matériel jusqu’à S3). Anneau « Commandes » = contrats signés / devis envoyés en attente / devis refusés + contrats annulés (devient « Réservations » en S4). La carte « Prochains mariages » tient la place de « Matériel aujourd’hui » jusqu’à S3. Planning 7 jours = mariages, tâches (3 par jour au plus), échéances ; alertes = échéances en retard (urgent > 7 j), mariage à J-7 avec tâches ouvertes, tâches en retard ; équipe du jour = tâches du jour par membre (pointage en S7).
  - Rôles : l’assistant ne reçoit aucun montant (signature remplacée par sa journée), le planner ni bénéfice, ni marge, ni dépenses ; filtrage serveur dans `strip_for_role`.
  - Catégories de dépenses (§6.2, avancé) : `finance.ExpenseCategory` (10 par défaut à l’inscription et par migration, modifiables, jamais supprimées), `Expense.category/supplier/method`, `Expense.wedding` facultatif ; une dépense générale exige sa catégorie ; une dépense de mariage sans catégorie va en « Sous-traitance ». `GET/POST /expense-categories`, `PATCH /expense-categories/{id}` (propriétaire, comptable). Modale « Enregistrer une dépense » (`finance/components/ExpenseModal.vue`).
  - Couleurs des graphiques validées par calcul (script dataviz) : jetons `--chart-income`, `--chart-expense`, `--chart-profit`, `--chart-1…5` (ordre violet, fuchsia, or, vert, corail : fuchsia jamais à côté du vert, anneau compris), `--chart-other`, `--chart-grid`, `--tooltip-bg` dans les trois thèmes. L’anneau des dépenses attribue les couleurs aux 5 catégories les plus lourdes sur 12 mois (couleur stable d’une période à l’autre), le reste en « Autres ». Géométrie pure testée : `dashboard/charts.ts` ; défilement des chiffres `composables/useCountUp.ts` (coupé si animations réduites).
  - `seed_demo` : 12 mois d’activité (`core/management/commands/demo_history.py`) : 10 contrats, saisonnalité déc./avr./août, une prestation déficitaire (Kribi), dépenses mensuelles, échéance en retard (Famille Ekotto), tâches du jour ; marge annuelle ≈ 34 %. Les coûts d’un mariage sont datés du jour de l’événement.
- [x] Étape S9 — Données fictives (§11) — remplace l’étape F pour ces modules
  - `seed_demo` conforme au §11, vérifié par `core/tests/test_seed_demo.py::test_seed_demo_matches_the_fictional_data_of_section_11` : 30 articles, 4 packs ; 12 réservations sur six semaines (2 clôturées dont le baptême avec 6 verres cassés et 2 housses manquantes facturés, 1 récupérée en retour en retard, 1 en cours, 1 installée, 2 en préparation livrées dans 1 et 3 jours, 3 confirmées, 1 en attente d’acompte, 1 annulée) ; 5 mariages complets liés à leur fiche mariage (créée si absente : `demo_reservations._wedding`), 4 locations (anniversaire, baptême, séminaire, dot), 2 ventes à l’Agence Lumière Douala, 1 mixte ; montants de 150 000 à 4 200 000 ; 15 clients actifs.
  - Alertes à l’ouverture : stock insuffisant (mariage Grâce & Yannick, 280 Chiavari pour 250, accepté « avant l’inventaire » : statut forcé par le seed, la vraie confirmation le refuse), verres à pied sous le seuil (casse + verres sortis sur les événements en cours), retour en retard, 2 factures en retard exactement (les autres reçoivent une échéance plus lointaine). Avoir créé par l’annulation des Fiançailles Tchouta (factures d’acompte et finale émises avant). Coûts directs par réservation (carburant, fleurs et consommables) et une réservation déficitaire : le mariage Ekotto à Yaoundé (camion aller-retour 1 150 000).
  - Écart assumé : les couples Aïcha & Serge, Estelle & Hervé, Christelle & Marc ont leur mariage dans l’historique de 12 mois (S8) ; les 5 mariages réservés sont ceux des six semaines (Diabaté, Mariam & Idriss, Kouamé, Ekotto, Grâce & Yannick).
  - `make demo-reset` : sauvegarde `backups/db-avant-demo-reset-*.dump`, recrée la base de dev, migre, `seed_demo`, `seed_e2e` (à lancer par l’utilisateur : supprime les données de dev).
- [ ] Étape S10 — Tests transverses et captures (§13)

**Retours du 12-13/11/2026 (décisions produit, font foi).**
- Toutes les fonctionnalités pour toutes les agences, quelle que soit l’offre : `settings.ALL_FEATURES_INCLUDED` (vrai par défaut) neutralise les limites d’offre (`max_users` à l’invitation et au changement d’offre) ; les rôles restent (le propriétaire voit tout, les autres selon leur rôle). Note dans Paramètres › Abonnement. Les futurs modules pourront être réservés à une offre.
- Pages en pleine largeur (plus de `max-w-[1360px]` dans `AppLayout`) ; « Mes missions » garde sa colonne mobile.
- Boutons explicites : main au survol sur tout élément cliquable (`main.css`, Tailwind 4 ne la met pas), `WButton secondary` = contour et texte violets, `ghost` = texte violet.
- « Télécharger » au même endroit (en haut à droite) sur chaque écran : `components/DownloadMenu.vue` (PDF, CSV, Excel). Serveur : `GET /exports/{kind}?output=pdf|csv|xlsx` (`core/exports.py` : reservations, clients, quotes, items, movements, invoices, revenues, expenses, staff, pay, calendar ; mêmes droits et mêmes montants masqués que l’écran ; audité `export.downloaded`), rapports `?output=csv` en plus, moteur commun `finance.reports.respond` (CSV « ; » UTF-8 avec BOM pour Excel français). Finances : le menu suit l’onglet (trésorerie → rapport CA, rentabilité → rapport marges, contrats → ancien export CSV/Excel).
- Paie dans le menu (13/11/2026) : « Présences » = pointage seul ; « Paie » (`/paie`, propriétaire et comptable) = onglets « Payer la journée » (`DayPayPanel` : `GET /pay/day?date=&reservation=` liste qui a travaillé ce jour-là avec le montant proposé selon le taux et le pointage, salariés exclus ; `POST /staff-payments` paie plusieurs personnes d’un coup, une dépense « Salaires et journaliers » chacune, modèle `StaffPayment`), « Salaires du mois » (`PayPeriodsPanel`, `PayLine.already_paid` déduit ce qui a été payé le jour même : jamais deux fois), « Historique ». Audit `staff.paid_on_the_spot`.
- Badge « Carte employé » (modèle par défaut `carte`, référence `photo/lop.jpeg` fournie le 13/11/2026) : portrait 54 × 85,6 mm recto-verso (`staff/templates/staff/badge_card.html`) — recto : logo, bandes diagonales, photo cadre or, nom, poste, Département / Matricule / Contact avec icônes, vague et slogan (`branding.slogan` ou `quote_tagline`) ; verso : logo, 3 valeurs (engagements courts, sinon « Rigueur • Élégance • Confiance »), « CARTE EMPLOYÉ / PERSONNEL / PRESTATAIRE » selon le type, QR, « Scannez pour vérifier l’authenticité », raison sociale et activité. Couleurs fixes de la référence (violet #2b1252, dégradé or) pour une copie fidèle ; logo de l’agence. Textes mesurés avec Montserrat (`staff.badges.fit`, `two_lines` : slogan sur deux lignes équilibrées), silhouette grise sans photo, département de démo par poste (`demo_staff.fill_departments`). PDF : recto puis verso colonnes en miroir (impression recto-verso, bord long). `StaffMember.department`, `employee_number` (`services.ensure_employee_number` : `ME-2026-001`, ASCII). QR = `FRONTEND_URL/b/<jeton de 36 caractères : uuid + HMAC tronqué>` → page publique `/b/:token` (`GET /public/badges/{jeton}`, `noindex`) : « Badge valide » si la personne est active, nom, poste, photo (URL signée 1 h), jamais de téléphone ni de paie ; jeton modifié = « Badge non reconnu ».
- Badges en 4 modèles (`staff/badges.py` `DESIGNS` : classique, portrait 54 × 85,6 mm 9 par A4, élégant, minimal ; QR toujours sombre sur blanc), aperçu PNG `GET /staff/badges/preview?design=&staff=`, choix dans `BadgesModal` (Personnel et fiche).
- Tâches repensées (13/11/2026) : tableau en trois colonnes « À faire → Faites, à valider → Validées » (`TasksTab.vue`, `TaskCard.vue` : quoi, qui, événement, lieu, échéance J-x / en retard, commentaire, photo, renvoi motivé), 6 cartes par colonne puis « Afficher plus ». `StaffTask.status` = `todo|done|validated` + `done_at/by`, `validated_at/by`, `rejection_reason` ; la personne coche « faite » (PATCH), le propriétaire ou le planner valide (`POST /staff-tasks/{id}/validate`) ou renvoie avec motif (`/reject`) ; une tâche validée ne change plus côté personnel.
- Matériel partenaire (à construire, données attendues de l’utilisateur via `docs/modeles/materiel-interne.xlsx` et `materiel-partenaires.xlsx`) : quantités du partenaire indicatives → chaque ligne partenaire « à confirmer » par appel ; casse et pertes refacturées au client au prix réclamé par le partenaire.
- Pages de connexion et d’inscription (13/11/2026, `app/layouts/AuthLayout.vue`) : panneau gauche = accroche, 6 modules avec les icônes du menu (Réservations, Stock, Devis et factures, Finances, Personnel et paie, Calendrier), bloc « Besoin d’aide ? » ; formulaire en carte à droite, mention « Connexion sécurisée ». Contacts de Wedivo hors du code : `VITE_SUPPORT_PHONE`, `VITE_SUPPORT_WHATSAPP`, `VITE_SUPPORT_EMAIL`, `VITE_SUPPORT_HOURS` (`app/support.ts`, bloc masqué sans valeur ; `frontend/.env.development` : +237 657 84 74 84 (appel et WhatsApp), pas d’email ; mêmes valeurs à reporter en production). Vitest se lance dans le conteneur `frontend` (Node 22) : le Node 20 de l’hôte ne charge plus `undici`.
- Comptes (13/11/2026) : « Mon profil » `/profil` (tous les rôles, lien sur le nom en bas de la barre latérale) — nom et téléphone (`PATCH /auth/me`), mot de passe (`POST /auth/me/password`, l’actuel d’abord) ; l’email reste l’identifiant. Le propriétaire crée un compte sans email d’invitation : `POST /organization/members` (nom, email, téléphone, rôle, mot de passe provisoire ; un compte Wedivo existant garde son mot de passe), `POST /organization/members/{id}/password` (nouveau provisoire, refusé si le compte sert dans un autre espace), `POST /staff/{id}/account` (« Créer son accès » depuis la fiche du personnel, compte relié à la fiche → « Mes missions »). Tout est audité (`membership.created`, `membership.password_set`). `User.must_change_password` : la garde du routeur renvoie vers `/profil` tant que le mot de passe provisoire n’est pas changé. Mot de passe proposé `app/passwords.ts` (sans caractères ambigus) ; `components/AccountCredentials.vue` affiche l’accès et un message à copier ou à ouvrir dans WhatsApp (jamais envoyé par Wedivo). Parcours `e2e/team-accounts.spec.ts`.
- Espace du personnel (13/11/2026) : l’accueil (`modules/dashboard/pages/HomePage.vue`) affiche « Mon espace » (`modules/staff/components/MySpace.vue`, menu « Mon espace ») pour personnel et chef d’équipe, le tableau de bord pour les autres rôles. `GET /me/overview` (`staff.services.overview`) : missions de la semaine et du mois, heures pointées du mois, ponctualité et présence sur 90 j (anneau), tâches à faire / faites / validées (anneau), heures par semaine sur 8 semaines (`WAreaChart`), prochaine mission, équipe du jour (chef d’équipe, groupée par réservation, pointage sur place) ; jamais de montant. `/me/missions` couvre 14 j passés et 30 j à venir avec `state` (`upcoming|in_progress|done`, `services.mission_state`) ; page « Mes missions » groupée Aujourd’hui / Demain / Cette semaine / Plus tard / Terminées (`modules/staff/missions.ts`, testé), carte `MissionCard` (étape aux couleurs du calendrier, état, arrivée / départ, itinéraire, client, détails dépliables : tâches avec barre d’avancement, matériel, équipe).
- PWA (13/11/2026) : `public/manifest.webmanifest`, icônes tirées du logo HD (`icon-192/512`, `icon-maskable-512`, `apple-touch-icon`, `badge-96` monochrome), `public/sw.js` (navigation réseau d’abord puis coquille en cache, `/assets/*` cache d’abord, jamais `/api/` ; push et clic sur notification ; en dev `?dev=1` = aucun cache), `app/pwa.ts` (enregistrement, invite d’installation, abonnement push, message du SW → `invalidateQueries`). En production, servir `/sw.js` avec `Cache-Control: no-cache` et en HTTPS (le service worker et le push exigent un contexte sécurisé ; `localhost` seul fait exception).
- Notifications push en temps réel (13/11/2026) : app `notifications` — `PushSubscription` (appareil d’un utilisateur, table de contrôle comme `Membership`, pas de RLS), `notifications.push.notify(users, title, body, url, kind, tag)` après le commit puis Celery (`send_push`, file `default`, appareils 404/410 oubliés), titre préfixé du nom de l’agence. Clés VAPID dans `.env` (`manage.py generate_vapid_keys` ; sans clés rien n’est envoyé et l’interface masque l’interrupteur). API : `GET /push/config`, `POST /push/subscriptions`, `POST /push/subscriptions/remove`, `POST /push/test`. Déclencheurs : nouvelle mission (`staff.services.assign` → la personne), nouvelle tâche (création → la personne), tâche faite par la personne (→ propriétaire et planners), tâche renvoyée avec motif (→ la personne), paiement de réservation (→ propriétaire et comptable), nouvelle alerte urgente (`alerts.services.refresh` → rôles qui la voient). Front : bloc « Application et notifications » de « Mon profil » (`components/PushSettings.vue` : installer, activer, tester, désactiver), invitation sur l’accueil (`components/PushPrompt.vue`, « Plus tard » mémorisé), désabonnement de l’appareil à la déconnexion. Dépendances : `pywebpush`, `py-vapid`, `http-ece`, `cryptography` (image backend reconstruite).
- Tâches dans « Mes missions » (17/11/2026) : une tâche donnée sur un événement où la personne n’a pas de mission devient une carte `kind: "tasks"` (« Tâches à faire » : lieu, date, itinéraire, client, tâches à cocher, sans pointage ; `staff.views._task_cards`) ; les missions ont `kind: "mission"`. Dans toute carte, les tâches sont visibles sans ouvrir « Détails » (matériel et équipe restent repliés).
- Notifications comme WhatsApp (17/11/2026) : `notifications.Notification` (TenantModel + RLS, une ligne par personne) écrite par `push.notify()` à chaque événement, avec ou sans clés VAPID, puis push après commit avec `badge` = non lues de la personne (toutes agences, `tasks.unread_counts`). Qui est prévenu : `notifications/flow.py` (jamais l’auteur de l’action ; jamais de montant aux rôles sans argent) — réservation créée, confirmée ou en attente d’acompte, changement d’étape, sortie et retour du matériel (casse), annulation ; mission affectée ; tâche créée, faite, renvoyée, validée ; arrivée en retard, absence ; journée payée (sans montant) ; paiement reçu ; devis accepté ou refusé en ligne par le client ; alertes urgentes et importantes. API `GET /notifications` (50 dernières, `unread`, `unread_all`), `POST /notifications/{id}/read`, `POST /notifications/read-all`. Front : cloche à deux onglets « Notifications » (non lues en gras + point violet, clic = lu + page) et « Alertes » ; chiffre rouge = non lues (sinon les alertes) ; « (3) Wedivo » dans l’onglet et chiffre sur l’icône de l’application installée (Badging API, `modules/notifications/badge.ts`, aussi posé par `sw.js` à la réception du push) ; temps réel = push instantané + relecture toutes les 10 s et au retour sur l’onglet.
- WhatsApp sur les documents (20/11/2026) : `composables/useWhatsApp.ts` + `components/WhatsAppButton.vue` — jamais d’envoi par Wedivo (§2) : sur téléphone, feuille de partage avec le PDF joint ; sur ordinateur, PDF téléchargé + `wa.me/<numéro>?text=`. Devis : bouton « Envoyer sur WhatsApp » de l’éditeur (`POST /quotes/{id}/send` `{channel: "whatsapp"}` : marqué envoyé et version figée, sans email ni adresse vérifiée, message avec le lien public). Factures (onglet Factures, fiche réservation ; `client_detail.phone`), bons de sortie/retour (téléphone du client), bons de commande partenaires (téléphone du partenaire).
- Croquis des salles (20/11/2026) : app `floorplans` (`FloorPlan` TenantModel + RLS : `name`, `venue`, `length`/`width` en mètres, `elements` JSON `{id, type, x, y, w, h, rotation, label, seats}` validés par `serializers.ELEMENT_TYPES`, `notes` ; `chairs` calculé). API `/floor-plans` (+ `/{id}`) : tous les membres lisent (rôles terrain compris), propriétaire, planner et assistant dessinent. Front `/croquis` (menu Événementiel) : `PlanCanvas.vue` (SVG à l’échelle, 1 unité = 1 m, couleurs fixes `PAPER` comme une feuille), glisser à la souris ou au doigt (pas de 5 cm), clavier, annuler, export PNG (`image.ts`) et envoi sur WhatsApp.
- Mode hors ligne (20/11/2026) : `src/offline/` — `cache.ts` garde les réponses déjà vues (TanStack `dehydrate`/`hydrate`, IndexedDB `storage.ts`, par personne et par espace, 7 jours, effacées à la déconnexion) ; `queue.ts` garde les écritures (POST/PATCH/PUT/DELETE, jamais `/auth/`, `/public/`, fichiers) qui n’ont pas atteint le serveur (`ERR_NETWORK`, pas les délais dépassés) : `ApiError` `offline_queued` (toast en information), rejouées dans l’ordre, dans leur espace, au retour du réseau (événement `online` + essai toutes les 30 s), refus du serveur mis de côté avec la raison (réessayer / abandonner). `OfflineStatus.vue` dans la barre du haut. Mutations en `networkMode: 'always'`. Session mémorisée (`wedivo-session`) : démarrage hors ligne, confirmée au retour. En production, tous les écrans sont préchargés pour s’ouvrir hors ligne.
- Croquis 3D, suite (23/11/2026) : « Entrer dans la salle » (`scene3d/walk.ts` : à 1,65 m, regard au glisser, pavé tactile + flèches/ZQSD/WASD, Maj pour courir, collisions murs et mobilier `SOLID` avec glissement), plafond et murs opaques à pied, seuls les numéros de table restent affichés ; ambiance enregistrée `FloorPlan.ambiance` (`floor` tiles/parquet/marble/concrete/carpet/grass, `walls` white/cream/grey/none = plein air, `light` day/evening, `height`), sols dessinés sur canvas (`scene3d/textures.ts`), soirée = lustres, guirlandes, bougies, piste lumineuse, projecteur DJ ; nouveaux éléments `head_table` (chaises d’un seul côté), `cocktail`, `cake`, `lounge`, `photobooth`, `plant`, `chandelier`, `screen` (`scene3d/objects.ts`). Partage d’un document : seul le fichier part, sans message (sur ordinateur : PDF téléchargé + discussion vide).
- Partage des documents et vue 3D (23/11/2026) : devis — « Envoyer sur WhatsApp » joint désormais le PDF (version figée de `/quotes/{id}/generate`) avec le message et le lien, « Partager le PDF » ouvre la feuille de partage du téléphone pour toute application (sur ordinateur : PDF téléchargé + message copié) ; `useWhatsApp().shareAnywhere`, et `ShareReady.vue` (monté dans `App.vue`) redemande un toucher quand le téléphone refuse le partage après la préparation du PDF (`NotAllowedError`). Croquis : bascule « Plan 2D / Vue 3D » (`Plan3D.vue`, three.js 0.170 chargé à la demande) — sol, murs transparents (masquables), tables nappées avec centre de table, chaises orientées dos à la table, estrade, piste, buffet, bar, DJ, arche fleurie, poteaux, étiquettes ; vues d’ensemble, de dessus, à hauteur d’invité (depuis l’entrée) ; l’image et l’envoi WhatsApp prennent la vue affichée. Lecture seule : on édite en 2D.
- Anti-robot (20/11/2026) : `core/antibot.py` (champ piège `website` + jeton daté `GET /auth/form-token`, 2 h max, `ANTIBOT_MIN_SECONDS` pour l’inscription) sur connexion, inscription, mot de passe oublié, ajouté par `authApi` (`api/formGuard.ts`, `HoneypotField.vue`) ; `core/throttling.py` (`API_RATE_ANON`, `API_RATE_USER`) ; `audit.client_ip` = dernière adresse publique de `X-Forwarded-For` ; `robots.txt` interdit tout. Désactivé en tests (`ANTIBOT_ENABLED=False`) sauf `core/tests/test_antibot.py`.
- Mode présentation (16/11/2026) : page `/presentation` (menu « Mode présentation » pour propriétaire, planner, assistant, comptable), lecteur `components/PresentationPlayer.vue` monté dans `AppLayout` : joue seul les parcours de `modules/presentation/scenarios.ts` (agence, location A→Z, magasinier, terrain, argent ; textes `presentation.scenarios.*`) — change de rôle (`POST /demo/switch`, `accounts/demo.py`, sans mot de passe, audité `demo.role_switched`), ouvre l’écran ou une vraie fiche de la démo, entoure la cible avec un pointeur, avance seul (pause Espace, ← →, vitesse 0,75/1/1,5, Échap), rend le rôle de départ en quittant ; panneau à gauche quand une fiche est ouverte à droite. Ouvert seulement si `DEMO_MODE` et l’espace dans `DEMO_ORGANIZATIONS` (défaut faux ; vrai en dev pour `maison-elegance`, `canopy-houses`). La visite guidée se tait pendant une présentation. Démo : compte magasinier `joel.mbarga@maison-elegance.ci` (`demo_staff.ensure_logins`).
- Suppression (13/11/2026, propriétaire et planner, auditée) : personnel `DELETE /staff/{id}` (`staff.services.delete_staff`) — sans historique la fiche disparaît, sinon `is_deleted` (hors listes, planning, badges, exports ; missions passées, pointages et paie gardés), missions à venir non pointées retirées avec leurs tâches, accès à l’espace coupé (sauf propriétaire) ; réponse `permanent`, `removed_assignments`, `access_closed`. Fournisseurs et partenaires `DELETE /vendors/{id}` — sans mariage supprimé, sinon `is_deleted` (hors carnet, toujours sur ses mariages, plus réservable). Boutons « Supprimer » rouges avec confirmation (bas de la fiche du personnel, pied de la fiche fournisseur). La règle « jamais supprimé » du §S7 est remplacée.
- Carnet « Partenaires et fournisseurs » (13/11/2026) : `Vendor.kind` = `supplier` (Fournisseur : l’agence lui achète) | `partner` (Partenaire : travaille avec l’agence ou complète son matériel), `?kind=` sur `/vendors`, onglets Tous / Fournisseurs / Partenaires (les catégories suivent l’onglet), badge dans la liste, colonne Contact = nom, téléphone, ville ; menu « Partenaires & fournisseurs » ; démo : 5 partenaires (salle, sono, location de matériel, photographe, DJ), le type n’est posé qu’à la création.
- « Prestataires » devient « Fournisseurs » (13/11/2026) : menu, écrans, messages, route `/fournisseurs` (`/prestataires` redirige ; l’app Django reste `vendors`). Fiche complète : `contact_name`, `whatsapp`, `city`, `address`, `tax_id` (NIU), `trade_register` (RCCM), `payment_terms`, `mobile_money`, `bank_details` ; `services` (« Services proposés », remplace l’évaluation 1–5 supprimée le 13/11/2026, migration `vendors.0003`) ; catégories en plus : fleuriste, sonorisation et lumière, fournitures et consommables, sécurité, autre. Liste : recherche, colonne Contact, WhatsApp et appel. Démo : `core/management/commands/demo_vendors.py` (13 fournisseurs camerounais, champs vides complétés sans écraser, numéros +225 remplacés, fournisseurs posés sur les 3 prochains mariages). Le badge « CARTE PRESTATAIRE » du personnel freelance n’est pas concerné.
- Entrée « Tâches » dans le menu (groupe Équipe, `/taches`, `staff/pages/TasksPage.vue` = même vue que l’onglet, export `/exports/tasks`).
- Coordonnées camerounaises fictives des clients (téléphones +237 mobiles et fixes 233 / 222, e-mails, quartiers de Douala et Yaoundé) : `core/management/commands/demo_cameroon.py`, appliqué à chaque `seed_demo` ; convertit aussi une base semée à Abidjan (lieux, téléphones du personnel, des comptes et des clients archivés) sans rien supprimer.
- Démo camerounaise (13/11/2026) : Maison Élégance Events à Douala (CM, XAF, `Africa/Douala`), adresses et salles de Douala, Yaoundé et Kribi, téléphones +237, RC/DLA et NIU, MTN MoMo et Orange Money ; seconde agence « Atelier Kribi Mariages » (slug `atelier-bassam` et e-mails de connexion `.ci` inchangés pour ne pas casser les accès). Les dates de toute l’interface suivent le fuseau de l’agence (`useDate.setAgencyTimezone`, réglé par `useOrgTimezone` dans `AppLayout`).
- Personnel › onglet « Tâches » (`staff/components/TasksTab.vue`) : tâches par personne ou par événement, filtre à faire / faites / toutes, ajout rapide (personne, événement, tâche) et coche par propriétaire et planner ; `/staff-tasks?status=` triées par personne puis date d’événement (annulées exclues). `seed_demo` crée les tâches de chaque affectation (faites si passées).
- Personnel : photo (fiche, cartes) et badges PDF format carte bancaire 85,6 × 54 mm, 8 par A4 en positions absolues, logo et palette de l’agence, photo ou initiales, QR `WDV1:STAFF:<id>` (`staff/badges.py`, `GET /staff/badges?ids=`) ; boutons « Imprimer les badges » (Personnel) et « Imprimer son badge » (fiche).

Ports locaux (choisis pour éviter les conflits avec les autres projets de la machine) : Nginx `8090`, MinIO `9100/9101`, PostgreSQL `5434`, Redis `6380`.

### Décisions d’implémentation (à respecter)
- L’application se connecte à PostgreSQL avec le rôle `wedivo` **non superutilisateur, NOBYPASSRLS** (`infra/postgres/init-app-role.sql`) : le RLS ne s’applique jamais aux superutilisateurs.
- Toute nouvelle table métier hérite de `core.models.TenantModel` et sa migration ajoute `core.rls.enable_rls("<table>")`.
- Contexte d’organisation : `core.tenant.tenant_context(org)` (requêtes via `TenantMiddleware`), `tenant_context_for_id(id)` dans les tâches Celery, `bypass_tenant()` + manager `all_tenants` pour l’administration.
- Vérification d’appartenance : permission DRF par défaut `core.permissions.IsTenantMember` (le JWT en cookie n’est lu que par DRF, après les middlewares). Rôles : `roles_allowed(...)`, `read_any_write_roles(...)`.
- Endpoints publics : hériter de `accounts.views.PublicAPIView`.
- Erreurs métier : lever `core.exceptions.BusinessError(code, message, fields)`.
- `Membership` n’est pas une table tenant (table de contrôle d’accès) : toujours filtrer sur `organization` explicitement.
- Frontend : composants du design system importés depuis `@/design` ; textes dans `src/i18n/fr.ts` ; appels API via `src/api/*` (camelCase côté app, conversion automatique) ; erreurs serveur affichées avec `useServerErrors`.
- Navigation : un module n’apparaît dans le menu, la barre d’onglets mobile et la palette Ctrl+K qu’en passant `ready: true` dans `src/app/navigation.ts` (on n’affiche jamais un module non construit).
- Icône du logo : `frontend/src/assets/logo-mark.png` (symbole seul, recadré depuis le logo complet).
- Champs de formulaire (`WInput`, `WSelect`, `WTextarea`) : `class`/`style` vont sur l’enveloppe (mise en page), le reste sur l’élément natif ; `hide-label` masque le libellé visuellement sans le retirer des lecteurs d’écran.
- Vues de liste DRF sur une table tenant : dans `get_queryset`, renvoyer `Model.all_tenants.none()` si `swagger_fake_view` (la génération OpenAPI n’a pas d’organisation).
- Clients : doublons repérables sur `phone_key` (9 derniers chiffres) ou email ; suppression logique (`is_deleted`, auditée) ; archivage (`is_archived`) pour sortir un client de la liste sans perdre son historique.
- Clés étrangères vers une table tenant dans un serializer : `core.fields.TenantPrimaryKeyRelatedField(Model)` (queryset résolu à la validation, dans l’organisation active). Filtres django-filter : `UUIDFilter` plutôt que des filtres de modèle.
- Numérotation : `organizations.numbering.next_number(kind)` (verrou de ligne, par organisation et par année) ; devis `<quote_prefix>-AAAA-NNNN`, contrats `CT-AAAA-NNNN`.
- Devis : montants recalculés côté serveur (`quotes/calculations.py`), miroir exact côté front (`modules/quotes/calculations.ts`, arithmétique entière). Lien public client : `/proposition/<jeton>`. PDF du devis : moteur `documents` (R3) ; reçus : `backend/templates/pdf/` (polices Sora/Manrope intégrées).
- `contracts` (Contract, PaymentSchedule) et `events` (Wedding) existent en version minimale, créés par la conversion d’un devis ; ils sont complétés aux étapes 7 et 9.
- Paiements : `contracts.services.record_payment` (verrou sur le contrat, jamais au-delà du solde, répartition sur l’échéancier dans l’ordre via `allocate`, reçu `RC-AAAA-NNNN` envoyé par Celery) ; annulation (`cancel_payment`) avec motif, jamais de suppression. Les droits financiers suivent `finance.visibility` : propriétaire et comptable voient tout, le planner les soldes sans marges, l’assistant rien.
- Tableau de bord et résumé financier : un calcul par organisation mis en cache 60 s (`org:{id}:dashboard`, `org:{id}:finance:summary`), invalidé par `finance.signals` (post_save/post_delete) ; filtré par rôle à la réponse. Attention : les `queryset.update()` ne déclenchent pas les signaux (le cache expire alors au bout de 60 s).
- Graphiques : pas d’ECharts (retiré). Courbe des encaissements = `WAreaChart` (SVG, géométrie pure testée dans `design/components/areaChart.ts`) ; pipeline = lignes HTML/CSS.
- Design system : tokens du complément §3 dans `design/tokens.css` (clair, sombre système, sombre forcé) ; `main.css` remet la palette Tailwind à zéro (`--color-*: initial`) : seules les couleurs Wedivo existent (`bg-surface-3`, `border-line-2`, `text-hero-muted`, `bg-scrim`…). Ombres : `shadow-wd` / `shadow-wd-lg`. Utilitaire `num` pour les montants. Icônes lucide à 1.8 via CSS (`svg.lucide`). Point de rupture de la coquille : `nav:` (> 960 px).
- Composants ajoutés : `WLogo`, `WRibbons`, `WTile`, `WChips`, `WPhaseTag`, `WDateBlock`, `WChannelIcon`, `WAvatar`, `WNote`, `WAlert`, `WAreaChart` ; `WInput addon=".wedivo.app"` pour un suffixe gris ; `WButton icon` pour un bouton carré.
- Galerie `/dev/ui` (développement seulement, absente du build) : tous les composants en clair et sombre côte à côte grâce aux classes `.theme-light` / `.theme-dark`.
- Coquille : `app/layouts/SidebarContent.vue` (barre latérale, réutilisée dans le tiroir mobile de 282 px), ordre du menu dans `app/navigation.ts` ; `meta.navKey` sur une route pour allumer une entrée du menu (éditeur de devis → « Devis »). Le catalogue n’est plus dans le menu (`hiddenFromMenu`) : Paramètres › Catalogue, bouton « Gérer le catalogue » des devis et page `/catalogue` pour les planners. Étiquettes P2/P3 : `phase` sur l’entrée + drapeau `VITE_PHASE_TAGS=true` (`app/features.ts`), affichées seulement pour un module construit.
- Recherche Ctrl+K : `GET /search?q=` (`core.views.SearchView`, 5 clients + 5 devis, réutilise `crm.selectors.search` et `quotes.selectors.search`) ; la palette groupe Pages / Clients / Devis / Actions (12 résultats maximum).
- Offres : table `organizations.SubscriptionPlan` (prix, limites, modules, points affichés), créée par migration et modifiable dans l’admin ; `GET /plans` public. Aucun prix dans le code front.
- Inscription : « Mariages organisés par an » est une tranche, on stocke sa borne basse (0, 10, 30, 60) ; 8 pays comme le prototype.
- Indicateurs calculés côté serveur : `finance/dashboard.py` (variation des encaissements vs les 6 mois précédents ; prospects, conversion et temps gagné retirés en S1, refonte complète en S8) ; tuiles des devis : `GET /quotes/stats` (`quotes.selectors.stats`).
- Devis : la liste expose `has_contract` (sous-requête `Exists`). La date et les invités se saisissent dans le devis (plus de pré-remplissage depuis la fiche). Un nouveau devis part des prestations `is_default` du catalogue ; `ServiceItem.quantity_rule` (`one`, `per_guest`, `per_ten_guests`) donne la quantité proposée, même règle côté front (`suggestedQuantity`). Réajouter une prestation augmente sa quantité. Aperçu et PDF : même mise en page, feuille blanche.
- Clients : `/clients?nouveau=1` ouvre la modale de création, `/clients?client=<id>` ouvre la fiche.
- Équipe : `accounts.TeamInvitation` (table de contrôle d’accès comme `Membership`, jeton stocké en SHA-256, 7 jours) ; `POST /organization/invitations` vérifie la limite d’utilisateurs de l’offre (`SubscriptionPlan.max_users`) ; lien `/invitation/<jeton>` (`GET/POST /auth/invitations/<jeton>[/accept]`, compte existant = son mot de passe, nouveau compte vérifié d’office) ; `PATCH /organization/members/{id}` (rôle, désactivation ; le propriétaire ne change jamais). Tout est audité.
- Paramètres : `/parametres/:tab` (entreprise, equipe, catalogue, abonnement, integrations), propriétaire seulement. Le sous-domaine se change avec les règles de l’inscription (les liens publics utilisent `FRONTEND_URL`, ils survivent) ; logo en multipart. Offre : `POST /organization/plan`, libre pendant l’essai, refusée ensuite (pas de paiement intégré). Intégrations autres que l’email : « Bientôt », boutons désactivés.
- Mariages : `events.Task` (avancement = faites ÷ total), liste standard = `events.TaskTemplateItem` par organisation (12 tâches du complément, créées au démarrage de l’espace ; échéance passée → aujourd’hui + 3 j) ; `bulk_create` ne passe pas par `save()` : renseigner `organization` explicitement (sinon le RLS refuse). Un mariage lié à un contrat ne se supprime pas. Calendrier : voir S5 (`events.calendar`). Alerte J-2 par email au responsable (`events.tasks.notify_due_tasks`, beat 8 h, une fois par échéance via `alert_sent_for`) ; pas encore de notifications in-app.
- Prestataires : app `vendors` (`Vendor`, `VendorAssignment` coût / payé ≤ coût) ; collaborations et montant dû par sous-requêtes ; les montants sont masqués et ignorés pour l’assistant (`MoneyAware`) ; « À payer aux prestataires » = `vendors_due` du résumé financier. Permissions communes : `events.permissions.PERMISSIONS` (propriétaire, planner, assistant écrivent ; comptable lit).
- `logo-mark.png` est détouré (fond transparent) ; l’original reste dans `docs/brand/`.
- Export : `/finance/export?type=csv|xlsx` (pas `format`, réservé par DRF).
- Tests de parcours : `make e2e` (lance `seed_e2e` : espace « Studio E2E », compte vérifié `e2e@wedivo.test`, refusé hors DEBUG) (Playwright sur le Chrome headless déjà téléchargé, trouvé par le Makefile ; plateforme lancée). `SIGNUP_RATE_LIMIT` est relevé dans le `.env` de dev pour pouvoir les rejouer.

## 1. Rôle et mission

Tu es un ingénieur logiciel senior full-stack, expert en Vue 3, Django REST Framework, PostgreSQL, Redis et Nginx, et en conception de produits SaaS multi-tenant de type fintech. Tu travailles avec soin, par petites étapes vérifiables, et tu écris du code de production : typé, testé, sécurisé et documenté.

Mission : construire **Wedivo**, une plateforme SaaS destinée aux wedding planners (marché principal : Afrique francophone, devise FCFA). Chaque entreprise cliente crée son propre compte et obtient un espace isolé. Chaque fonctionnalité doit faire gagner du temps au wedding planner, l’aider à mieux maîtriser ses coûts ou augmenter ses revenus.

**Principe directeur.** Avant d’ajouter une fonctionnalité : fait-elle gagner du temps ? Aide-t-elle à contrôler les coûts ? Aide-t-elle à générer des revenus ? Sinon, elle n’entre pas dans le MVP.

## 2. Contexte produit

### Utilisateurs
- **Propriétaire** : crée l’espace, gère l’abonnement, l’équipe et voit toutes les données, y compris les finances.
- **Wedding planner** : gère les prospects, devis, mariages, tâches et prestataires.
- **Assistant** : exécute les tâches, met à jour les prospects et les mariages, sans accès aux marges.
- **Comptable** : accède aux paiements, dépenses et marges, en lecture sur le reste.
- **Invité** (externe, sans compte) : reçoit une invitation, confirme sa présence via un lien public.

### Problèmes à résoudre
- Les demandes arrivent par WhatsApp, Facebook, Instagram et téléphone : des prospects sont oubliés.
- Un devis prend environ deux heures. Objectif : vingt minutes.
- Des prospects et clients ne sont pas relancés (exemple observé : 32 personnes sans relance).
- Le planner ne sait pas précisément ce qui est encaissé, ce qui reste à recevoir et ce que chaque mariage rapporte.
- Plusieurs mariages en parallèle, beaucoup de prestataires et d’échéances : risques d’oubli.

### Phasage
| Phase | Modules | Objectif |
|---|---|---|
| Phase 1 (MVP) | Création de compte entreprise, équipe et rôles, prospects et clients, catalogue, devis PDF, relances programmées (email), contrats et paiements, tableau de bord | Convertir plus de prospects, réduire le temps commercial |
| Phase 2 | Mariages, tâches, calendrier, prestataires, dépenses et marges | Organisation des mariages et maîtrise des coûts |
| Phase 3 | Invitations électroniques, PDF et QR codes, confirmations de présence, contrôle à l’entrée, WhatsApp Business, Mobile Money | Différenciation |

**Ne jamais promettre ce qui n’est pas intégré.** Les relances par email sont automatiques. WhatsApp exige l’API WhatsApp Business et des modèles approuvés par Meta : tant que l’intégration n’existe pas, l’interface propose un message à copier et l’action reste manuelle.

## 3. Stack technique

| Couche | Choix | Notes |
|---|---|---|
| Frontend | Vue 3 (Composition API, `<script setup lang="ts">`), Vite, TypeScript strict | SPA, chargement différé par module |
| État et données | Pinia, Vue Router, TanStack Query (Vue), Axios | Pinia pour la session ; TanStack Query pour toutes les données serveur |
| UI | Tailwind CSS configuré sur les tokens Wedivo + composants maison | Pas de librairie de composants lourde ; icônes lucide-vue-next |
| Formulaires | VeeValidate + Zod | Mêmes règles que le backend |
| Graphiques | Apache ECharts (vue-echarts) | Encaissements, pipeline |
| Backend | Python 3.12, Django 5.2 LTS, Django REST Framework | Gunicorn avec workers Uvicorn |
| Auth | djangorestframework-simplejwt, tokens en cookies httpOnly | Argon2 pour les mots de passe |
| Documentation API | drf-spectacular (OpenAPI 3) | Types TS générés avec openapi-typescript |
| Base de données | PostgreSQL 16 | UUID, Row-Level Security, index par organisation |
| Cache et files | Redis 7, Celery 5 + Celery beat | Cache, broker, limites de débit, verrous |
| PDF | WeasyPrint (gabarits HTML/CSS) | Devis, contrats, reçus, invitations |
| QR codes | segno | Contenu signé HMAC |
| Fichiers | Stockage S3 compatible (MinIO en local) via django-storages | URLs signées à durée limitée |
| Email | django-anymail (Brevo, Mailgun ou SES) | Webhooks de délivrabilité |
| Serveur web | Nginx | TLS, wildcard `*.wedivo.app`, statiques, reverse proxy, limites |
| Conteneurs | Docker, Docker Compose | Un fichier dev, un fichier prod |
| Tests | pytest-django, factory_boy, Vitest, Vue Test Utils, Playwright | Voir section 12 |
| Observabilité | Sentry, logs JSON structurés | Identifiant d’organisation dans chaque log |

Versions stables et récentes, épinglées précisément dans `requirements*.txt` et `package-lock.json`.

## 4. Structure du dépôt

```
wedivo/
├── backend/
│   ├── config/              # settings/{base,dev,prod}.py, urls.py, asgi.py, celery.py
│   ├── core/                # TenantModel, TenantManager, middleware, permissions, pagination, audit, utils
│   ├── accounts/            # User, Membership, rôles, invitations d’équipe, auth JWT
│   ├── organizations/       # Organization, abonnement, paramètres, numérotation des documents
│   ├── crm/                 # Prospect, Interaction
│   ├── catalog/             # ServiceCategory, ServiceItem
│   ├── quotes/              # Quote, QuoteLine, services PDF
│   ├── contracts/           # Contract, PaymentSchedule, Payment
│   ├── finance/             # Expense, VendorPayable, services de calcul
│   ├── reminders/           # ReminderRule, ReminderJob, canaux d’envoi
│   ├── events/              # Wedding, Task
│   ├── vendors/             # Vendor, VendorAssignment
│   ├── invitations/         # InvitationTemplate, Guest, CheckIn
│   ├── notifications/       # emails transactionnels, notifications in-app
│   ├── templates/pdf/       # gabarits WeasyPrint
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/             # main.ts, router, guards, layouts (AuthLayout, AppLayout)
│   │   ├── design/          # tokens.css, thème tailwind, composants W*
│   │   ├── api/             # client Axios, intercepteurs, types OpenAPI générés
│   │   ├── stores/          # session, organisation, préférences (thème)
│   │   ├── composables/     # useMoney, useDate, useToast, usePermissions
│   │   └── modules/         # auth, dashboard, crm, quotes, reminders, finance,
│   │                        # events, calendar, vendors, invitations, settings
│   └── tests/
├── infra/
│   ├── nginx/
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── .env.example
├── Makefile                 # make dev, make test, make migrate, make seed, make lint
└── README.md
```

Chaque app Django : `models.py`, `serializers.py`, `services.py` (logique métier), `selectors.py` (lectures complexes), `views.py` (fines), `urls.py`, `permissions.py`, `tasks.py` si besoin, `tests/`. Chaque module Vue : `pages/`, `components/`, `api.ts` (hooks TanStack Query), `routes.ts`, `types.ts`.

## 5. Multi-tenant : un espace par entreprise

Stratégie : **schéma PostgreSQL partagé + colonne `organization_id` + Row-Level Security**. Chaque entreprise a l’adresse `slug.wedivo.app`.

1. Toutes les tables métier héritent de `TenantModel` : `id` UUID, `organization` (FK indexée), `created_at`, `updated_at`, `created_by`.
2. `TenantMiddleware` résout l’organisation à partir du sous-domaine (ou de l’en-tête `X-Organization` en dev), la met en cache Redis 5 min et la stocke dans un `contextvar`.
3. Le middleware vérifie que l’utilisateur a un `Membership` actif dans cette organisation ; sinon 403.
4. `TenantManager` filtre chaque queryset sur l’organisation courante. Un manager `all_tenants` séparé, réservé à l’administration, lève le filtre explicitement.
5. À chaque requête, `SET LOCAL app.current_org = '<uuid>'` dans la transaction ; une migration crée les politiques RLS sur chaque table métier.
6. Les tâches Celery reçoivent toujours `organization_id` et réactivent le contexte avant toute requête.
7. Clés de cache Redis toujours préfixées : `org:{id}:...`.
8. Un utilisateur peut appartenir à plusieurs organisations ; l’interface permet de changer d’espace.

```sql
ALTER TABLE crm_prospect ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_prospect FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON crm_prospect
  USING (organization_id = current_setting('app.current_org', true)::uuid);
```

**Test obligatoire.** Pour chaque endpoint, un test vérifie qu’un utilisateur de l’organisation A ne peut ni lire, ni modifier, ni supprimer une ressource de l’organisation B (réponse 404, jamais 403).

### Parcours de création de compte entreprise
1. Assistant en 3 étapes : (1) entreprise : nom, ville, pays, nombre de mariages par an ; (2) compte : nom complet, email, téléphone, mot de passe ; (3) espace : sous-domaine proposé à partir du nom (modifiable, disponibilité en direct) et choix de l’offre.
2. `POST /api/v1/auth/signup` crée dans une seule transaction : organisation, utilisateur, membership « owner », catalogue d’exemple, règles de relance par défaut, numérotation des documents.
3. Email de vérification via Celery. Essai de 14 jours sur l’offre Pro.
4. Redirection vers le tableau de bord avec une liste de démarrage : compléter le catalogue, ajouter des prospects, inviter l’équipe.
5. Sous-domaines réservés : `www, app, api, admin, static, mail, support, docs, status`.

## 6. Design system (inspiré du logo)

Style **SaaS fintech** sobre, précis et rassurant, avec une touche chaleureuse liée au mariage. Logo : W formé d’un ruban violet qui se transforme en cœur magenta-corail, surmonté d’une étoile dorée ; logotype « Wedivo » marine très foncé avec un point doré sur le i. Slogan : « Planifiez · Gérez · Célébrez ».

```css
:root {
  --bg:#F5F4FA; --surface:#FFFFFF; --surface-2:#F1EFF8; --line:#E5E2F0;
  --ink:#17153B; --ink-2:#4A4769; --muted:#85829F;
  --violet:#5126C2; --violet-soft:#EEE8FD;
  --fuchsia:#C42C7E; --fuchsia-soft:#FCE6F1;
  --coral:#E3622F;  --coral-soft:#FEEBE2;
  --gold:#B97A0E;   --gold-soft:#FDF2DC; --gold-bright:#F4A62A;
  --green:#0E8F69;  --green-soft:#DFF4EC;
  --red:#D23A50;    --red-soft:#FCE6EA;
  --hero:#17153B;
  --ribbon:linear-gradient(118deg,#4A22B5 0%,#8E2BA8 42%,#E03E7D 70%,#F68A45 100%);
  --r-sm:8px; --r:12px; --r-lg:18px;
}
/* Sombre : --bg:#0D0C20; --surface:#16152E; --surface-2:#1E1C3A; --line:#29274A;
   --ink:#F2F1FA; --ink-2:#C6C3DE; --violet:#9F82FF; --green:#3DD3A0; --hero:#221F4C */
```

### Règles visuelles
- **Typographies** : Sora (titres et montants, `font-variant-numeric: tabular-nums`) et Manrope (interface). Échelle : 12, 13, 14.5 (base), 15.5, 17, 20, 26, 40.
- **Le ruban** est réservé au bloc « Solde à recevoir » du tableau de bord, à l’indicateur du menu actif, aux barres de progression des mariages et à la courbe des encaissements. Nulle part ailleurs.
- Bouton principal : violet plein. Secondaires : fond blanc, bordure fine. Hauteur 40 px, rayon 10 px.
- Montants en FCFA, séparateur de milliers espace fine : `1 500 000 FCFA`. Format court : `6,3 M`. Stockage en entiers.
- Dates en français : « 14 nov. 2026 ». Fuseau par organisation (défaut `Africa/Abidjan`).
- Pastilles de statut : nouveau (violet), contacté (or), devis envoyé (fuchsia), négociation (corail), confirmé (vert), perdu (gris).
- Pas de libellés en majuscules, pas de surcharge d’ombres : bordures fines, ombre légère seulement sur tiroirs et modales.
- Thème clair et sombre (préférence système + bascule manuelle mémorisée).
- Rédaction : phrases courtes, verbes d’action, même nom du bouton au message (« Envoyer le devis » → « Devis envoyé »). Les erreurs disent quoi corriger.

### Mise en page
- Bureau : barre latérale fixe 252 px (logo, sélecteur d’entreprise, navigation groupée Pilotage / Commercial / Organisation / Espace, profil en bas) et barre supérieure (recherche Ctrl+K, thème, notifications).
- Mobile (< 960 px) : menu latéral escamotable et barre d’onglets en bas : Accueil, Prospects, Devis, Finances, Plus. Zones sûres iOS.
- Détails en tiroir latéral ; créations rapides en modale.
- Accessibilité : contraste AA, focus visible, clavier complet, `aria-live`, `prefers-reduced-motion`.
- Composants : WButton, WInput, WSelect, WTextarea, WSwitch, WBadge, WCard, WTable, WDrawer, WModal, WToast, WTabs, WEmptyState, WMoney, WProgress, WKanban, WCommandPalette.

## 7. Modules fonctionnels

### 7.1 Tableau de bord (Phase 1)
- Accueil avec le nombre de relances du jour et le prochain mariage.
- Bloc « Solde à recevoir » (contrats − paiements reçus) : déjà encaissé, contrats signés, marge prévisionnelle. Boutons « Enregistrer un paiement » et « Voir l’échéancier ».
- Indicateurs : prospects actifs, taux de conversion (confirmés / (confirmés + perdus)), devis en attente et montant en jeu, temps gagné estimé.
- Graphique des encaissements sur 6 mois ; pipeline par statut (nombre et budget) ; relances du jour avec « Marquer faite » ; prochains mariages avec avancement.
- Un seul endpoint `/dashboard/summary`, cache Redis 60 s invalidé à chaque paiement, devis ou changement de statut.

### 7.2 Prospects et clients (Phase 1)
- Kanban par statut (nouveau, contacté, devis envoyé, négociation, client confirmé, perdu), glisser-déposer, mise à jour optimiste ; vue tableau avec tri et filtres.
- Champs : nom ou couple, téléphone, email, canal (WhatsApp, Facebook, Instagram, téléphone, recommandation, autre), budget, date du mariage, invités, besoins, responsable, prochaine relance.
- Fiche en tiroir : informations, historique (appel, message, rendez-vous, note), changement de statut, programmation de relance, « Appeler », « Créer un devis ».
- Recherche plein texte, filtres canal/responsable ; import CSV/XLSX avec correspondance des colonnes et détection des doublons (téléphone ou email).
- Tout changement de statut crée une entrée d’historique. « Perdu » demande un motif.
- **Accepté si** : un prospect créé apparaît immédiatement dans « Nouveau » ; le déplacer met à jour le serveur ; en cas d’erreur la carte revient avec un message.

### 7.3 Catalogue et devis (Phase 1)
- Catalogue : prestations par catégorie (coordination, décoration, restauration, animation, image, logistique, invitations), unité (forfait, unité, invité, journée, soirée), prix unitaire, actif.
- Éditeur : client (recherche parmi les prospects), date, invités, lignes depuis le catalogue en un clic (unité « invité » = nombre d’invités), lignes libres, remise %, acompte %, conditions.
- Aperçu PDF en direct. Totaux calculés côté client et recalculés côté serveur (le serveur fait foi).
- Numérotation par organisation et année : `DV-2026-0048`, sans doublon.
- Statuts : brouillon, envoyé, accepté, refusé, expiré (validité 30 jours par défaut).
- « Envoyer le devis » : PDF (Celery), email avec lien public, date d’envoi, relances planifiées.
- « Convertir en contrat » : contrat, échéancier (acompte, versements, solde 7 jours avant le mariage), fiche mariage, prospect « client confirmé ».
- Dupliquer ; modèles réutilisables.
- **Accepté si** : un devis de 3 prestations se crée en moins de 2 minutes ; le PDF reprend logo, mentions et montants exacts.

### 7.4 Relances programmées (Phase 1)
- Règles activables : devis sans réponse (J+3 puis J+7), prospect sans échange depuis 7 jours (tâche interne), échéance de paiement (J-2 et jour J), rendez-vous (veille à 18 h).
- Variables : `{prenom}`, `{date_mariage}`, `{montant}`, `{numero_devis}`, `{lien_devis}`, `{nom_entreprise}`.
- File : aujourd’hui, à venir, faites. Actions : marquer faite, reporter, annuler, envoyer maintenant.
- Bandeau quand des prospects sont sans relance depuis plus de 7 jours, action groupée « Programmer leur relance ».
- Revérification de la condition avant envoi ; idempotence.
- Canaux : email (auto), tâche interne, WhatsApp (manuel, message à copier).
- Envois entre 8 h et 20 h dans le fuseau de l’organisation.

### 7.5 Contrats, paiements et finances (Phase 1, marges en Phase 2)
- Liste : client, date, montant, encaissé, solde, marge estimée, progression.
- Paiement : contrat, montant, date, mode (virement, espèces, Orange Money, MTN MoMo, Wave, chèque), référence, justificatif. Solde les échéances dans l’ordre ; reçu PDF ; rappels inutiles annulés.
- Un paiement ne peut pas dépasser le solde. Annulation (jamais suppression) tracée dans l’audit.
- Détail : montant, dépenses estimées, marge (montant et %), encaissé, solde, échéancier avec « Marquer payé ».
- Exemple de référence : contrat 1 500 000, dépenses 900 000, marge 600 000, encaissé 500 000, solde 1 000 000 FCFA.
- Mention : « La marge prévisionnelle n’est pas le bénéfice net comptable de l’entreprise ».
- Dépenses par mariage, montants dus aux prestataires ; export CSV et Excel.

### 7.6 Mariages, tâches et calendrier (Phase 2)
- Fiche mariage : couple, date, lieu, invités, budget, contrat, prestataires, tâches, avancement, compte à rebours J-x.
- Tâches : titre, responsable, échéance, statut, commentaire. Modèle standard. Badges « En retard » et « Bientôt ».
- Calendrier mensuel et agenda : mariages, tâches, échéances, rendez-vous ; filtre par membre.
- Alertes in-app et email J-2.

### 7.7 Prestataires (Phase 2)
- Répertoire par catégorie (décoration, traiteur, photographe, vidéaste, DJ, salle, gâteau, location de matériel, transport) : coordonnées, note /5, collaborations, montant dû.
- Association à un mariage avec prestation, coût, statut de paiement.

### 7.8 Invitations et QR codes (Phase 3)
- Éditeur d’invitation avec aperçu. Liste d’invités (import CSV), code unique `WDV-XX-0001`, QR signé HMAC.
- PDF par invité, email, page publique RSVP. Statistiques, rappel automatique.
- Mode « Contrôle à l’entrée » mobile : scan ou saisie ; valide, déjà utilisé (heure), décliné, inconnu.
- Génération et envoi développés et testés séparément.

### 7.9 Paramètres (Phase 1)
- Entreprise : nom, logo, sous-domaine, ville, pays, devise (XOF, XAF, EUR), fuseau, mentions légales, préfixe de numérotation.
- Équipe : membres, invitation par email avec rôle, changement de rôle, désactivation. Tableau des droits.
- Catalogue, modèles de messages, règles de relance.
- Abonnement : Essentiel, Pro, Agence (prix en base, pas dans le code), essai, limites par offre.
- Intégrations : email, WhatsApp Business (Phase 3), Mobile Money (Phase 3), Google Agenda (plus tard).

### 7.10 Recherche globale
Palette Ctrl+K : pages, prospects, devis, contrats, mariages, prestataires. Côté serveur avec `pg_trgm`, limitée à l’organisation.

## 8. Modèle de données

Modèles métier héritent de `TenantModel`. Montants en `BigIntegerField`. Dates de mariage en `DateField`, horodatages UTC.

| Modèle | Champs principaux | Relations et contraintes |
|---|---|---|
| Organization | slug (unique), name, logo, country, city, currency, timezone, plan, trial_ends_at, quote_prefix, legal_mentions, is_active | Racine, pas tenant |
| User | email (unique, identifiant), full_name, phone, is_verified | Modèle personnalisé dès la première migration |
| Membership | role (owner, planner, assistant, accountant), is_active, invited_at, joined_at | User ↔ Organization, unique (user, organization) |
| Prospect | name, phone, email, source, status, budget, wedding_date, guest_count, needs, lost_reason, next_follow_up_at | owner → User ; index (organization, status) |
| Interaction | kind (call, message, meeting, note, status_change), content, occurred_at | → Prospect, author → User |
| ServiceCategory / ServiceItem | name, order · name, unit, unit_price, is_active | ServiceItem → ServiceCategory |
| Quote | number (unique par org), status, issue_date, valid_until, discount_pct, deposit_pct, subtotal, discount_amount, total, sent_at, accepted_at, pdf_file, public_token | → Prospect |
| QuoteLine | label, unit, unit_price, quantity, amount, position | → Quote, service_item (nullable) |
| Contract | number, total, signed_at, wedding_date, status | → Quote (1-1), → Prospect |
| PaymentSchedule | label, amount, due_date, is_paid | → Contract |
| Payment | amount, method, paid_at, reference, receipt_file, is_cancelled | → Contract, recorded_by → User |
| Wedding | title, date, venue, guest_count, budget, status | → Contract (nullable) |
| Task | title, due_date, status, notes | → Wedding, assignee → User |
| Vendor | name, category, phone, email, rating, notes | — |
| VendorAssignment | service, cost, paid_amount | → Wedding, → Vendor |
| Expense | label, amount, date, is_paid | → Wedding, vendor (nullable) |
| ReminderRule | trigger, delay_days, channel, template, is_active | — |
| ReminderJob | scheduled_for, status (pending, sent, done, cancelled, failed), channel, payload, sent_at | Cible générique : prospect, quote, payment_schedule ou task |
| Guest | name, email, phone, party_size, code (unique), rsvp_status, rsvp_at | → Wedding |
| CheckIn | scanned_at, device | → Guest, scanned_by → User |
| AuditLog | action, target_type, target_id, changes (JSON), ip | actor → User |

`CheckConstraint` (montants ≥ 0, pourcentages 0–100), index sur les colonnes filtrées. Commande `python manage.py seed_demo` : organisation « Maison Élégance Events » (Abidjan) avec données réalistes.

## 9. API REST

Préfixe `/api/v1`. JSON snake_case côté API, camelCase côté front. Pagination par curseur, filtres django-filter. Format d’erreur :

```json
{ "code": "payment_exceeds_balance",
  "message": "Le montant dépasse le solde restant (1 000 000 FCFA).",
  "fields": { "amount": ["Maximum 1 000 000"] } }
```

| Méthode | Endpoint | Rôle |
|---|---|---|
| POST | /auth/signup · /auth/login · /auth/refresh · /auth/logout | Session JWT en cookies |
| GET | /auth/slug-available?slug= | Disponibilité du sous-domaine |
| POST | /auth/verify-email · /auth/password-reset | Vérification et réinitialisation |
| GET, PATCH | /organization · /organization/members · /organization/invitations | Paramètres et équipe |
| CRUD | /prospects · /prospects/{id}/interactions | Prospects et historique |
| PATCH | /prospects/{id}/status | Changement de statut |
| POST | /prospects/import | Import CSV/XLSX |
| CRUD | /catalog/categories · /catalog/items | Catalogue |
| CRUD | /quotes | Devis et lignes imbriquées |
| POST | /quotes/{id}/send · /accept · /refuse · /duplicate · /convert | Cycle de vie |
| GET | /quotes/{id}/pdf · /public/quotes/{token} | PDF et page publique |
| GET | /contracts · /contracts/{id} | Contrats et échéancier |
| POST | /contracts/{id}/payments · /payments/{id}/cancel | Paiements |
| GET | /finance/summary · /finance/export | Totaux, marges, export |
| GET, PATCH | /reminders/rules · /reminders/jobs | Règles et file |
| POST | /reminders/jobs/{id}/done · /snooze · /send-now · /bulk-schedule | Actions |
| CRUD | /weddings · /weddings/{id}/tasks · /vendors · /expenses | Phase 2 |
| GET | /calendar?from=&to= | Calendrier |
| CRUD, POST | /weddings/{id}/guests · /invitations/send · /checkin | Phase 3 |
| GET, POST | /public/rsvp/{code} | RSVP public |
| GET | /dashboard/summary · /search?q= | Tableau de bord, recherche |

Schéma OpenAPI sur `/api/schema`, documentation sur `/api/docs` (restreinte en production).

## 10. Redis et tâches de fond

- Redis base 0 : broker Celery. Files : `default`, `pdf`, `emails`, `reminders`.
- Redis base 1 : cache (organisation par slug, résumé du tableau de bord, résumé financier).
- Redis base 2 : limites de débit, révocation des refresh tokens, verrous.

```python
beat_schedule = {
  "dispatch-reminders":   {"task": "reminders.tasks.dispatch_due_jobs", "schedule": crontab(minute="*/15")},
  "payment-due-notices":  {"task": "contracts.tasks.notify_due_payments", "schedule": crontab(hour=8, minute=0)},
  "flag-stale-prospects": {"task": "crm.tasks.flag_stale_prospects", "schedule": crontab(hour=7, minute=30)},
  "expire-quotes":        {"task": "quotes.tasks.expire_quotes", "schedule": crontab(hour=1, minute=0)},
  "trial-ending":         {"task": "organizations.tasks.notify_trial_ending", "schedule": crontab(hour=9, minute=0)},
}
```

Tâches idempotentes, retries exponentiels (3 essais), journalisation, alerte Sentry en échec définitif.

## 11. Sécurité et rôles

| Droit | Propriétaire | Planner | Assistant | Comptable |
|---|---|---|---|---|
| Prospects, devis | Oui | Oui | Oui (sans suppression) | Lecture |
| Paiements, marges, exports | Oui | Lecture des soldes | Non | Oui |
| Mariages, tâches, prestataires | Oui | Oui | Oui | Lecture |
| Équipe, paramètres, abonnement | Oui | Non | Non | Non |

- Permissions vérifiées côté serveur (classes DRF par rôle et par offre) ; le front masque seulement.
- Access token 15 min, refresh 7 jours avec rotation, cookies httpOnly, Secure, SameSite=Lax ; CSRF.
- Argon2, 5 tentatives de connexion / 15 min, email vérifié avant les envois.
- Liens publics avec jetons aléatoires ; QR signés HMAC.
- Audit : paiements, annulations, changements de rôle, suppressions, exports.
- En-têtes : HSTS, CSP stricte, X-Frame-Options, Referrer-Policy. Secrets en variables d’environnement.
- Suppression logique ; export complet des données d’une organisation sur demande.

## 12. Qualité et tests

- Backend : pytest-django, couverture ≥ 85 % sur `services.py` et permissions ; isolation multi-tenant sur chaque endpoint ; calculs testés avec l’exemple de référence.
- Frontend : Vitest (composables, composants) ; Playwright (création de compte, devis, conversion, paiement, kanban).
- Outils : ruff, black, mypy ; ESLint, Prettier, vue-tsc ; pre-commit.
- CI GitHub Actions : lint, tests, build, analyse des dépendances.
- Performance : pas de N+1, listes paginées < 300 ms, SPA rapide sur mobile 3G.

## 13. Déploiement

Services : `nginx`, `frontend`, `api` (Gunicorn + Uvicorn), `worker`, `beat`, `db` (PostgreSQL 16), `redis`, `minio` (local). Nginx wildcard `~^(?<tenant>[a-z0-9-]+)\.wedivo\.app$`, TLS Let’s Encrypt (challenge DNS), `/api/` proxifié avec `limit_req`, `/assets/` cache 1 an, `try_files $uri /index.html`. Sauvegardes PostgreSQL quotidiennes (30 jours), migrations automatiques avant redémarrage de l’API. Environnements dev, staging, production.

## 14. Règles de travail pour l’IA

1. Travaille par étapes. Au début de chaque étape, plan court (fichiers, choix techniques), puis implémentation.
2. N’invente pas de fonctionnalités hors de ce document. Si une info manque, option la plus simple, hypothèse signalée.
3. La logique métier vit dans les services Django, jamais dans les vues ni dans les composants Vue.
4. Tout code qui lit ou écrit des données métier respecte l’isolation par organisation.
5. Tests écrits avec le code. Une étape n’est pas terminée si les tests échouent.
6. Textes de l’interface en français via vue-i18n. Code, variables et commentaires en anglais.
7. Pas de données en dur dans les composants. Pas de prix d’abonnement dans le code.
8. États de chargement (squelettes), d’erreur (message et action) et vides sur chaque écran.
9. Commits petits, Conventional Commits.
10. Fin d’étape : résumé, commandes, limites connues, prochaine étape.

## 15. Définition de terminé (MVP Phase 1)

- `make dev` lance toute la plateforme ; `make seed` charge les données de démonstration.
- Une agence crée son compte, obtient son sous-domaine, invite un membre et se connecte.
- Elle ajoute des prospects, les déplace dans le kanban, programme des relances.
- Elle crée un devis depuis le catalogue, l’envoie en PDF, voit les relances partir, le convertit en contrat.
- Elle enregistre des paiements et voit solde et marge se mettre à jour sur le tableau de bord.
- Les données de deux agences sont strictement isolées (tests verts).
- L’interface respecte le design system, fonctionne sur mobile et en thème sombre.
- Tests et lint passent en CI ; le README explique installation et déploiement.
