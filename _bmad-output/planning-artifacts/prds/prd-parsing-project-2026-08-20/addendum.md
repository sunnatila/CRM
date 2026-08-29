# Addendum — OperatorDesk Lead Workflow v2

PRD ga sig'magan, lekin quyi oqim ishlari (arxitektura, UX spec, epiklar) uchun kerak bo'lgan chuqurlik. PRD qobiliyatni belgilaydi; bu hujjat "qanday" degan savolga tegadi va **taklif** darajasida qoladi — arxitektor uni tasdiqlaydi yoki almashtiradi.

---

## 1. Hozirgi kodda aniqlangan to'siqlar (dalillar)

PRD §1 dagi "operatorlar ishlay olmayapti" da'vosining kod darajasidagi manbasi. Har biri o'chiriladigan yoki almashtiriladigan aniq nuqta.

| # | Manzil | Nima bo'ladi | Qaysi FR yopadi |
|---|---|---|---|
| 1 | `services/claims.py` — `ActiveClaimExists` | Bitta faol ish qoidasi; boshqasiga o'tish uchun majburiy "kechiktirish" | FR-5 |
| 2 | `services/claims.py` — `defer_claim`, `AUTO_APPROVE_MAX_DAYS = 2` | 3+ kun → admin tasdig'i; javob kelguncha operator yangi ish ololmaydi | FR-17 |
| 3 | `services/claims.py` — `OverdueClaimsBlock` | Muddati o'tgan bitta ish barcha yangi ishlarni bloklaydi | FR-17 |
| 4 | `api/routes/reviews.py` — `row.locked = True` (submit_review) | Saqlash abadiy qulflaydi; tuzatish admin ruxsati orqali | FR-10, FR-18 |
| 5 | `routes/operator/company-review.tsx` — `canSubmit` | Har ikkala maydonga izoh majburiy; qisman saqlash yo'q | FR-19 |
| 6 | — (mavjud emas) | Qoralama saqlanmaydi; chiqib ketilsa ma'lumot yo'qoladi | FR-7 |
| 7 | `api/routes/reviews.py` — `Company.id.not_in(claimed_ids)` | Band Lead ro'yxatdan butunlay yo'qoladi; taqdiri ko'rinmaydi | FR-14 |
| 8 | `components/status-badge.tsx` — `pending/confirmed/absent` | Maydon statusi Lead statusi o'rnida ishlatilyapti | FR-1 |

**Diagnoz.** Sakkiztasi ham bitta xatoning ko'rinishlari: tizim operatorga ishonmaslik uchun loyihalangan. Har bir cheklov o'z-o'zicha mantiqli ("ikki kishi bir ishni qilmasin", "ma'lumot buzilmasin"), lekin birgalikda ular operatorni harakatsiz qoldiradi. v2 bir xil xavflarni bir xil darajada qoplaydi — faqat oldindan bloklash o'rniga keyin ko'rinuvchanlik bilan.

---

## 2. Ma'lumot modeli (taklif)

### 2.1 Yangi: `lead_states` — bir kompaniyaga bir qator

```
id                PK
company_id        FK companies.id, UNIQUE, index
status            varchar(16)  -- new | in_progress | waiting | approved | rejected
assigned_to_id    FK users.id, nullable, index   -- faqat in_progress da to'ladi
assigned_at       timestamptz, nullable
last_activity_at  timestamptz, nullable          -- FR-8 (4 soat) shu ustunga tayanadi
last_actor_id     FK users.id, nullable          -- FR-12: "Malika, 2 soat oldin"
created_at        timestamptz
updated_at        timestamptz
```

Indekslar: `(status, last_activity_at)` — navbat tablari va qotib qolganlar ro'yxati uchun; `(assigned_to_id, status)` — "Mening ishim" uchun.

**Yo'q qator = Yangi.** Migratsiya barcha kompaniyalarga qator yaratmaydi; ro'yxat `LEFT JOIN lead_states` + `COALESCE(status, 'new')` bilan o'qiydi. Sabab: skrap yangi kompaniya qo'shganda review domeni aralashmasligi kerak (AD-2 chegarasi saqlanadi). Qator birinchi tegishda lazily yaratiladi.

### 2.2 Yangi: `lead_events` — o'zgarmas tarix

```
id           PK
company_id   FK companies.id, index
actor_id     FK users.id, nullable        -- NULL = tizim (avtomatik bo'shatish, migratsiya)
type         varchar(24)  -- status_change | handover | comment | finish | reopen
                          -- | auto_release | admin_release | admin_assign | migration
from_status  varchar(16), nullable
to_status    varchar(16), nullable
note         text, nullable
created_at   timestamptz, index
```

Indeks: `(company_id, created_at DESC)`.

Faqat `INSERT`. `UPDATE`/`DELETE` uchun API yo'q — FR-11 talabi.

**Nega bitta jadval, ikkita emas?** Handover izohi alohida mexanizm emas — u tarixning bir turi. Ikkita jadval (izohlar + audit) bir xil ma'lumotni ikki joyda saqlab, "oxirgi izoh" so'rovini murakkablashtirar edi.

### 2.3 O'zgaradi: `company_reviews`

- `available` endi `NULL` bo'lib qolishi mumkin — bu "belgilanmagan" degani (qoralama holati). Hozirgi frontend `available` ni `false` ga majburlaydi (`company-review.tsx` dagi izohga qarang) — bu olib tashlanadi, chunki uch holatli maydon endi tabiiy ifodalanadi.
- `locked` ustuni **yozilmaydi**. Ustunni darhol o'chirmaslik tavsiya etiladi (ortga qaytish yo'li), lekin hech bir kod uni o'qimasligi kerak.
- Qator endi qoralama saqlashda ham yaratiladi/yangilanadi, faqat yakunlashda emas.

### 2.4 Retire: `company_claims`, `claim_requests`, `permission_requests`

Bitta reliz davomida bazada qoladi, yozuvsiz. Ular bilan ishlaydigan barcha route, service, schema va frontend ekranlari o'chiriladi. Keyingi relizda `drop table` migratsiyasi.

---

## 3. API sirti (taklif)

Prefiks `/api/reviews` → `/api/leads`. Yagona iste'molchi frontend, shuning uchun breaking change xavfsiz — lekin bu ongli qaror, tasodif emas: yangi lug'atni (PRD §3) API darajasida ham qo'llash kelajakdagi chalkashlikni oldini oladi.

| Metod | Yo'l | Vazifa | FR |
|---|---|---|---|
| `GET` | `/leads` | Ro'yxat: `status`, `q`, `category`, `page`. Javobda `items` **va** `total` **va** har bir status bo'yicha `counts` — bitta so'rovda | FR-14 |
| `GET` | `/leads/{company_id}` | Tafsilot: kompaniya + tekshiruv maydonlari + tarix + `available_actions` | FR-11 |
| `POST` | `/leads/{company_id}/start` | Band qilish. `409 held_by_other` \| `409 handover_required` (o'zida boshqa in_progress bor) | FR-3 |
| `POST` | `/leads/{company_id}/switch` | Atomar almashish: `{from_company_id, note}` — eskisini Kutilmoqda, yangisini Jarayonda | FR-5 |
| `PATCH` | `/leads/{company_id}/draft` | Qoralama avtomatik saqlash: `{website?, lms?}` | FR-7 |
| `POST` | `/leads/{company_id}/pause` | `{note}` majburiy → Kutilmoqda | FR-6 |
| `POST` | `/leads/{company_id}/finish` | `{result: approved\|rejected, note}` | FR-9 |
| `POST` | `/leads/{company_id}/reopen` | `{note}` majburiy → Jarayonda | FR-10 |
| `POST` | `/leads/{company_id}/comment` | `{note}` — status o'zgarmaydi | FR-13 |
| `POST` | `/leads/{company_id}/release` | **admin**: `{note}` majburan bo'shatish | FR-16 |
| `POST` | `/leads/{company_id}/assign` | **admin**: `{operator_id, note}` | FR-16 |
| `GET` | `/leads/attention` | **admin**: uzoq turganlar + ko'p qo'l almashganlar | FR-16 |

**O'chiriladi:** `POST /claims/*`, `GET /claims/me`, `POST /claim-requests/*`, `POST /reviews/{id}/{field}/request-permission`, `POST /permission-requests/*`.

### 3.1 Band qilish poygasi (NFR-4)

Ilova kodida "avval tekshir, keyin yoz" ishlamaydi — ikki so'rov orasida boshqa operator ulgurib qoladi. Shartli `UPDATE` kerak:

```sql
UPDATE lead_states
   SET status = 'in_progress', assigned_to_id = :me,
       assigned_at = now(), last_activity_at = now()
 WHERE company_id = :cid
   AND (status IN ('new','waiting')
        OR (status = 'in_progress' AND last_activity_at < now() - interval '4 hours'))
RETURNING id;
```

Qator qaytmasa → `409`. Qator yo'q bo'lsa (hech qachon tegilmagan Lead) → `INSERT ... ON CONFLICT (company_id) DO NOTHING` keyin qayta urinish, yoki `INSERT ... ON CONFLICT DO UPDATE ... WHERE` bitta amalda.

`WHERE` ichidagi 4 soatlik shart FR-8 ni **fon jarayonisiz** amalga oshiradi: avtomatik bo'shatish alohida cron emas, o'qish va band qilish so'rovlaridagi hisoblangan shart. Bu mavjud `is_overdue()` naqshining o'zi — u ham hisoblangan, saqlanmagan. Bitta yon ta'sir: bo'shatish hodisasi tarixga faqat kimdir Leadga tegilganda yoziladi. Agar tarix darhol yozilishi talab qilinsa, kunlik supurish vazifasi qo'shiladi — lekin bu MVP uchun kerak emas.

---

## 4. Frontend eslatmalari

### 4.1 Navigatsiya qo'riqchisi (FR-6) — muhim texnik shart

`App.tsx` hozir `<BrowserRouter>` ishlatadi. React Router'ning `useBlocker` hooki **faqat data router**da ishlaydi (`createBrowserRouter`). FR-6 ni to'g'ri bajarish uchun `App.tsx` `createBrowserRouter` + `<RouterProvider>` ga ko'chirilishi kerak. Bu kichik, lekin butun marshrutlash konfiguratsiyasiga tegadigan o'zgarish — epiklar rejalashtirilganda alohida qadam sifatida hisobga olinsin.

Muqobil (tavsiya etilmaydi): har bir navigatsiya nuqtasini qo'lda ushlab qolish — yon menyu, orqaga tugmasi, jadval qatorlari. Osongina teshik qoldiradi.

`beforeunload` yorliq yopilishini faqat brauzerning umumiy ogohlantirishi bilan qoplaydi — izohni majburlay olmaydi. FR-8 shu teshikni yopadi.

### 4.2 Status ranglari (`index.css`)

Hozir uchta token bor: `--status-confirmed` (yashil), `--status-absent` (kulrang), `--status-pending` (sariq). Beshtaga kengaytiriladi, ochiq va qorong'i mavzu uchun alohida:

| Status | Rol | Taklif (light) |
|---|---|---|
| Yangi | neytral, "hali tegilmagan" | slate — `--status-new` |
| Jarayonda | faol, e'tibor tortadi | ko'k/indigo — `--status-progress` |
| Kutilmoqda | kutish, sariq (mavjud `pending` qayta ishlatiladi) | `--status-waiting` |
| Tasdiqlangan | ijobiy yakun (mavjud `confirmed`) | `--status-approved` |
| Rad etilgan | salbiy yakun — **yangi rang kerak** | qizil — `--status-rejected` |

Eski `absent` (kulrang) endi maydon darajasida ("LMS yo'q") qoladi, Lead statusi sifatida emas. Ikkala lug'at aralashib ketmasligi uchun `StatusBadge` ikkita alohida komponentga bo'linsin: `LeadStatusBadge` (beshta) va `FieldStatusBadge` (mavjud, o'zgarishsiz).

Rad etilgan uchun qizil qo'shilganda `DESIGN.md` dagi kontrast tekshiruvi takrorlanishi kerak (NFR-6).

### 4.3 O'chiriladigan fayllar

`components/claim-banner.tsx`, `components/defer-dialog.tsx`, `routes/admin/claim-requests.tsx`, `routes/admin/permission-requests.tsx`.
`routes/operator/my-requests.tsx` → "Mening ishlarim" ga qayta yoziladi.

### 4.4 Yangi komponentlar

`lead-status-badge.tsx`, `handover-dialog.tsx` (FR-5/FR-6 uchun bitta umumiy dialog), `lead-timeline.tsx`, `lead-actions-bar.tsx`, `autosave-indicator.tsx`.

---

## 5. Yo'l-yo'lakay tuzatiladigan kod kamchiliklari

Foydalanuvchi "kod va tizimni yengillashtirish" ni aniq so'radi. Quyidagilar yangi funksiya emas — shu ishga tabiiy tushadigan tuzatishlar.

1. **N+1 so'rovlar — `reviews.py::_load_detail`.** Har bir maydon uchun alohida `session.get(User, ...)`. Bitta `IN` so'rovi bilan to'plamli o'qish. (NFR-2)
2. **N+1 so'rovlar — `claims.py::to_claim_out` va `claim_requests.py::_to_out`.** Har bir qator uchun `Company` va `User` alohida o'qiladi. Claim domeni bilan birga yo'qoladi, lekin naqsh yangi kodda takrorlanmasligi kerak.
3. **Ikkita so'rov bitta ro'yxat uchun — `queue.tsx`.** `/reviews` va `/reviews/count` alohida chaqiriladi. Bitta javobga birlashtiriladi. (FR-14)
4. **Backend testlari umuman yo'q.** `backend/tests/` bo'sh. Status mashinasi, band qilish poygasi va migratsiya uchun testlar shu ishning bir qismi. (NFR-8)
5. **`available` uchun uch holatli maydon `false` ga majburlanmoqda.** `company-review.tsx` dagi izoh buni ongli vaqtinchalik yechim deb tan oladi. Qoralama modeli bilan tabiiy hal bo'ladi.
6. **Kategoriya ro'yxati har so'rovda qayta hisoblanadi.** `GET /reviews/categories` barcha `category` matnlarini o'qib ajratadi. ~250 kompaniyada arzon, o'sganda emas. Kesh yoki materiallashtirilgan ko'rinish — hozir emas, lekin belgilab qo'yilsin.
7. **Xato javoblari nomuvofiq.** Ba'zilari `detail` string, ba'zilari `{code, message, ...}` obyekt. Yangi `/leads` API bitta shaklga tayansin: `{code, message, ...context}`.

---

## 6. Ko'rib chiqilib rad etilgan muqobillar

**Yumshoq band qilish (soft lock).** Boshlang'ich taklif: Lead ko'rinadi, egasi yozilgan, boshqa operator ogohlantirish bilan "o'zimga olaman" qila oladi. Foydalanuvchi rad etdi: *"agar kimdir ishlab turgan vaqtda boshqa ishchi o'shani qilishi kerak emas"*. Qo'ng'iroq markazi konteksti buni to'g'ri qiladi — ikki operator bir mijozga qo'ng'iroq qilishi mijoz oldida obro'ga zarar. Shuning uchun FR-4 to'liq ko'rinmaslikni talab qiladi.

**Ikki bosqichli yakunlash (operator yuboradi → admin tasdiqlaydi).** Rad etildi: bu aynan olib tashlanayotgan muammoni (admin bo'yin-bo'g'iz) yangi joyga ko'chirar edi. Sifat nazorati o'rniga SM-C1 (qayta ochilganlar ulushi) kuzatiladi.

**Muddatni saqlab, faqat blokirovkani olib tashlash.** Rad etildi: muddat operatorga hech qanday foyda bermas edi — u faqat admin uchun signal edi, va o'sha signalni `last_activity_at` bepul beradi. Operatordan kun soni so'rash — ma'nosiz ish.

**Statuslarni sozlanadigan qilish.** Rad etildi (PRD §5). Beshta status navbatning o'qilishini kafolatlaydi; sozlanadigan status har bir operatorga boshqacha ish oqimi degani.

**Har bir qoralama saqlashni tarixga yozish.** Rad etildi: tarix o'qib bo'lmaydigan darajada shovqinga to'lar edi va FR-12 ning ("oxirgi izoh") ma'nosi yo'qolar edi. `[ASSUMPTION]` sifatida PRD §12 da belgilangan — audit talabi qat'iylashsa qayta ko'riladi.

---

## 7. Amalga oshirish tartibi (taklif)

Har bir bosqich o'zicha ishlaydigan holatda tugaydi.

1. **Poydevor** — `lead_states` + `lead_events` jadvallari, status mashinasi servisi, testlar. Frontend tegilmaydi.
2. **Migratsiya** — §10 qoidalari, ortga qaytish yo'li bilan. Nusxa bazada sinaladi.
3. **Yangi API** — `/leads` to'liq sirti, eski API hali tirik.
4. **Frontend: navbat va Lead sahifasi** — beshta tab, tarix paneli, avtomatik saqlash, `createBrowserRouter` ga ko'chirish.
5. **Handover qo'riqchisi** — FR-5/FR-6 dialogi. Bu bosqichda tizim to'liq ishlaydi.
6. **Eski mexanizmni o'chirish** — claim/permission route'lari, ekranlari, komponentlari. Jadvallar arxiv sifatida qoladi.
7. **Admin nazorat ko'rinishlari** — FR-16 bloklari.
8. **Sayqal** — status ranglari, kontrast tekshiruvi, mikromatn, tezlik o'lchovlari.

1–3 bosqichlar foydalanuvchiga ko'rinmaydi; 4–5 bosqichlar birga yetkaziladi (yarim ko'chirilgan frontend ishlatib bo'lmaydi).
