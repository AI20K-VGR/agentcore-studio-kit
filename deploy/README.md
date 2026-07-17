# Deploy

Placeholder (Decision #10). Deploy scope for this kit is **compose-local only** —
`docker compose --profile app up -d` (see root `README.md` / `docker-compose.yml`).

No Kubernetes manifests are scaffolded here. Real k8s deploy is out of scope for this template
and is planned for week 6 of the OJT program — when that work starts, it belongs under this
directory (e.g. `deploy/k8s/`, following the flat-manifest precedent observed in
`document-intake`'s own `deploy/k8s/` — see
`plans/260717-1516-studio-kit-template/research/document-intake-patterns.md` §13).
