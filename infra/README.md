# Infrastructure Assets

The root `docker-compose.yml` is the local development stack. Its `production`
profile adds Caddy for automatic HTTPS and routes public traffic to the dashboard
and API. See `docs/DEPLOYMENT_SECURITY.md` before using that profile. Continuous
integration is defined in `.github/workflows/ci.yml`.

