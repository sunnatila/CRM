---
stepsCompleted: [1, 2, 3]
implementationStatus: "Epic 1-7 bajarildi 2026-08-20. Qolgan: eski jadvallarni o'chirish (keyingi reliz, AR-12)."
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-parsing-project-2026-08-20/prd.md
  - _bmad-output/planning-artifacts/prds/prd-parsing-project-2026-08-20/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-parsing-project-2026-07-26/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-parsing-project-2026-07-28/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-parsing-project-2026-07-28/EXPERIENCE.md
conflictPolicy: "PRD ustun. ARCHITECTURE-SPINE.md AD-8/AD-11 va DESIGN/EXPERIENCE'ning 3 rangli status lug'ati hamda qulflanadigan-maydon naqshi bekor. Qolgan barcha qarorlar amal qiladi."
---

# OperatorDesk Lead Workflow v2 - Epic Breakdown

## Overview

Bu hujjat OperatorDesk Lead Workflow v2 uchun to'liq epik va story taqsimotini beradi — PRD, UX dizayn shartnomasi va Arxitektura talablarini amalga oshiriladigan storylarga ajratadi.

**Muhim kontekst:** bu yangi mahsulot emas — **ishlab turgan tizimning ish oqimini almashtirish**. Shuning uchun har bir epik ikki tomonlama: yangisini qurish **va** eskisini olib tashlash. Storylar shunday tartiblanganki, har bir epik oxirida tizim ishlaydigan holatda qoladi.

## Requirements Inventory

### Functional Requirements

**Status modeli (PRD §4.1)**

- **FR-1:** Tizim har bir Leadni aynan beshta Lead statusdan birida saqlaydi (`new`, `in_progress`, `waiting`, `approved`, `rejected`). Statussiz Lead bo'lmaydi; hech qachon tegilmagan Lead **Yangi** deb o'qiladi. API beshtadan tashqari qiymatga 422 qaytaradi.
- **FR-2:** Tizim ruxsat etilgan o'tishlar jadvalida bo'lmagan har qanday status o'tishini rad etadi (409 + tushunarli o'zbekcha xabar). O'tish qoidalari faqat serverda yashaydi; frontend serverdan kelgan `available_actions` ni ko'rsatadi. Har bir muvaffaqiyatli o'tish tarixga bitta yozuv qo'shadi.

**Eksklyuziv band qilish (PRD §4.2)**

- **FR-3:** Operator **Yangi** yoki **Kutilmoqda** Leadni bosganda, Lead darhol **Jarayonda**ga o'tadi va unga biriktiriladi — alohida tasdiqlash bosqichisiz. Poygada birinchisi oladi, ikkinchisi 409 `held_by_other`.
- **FR-4:** Operator boshqa operatorga biriktirilgan **Jarayonda** Leadni hech bir yo'l bilan ko'ra olmaydi: ro'yxatda chiqmaydi, `GET /leads/{id}` 404 qaytaradi. Admin bundan mustasno.
- **FR-5:** Operator **Jarayonda** Leadi bor holda boshqasini boshlamoqchi bo'lsa, bitta dialogda Handover izohi so'raladi; izoh bo'sh bo'lsa davom etib bo'lmaydi. Ikkala o'tish bitta tranzaksiyada.
- **FR-6:** **Jarayonda** Lead sahifasidan chiqishga urinish (orqaga, yon menyu, boshqa Lead, yangilash) FR-5 dialogini chiqaradi. Ilova ichidagi har qanday navigatsiya ushlab qolinadi.

**Qoralama va yakunlash (PRD §4.3)**

- **FR-7:** **Jarayonda** Lead egasining tekshiruv maydonlaridagi o'zgarishlari ~1 soniya ichida avtomatik saqlanadi, "Saqlandi" indikatori bilan. Status o'zgarmaydi, tarixga yozuv qo'shilmaydi, faqat `last_activity_at` yangilanadi. Xatoda ma'lumot ekranda qoladi.
- **FR-8:** **Jarayonda** Lead 4 soat harakatsiz qolsa avtomatik **Kutilmoqda**ga o'tadi; tarixga tizim yozuvi tushadi; qoralama ma'lumot saqlanib qoladi.
- **FR-9:** Operator **Jarayonda** Leadni **Tasdiqlangan** (Website va LMS ikkalasi belgilangan bo'lsa) yoki **Rad etilgan** (sabab majburiy) holatiga o'tkazadi. Admin tasdig'i talab qilinmaydi.
- **FR-10:** Har qanday operator **Tasdiqlangan**/**Rad etilgan** Leadni sabab yozib qayta ocha oladi; Lead **Jarayonda**ga o'tadi va unga biriktiriladi; oldingi ma'lumot saqlanadi.

**Lead tarixi (PRD §4.4)**

- **FR-11:** Tizim har bir muhim hodisani o'zgarmas tarix yozuvi sifatida saqlaydi (status o'zgarishi, Handover izohi, erkin izoh, yakunlash, qayta ochish, avtomatik bo'shatish, admin aralashuvi). Har yozuvda: kim/tizim, qachon, tur, matn. Tahrirlash va o'chirish API'si yo'q.
- **FR-12:** **Kutilmoqda** ro'yxatida har bir qator ostida oxirgi Handover izohi muallifi va vaqti bilan ko'rinadi; uzuni qisqartiriladi.
- **FR-13:** Operator **Jarayonda** Leadga status o'zgartirmasdan erkin izoh qo'sha oladi; bo'sh izoh qabul qilinmaydi.

**Navbat va ko'rinuvchanlik (PRD §4.5)**

- **FR-14:** Navbat status bo'yicha tablarga bo'linadi, har birida joriy soni bilan. Operator: Yangi · Mening ishim · Kutilmoqda · Tasdiqlangan · Rad etilgan. Admin: plus Jarayonda (hammasi). Ro'yxat va sanoqlar bitta so'rovda keladi. Nomi/kategoriya filtrlari har tabda ishlaydi.
- **FR-15:** Band qilish/bo'shatish hodisalari mavjud WebSocket kanali orqali boshqa operatorlarga uzatiladi va ochiq navbat o'zi yangilanadi; ulanish uzilsa davriy yangilanishga qaytadi.
- **FR-16:** Admin panelida "Uzoq turgan ishlar" (2 kundan ortiq **Kutilmoqda**) va "Ko'p qo'l almashgan" (3 martadan ko'p) bloklari; admin har qanday **Jarayonda** Leadni majburan bo'shata yoki qayta biriktira oladi (sabab majburiy); har aralashuv tarixga yoziladi.

**Olib tashlanadigan mexanizmlar (PRD §4.6)**

- **FR-17:** Muddat kiritish, muddat cho'zish/voz kechish so'rovlari, "muddati o'tdi" bloklashi va admin panelidagi "Ish so'rovlari" bo'limi mavjud emas. Hech qanday operator harakati admin javobini kutishga majbur qilmaydi.
- **FR-18:** Tekshiruv maydonlari qulflanmaydi; ruxsat so'rash API'lari va "Ruxsat so'rovlari" bo'limi mavjud emas; mavjud so'rovlar tarixi arxiv sifatida qoladi.
- **FR-19:** Leadni ochish yoki undan chiqish maydonlarni to'ldirishni talab qilmaydi; qisman to'ldirish mumkin. Majburiy to'ldirish faqat **Tasdiqlash**da qoladi (FR-9).

### NonFunctional Requirements

- **NFR-1:** Navbat sahifasi 300 ms ichida javob berishi kerak (250–5 000 Lead oralig'ida). `status` va biriktirish maydonlari indekslangan bo'lishi shart.
- **NFR-2:** Lead ro'yxati va Lead sahifasi N+1 so'rov qilmasligi kerak — operator va tekshiruv maydonlari to'plamli o'qilishi shart.
- **NFR-3:** Ikki bosqichli o'tishlar (FR-5) bitta tranzaksiyada bajarilishi shart; yarim bajarilgan holat mumkin emas.
- **NFR-4:** Band qilish poygasi bazada hal qilinishi kerak (shartli `UPDATE`), ilova kodidagi "avval tekshir, keyin yoz" bilan emas.
- **NFR-5:** Hech bir avtomatik harakat (bo'shatish, migratsiya) operator kiritgan ma'lumotni o'chirmaydi.
- **NFR-6:** WCAG 2.2 AA saqlanadi. Status hech qachon faqat rang bilan berilmaydi: ikonka + rang + matn. Majburiy izoh xatosi `aria-live` orqali e'lon qilinadi.
- **NFR-7:** Operatorga ko'rinadigan barcha matn o'zbek tilida; texnik identifikatorlar (`in_progress`, `waiting`) ekranga chiqmaydi.
- **NFR-8:** Status mashinasi va band qilish poygasi avtomatik testlar bilan qoplanishi shart. *(Hozir `backend/tests/` bo'sh.)*
- **NFR-9:** Har bir status o'tishi tarixga yoziladi; tarix hisobot uchun yetarli bo'lishi kerak (kim, qachon, qancha vaqt turdi).

### Additional Requirements

**Arxitekturadan (amal qiladigan qarorlar):**

- **AR-1** (AD-1, AD-5, AD-6): Backend FastAPI + async SQLAlchemy + PostgreSQL; sxema o'zgarishlari faqat Alembic migratsiyalari orqali; katalog tuzilishi `api/routes` → `services` → `models`/`schemas` saqlanadi.
- **AR-2** (AD-2, AD-3): `companies` jadvali skrap domeniga tegishli; review domeni uni **hech qachon yozmaydi**. Yangi `lead_states` skrap yo'liga bog'lanmasligi kerak — `LEFT JOIN` + `COALESCE(status,'new')` bilan lazily o'qiladi, skrap yangi kompaniya qo'shganda qator yaratish talab qilinmaydi.
- **AR-3** (AD-7): JWT autentifikatsiya, yagona `users` jadvali, `role ∈ {operator, admin}` — o'zgarishsiz. Har bir yangi route JWT talab qiladi; admin route'lari qo'shimcha `role == "admin"` tekshiradi.
- **AR-4** (AD-9): Bildirishnomalar uchun DB yozuv + WebSocket yetkazish mexanizmi qayta ishlatiladi (FR-15). `ConnectionManager` jarayon ichidagi xotirada — bitta uvicorn worker'da ishlaydi. **`link` taksonomiyasi yangilanishi shart**: `permission-request:` va `claim-request:` prefikslari yo'qoladi.
- **AR-5** (AD-10): Frontend React + TypeScript + Vite + Tailwind + shadcn/ui; `API_BASE` nisbiy `/api`; nginx bir xil origin orqali proksilaydi; JWT `localStorage` da. O'zgarishsiz.
- **AR-6** (AD-12): Kategoriya filtri `string_to_array(category,'; ')` + `ANY(...)` orqali ishlaydi — yangi `/leads` endpointlarida saqlanishi shart.
- **AR-7** (Conventions): DB ustunlari `snake_case`, barcha vaqt belgilari UTC, konfiguratsiya faqat `core/config.py` orqali (`os.environ` to'g'ridan-to'g'ri o'qilmaydi).

**Addendum'dan (texnik talablar):**

- **AR-8:** Yangi jadvallar `lead_states` (bir kompaniyaga bir qator, `company_id` UNIQUE) va `lead_events` (faqat `INSERT`). Indekslar: `(status, last_activity_at)`, `(assigned_to_id, status)`, `(company_id, created_at DESC)`.
- **AR-9:** 4 soatlik avtomatik bo'shatish **fon jarayonisiz** — band qilish `WHERE` shartida hisoblanadi (mavjud `is_overdue()` naqshi kabi). Cron yoki scheduler qo'shilmaydi.
- **AR-10:** API prefiksi `/api/reviews` → `/api/leads`. Eski `/claims`, `/claim-requests`, `/permission-requests` route'lari o'chiriladi.
- **AR-11:** `App.tsx` `<BrowserRouter>` dan `createBrowserRouter` + `<RouterProvider>` ga ko'chirilishi shart — `useBlocker` (FR-6) faqat data router'da ishlaydi.
- **AR-12:** Migratsiya ortga qaytish yo'li bilan; `company_claims`, `claim_requests`, `permission_requests` bitta reliz davomida bazada arxiv sifatida qoladi (yozuvsiz), keyingi relizda alohida migratsiyada o'chiriladi. `company_reviews.locked` ustuni qoladi lekin hech bir kod uni o'qimaydi.
- **AR-13:** Xato javoblari bitta shaklga keltiriladi: `{code, message, ...context}`.
- **AR-14:** `company_reviews.available` `NULL` bo'la olishi kerak ("belgilanmagan"); frontend'dagi `false` ga majburlash olib tashlanadi.

### UX Design Requirements

**Dizayn tokenlari va status lug'ati:**

- **UX-DR1:** Lead statusi uchun beshta rang tokeni yaratish (`--status-new` slate, `--status-progress` ko'k/indigo, `--status-waiting` sariq, `--status-approved` yashil, `--status-rejected` **qizil — yangi rang**), ochiq va qorong'i mavzu uchun alohida qiymatlar bilan. Har biri uchun WCAG AA kontrast tekshiruvi bajarilishi shart.
- **UX-DR2:** `StatusBadge` ikkiga bo'linadi: `LeadStatusBadge` (beshta Lead statusi) va `FieldStatusBadge` (mavjud uchta maydon holati — `confirmed`/`absent`/`pending`, o'zgarishsiz). Ikkala lug'at aralashmasligi kerak.
- **UX-DR3:** Har bir status badge ikonka + rang + o'zbekcha matn bilan beriladi; rang yolg'iz o'zi ma'no tashimaydi (NFR-6). Beshta status uchun beshta aniq ikonka tanlanadi.
- **UX-DR4:** DESIGN.md dagi "to'rtinchi status rangini o'ylab topmang" qoidasi bekor bo'ldi — hujjat yangi beshta rangli lug'at bilan yangilanishi shart.

**Yangi komponentlar:**

- **UX-DR5:** `HandoverDialog` — FR-5 va FR-6 uchun yagona umumiy dialog. Izoh maydoni bo'sh bo'lsa asosiy tugma o'chiq; "Ishda qolish" muqobil harakati bor.
- **UX-DR6:** `LeadTimeline` — Lead tarixi paneli, eng yangisidan boshlab; har yozuvda muallif (yoki "Tizim"), vaqt, tur ikonkasi, matn.
- **UX-DR7:** `LeadActionsBar` — serverdan kelgan `available_actions` asosida mumkin bo'lgan harakatlarni ko'rsatadi (Boshlash / Qoldirish / Tasdiqlash / Rad etish / Qayta ochish / Izoh qo'shish).
- **UX-DR8:** `AutosaveIndicator` — "Saqlanmoqda…" / "Saqlandi" / "Saqlanmadi — qayta urinish" uch holati.

**Ekranlar:**

- **UX-DR9:** Navbat ekrani ikkita tabdan (`to'ldirilishi kerak`/`to'ldirilgan`) beshta status tabiga o'tadi, har birida sanoq bilan. Band qilish banneri olib tashlanadi. Har tab uchun alohida bo'sh holat matni yoziladi.
- **UX-DR10:** Lead sahifasi qayta quriladi: status sarlavhasi + egasi + `LeadActionsBar` + avtomatik saqlanadigan maydonlar + `LeadTimeline`. "Saqlash → abadiy qulf" `AlertDialog` i olib tashlanadi.
- **UX-DR11:** `routes/operator/my-requests.tsx` → **"Mening ishlarim"**: operatorning joriy ishi va yaqinda yakunlagan Leadlari.
- **UX-DR12:** Admin boshqaruv paneli kengayadi: status bo'yicha taqsimot + "Uzoq turgan ishlar" + "Ko'p qo'l almashgan" bloklari.
- **UX-DR13:** Yangi admin ekrani **"Barcha Leadlar"** — har qanday statusdagi Leadni egasi bilan ko'rish, majburan bo'shatish, qayta biriktirish.
- **UX-DR14:** O'chiriladigan ekranlar/komponentlar: `components/claim-banner.tsx`, `components/defer-dialog.tsx`, `routes/admin/claim-requests.tsx`, `routes/admin/permission-requests.tsx`.
- **UX-DR15:** Bildirishnoma `link` taksonomiyasi va `resolveLink()` yangilanadi: `permission-request:`/`claim-request:` prefikslari o'chadi, `lead:{company_id}` qoladi.

**Saqlanadigan naqshlar va mikromatn:**

- **UX-DR16:** EXPERIENCE.md ohangi saqlanadi — sodda, operatsion, undov belgisisiz. Barcha yangi holatlar uchun o'zbekcha mikromatn yoziladi (dialog sarlavhalari, bo'sh holatlar, xato xabarlari, tugma yorliqlari).
- **UX-DR17:** Majburiy izoh validatsiya xatosi `aria-live` orqali e'lon qilinadi va maydonga bog'lanadi, faqat rang bilan ko'rsatilmaydi.
- **UX-DR18:** Mavjud jadval naqshlari saqlanadi: zich va skanerlanadigan, telefon/ID uchun mono raqamlar, cheksiz skroll emas sahifalash, qator bosilganda detalga o'tish, `Esc` dialogni yopadi.
- **UX-DR19:** EXPERIENCE.md yangilanadi: status lug'ati bo'limi, "qulflangan maydon" komponent holati, "Saqlash ikkala maydonni birga yuboradi" qoidasi va ruxsat so'rash oqimi bekor — o'rniga Lead status oqimi, qoralama va Handover naqshlari yoziladi.

### FR Coverage Map

| Talab | Qoplaydigan storylar |
|---|---|
| FR-1 | 1.2, 4.1 |
| FR-2 | 1.2, 1.5, 3.3 |
| FR-3 | 1.3, 3.3, 4.3 |
| FR-4 | 1.3, 3.1, 3.2 |
| FR-5 | 3.3, 4.6 |
| FR-6 | 4.2, 4.6 |
| FR-7 | 3.4, 4.4 |
| FR-8 | 1.3, 1.5 |
| FR-9 | 3.3, 4.4 |
| FR-10 | 3.3, 4.4 |
| FR-11 | 1.4, 4.5 |
| FR-12 | 3.1, 4.3 |
| FR-13 | 3.3, 4.5 |
| FR-14 | 3.1, 4.3 |
| FR-15 | 5.1 |
| FR-16 | 3.5, 5.2, 5.3 |
| FR-17 | 6.1, 6.2 |
| FR-18 | 6.1, 6.2 |
| FR-19 | 3.4, 4.4 |
| NFR-1 | 1.1, 3.1 |
| NFR-2 | 3.1, 3.2 |
| NFR-3 | 3.3, 1.5 |
| NFR-4 | 1.3, 1.5 |
| NFR-5 | 1.3, 2.1, 2.2 |
| NFR-6 | 4.1, 4.6 |
| NFR-7 | 4.1, 4.3, 4.4, 4.6 |
| NFR-8 | 1.5, 2.2 |
| NFR-9 | 1.4, 5.2 |
| AR-1…AR-2 | 1.1 |
| AR-3 | 3.1, 3.5 |
| AR-4 | 5.1, 5.4 |
| AR-5 | 4.2 |
| AR-6 | 3.1 |
| AR-7 | 1.1, 1.4 |
| AR-8 | 1.1 |
| AR-9 | 1.3 |
| AR-10 | 3.1, 6.1 |
| AR-11 | 4.2 |
| AR-12 | 2.1, 2.2, 6.1 |
| AR-13 | 3.6 |
| AR-14 | 3.4, 4.4 |
| UX-DR1…DR4 | 4.1 |
| UX-DR5 | 4.6 |
| UX-DR6 | 4.5 |
| UX-DR7, DR8 | 4.4 |
| UX-DR9 | 4.3 |
| UX-DR10 | 4.4 |
| UX-DR11 | 4.7 |
| UX-DR12 | 5.2 |
| UX-DR13 | 5.3 |
| UX-DR14 | 6.2 |
| UX-DR15 | 5.4 |
| UX-DR16…DR18 | 4.3, 4.4, 4.6 |
| UX-DR19 | 7.2 |

## Epic List

| # | Epik | Maqsad | Storylar |
|---|---|---|---|
| 1 | Lead status poydevori | Status mashinasi, eksklyuziv band qilish va tarix — backend'da, foydalanuvchiga ko'rinmasdan | 5 |
| 2 | Ma'lumot migratsiyasi | Ishlab turgan ma'lumotni yangi modelga ko'chirish, hech kimning ishini yo'qotmasdan | 2 |
| 3 | Lead API | `/api/leads` to'liq sirti — eski API hali tirik turganda | 6 |
| 4 | Operator interfeysi | Beshta tab, Lead sahifasi, avtomatik saqlash, Handover qo'riqchisi | 7 |
| 5 | Jonli yangilanish va admin nazorati | WebSocket, admin bloklari, Barcha Leadlar ekrani | 4 |
| 6 | Eski mexanizmni olib tashlash | Claim/permission kodini butunlay o'chirish | 3 |
| 7 | Hujjatlarni moslashtirish | Arxitektura va UX hujjatlarini yangi haqiqatga keltirish | 2 |

**Tartib qoidasi:** 1→2→3 foydalanuvchiga ko'rinmaydi (eski tizim ishlab turadi). 4→5 birga yetkaziladi — yarim ko'chirilgan frontend ishlatib bo'lmaydi. 6 faqat 4–5 ishlagani tasdiqlangach. 7 istalgan paytda.

---

## Epic 1: Lead status poydevori

Status mashinasi, eksklyuziv band qilish va o'zgarmas tarix backend'da quriladi. Foydalanuvchiga hech narsa ko'rinmaydi — eski tizim to'liq ishlab turadi. Epik oxirida yangi model testlar bilan qoplangan va ishonchli bo'ladi.

### Story 1.1: Lead holati va tarix jadvallari

As a dev,
I want `lead_states` va `lead_events` jadvallari Alembic migratsiyasi bilan yaratilishini,
So that Lead statusi va tarixi skrap domeniga tegmasdan saqlanadigan joyga ega bo'lsin.

**Acceptance Criteria:**

**Given** bo'sh baza (`alembic upgrade head`)
**When** migratsiya bajariladi
**Then** `lead_states` jadvali yaratiladi: `company_id` (FK, UNIQUE), `status`, `assigned_to_id` (FK, nullable), `assigned_at`, `last_activity_at`, `last_actor_id` (FK, nullable), `created_at`, `updated_at`
**And** `lead_events` jadvali yaratiladi: `company_id` (FK), `actor_id` (FK, nullable), `type`, `from_status`, `to_status`, `note`, `created_at`
**And** indekslar mavjud: `(status, last_activity_at)`, `(assigned_to_id, status)`, `(company_id, created_at DESC)`
**And** barcha vaqt ustunlari `timezone=True` (AR-7)

**Given** migratsiya bajarilgan
**When** `alembic downgrade -1` chaqiriladi
**Then** ikkala jadval ham toza o'chadi va mavjud jadvallarga zarar yetmaydi

**Given** skrap yangi kompaniya qo'shadi
**When** `companies` ga qator qo'shiladi
**Then** `lead_states` ga hech narsa yozilmaydi — qator faqat birinchi tegishda yaratiladi (AR-2)

### Story 1.2: Status mashinasi

As a dev,
I want ruxsat etilgan o'tishlar bitta joyda e'lon qilinishini va har qanday boshqa o'tish rad etilishini,
So that status qoidalari kod bo'ylab tarqalib ketmasin.

**Acceptance Criteria:**

**Given** `services/leads.py` dagi o'tish jadvali
**When** har qanday status o'zgarishi so'raladi
**Then** faqat PRD §4.1 jadvalidagi o'tishlar ruxsat etiladi
**And** ruxsat etilmagan o'tish `LeadTransitionError` ko'taradi, u 409 va o'zbekcha xabarga aylanadi (FR-2)
**And** beshtadan tashqari status qiymati Pydantic darajasida 422 beradi (FR-1)

**Given** har qanday Lead va foydalanuvchi
**When** `available_actions(lead, user)` chaqiriladi
**Then** o'sha foydalanuvchi shu paytda bajara oladigan harakatlar ro'yxati qaytadi
**And** frontend bu ro'yxatni ko'rsatadi, o'z qoidalarini takrorlamaydi

### Story 1.3: Eksklyuziv band qilish va avtomatik bo'shatish

As an operator,
I want Leadni band qilganimda uni boshqa hech kim ololmasligini, lekin men uni abadiy ushlab qololmasligimni,
So that ikki operator bir mijozga qo'ng'iroq qilmasin va qotib qolgan ish navbatga qaytsin.

**Acceptance Criteria:**

**Given** ikkita operator bir vaqtda bir Leadni band qilmoqchi
**When** ikkalasi ham `claim` chaqiradi
**Then** faqat bittasi muvaffaqiyatli bo'ladi — shartli `UPDATE ... RETURNING` orqali, ilova kodidagi tekshiruv bilan emas (NFR-4)
**And** ikkinchisi `held_by_other` xatosini oladi

**Given** `in_progress` Lead va uning `last_activity_at` dan 4 soat o'tgan
**When** boshqa operator uni band qilmoqchi bo'ladi
**Then** band qilish muvaffaqiyatli bo'ladi — 4 soatlik shart `WHERE` ichida hisoblanadi, fon jarayoni yo'q (AR-9)
**And** tarixga `auto_release` yozuvi tushadi
**And** oldingi egasining qoralama ma'lumoti o'chmaydi (NFR-5)

**Given** hech qachon tegilmagan Lead (`lead_states` da qator yo'q)
**When** band qilinadi
**Then** qator atomik tarzda yaratiladi (`INSERT ... ON CONFLICT`) va poyga holatida dublikat qator paydo bo'lmaydi

### Story 1.4: Tarix yozish

As an admin,
I want har bir muhim hodisa o'chirib bo'lmaydigan tarzda yozilishini,
So that "kim, qachon, nima qildi" savoliga har doim javob bo'lsin.

**Acceptance Criteria:**

**Given** har qanday status o'tishi, izoh, yakunlash, qayta ochish, avtomatik bo'shatish yoki admin aralashuvi
**When** amal bajariladi
**Then** `lead_events` ga bitta qator qo'shiladi: kim (yoki `NULL` = tizim), qachon, tur, eski/yangi status, matn (FR-11)
**And** tarix yozuvini yangilaydigan yoki o'chiradigan servis funksiyasi mavjud emas
**And** yozuv status o'zgarishi bilan bitta tranzaksiyada bo'ladi — biri saqlanib ikkinchisi yo'qolmaydi

**Given** qoralama avtomatik saqlash
**When** maydon o'zgaradi
**Then** tarixga yozuv qo'shilmaydi, faqat `last_activity_at` yangilanadi (FR-7)

### Story 1.5: Poydevor testlari

As a dev,
I want status mashinasi va band qilish poygasi testlar bilan qoplanishini,
So that keyingi epiklar ishonchli poydevor ustiga qurilsin.

**Acceptance Criteria:**

**Given** `backend/tests/` (hozir bo'sh)
**When** test to'plami ishga tushiriladi
**Then** har bir ruxsat etilgan o'tish uchun ijobiy test bor
**And** ruxsat etilmagan o'tishlar uchun salbiy testlar bor (kamida: Yangi→Tasdiqlangan, Kutilmoqda→Rad etilgan, boshqaning Leadini band qilish)
**And** parallel band qilish poygasi testi ikkitadan faqat bittasi muvaffaqiyatli bo'lishini tasdiqlaydi (NFR-4)
**And** 4 soatlik avtomatik bo'shatish testi vaqtni siljitib tekshiradi
**And** FR-5 ikki bosqichli o'tishning atomarligi testi bor (NFR-3)

---

## Epic 2: Ma'lumot migratsiyasi

Ishlab turgan ma'lumot yangi modelga ko'chiriladi. Hech kimning ishi yo'qolmaydi va ortga qaytish yo'li ochiq qoladi.

### Story 2.1: Status ko'chirish migratsiyasi

As an admin,
I want mavjud to'ldirilgan yozuvlar va band qilishlar yangi statuslarga to'g'ri ko'chirilishini,
So that yangi tizim yoqilganda operatorlar ishini qaytadan boshlamasin.

**Acceptance Criteria:**

**Given** ishlab turgan bazadagi ma'lumot
**When** migratsiya bajariladi
**Then** har ikki tekshiruv maydoni to'ldirilgan kompaniyalar → **Tasdiqlangan**
**And** bitta maydon to'ldirilganlar → **Kutilmoqda** + tizim izohi
**And** `active` claim'lar → **Jarayonda**, o'sha operatorga biriktirilgan, `last_activity_at` = migratsiya vaqti
**And** `deferred` claim'lar → **Kutilmoqda**, eski `reason` matni Handover izohi sifatida ko'chirilgan (bo'sh bo'lsa tizim izohi)
**And** qolgan kompaniyalar uchun `lead_states` qatori yaratilmaydi (ular **Yangi** deb o'qiladi)
**And** har bir ko'chirilgan Lead uchun `lead_events` ga `migration` turidagi yozuv tushadi

**Given** migratsiya bajarilgan
**When** hech bir eski jadval tekshiriladi
**Then** `company_claims`, `claim_requests`, `permission_requests`, `company_reviews.locked` — hech biri o'chirilmagan yoki o'zgartirilmagan (AR-12, NFR-5)

### Story 2.2: Migratsiyani tekshirish va ortga qaytarish

As a dev,
I want migratsiya natijasini tekshiradigan va uni ortga qaytara oladigan yo'l bo'lishini,
So that yangi model kutilmaganda ishlamay qolsa tizim tiklanadi.

**Acceptance Criteria:**

**Given** migratsiyadan oldingi holat
**When** `alembic downgrade` chaqiriladi
**Then** `lead_states` va `lead_events` o'chadi, eski jadvallar avvalgi holatda ishlaydi

**Given** nusxa baza
**When** tekshiruv testi bajariladi
**Then** ko'chirilgan Leadlar soni manba yozuvlar soniga teng ekani tasdiqlanadi
**And** hech bir `in_progress` Lead egasiz qolmagani tasdiqlanadi
**And** hech bir `waiting` Lead izohsiz qolmagani tasdiqlanadi (FR-12 kafolati)

---

## Epic 3: Lead API

`/api/leads` to'liq sirti quriladi. Eski API hali tirik — frontend hali eskisiga tayanadi, shuning uchun bu epik hech narsani buzmaydi.

### Story 3.1: Lead ro'yxati — tablar, sanoqlar, ko'rinuvchanlik

As an operator,
I want navbatni status bo'yicha ko'rishni va boshqaning ishi menga ko'rinmasligini,
So that faqat men ishlashim mumkin bo'lgan narsalarni ko'ray.

**Acceptance Criteria:**

**Given** operator sifatida autentifikatsiya qilingan so'rov
**When** `GET /api/leads?status=new` chaqiriladi
**Then** javobda `items`, `total` **va** har bir status bo'yicha `counts` bitta so'rovda keladi (FR-14)
**And** boshqa operatorga biriktirilgan `in_progress` Leadlar hech bir status filtrida chiqmaydi (FR-4)
**And** `q` (nom) va `category` filtrlari ishlaydi, kategoriya `string_to_array` + `ANY` orqali (AR-6)
**And** `waiting` statusidagi har bir element oxirgi Handover izohini, muallifini va vaqtini o'z ichiga oladi (FR-12)
**And** so'rov N+1 qilmaydi — operator ismlari to'plamli o'qiladi (NFR-2)
**And** hech qachon tegilmagan kompaniyalar `LEFT JOIN` + `COALESCE` orqali **Yangi** sifatida chiqadi (AR-2)

**Given** admin sifatida so'rov
**When** ro'yxat so'raladi
**Then** barcha Leadlar, jumladan boshqalarning `in_progress` Leadlari egasi ismi bilan chiqadi

### Story 3.2: Lead tafsiloti

As an operator,
I want Lead sahifasi uchun kerak bo'lgan hamma narsani bitta so'rovda olishni,
So that sahifa tez ochilsin va men nima qila olishimni bilaman.

**Acceptance Criteria:**

**Given** menga biriktirilgan yoki bo'sh Lead
**When** `GET /api/leads/{company_id}` chaqiriladi
**Then** javobda kompaniya ma'lumoti, tekshiruv maydonlari, Lead tarixi va `available_actions` bo'ladi
**And** so'rov N+1 qilmaydi — tarix mualliflari to'plamli o'qiladi (NFR-2)

**Given** boshqa operatorga biriktirilgan `in_progress` Lead
**When** operator uni to'g'ridan-to'g'ri so'raydi
**Then** **404** qaytadi (403 emas — mavjudligi ham oshkor qilinmaydi) (FR-4)
**And** admin uchun bu holat 200 qaytaradi

### Story 3.3: Status o'tish endpointlari

As an operator,
I want ishni boshlash, qoldirish, almashtirish, yakunlash va qayta ochishni,
So that hech kimdan ruxsat so'ramasdan ishlay olay.

**Acceptance Criteria:**

**Given** bo'sh Lead
**When** `POST /leads/{id}/start`
**Then** Lead `in_progress` bo'ladi, menga biriktiriladi (FR-3)
**And** menda allaqachon boshqa `in_progress` Lead bo'lsa, `409 handover_required` qaytadi (joriy Lead ma'lumoti bilan)

**Given** menda `in_progress` Lead bor va boshqasiga o'tmoqchiman
**When** `POST /leads/{id}/switch` `{from_company_id, note}` bilan chaqiriladi
**Then** eski Lead `waiting`, yangisi `in_progress` bo'ladi — **bitta tranzaksiyada** (NFR-3)
**And** `note` bo'sh bo'lsa 422 qaytadi (FR-5)
**And** yangisini band qilib bo'lmasa, eskisi ham o'zgarmaydi

**Given** menga biriktirilgan `in_progress` Lead
**When** `POST /leads/{id}/pause` `{note}` chaqiriladi
**Then** Lead `waiting` bo'ladi, ega bo'shaydi, izoh tarixga tushadi; bo'sh izoh 422

**When** `POST /leads/{id}/finish` `{result, note}` chaqiriladi
**Then** `approved` uchun Website va LMS ikkalasi belgilangan bo'lishi shart, aks holda 409 (FR-9)
**And** `rejected` uchun `note` majburiy
**And** ega bo'shaydi va tarixga yakunlovchi yozuv tushadi

**Given** `approved` yoki `rejected` Lead
**When** `POST /leads/{id}/reopen` `{note}` chaqiriladi
**Then** Lead `in_progress` bo'ladi va menga biriktiriladi; `note` bo'sh bo'lsa 422 (FR-10)
**And** oldingi tekshiruv ma'lumoti saqlanib qoladi

**When** `POST /leads/{id}/comment` `{note}` chaqiriladi
**Then** status o'zgarmaydi, tarixga izoh tushadi; bo'sh izoh 422 (FR-13)

### Story 3.4: Qoralama avtomatik saqlash

As an operator,
I want yozganlarim o'z-o'zidan saqlanishini,
So that sahifadan chiqib ketsam ham ish yo'qolmasin.

**Acceptance Criteria:**

**Given** menga biriktirilgan `in_progress` Lead
**When** `PATCH /leads/{id}/draft` `{website?, lms?}` chaqiriladi
**Then** tekshiruv maydonlari yangilanadi, status o'zgarmaydi, tarixga yozuv qo'shilmaydi (FR-7)
**And** `available` `null` bo'lib qolishi mumkin — "belgilanmagan" (AR-14, FR-19)
**And** faqat bitta maydonni yuborish mumkin
**And** `last_activity_at` yangilanadi (4 soatlik hisobni siljitadi)

**Given** menga biriktirilmagan Lead
**When** qoralama saqlashga urinaman
**Then** 409 qaytadi — faqat ega qoralama yoza oladi

### Story 3.5: Admin endpointlari

As an admin,
I want qotib qolgan ishlarni ko'rish va aralasha olishni,
So that operatorni bloklamasdan nazorat qila olay.

**Acceptance Criteria:**

**Given** admin sifatida
**When** `GET /leads/attention` chaqiriladi
**Then** 2 kundan ortiq `waiting` turgan va 3 martadan ko'p qo'l almashgan Leadlar qaytadi (FR-16)

**When** `POST /leads/{id}/release` `{note}` chaqiriladi
**Then** har qanday `in_progress` Lead `waiting` bo'ladi; `note` majburiy; tarixga `admin_release` yoziladi

**When** `POST /leads/{id}/assign` `{operator_id, note}` chaqiriladi
**Then** Lead ko'rsatilgan operatorga biriktiriladi; tarixga `admin_assign` yoziladi
**And** operator bu harakatlarni chaqirsa 403 qaytadi (AR-3)

### Story 3.6: Xato javoblari bitta shaklda

As a frontend dev,
I want har bir xato javobi bir xil shaklda kelishini,
So that xatolarni ishlash kodi har endpoint uchun qaytadan yozilmasin.

**Acceptance Criteria:**

**Given** `/api/leads` ostidagi har qanday xato
**When** javob qaytadi
**Then** shakl `{code, message, ...context}` bo'ladi (AR-13)
**And** `message` operatorga ko'rsatishga tayyor o'zbekcha matn (NFR-7)
**And** `code` mashina o'qiy oladigan qiymat (`held_by_other`, `handover_required`, `invalid_transition`, `note_required`, `fields_incomplete`)

---

## Epic 4: Operator interfeysi

Bu yerda operator o'zgarishni ko'radi. 3-epik bilan birga yetkaziladi — yarim ko'chirilgan frontend ishlatib bo'lmaydi.

### Story 4.1: Beshta status rangi va badge komponentlari

As an operator,
I want har bir statusni bir qarashda farqlashni,
So that navbatni o'qish uchun o'ylab o'tirmayin.

**Acceptance Criteria:**

**Given** `index.css` dagi dizayn tokenlari
**When** yangi tokenlar qo'shiladi
**Then** beshta Lead status uchun ochiq va qorong'i mavzu qiymatlari mavjud: `new` (slate), `progress` (ko'k), `waiting` (sariq), `approved` (yashil), `rejected` (**qizil — yangi**) (UX-DR1)
**And** har bir juftlik WCAG AA kontrastdan o'tadi (NFR-6)

**Given** status ko'rsatilishi kerak bo'lgan har qanday joy
**When** komponent render qilinadi
**Then** `LeadStatusBadge` beshta Lead statusini, `FieldStatusBadge` mavjud uchta maydon holatini ko'rsatadi — ikki lug'at aralashmaydi (UX-DR2)
**And** har bir badge ikonka + rang + o'zbekcha matn bilan chiqadi (UX-DR3, NFR-6)

### Story 4.2: Data router'ga ko'chirish

As a dev,
I want `App.tsx` `createBrowserRouter` ga o'tishini,
So that navigatsiya qo'riqchisi (FR-6) ishonchli ishlasin.

**Acceptance Criteria:**

**Given** mavjud `<BrowserRouter>` konfiguratsiyasi
**When** `createBrowserRouter` + `<RouterProvider>` ga ko'chiriladi
**Then** barcha mavjud marshrutlar va rol qo'riqchilari avvalgidek ishlaydi (AR-11)
**And** `useBlocker` mavjud bo'ladi
**And** to'g'ridan-to'g'ri URL bilan kirish va sahifani yangilash ishlaydi

### Story 4.3: Navbat — beshta tab

As an operator,
I want navbatni status bo'yicha ko'rishni,
So that nima qila olishimni darhol bilay.

**Acceptance Criteria:**

**Given** navbat sahifasi
**When** operator sifatida ochiladi
**Then** beshta tab ko'rinadi: Yangi · Mening ishim · Kutilmoqda · Tasdiqlangan · Rad etilgan, har birida sanoq (FR-14, UX-DR9)
**And** admin uchun qo'shimcha "Jarayonda (hammasi)" tabi bor
**And** "Kutilmoqda" tabida har qator ostida oxirgi izoh muallifi va vaqti bilan ko'rinadi (FR-12)
**And** har tab uchun alohida bo'sh holat matni bor (UX-DR9)
**And** band qilish banneri, muddat ogohlantirishlari yo'q (FR-17)
**And** qator bosilganda Lead darhol band qilinadi va sahifa ochiladi (FR-3)
**And** boshqa operator band qilib ulgurgan bo'lsa, tushunarli xabar chiqadi va ro'yxat yangilanadi

### Story 4.4: Lead sahifasi — harakatlar, avtomatik saqlash, yakunlash

As an operator,
I want Lead sahifasida ishlashni va yozganlarim o'z-o'zidan saqlanishini,
So that ish yo'qolmasin va yakunlash ongli qaror bo'lsin.

**Acceptance Criteria:**

**Given** menga biriktirilgan Lead sahifasi
**When** maydonni o'zgartiraman
**Then** ~1 soniyada avtomatik saqlanadi va `AutosaveIndicator` "Saqlandi" ko'rsatadi (FR-7, UX-DR8)
**And** saqlash muvaffaqiyatsiz bo'lsa ma'lumot ekranda qoladi va qayta urinish taklif qilinadi
**And** "Saqlagandan so'ng faqat ruxsat bilan tahrirlanadi" dialogi yo'q (FR-18)

**Given** Lead sahifasi
**When** harakatlar paneli render qilinadi
**Then** u serverdan kelgan `available_actions` ni ko'rsatadi, o'z qoidasini takrorlamaydi (UX-DR7)
**And** "Tasdiqlash" Website yoki LMS belgilanmagan bo'lsa o'chiq turadi va sababi yozilgan bo'ladi (FR-9)
**And** "Rad etish" va "Qayta ochish" izoh so'raydi (FR-9, FR-10)
**And** hech bir maydon "qulflangan" holatda ko'rinmaydi (FR-18)

### Story 4.5: Lead tarixi paneli

As an operator,
I want Leadda nima bo'lganini ko'rishni,
So that boshqa operator qoldirgan ishni nolga tushirmasdan davom ettiray.

**Acceptance Criteria:**

**Given** Lead sahifasi
**When** tarix paneli ochiladi
**Then** hodisalar eng yangisidan boshlab ko'rinadi (FR-11, UX-DR6)
**And** har yozuvda muallif (yoki "Tizim"), vaqt, tur ikonkasi va matn bor
**And** erkin izoh qo'shish maydoni bor va yuborilgach sahifa yangilanmasdan ro'yxatga tushadi (FR-13)

### Story 4.6: Handover dialogi va navigatsiya qo'riqchisi

As an operator,
I want ishni yarim qoldirsam izoh so'ralishini,
So that mening o'rnimga o'tirgan operator qayerda to'xtaganimni bilsin.

**Acceptance Criteria:**

**Given** `in_progress` Lead sahifasidaman
**When** orqaga qaytish, yon menyu, boshqa Lead yoki sahifani yangilashga urinaman
**Then** `HandoverDialog` chiqadi (FR-6, UX-DR5)
**And** izoh bo'sh yoki faqat bo'shliq bo'lsa asosiy tugma o'chiq turadi (FR-5)
**And** "Ishda qolish" tanlansa sahifada qolaman va hech nima o'zgarmaydi
**And** tasdiqlansa Lead `waiting` bo'ladi va navigatsiya davom etadi

**Given** navbatdan boshqa Leadni bosaman
**When** menda `in_progress` Lead bor
**Then** o'sha dialog chiqadi va tasdiqlangach ikkala o'tish birga bajariladi (FR-5)

**Given** izoh maydoni bo'sh qoldirilgan
**When** yuborishga urinaman
**Then** xato `aria-live` orqali e'lon qilinadi va maydonga bog'lanadi (UX-DR17, NFR-6)

### Story 4.7: "Mening ishlarim"

As an operator,
I want o'z ishlarimni bir joyda ko'rishni,
So that nima qilganim va nima qolganini bilay.

**Acceptance Criteria:**

**Given** eski "Mening so'rovlarim" sahifasi
**When** u "Mening ishlarim" ga almashtiriladi
**Then** joriy `in_progress` Lead va yaqinda yakunlanganlar ko'rinadi (UX-DR11)
**And** so'rovlar oqimiga oid hech narsa qolmaydi (FR-17, FR-18)

---

## Epic 5: Jonli yangilanish va admin nazorati

Navbat o'zi yangilanadi va admin bloklamasdan nazorat qiladi.

### Story 5.1: Lead hodisalarini WebSocket orqali uzatish

As an operator,
I want navbatning o'zi yangilanishini,
So that boshqa kim allaqachon olgan Leadni bosib xato olmayin.

**Acceptance Criteria:**

**Given** mavjud WebSocket kanali (AD-9)
**When** Lead band qilinadi yoki bo'shaydi
**Then** hodisa ulangan operatorlarga uzatiladi va ochiq navbat yangilanadi (FR-15)
**And** yangi infratuzilma qo'shilmaydi — mavjud `ConnectionManager` ishlatiladi (AR-4)
**And** ulanish uzilsa navbat davriy yangilanishga qaytadi va ishlashda davom etadi

### Story 5.2: Admin boshqaruv paneli bloklari

As an admin,
I want diqqat talab qiladigan ishlarni darhol ko'rishni,
So that qotib qolgan Leadlarni o'zim topib o'tirmayin.

**Acceptance Criteria:**

**Given** admin boshqaruv paneli
**When** ochiladi
**Then** status bo'yicha taqsimot ko'rinadi (UX-DR12)
**And** "Uzoq turgan ishlar" (2 kundan ortiq `waiting`) bloki bor
**And** "Ko'p qo'l almashgan" (3 martadan ko'p) bloki bor (FR-16)
**And** har element bosilganda o'sha Lead sahifasiga olib boradi

### Story 5.3: "Barcha Leadlar" ekrani

As an admin,
I want har qanday Leadni ko'rish va kerak bo'lsa aralasha olishni,
So that operatorni bloklamasdan boshqara olay.

**Acceptance Criteria:**

**Given** yangi admin ekrani
**When** ochiladi
**Then** har qanday statusdagi Lead egasi bilan ko'rinadi (UX-DR13)
**And** `in_progress` Leadni majburan bo'shatish mumkin, sabab majburiy (FR-16)
**And** Leadni boshqa operatorga biriktirish mumkin, sabab majburiy
**And** har aralashuv tarixga yoziladi va tegishli operatorga bildirishnoma boradi

### Story 5.4: Bildirishnomalarni tozalash

As an operator,
I want faqat menga tegishli bildirishnomalarni olishni,
So that yo'q bo'lib ketgan oqimlar haqidagi xabarlar chalkashtirmasin.

**Acceptance Criteria:**

**Given** bildirishnoma `link` taksonomiyasi
**When** yangilanadi
**Then** `permission-request:` va `claim-request:` prefikslari olib tashlanadi (AR-4, UX-DR15)
**And** `lead:{company_id}` prefiksi Lead sahifasiga olib boradi
**And** qoladigan bildirishnomalar: ishingiz majburan bo'shatildi, sizga Lead biriktirildi
**And** `resolveLink()` da qo'llab-quvvatlanmaydigan prefiks kelsa xato bermaydi (eski yozuvlar bazada qoladi)

---

## Epic 6: Eski mexanizmni olib tashlash

Faqat 4- va 5-epiklar ishlagani tasdiqlangach bajariladi. Jadvallar bazada arxiv sifatida qoladi (AR-12) — bu yerda faqat kod o'chiriladi.

### Story 6.1: Backend — claim va permission oqimlarini o'chirish

As a dev,
I want ishlatilmaydigan route va servislar o'chirilishini,
So that kod bazasida ikkita raqobatdosh ish oqimi qolmasin.

**Acceptance Criteria:**

**Given** kod bazasi
**When** tozalash bajariladi
**Then** `api/routes/claims.py`, `api/routes/claim_requests.py`, `api/routes/permission_requests.py`, `services/claims.py` o'chiriladi (FR-17, FR-18)
**And** `api/routes/reviews.py` dagi eski endpointlar o'chiriladi (AR-10)
**And** `main.py` dagi router ro'yxatidan tegishli qatorlar olib tashlanadi
**And** `company_claims`, `claim_requests`, `permission_requests` jadvallari va `company_reviews.locked` **o'chirilmaydi** (AR-12)
**And** hech bir qolgan kod `locked` ni o'qimaydi yoki yozmaydi

### Story 6.2: Frontend — so'rov ekranlarini o'chirish

As an operator,
I want interfeysda ishlamaydigan tugmalar qolmasligini,
So that chalkashmayin.

**Acceptance Criteria:**

**Given** frontend kod bazasi
**When** tozalash bajariladi
**Then** `claim-banner.tsx`, `defer-dialog.tsx`, `admin/claim-requests.tsx`, `admin/permission-requests.tsx` o'chiriladi (UX-DR14)
**And** `app-shell.tsx` dagi `ADMIN_NAV` va `OPERATOR_NAV` yangilanadi
**And** `lib/types.ts` dan `Claim`, `MyClaims`, `ClaimRequestItem`, `ClaimBlockError`, `PermissionRequestItem` olib tashlanadi
**And** o'chirilgan marshrutlarga to'g'ridan-to'g'ri kirish bosh sahifaga yo'naltiradi

### Story 6.3: Yakuniy tekshiruv

As a dev,
I want tozalashdan keyin tizim to'liq ishlashini,
So that o'chirish jarayonida hech narsa buzilmagani aniq bo'lsin.

**Acceptance Criteria:**

**Given** tozalash tugagan
**When** backend testlari va frontend qurilishi ishga tushiriladi
**Then** hammasi xatosiz o'tadi
**And** butun operator oqimi uchdan uchgacha ishlaydi: boshlash → qoldirish (izoh bilan) → boshqa operator olishi → yakunlash → qayta ochish
**And** kod bazasida `claim`, `defer`, `permission_request`, `locked` so'zlariga ishlaydigan havola qolmaydi

---

## Epic 7: Hujjatlarni moslashtirish

Hujjat va kod bir-biriga mos qoladi. Istalgan paytda bajarilishi mumkin.

### Story 7.1: Arxitektura hujjatini yangilash

As a dev,
I want arxitektura hujjati haqiqatni aks ettirishini,
So that keyingi ishlar eskirgan qaror ustiga qurilmasin.

**Acceptance Criteria:**

**Given** `ARCHITECTURE-SPINE.md`
**When** yangilanadi
**Then** AD-8 (qulf modeli) va AD-11 (claim/muddat) bekor deb belgilanadi, sababi va o'rnini bosgan qaror ko'rsatiladi
**And** yangi AD qo'shiladi: Lead status mashinasi, eksklyuziv biriktirish, hisoblangan avtomatik bo'shatish, o'zgarmas tarix
**And** AD-9 ning `link` taksonomiyasi yangilanadi
**And** "Deferred" bo'limidagi hal bo'lgan bandlar (deaktivatsiya qilingan operatorning claim'i, cheksiz deferred claim to'planishi) yopiladi

### Story 7.2: UX hujjatlarini yangilash

As a designer,
I want UX hujjatlari yangi oqimni tasvirlashini,
So that keyingi dizayn ishi eski naqshni takrorlamasin.

**Acceptance Criteria:**

**Given** `DESIGN.md`
**When** yangilanadi
**Then** "to'rtinchi status rangini o'ylab topmang" qoidasi beshta rangli Lead status lug'ati bilan almashtiriladi (UX-DR4)
**And** `status-rejected` qizil tokeni va uning kontrast qiymatlari yoziladi
**And** "Locked-field indicator" komponenti olib tashlanadi

**Given** `EXPERIENCE.md`
**When** yangilanadi
**Then** status lug'ati, "Saqlash ikkala maydonni birga yuboradi" qoidasi va ruxsat so'rash oqimi olib tashlanadi (UX-DR19)
**And** Lead status oqimi, qoralama va Handover naqshlari yoziladi
**And** yangi foydalanuvchi yo'llari PRD dagi UJ-1…UJ-5 bilan mos keladi
