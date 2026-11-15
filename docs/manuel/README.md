# Manuel d’utilisation de Wedivo

- `Manuel-utilisateur-Wedivo.pdf` : le manuel à remettre aux utilisateurs (44 pages, A4).
- `manuel.html` : sa source (texte et mise en page), `captures/` : les captures d’écran,
  `fonts/` : les polices de Wedivo (licence OFL).

Régénérer le PDF après une modification du texte (plateforme lancée avec `make dev`) :

```bash
docker compose -f infra/docker-compose.dev.yml exec -T api python -c "
from weasyprint import HTML
HTML(filename='/docs/manuel/manuel.html', base_url='/docs/manuel/').write_pdf('/tmp/Manuel-Wedivo.pdf')"
docker compose -f infra/docker-compose.dev.yml cp api:/tmp/Manuel-Wedivo.pdf docs/manuel/Manuel-utilisateur-Wedivo.pdf
```

Les captures ont été prises sur les données de démonstration (`make seed`), en 1360 × 860
(ordinateur) et 390 × 844 (téléphone).
