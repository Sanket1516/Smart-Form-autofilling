# Single-host deployment

The production Compose profile gives the dashboard and API a public HTTPS
entrypoint through Caddy. MongoDB, ChromaDB, Redis, the backend, and frontend
ports bind only to loopback; data services are also on private Docker networks.
This is a single-host deployment baseline, not a substitute for encrypted
storage, backups, monitoring, or an incident plan.

## Prepare the host

1. Use a supported Linux host with Docker Compose v2. Point the domain's A/AAAA
   records to that host, allow inbound TCP 80/443 (and UDP 443 for HTTP/3), and
   ensure the host's data volume is encrypted.
2. Copy `.env.example` to `.env`, then set:
   - `APP_ENV=production`
   - `APP_DOMAIN` to the public DNS name, without a scheme
   - `CORS_ORIGINS=https://<your-domain>`
   - `VITE_API_BASE_URL=` so the dashboard uses the same-origin API proxy
   - a unique `JWT_SECRET_KEY` and a unique `MONGODB_ROOT_PASSWORD`, each at
     least 32 characters. URL-safe generated values work with MongoDB URLs.
   - a real `LLM_PROVIDER`, its supported `LLM_MODEL`, and credentials where
     required. Production refuses the mock provider.
3. Review the LLM provider's data handling. Documents and form labels sent for
   extraction or answers may leave the host when using a hosted provider.
4. Add a backup and deletion policy for MongoDB, ChromaDB, and uploaded files.
   Encrypt backups, restrict who can restore them, and test deletion from both
   live data and backups. Docker named volumes are not encrypted automatically.

## Start and operate

From the repository root, run:

```sh
docker compose -p smart-form-production --profile production up --build -d
docker compose -p smart-form-production --profile production ps
```

The project name keeps production volumes separate from the development stack.
Caddy obtains and renews HTTPS certificates automatically. The backend rejects
production startup if the domain, secure origins, MongoDB password, real LLM, or
shared Redis rate-limit storage is missing or unsafe. Application OpenAPI/docs
endpoints are disabled in production mode.

Do not expose MongoDB, ChromaDB, Redis, the backend, or the frontend by changing
their port bindings to `0.0.0.0`. If using managed databases instead, keep their
network access restricted to the application host and configure provider-side
encryption, authentication, backups, and retention.
