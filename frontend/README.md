# frontend

React + TypeScript + Vite + Tailwind SPA (manager / recruiter / tenant-admin console).

Planned layout:

```
src/
  pages/
  components/
  features/     requisitions, jd-review, scoring-matrix, candidates, admin
  api/          typed API client generated from each service's OpenAPI spec (never import backend code)
  theme/        Teamora brand tokens
public/
e2e/            Playwright end-to-end tests
Dockerfile
package.json
.env.example
```

Deploys as one Coolify application: Base Directory `/frontend`, watch path `frontend/**`.
