# Wedivo

Plateforme SaaS multi-entreprise pour wedding planners — *Planifiez · Gérez · Célébrez*.

Les spécifications complètes et l’avancement par étape sont dans [CLAUDE.md](CLAUDE.md).

## Prérequis

- Docker et Docker Compose v2
- GNU Make

Node et Python ne sont pas nécessaires sur la machine : tout tourne dans les conteneurs.

## Démarrer en local

```bash
make dev        # crée .env si absent, construit et lance tous les services
make ps         # état des services
make logs       # journaux
make down       # arrêt
```

| Service | Adresse |
|---|---|
| Application (Nginx → Vite) | http://localhost:8090 |
| API | http://localhost:8090/api/v1/health |
| Documentation OpenAPI | http://localhost:8090/api/docs |
| Console MinIO | http://localhost:9101 |
| PostgreSQL | `localhost:5434` (wedivo / wedivo) |
| Redis | `localhost:6380` |

Les ports sont choisis pour ne pas entrer en conflit avec d’autres projets locaux ; ils se modifient dans [infra/docker-compose.dev.yml](infra/docker-compose.dev.yml).

## Données de démonstration

Toutes les données de démonstration sont **fictives** et créées par le code (aucune base réelle n’est fournie) :

```bash
make seed       # crée l’agence « Maison Élégance Events » (Douala, FCFA) et une seconde agence
make demo-reset # repart d’une base vide puis recrée la démo (sauvegarde la base avant)
```

Contenu : 30 articles de matériel et 4 packs, 12 réservations sur six semaines (tous les statuts), 15 clients camerounais (+237), factures et avoir, 12 mois d’activité financière, 10 personnes du personnel avec pointages et paie, tâches, 13 partenaires et fournisseurs, mariages, invités et billets.

Mot de passe commun : `Wedivo-demo-2026`

| Rôle | Email |
|---|---|
| Propriétaire | aicha.kone@maison-elegance.ci |
| Wedding planner | yao.kouassi@maison-elegance.ci |
| Assistant | mariam.traore@maison-elegance.ci |
| Comptable | serge.bamba@maison-elegance.ci |
| Chef d’équipe | didier.kra@maison-elegance.ci |
| Personnel | linda.abena@maison-elegance.ci |
| Seconde agence (propriétaire) | koffi.nguessan@atelier-bassam.ci |

En développement, l’espace se choisit avec l’en-tête `X-Organization: maison-elegance` ; en production, par le sous-domaine `maison-elegance.wedivo.app`.

Notifications push : générer des clés avec `docker compose -f infra/docker-compose.dev.yml exec api python manage.py generate_vapid_keys` et les copier dans `.env` (voir `.env.example`).

## Tests et qualité

```bash
make test       # pytest (backend) + Vitest (frontend)
make lint       # ruff, black, mypy, ESLint, Prettier, vue-tsc
make format     # formatage automatique
make e2e        # parcours navigateur (Playwright) sur la plateforme lancée
```

`make e2e` utilise le Google Chrome installé sur la machine ; pour un autre binaire : `PLAYWRIGHT_CHROME_PATH=/chemin/vers/chrome make e2e`.

Hooks Git : `pip install pre-commit && pre-commit install`.

## Structure

```
backend/    Django 5.2 + DRF + Celery (config/, core/, puis une app par domaine)
frontend/   Vue 3 + Vite + TypeScript strict + Tailwind (tokens Wedivo)
infra/      Docker Compose et configuration Nginx
```

## Déploiement

La configuration de production (Compose, Nginx wildcard `*.wedivo.app`, TLS, sauvegardes) arrive à l’étape 10.
