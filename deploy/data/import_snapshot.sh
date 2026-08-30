#!/usr/bin/env bash
#
# Load a scraped-companies snapshot onto the server, with every lead reset to
# "Yangi".
#
# WHAT IT REPLACES
#   companies         <- from the snapshot
#   rubric_progress   <- from the snapshot (so the server's own scrapes resume
#                        where the local one got to, instead of re-walking the
#                        whole catalog: see AD-16)
#
# WHAT IT WIPES, on purpose
#   Everything that carries a foreign key into those two, directly or through
#   another table: lead_states, lead_events, company_reviews, company_claims,
#   permission_requests, claim_requests.
#
#   Two reasons, and both matter:
#     1. A lead's status is derived from lead_states. With no row there,
#        `effective_status` reports NEW -- so clearing it is precisely what makes
#        every company read as "Yangi", including ones that were in_progress or
#        waiting.
#     2. Postgres will not truncate a table while another one still references
#        it, and rows pointing at companies that no longer exist are meaningless
#        anyway.
#
#   That list is NOT hardcoded below. It is computed from the live foreign-key
#   graph every run, and printed before you confirm. A future migration that adds
#   another table referencing companies will be picked up automatically instead
#   of failing the import halfway.
#
# WHAT IT LEAVES ALONE
#   users, notifications, scrape_runs, alembic_version
#   Server accounts and their history are not part of a data snapshot.
#
# Usage, from the project root on the SERVER:
#   bash deploy/data/import_snapshot.sh deploy/data/companies_snapshot.sql
#
set -euo pipefail

SNAPSHOT="${1:-deploy/data/companies_snapshot.sql}"
COMPOSE="${COMPOSE:-docker compose}"
DB="${DB:-parsing}"
PSQL="$COMPOSE exec -T postgres psql -U parsing -d $DB"

# `docker compose exec -T` swallows whatever is on stdin, so any psql call that
# is not meant to read a script has to be fed /dev/null explicitly. Without this
# the informational queries below eat the answer to the confirmation prompt and
# the import silently reports itself cancelled.
psqlq() { $PSQL "$@" </dev/null; }

if [ ! -f "$SNAPSHOT" ]; then
  echo "Snapshot topilmadi: $SNAPSHOT" >&2
  exit 1
fi

# The snapshot travels compressed (5.9M -> 0.9M), so read it either way rather
# than making the operator remember to gunzip first.
case "$SNAPSHOT" in
  *.gz) snapcat() { gzip -cd "$SNAPSHOT"; } ;;
  *)    snapcat() { cat "$SNAPSHOT"; } ;;
esac

# Every table that depends on companies/rubric_progress, transitively. Asking the
# database beats maintaining a list by hand -- the list drifts, the database
# cannot.
TABLES=$(psqlq -At -c "
WITH RECURSIVE fk AS (
  SELECT conrelid AS child, confrelid AS parent FROM pg_constraint WHERE contype='f'
),
deps AS (
  SELECT 'companies'::regclass::oid AS t
  UNION SELECT 'rubric_progress'::regclass::oid
  UNION SELECT fk.child FROM fk JOIN deps ON fk.parent = deps.t
)
SELECT string_agg(t::regclass::text, ', ' ORDER BY t::regclass::text) FROM deps;" | tr -d '\r')

if [ -z "$TABLES" ]; then
  echo "Jadvallar ro'yxatini aniqlab bo'lmadi -- baza ishlayaptimi?" >&2
  exit 1
fi

# The snapshot carries the alembic revision it was taken at. A server on a
# different revision can have different columns, and the COPY would then fail
# somewhere in the middle of 10k rows -- safe, because of the transaction, but
# baffling to read. Better to say so up front.
# `set -o pipefail` + `head -1` is a trap: head closes the pipe, gzip/cat die of
# SIGPIPE, and the whole script exits silently under `set -e`. The subshell turns
# pipefail off just for this read.
SNAP_REV=$(set +o pipefail; snapcat 2>/dev/null | head -1 | sed -n 's/^-- alembic_version: //p' | tr -d '\r')
SERVER_REV=$(psqlq -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d '\r' || true)

if [ -n "$SNAP_REV" ] && [ -n "$SERVER_REV" ] && [ "$SNAP_REV" != "$SERVER_REV" ]; then
  cat >&2 <<REV

XATO: sxema versiyalari mos kelmayapti.
      snapshot: $SNAP_REV
      server:   $SERVER_REV

  Avval serverda migratsiyalarni yangilang:
      docker compose run --rm backend alembic upgrade head

  (Bilib turib davom etmoqchi bo'lsangiz: SKIP_REV_CHECK=1)

REV
  [ "${SKIP_REV_CHECK:-}" = "1" ] || exit 1
fi

echo "==> Hozirgi holat"
psqlq -c "SELECT COALESCE(source,'JAMI') AS manba, count(*) FROM companies GROUP BY ROLLUP(source) ORDER BY 1;"
psqlq -c "SELECT status, count(*) FROM lead_states GROUP BY status;" || true

cat <<WARN

==> Bu amal quyidagi jadvallarni TOZALAYDI:
      $TABLES

    companies va rubric_progress snapshotdan qayta yuklanadi.
    Qolganlari bo'sh qoladi -- shuning uchun hamma lead "Yangi" bo'ladi
    (jarayonda va kutilmoqda holatidagilar ham).

    Tegilmaydi: users, notifications, scrape_runs, alembic_version

WARN
# Read from the terminal when there is one, so the prompt still works even if
# the script itself arrived on stdin. `[ -r /dev/tty ]` is not enough -- it can
# pass on a session with no controlling terminal and then fail to open -- so the
# open is the test.
if [ "${ASSUME_YES:-}" = "1" ]; then
  answer=ha
  echo "ASSUME_YES=1 -- tasdiqlash so'ralmadi."
elif exec 3</dev/tty 2>/dev/null; then
  read -r -p "Davom etamizmi? (ha/yo'q) " answer <&3 || answer=""
  exec 3<&-
else
  read -r -p "Davom etamizmi? (ha/yo'q) " answer || answer=""
fi
[ "$answer" = "ha" ] || { echo "Bekor qilindi."; exit 1; }

echo "==> Yuklanmoqda (bitta tranzaksiya -- yarim yuklangan holat bo'lmaydi)"
# One statement, not several: Postgres refuses to truncate a table while another
# still references it, so they have to go together rather than in some order.
# RESTART IDENTITY resets the sequences that the snapshot's setval() then sets.
{
  echo "BEGIN;"
  echo "TRUNCATE $TABLES RESTART IDENTITY;"
  snapcat
  echo "COMMIT;"
} | $PSQL -v ON_ERROR_STOP=1 >/dev/null

echo "==> Natija"
psqlq -c "SELECT COALESCE(source,'JAMI') AS manba, count(*) AS kompaniyalar FROM companies GROUP BY ROLLUP(source) ORDER BY 1;"
psqlq -c "SELECT count(*) AS lead_holatlari FROM lead_states;"
psqlq -c "SELECT count(*) AS rubrika_progress FROM rubric_progress;"

echo
echo "Tayyor. Barcha kompaniyalar 'Yangi' holatida."
echo "Tekshirish: admin panelda 'Yangi' soni jami kompaniyalar soniga teng bo'lishi kerak."
