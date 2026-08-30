#!/usr/bin/env bash
#
# Bir buyruq bilan: lokal bazadagi kompaniyalarni to'g'ridan-to'g'ri serverga
# oqizadi. Oraliq fayl yo'q, scp yo'q -- pg_dump quvur orqali serverning
# psql'iga tushadi va u yerda bitta tranzaksiyada yoziladi.
#
# Barcha leadlar "Yangi" bo'ladi: lead_states bo'shatiladi, effective_status esa
# qator bo'lmasa NEW qaytaradi. users/notifications/scrape_runs tegilmaydi.
#
#   bash deploy/data/push_to_server.sh                      # crm.nextin.uz
#   bash deploy/data/push_to_server.sh root@1.2.3.4         # boshqa server
#
set -euo pipefail

SERVER="${1:-root@85.198.80.167}"
REMOTE_DIR="${REMOTE_DIR:-crm_system}"
COMPOSE="${COMPOSE:-docker compose}"
SSH="${SSH:-ssh}"

# One ssh connection for the whole run: without this every step below would ask
# for the password again. -o ControlPersist keeps it alive between the checks and
# the load.
CTL="${TMPDIR:-/tmp}/opdesk-ssh-$$"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$CTL -o ControlPersist=120"
cleanup() { $SSH $SSH_OPTS -O exit "$SERVER" 2>/dev/null || true; }
trap cleanup EXIT

lpsql() { $COMPOSE exec -T postgres psql -U parsing -d parsing "$@" </dev/null; }
rsh()   { $SSH $SSH_OPTS "$SERVER" "$@"; }
rpsql() { rsh "cd ~/$REMOTE_DIR && docker compose exec -T postgres psql -U parsing -d parsing $* </dev/null"; }

echo "==> Serverga ulanmoqda: $SERVER"
rsh "test -d ~/$REMOTE_DIR" || { echo "Serverda ~/$REMOTE_DIR topilmadi." >&2; exit 1; }

# --- schema guard ----------------------------------------------------------- #
# Columns differ between revisions; a mismatch would fail somewhere inside 10k
# rows. The transaction makes that safe, but not comprehensible -- so check first.
LOCAL_REV=$(lpsql -At -c "SELECT version_num FROM alembic_version;" | tr -d '\r')
SERVER_REV=$(rpsql -At -c "'SELECT version_num FROM alembic_version;'" | tr -d '\r')
echo "    lokal sxema:  $LOCAL_REV"
echo "    server sxema: $SERVER_REV"
if [ "$LOCAL_REV" != "$SERVER_REV" ]; then
  echo
  echo "XATO: sxema versiyalari mos kelmayapti." >&2
  echo "  Serverda:  docker compose run --rm backend alembic upgrade head" >&2
  echo "  (bilib turib davom etish: SKIP_REV_CHECK=1)" >&2
  [ "${SKIP_REV_CHECK:-}" = "1" ] || exit 1
fi

# --- what gets emptied ------------------------------------------------------ #
# Asked of the SERVER's own foreign-key graph, not hardcoded: a migration that
# adds another table referencing companies is picked up instead of breaking the
# load halfway.
TABLES=$(rpsql -At -c "\"
WITH RECURSIVE fk AS (
  SELECT conrelid AS child, confrelid AS parent FROM pg_constraint WHERE contype='f'
), deps AS (
  SELECT 'companies'::regclass::oid AS t
  UNION SELECT 'rubric_progress'::regclass::oid
  UNION SELECT fk.child FROM fk JOIN deps ON fk.parent = deps.t
)
SELECT string_agg(t::regclass::text, ', ' ORDER BY t::regclass::text) FROM deps;\"" | tr -d '\r')
[ -n "$TABLES" ] || { echo "Jadvallar ro'yxatini aniqlab bo'lmadi." >&2; exit 1; }

LOCAL_N=$(lpsql -At -c "SELECT count(*) FROM companies;" | tr -d '\r')
SERVER_N=$(rpsql -At -c "'SELECT count(*) FROM companies;'" | tr -d '\r')

cat <<INFO

==> Ko'chiriladi:  $LOCAL_N ta kompaniya (lokal)  ->  server (hozir $SERVER_N ta)
==> Tozalanadi:    $TABLES
==> Tegilmaydi:    users, notifications, scrape_runs, alembic_version
INFO

if [ "${ASSUME_YES:-}" != "1" ]; then
  if { exec 3</dev/tty; } 2>/dev/null; then
    printf "Davom etamizmi? (ha/yo'q) "
    read -r answer <&3 || answer=""
    exec 3<&-
  else
    printf "Davom etamizmi? (ha/yo'q) "
    read -r answer || answer=""
  fi
  [ "$answer" = "ha" ] || { echo "Bekor qilindi."; exit 1; }
fi

# --- the actual load -------------------------------------------------------- #
# gzip on the wire: ~5.9M of SQL becomes ~0.9M, which matters far more than CPU
# on a home uplink. ON_ERROR_STOP + one transaction: it either all lands or
# nothing does.
echo "==> Oqizilmoqda..."
{
  echo "BEGIN;"
  echo "TRUNCATE $TABLES RESTART IDENTITY;"
  $COMPOSE exec -T postgres pg_dump -U parsing -d parsing \
    --data-only --no-owner --no-privileges -t companies -t rubric_progress </dev/null
  echo "COMMIT;"
} | gzip -c \
  | rsh "cd ~/$REMOTE_DIR && gzip -cd | docker compose exec -T postgres psql -U parsing -d parsing -v ON_ERROR_STOP=1 -q --output=/dev/null"

echo "==> Backend qayta ishga tushmoqda"
rsh "cd ~/$REMOTE_DIR && docker compose restart backend" >/dev/null 2>&1 || true

echo "==> Natija"
rpsql -c "\"SELECT COALESCE(source,'JAMI') AS manba, count(*) FROM companies GROUP BY ROLLUP(source) ORDER BY 1;\""
rpsql -c "'SELECT count(*) AS lead_holatlari FROM lead_states;'"

echo
echo "Tayyor. Barcha kompaniyalar 'Yangi' holatida."
