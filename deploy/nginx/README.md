# crm.nextin.uz — deployment

`crm.nextin.uz.conf` is the **host** nginx site (in front of Docker). It terminates
TLS and forwards everything to the frontend container, which already knows how to
route `/api`, `/static` and `/sqladmin` internally.

## Install

```bash
# 1. DNS: point crm.nextin.uz (A record) at the server, and confirm it resolves
dig +short crm.nextin.uz

# 2. Copy the site in
sudo cp deploy/nginx/crm.nextin.uz.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/crm.nextin.uz.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default        # if the stock site is still on
sudo mkdir -p /var/www/certbot

# 3. First run only: nginx will NOT start while the certificate is missing, so
#    comment out the whole `server { ... listen 443 ... }` block, then:
sudo nginx -t && sudo systemctl reload nginx

# 4. Get the certificate
sudo certbot certonly --webroot -w /var/www/certbot -d crm.nextin.uz

# 5. Uncomment the 443 block and reload
sudo nginx -t && sudo systemctl reload nginx

# 6. Once https://crm.nextin.uz is confirmed good, uncomment the HSTS line
#    and reload again. Do this last -- browsers remember HSTS for a year.
```

Renewal is automatic (certbot installs a systemd timer). The `.well-known` location
is served over plain HTTP on purpose so renewals keep working.

## App side

`docker-compose.yml` publishes the frontend on `127.0.0.1:3000` — loopback only,
so the only way in from outside is through this nginx and its TLS. Verify after any
compose change:

```bash
docker compose ps        # must read 127.0.0.1:3000->80/tcp, not 0.0.0.0:3000
```

## Verified

Tested against the running stack with a self-signed certificate before shipping:

| | |
| --- | --- |
| HTTP → HTTPS | `301` → `https://crm.nextin.uz/` |
| SPA over HTTPS | `200` |
| `POST /api/auth/login` | `200` |
| `/sqladmin/` | `302` (its own login) |
| ACME path | reachable over plain HTTP |
| **WebSocket** | `101 Switching Protocols` |
| **gzip** | 200,831 → 44,605 bytes (**77.8%** smaller) |
| Real browser | login + `wss://` connected, no console errors |

Note: WebSocket is negotiated over HTTP/1.1 even though the site serves HTTP/2 —
that is normal, browsers open the socket on its own connection. Testing it with
`curl` needs `--http1.1`, otherwise curl tries the upgrade over h2 and gets a 404.
