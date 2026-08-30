# Bazani serverga ko'chirish

Lokal mashinada yig'ilgan kompaniyalarni serverga o'tkazadi. **Barcha leadlar
"Yangi" holatida** bo'ladi — jarayondagi, kutilmoqda, tasdiqlangan yoki rad
etilganlari ham. Serverdagi foydalanuvchilar va ularning parollari tegilmaydi.

## Fayllar

| Fayl | Nima |
|---|---|
| `companies_snapshot.sql` | `companies` + `rubric_progress` ma'lumotlari (`pg_dump --data-only`) |
| `companies_snapshot.sql.gz` | O'shaning siqilgani — 5.9M o'rniga 0.9M, uzatish uchun |
| `import_snapshot.sh` | Serverda ishga tushiriladigan yuklovchi (`.sql` ham, `.gz` ham) |

Server: **crm.nextin.uz → 85.198.80.167**, loyiha `~/crm_system`.

## 1. Yangi snapshot olish (lokalda)

Scrape davom etayotgan bo'lsa snapshot eskiradi — ko'chirishdan sal oldin qayta oling:

```bash
REV=$(docker compose exec -T postgres psql -U parsing -d parsing -At \
        -c "SELECT version_num FROM alembic_version;" </dev/null | tr -d '\r')
{ echo "-- alembic_version: $REV"
  docker compose exec -T postgres pg_dump -U parsing -d parsing \
    --data-only --no-owner --no-privileges -t companies -t rubric_progress </dev/null
} > deploy/data/companies_snapshot.sql
gzip -cf deploy/data/companies_snapshot.sql > deploy/data/companies_snapshot.sql.gz
```

Birinchi qator — alembic revizyasi. Skript uni serverdagi sxema bilan solishtiradi
va mos kelmasa hech narsaga tegmasdan to'xtaydi.

`pg_dump` bitta tranzaksiyada o'qiydi, shuning uchun scrape ishlab turganda ham
yarim yozilgan holat tushmaydi.

## 2. Serverga yuborish

```bash
ssh root@85.198.80.167 'mkdir -p ~/crm_system/deploy/data'
scp deploy/data/companies_snapshot.sql.gz deploy/data/import_snapshot.sh \
    root@85.198.80.167:~/crm_system/deploy/data/
```

## 3. Serverda yuklash

```bash
cd ~/crm_system
docker compose up -d postgres          # baza ishlab turishi kerak
bash deploy/data/import_snapshot.sh deploy/data/companies_snapshot.sql.gz
```

Skript avval hozirgi holatni ko'rsatadi, nima o'chishini yozadi va `ha` deb
tasdiqlashni so'raydi. So'ramasdan ishlashi uchun: `ASSUME_YES=1`.

Yuklashdan keyin backendni qayta ishga tushiring, keshdagi eski sonlar qolmasligi uchun:

```bash
docker compose restart backend
```

## Nima o'chadi, nima qoladi

**Qayta yuklanadi:** `companies`, `rubric_progress`
`rubric_progress` ham ko'chiriladi — shunda serverdagi scrape butun katalogni
boshidan emas, lokal to'xtagan joydan davom ettiradi (AD-16).

**Tozalanadi:** `lead_states`, `lead_events`, `company_reviews`,
`company_claims`, `permission_requests`, `claim_requests`

Lead holati `lead_states` jadvalidan kelib chiqadi — qator bo'lmasa
`effective_status` "Yangi" qaytaradi. Ya'ni bu jadvalni tozalash aynan
"hammasi yangi bo'lsin" degani. Qolganlari `companies`ga tashqi kalit bilan
bog'langan, ular turganda Postgres `companies`ni tozalashga ruxsat bermaydi.

Bu ro'yxat skriptda qo'lda yozilmagan — har safar bazaning tashqi kalit
grafigidan hisoblanadi va tasdiqlashdan oldin ekranga chiqariladi. Kelajakda
yangi migratsiya jadval qo'shsa, skript uni o'zi topadi.

**Tegilmaydi:** `users`, `notifications`, `scrape_runs`, `alembic_version`

## Xavfsizlik

Hammasi **bitta tranzaksiya** ichida: xato bo'lsa hech narsa o'zgarmaydi,
yarim yuklangan baza qolmaydi.

## Tekshirilgan natijalar

Alohida `importtest` bazasida, jonli sxema bilan sinaldi:

| Tekshiruv | Natija |
|---|---|
| Eski `in_progress` / `waiting` / `approved` leadlar | hammasi yo'qoldi |
| Ilovaning o'z `status_sql_expr()` mantiqi | 10 057 tadan 10 057 tasi `new` |
| `lead_states` / `lead_events` / `company_reviews` | 0 / 0 / 0 |
| `company_claims` / `permission_requests` / `claim_requests` | 0 / 0 / 0 |
| `users` (server admini) | saqlandi |
| `companies` soni | snapshot bilan bir xil |
| `companies_id_seq` | `max(id)`ga surildi — yangi scrape konflikt bermaydi |
| Xato bo'lganda | tranzaksiya orqaga qaytdi, baza o'zgarmadi |
| Sxema versiyasi mos kelmaganda | hech narsaga tegmasdan to'xtadi (chiqish kodi 1) |
| Siqilgan `.gz` fayldan yuklash | ishladi |
| `alembic_version` | tegilmadi |

## Ma'lum bir jihat

`docker compose exec -T` stdin'ni yutib yuboradi, shuning uchun skriptdagi
ma'lumot beruvchi so'rovlar `/dev/null`dan o'qiydi va tasdiqlash `/dev/tty`dan
so'raladi. Buni o'zgartirmang — aks holda skript tasdiqlashni ololmay
"Bekor qilindi" deb chiqib ketadi.

Shuningdek `set -o pipefail` bilan `head -1` birga SIGPIPE beradi va skriptni
jimgina o'ldiradi, shuning uchun revizya o'qish `set +o pipefail` ichida.
