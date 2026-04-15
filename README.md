# Stark Bank Backend Challenge

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Place your private key PEM file in the project root
3. Install dependencies:

```bash
make dev
```

4. Start PostgreSQL and Redis, then run:

```bash
# Terminal 1 — Flask server
make run

# Terminal 2 — Huey worker (periodic tasks + background jobs)
make worker
```

## Testing

```bash
make test
```

## Architecture

- **Flask** — Webhook endpoint (`POST /webhook`)
- **Huey + Redis** — Periodic invoice creation (every 3h) and background transfer processing
- **Peewee + PostgreSQL** — Persistence for invoices and transfers
- **Stark Bank SDK** — API integration
