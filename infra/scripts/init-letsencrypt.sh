#!/bin/sh
# First HTTPS certificate on a new server. Run once from the repository root:
#   sh infra/scripts/init-letsencrypt.sh
# Needs DOMAIN and CERTBOT_EMAIL in .env and DNS records of DOMAIN and www.DOMAIN pointing here.
set -eu

# Single values from .env (sourcing it breaks on values such as «Name <mail>»)
env_value() { grep -E "^$1=" .env | head -n 1 | cut -d= -f2-; }
COMPOSE=${COMPOSE:-docker compose -f docker-compose.prod.yml}
DOMAIN=$(env_value DOMAIN)
CERTBOT_EMAIL=$(env_value CERTBOT_EMAIL)
LIVE="/etc/letsencrypt/live/$DOMAIN"

echo "1/4 Temporary self-signed certificate, so Nginx can start"
$COMPOSE run --rm --entrypoint sh certbot -c "
  mkdir -p $LIVE &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=localhost \
    -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem"

echo "2/4 Starting Nginx"
$COMPOSE up -d nginx

echo "3/4 Asking Let's Encrypt for $DOMAIN and www.$DOMAIN"
$COMPOSE run --rm --entrypoint sh certbot -c "rm -rf $LIVE /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf"
$COMPOSE run --rm certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" -d "www.$DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email

echo "4/4 Reloading Nginx with the real certificate"
$COMPOSE exec nginx nginx -s reload
echo "Done: https://$DOMAIN"
