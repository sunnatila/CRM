---
title: OperatorDesk — Lead Workflow v2
created: 2026-08-20
updated: 2026-08-20
status: final
---

# PRD: OperatorDesk — Lead Workflow v2

## 0. Hujjat maqsadi

Bu PRD OperatorDesk'ning operator ish oqimini boshdan qayta loyihalaydi. U mavjud tizimni yangi funksiya bilan kengaytirmaydi — **mavjud mexanizmni yengilroq mexanizm bilan almashtiradi**. O'quvchilar: PM, arxitektor (`ARCHITECTURE-SPINE.md` AD-8 va AD-11 ni qayta yozishi kerak), UX (`EXPERIENCE.md` status lug'ati va ekran oqimlarini yangilashi kerak), dev.

Tuzilishi: §3 Lug'at butun hujjat uchun majburiy so'z boyligi; §4 xususiyatlar guruhlangan, FR-lar ular ichida global raqamlangan; texnik "qanday" `addendum.md` ga chiqarilgan; taxminlar `[ASSUMPTION]` bilan belgilangan va §12 da indekslangan.

Mavjud kirish hujjatlari: `_bmad-output/planning-artifacts/architecture/architecture-parsing-project-2026-07-26/ARCHITECTURE-SPINE.md` va `_bmad-output/planning-artifacts/ux-designs/ux-parsing-project-2026-07-28/{EXPERIENCE,DESIGN}.md`. Bu PRD ular ustiga quriladi va ularning qaysi qarorlari bekor bo'lishini aniq nomlaydi.

---

## 1. Vizyon

OperatorDesk operatorlarga kompaniyalar ma'lumotini telefon orqali tekshirishga yordam berish uchun qurilgan. Amalda esa u operatorlarni **ishlashdan to'xtatib qo'ydi**. Sabab bitta: tizim *ishonchsizlik* ustiga qurilgan. Har bir odatiy harakat — boshqa ishga o'tish, muddatni cho'zish, o'z xatosini tuzatish — admin ruxsatini talab qiladi, va ruxsat kelguncha operator butunlay bloklanadi. Muddati o'tgan bitta ish operatorning butun kunini to'xtatadi.

Lead Workflow v2 bu almashtirishni amalga oshiradi: **ruxsat o'rniga ko'rinuvchanlik**. Operator xohlagan leadni oladi, xohlagan payt qo'yib turadi, o'z xatosini o'zi tuzatadi — hech kimdan so'ramasdan. Buning evaziga tizim bitta narsani qat'iy talab qiladi: **ishni yarim tashlab ketayotganda izoh**. Chunki keyingi operator o'sha leadni ochganda birinchi ko'radigan narsa — oldingi operator qayerda to'xtaganini aytuvchi jumla bo'lishi kerak.

Lead endi beshta aniq holatdan birida bo'ladi — **Yangi, Jarayonda, Kutilmoqda, Tasdiqlangan, Rad etilgan** — va bu holat butun jamoaga bir xil ko'rinadi. Admin nazorati qulflardan emas, to'liq tarixdan keladi: har bir status o'zgarishi, har bir izoh, har bir tahrir kim va qachon qilgani bilan yozib boriladi.

---

## 2. Maqsadli foydalanuvchi

### 2.1 Bajarilishi kerak bo'lgan ishlar (JTBD)

**Operator:**
- Navbatdan keyingi ishlashim mumkin bo'lgan leadni topib, darhol boshlash — hech kimdan ruxsat so'ramasdan.
- Mijoz javob bermasa yoki "keyinroq qo'ng'iroq qiling" desa, ishni **yo'qotmasdan** qo'yib turish va boshqasiga o'tish.
- Boshqa operator qoldirgan leadni ochganimda, uni qaytadan nolga tushirmasdan davom ettirish — nima qilingani va nima qolgani ko'rinib turishi kerak.
- O'zim yozgan xatoni o'zim tuzatish, kunlar davomida admin javobini kutmasdan.
- Kunim oxirida qancha ish bajarganimni ko'rish.

**Admin:**
- Hozir kim nima ustida ishlayotganini bir qarashda ko'rish.
- Qotib qolgan yoki qo'ldan qo'lga o'tib yurgan leadlarni topish.
- Har bir lead bo'yicha "kim, qachon, nima qildi" savoliga tarixdan javob olish.
- Operatorni bloklamasdan, kerak bo'lganda aralashish (ishni majburan bo'shatish, boshqa operatorga berish).

### 2.2 Bu kim uchun emas (v1)

- **Mijozning o'zi uchun emas** — bu ichki asbob, tashqi kirish yo'q.
- **Sotuv menejeri uchun emas** — bu lead sifatini tekshirish asbobi, bitim quvuri (sales pipeline) emas. Bitim summasi, bosqichlari, prognozi yo'q.
- **Skrap boshqaruvi uchun emas** — kompaniyalarni yig'ish SQLAdmin panelida qoladi (AD-2/AD-3), OperatorDesk ularni faqat o'qiydi.

### 2.3 Asosiy foydalanuvchi yo'llari

> **UJ-1. Malika navbatdan lead olib, uni tasdiqlaydi.**
> Malika smenaning boshida "Yangi" tabini ochadi — 140 ta lead. Birinchisini bosadi. Bosish bilanoq lead **Jarayonda**ga o'tadi, uning nomiga biriktiriladi va "Yangi" ro'yxatidan yo'qoladi — Bekzod endi uni ko'rmaydi ham. Malika kompaniyaga qo'ng'iroq qiladi, Website "mavjud", LMS "yo'q" deb belgilaydi, izohga "sayt bor, LMS ishlatmaydi, kelgusi yilga rejalari bor" deb yozadi. Har bir yozuv fon rejimida avtomatik saqlanadi. "Tasdiqlash" tugmasini bosadi. Lead **Tasdiqlangan**ga o'tadi, band bo'shaydi, Malika navbatga qaytadi. **Chekka holat:** LMS ni belgilamay "Tasdiqlash"ni bossa, tugma o'chiq turadi va tagida "Tasdiqlash uchun Website va LMS belgilanishi kerak" deb yozilgan bo'ladi.

> **UJ-2. Mijoz javob bermaydi — Malika izoh qoldirib boshqasiga o'tadi.**
> Malika uchinchi marta qo'ng'iroq qiladi, javob yo'q. Navbatga qaytib boshqa leadni bosadi. Ekranga bitta dialog chiqadi: "Bu ishni qoldiryapsiz. Qayerda to'xtadingiz?" — izoh maydoni bo'sh bo'lsa "Davom etish" tugmasi bosilmaydi. Malika "3 marta qo'ng'iroq qildim, javob yo'q. Ertalab 9–10 orasida urinib ko'rish kerak" deb yozadi va davom etadi. Eski lead **Kutilmoqda**ga o'tadi, band bo'shaydi, izoh lead tarixining eng ustiga tushadi. Yangi lead **Jarayonda**ga o'tadi. Bitta dialog, ikkita bosish — muddat yo'q, admin so'rovi yo'q, blokirovka yo'q.

> **UJ-3. Bekzod Malika qoldirgan ishni davom ettiradi.**
> Bekzod "Kutilmoqda" tabini ochadi. Har bir qatorda oxirgi izoh ko'rinib turadi: "Malika, 2 soat oldin: 3 marta qo'ng'iroq qildim, javob yo'q. Ertalab 9–10 orasida urinib ko'rish kerak". Bekzod o'shani bosadi, lead unga biriktiriladi. Ekranda Malika belgilab ketgan maydonlar va butun tarix turibdi — u nolga tushmaydi, davom ettiradi. Qo'ng'iroq qiladi, mijoz javob beradi, Bekzod ma'lumotni to'ldirib tasdiqlaydi. Tarixda ikkala operatorning ham hissasi qoladi.

> **UJ-4. Malika o'z xatosini o'zi tuzatadi.**
> Yarim soatdan keyin Malika ertalab tasdiqlagan leadda LMS ni noto'g'ri belgilaganini payqaydi. "Tasdiqlangan" tabidan o'shani topadi, "Qayta ochish" bosadi. Dialog sabab so'raydi: "LMS ni xato belgilabman, mijoz aytgani boshqa edi". Lead **Jarayonda**ga qaytadi, Malika tuzatib qayta tasdiqlaydi. **Eski tizimda bu admin ruxsatini talab qilar va kunlab kutar edi** — endi 20 soniya, va tarixda tuzatish sababi ham turadi.

> **UJ-5. Aziz (admin) qotib qolgan ishni ko'radi.**
> Aziz boshqaruv panelini ochadi. "Uzoq turgan ishlar" bloki: 4 ta lead 2 kundan beri **Kutilmoqda**da, 1 tasi 3 marta qo'ldan qo'lga o'tgan. Uchinchisini ochadi — tarixdan ko'rinadiki, uch operator ham bir xil raqamga qo'ng'iroq qilib bir xil natijaga kelgan. Azizning o'zi bu Leadni yakunlamaydi — u ish qiluvchi emas, kuzatuvchi. Buning o'rniga uni tajribali operatorga biriktiradi va izohga "uchta urinish behuda ketdi, boshqa raqam topish kerak" deb yozadi. Hech kim bloklanmagan edi, hech kim ruxsat kutmagan edi — Aziz shunchaki ko'rgani uchun aralashdi.

---

## 3. Lug'at

Bu atamalar butun hujjatda va barcha quyi oqim ishlarida (UX, arxitektura, epiklar, kod) **aynan shu shaklda** ishlatiladi. Sinonim kiritish — intizom buzilishi.

- **Lead** — bitta kompaniya yozuvi, operator nuqtai nazaridan. Bitta `companies` qatori ↔ bitta Lead (1:1). Kod darajasida `companies` jadvali skrap domeniga tegishli bo'lib qoladi; Lead holati alohida jadvalda yashaydi.
- **Lead status** — Leadning ish oqimidagi holati. Aynan beshta qiymat, boshqasi yo'q: **Yangi**, **Jarayonda**, **Kutilmoqda**, **Tasdiqlangan**, **Rad etilgan**.
- **Yangi** (`new`) — hech kim hali tegmagan Lead. Hech kimga biriktirilmagan.
- **Jarayonda** (`in_progress`) — aynan bitta operatorga biriktirilgan, hozir ishlanayotgan Lead. **Eksklyuziv**: boshqa hech bir operatorga ko'rinmaydi va ochilmaydi.
- **Kutilmoqda** (`waiting`) — boshlangan, lekin yakunlanmagan va hozir hech kimga biriktirilmagan Lead. Har bir operator ola oladi. Har doim kamida bitta **Handover izohi**ga ega.
- **Tasdiqlangan** (`approved`) — ma'lumot tekshirilgan va yakunlangan Lead. Hech kimga biriktirilmagan.
- **Rad etilgan** (`rejected`) — ishlash mumkin bo'lmagan Lead (aloqa yo'q, mijoz mos emas, mijoz rad etdi). Hech kimga biriktirilmagan.
- **Egasi** (`assigned_to`) — Leadni hozir ushlab turgan operator. Faqat **Jarayonda** statusidagi Leadning egasi bo'ladi; qolgan to'rt statusda ega bo'sh.
- **Handover izohi** — operator **Jarayonda**dan chiqayotganda majburiy yoziladigan matn: ish qayerda to'xtaganini keyingi operatorga tushuntiradi. Bo'sh bo'lishi mumkin emas.
- **Lead tarixi** — Lead ustidagi barcha hodisalarning vaqt bo'yicha tartiblangan ro'yxati: status o'zgarishlari, izohlar, maydon tahrirlari, avtomatik bo'shatishlar. O'zgartirilmaydi va o'chirilmaydi.
- **Tekshiruv maydoni** — Lead ichidagi ikkita ma'lumot birligi: **Website** va **LMS**. Har biri uchta qiymatdan biri: *mavjud*, *yo'q*, *belgilanmagan*, plus ixtiyoriy izoh.
- **Qoralama** (`draft`) — **Jarayonda** statusidagi Leadning hali yakunlanmagan tekshiruv maydonlari. Avtomatik saqlanadi, status o'zgartirmaydi.
- **Avtomatik bo'shatish** — **Jarayonda** Lead 4 soat davomida tegilmasa, tizim uni **Kutilmoqda**ga o'tkazadi va tarixga tizim izohini yozadi.
- **Operator** / **Admin** — `users.role` dagi ikkita rol (AD-7 o'zgarishsiz qoladi).

---

## 4. Xususiyatlar

### 4.1 Lead status modeli

**Tavsif.** Butun ish oqimi bitta status mashinasiga siqiladi. Har bir Lead beshta statusdan aynan bittasida bo'ladi, va statuslar orasidagi o'tishlar quyidagi jadval bilan cheklangan. Bu mavjud `company_reviews.locked` bayrog'i (AD-8), `company_claims.status` (AD-11) va maydon darajasidagi `pending/confirmed/absent` lug'atining — uchalasining ham — o'rnini bosadi.

Ruxsat etilgan o'tishlar:

| Qayerdan | Qayerga | Kim ishga tushiradi | Izoh |
|---|---|---|---|
| Yangi | Jarayonda | Operator ("Ishni boshlash") | shart emas |
| Kutilmoqda | Jarayonda | Operator ("Davom ettirish") | shart emas |
| Tasdiqlangan / Rad etilgan | Jarayonda | Operator ("Qayta ochish") | **majburiy** |
| Jarayonda | Kutilmoqda | Operator ("Qoldirish" yoki boshqa Leadga o'tish) | **majburiy** (Handover izohi) |
| Jarayonda | Kutilmoqda | Tizim (4 soat harakatsizlik) | tizim izohi avtomatik |
| Jarayonda | Kutilmoqda | Admin (majburan bo'shatish) | **majburiy** |
| Jarayonda | Tasdiqlangan | Operator ("Tasdiqlash") | ixtiyoriy |
| Jarayonda | Rad etilgan | Operator ("Rad etish") | **majburiy** (sabab) |

Ro'yxatda yo'q har qanday o'tish taqiqlangan. Jumladan: **Yangi**dan to'g'ridan-to'g'ri **Tasdiqlangan**ga o'tib bo'lmaydi — ish har doim **Jarayonda**dan o'tadi, shunda tarixda kim bajargani qoladi.

**Funksional talablar:**

#### FR-1: Beshta status, boshqasi yo'q

Tizim har bir Leadni aynan beshta Lead statusdan birida saqlaydi. UJ-1, UJ-2, UJ-3 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Hech bir Lead statussiz bo'la olmaydi; hech qachon tegilmagan Lead **Yangi** deb o'qiladi.
- Ro'yxatdagi har bir status uchun aniq rang + ikonka + o'zbekcha matn mavjud (rang yolg'iz o'zi ma'no tashimaydi — a11y).
- API `status` maydoniga beshtadan tashqari qiymat kelsa, 422 qaytaradi.

#### FR-2: O'tishlar jadval bilan cheklangan

Tizim yuqoridagi jadvalda bo'lmagan har qanday status o'tishini rad etadi.

**Natijalar (tekshiriladigan):**
- Ruxsat etilmagan o'tish urinishi 409 va tushunarli o'zbekcha xabar qaytaradi.
- O'tish qoidalari bitta joyda (serverda) yashaydi; frontend ularni takrorlamaydi, faqat serverdan kelgan mumkin bo'lgan harakatlar ro'yxatini ko'rsatadi.
- Har bir muvaffaqiyatli o'tish Lead tarixiga bitta yozuv qo'shadi (FR-11).

**Doiradan tashqarida:** foydalanuvchi tomonidan sozlanadigan status yoki o'tishlar. Beshta status qattiq belgilangan.

---

### 4.2 Eksklyuziv band qilish va ishqalanishsiz almashish

**Tavsif.** Ikkita operator bir vaqtda bir mijozga qo'ng'iroq qilmasligi kerak — bu qat'iy talab. Shuning uchun **Jarayonda** Lead egasidan boshqa hech bir operatorga **umuman ko'rinmaydi**: navbatning hech bir tabida, hech bir qidiruv natijasida chiqmaydi, to'g'ridan-to'g'ri URL bilan ham ochilmaydi.

Shu bilan birga, band qilish operatorni hech qachon bloklamaydi. Operatorda bir vaqtda bitta **Jarayonda** Lead bo'ladi — lekin boshqasiga o'tish bitta dialog va bitta izoh, xolos. Muddat kiritish yo'q, admin tasdig'i yo'q, "muddati o'tdi" holati yo'q. Aynan shu joyda eski tizim buzilgan edi.

`[ASSUMPTION: bir operatorda bir vaqtda faqat bitta Jarayonda Lead bo'lishi kerak degan qoida saqlanadi. Bu to'g'ridan-to'g'ri tasdiqlanmagan — u "boshqa ishga o'tmoqchi bo'lsa izoh so'ralsin" talabidan kelib chiqadi: agar operator bir vaqtda beshta Leadni ochiq ushlab tursa, "qoldirish" degan payt umuman kelmaydi va Handover izohi hech qachon so'ralmaydi. Ya'ni bu cheklov v2 ning asosiy talabini ushlab turuvchi ustun, ixtiyoriy qoida emas.]`

**Funksional talablar:**

#### FR-3: "Ishni boshlash" darhol band qiladi

Operator **Yangi** yoki **Kutilmoqda** Leadni bosganda, Lead darhol **Jarayonda**ga o'tadi va unga biriktiriladi — alohida tasdiqlash bosqichisiz. UJ-1, UJ-3 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Bosishdan keyin Lead o'sha zahoti "Yangi"/"Kutilmoqda" ro'yxatidan chiqadi va "Mening ishim" ga tushadi.
- Ikki operator bir Leadni bir vaqtda bosса, birinchisi oladi; ikkinchisi 409 `held_by_other` oladi va navbat avtomatik yangilanadi.
- Band qilish `assigned_to` va `assigned_at` ni yozadi; `last_activity_at` shu paytdan boshlab yuritiladi.

#### FR-4: Boshqaning ishi ko'rinmaydi

Operator boshqa operatorga biriktirilgan **Jarayonda** Leadni hech bir yo'l bilan ko'ra olmaydi.

**Natijalar (tekshiriladigan):**
- `GET /leads` operator uchun boshqaning **Jarayonda** Leadlarini qaytarmaydi (hech bir status filtri, qidiruv yoki kategoriya bilan).
- `GET /leads/{id}` boshqaning **Jarayonda** Leadi uchun 404 qaytaradi (403 emas — mavjudligini ham oshkor qilmaydi).
- Admin bundan mustasno: admin barcha Leadlarni egasi ismi bilan birga ko'radi.

#### FR-5: Boshqa ishga o'tish — bitta dialog, majburiy izoh

Operator **Jarayonda** Leadi bor holda boshqa Leadni boshlamoqchi bo'lsa, tizim bitta dialogda Handover izohini so'raydi; izoh berilgach ikkala o'tish bitta amalda bajariladi. UJ-2 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Izoh maydoni bo'sh yoki faqat bo'shliqdan iborat bo'lsa, "Davom etish" tugmasi o'chiq turadi.
- Tasdiqlangach: eski Lead → **Kutilmoqda** (ega bo'shaydi, izoh tarixga yoziladi), yangi Lead → **Jarayonda**. Ikkalasi bitta tranzaksiyada; yangisini band qilib bo'lmasa, eskisi ham o'zgarmaydi.
- Muddat, kun soni, admin so'rovi yoki tasdiqlash kutish — hech biri yo'q.
- Operator dialogni bekor qilsa, hech nima o'zgarmaydi va u joriy Leadida qoladi.

#### FR-6: Ishdan chiqishda ushlab qolish (navigatsiya qo'riqchisi)

Operator **Jarayonda** Lead sahifasidan chiqmoqchi bo'lganda — orqaga qaytish, yon menyu, boshqa Lead, sahifani yangilash — tizim FR-5 dagi bir xil dialogni ko'rsatadi. UJ-2 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Ilova ichidagi har qanday navigatsiya ushlab qolinadi; izohsiz o'tib bo'lmaydi.
- "Qoldirish" ni tanlasa → **Kutilmoqda**; "Ishda qolish" ni tanlasa → sahifada qoladi.
- Brauzer yorlig'ini yopish yoki quvvat o'chishi — brauzer bu yerda izohni majburlay olmaydi; bu holat FR-8 (avtomatik bo'shatish) bilan qoplanadi.

**Doiradan tashqarida:** brauzer yopilishida izohni majburlash — texnik jihatdan imkonsiz.

---

### 4.3 Qoralama va yakunlash

**Tavsif.** Eski tizimda ma'lumot faqat "Saqlash" bosilganda yoziladi, va o'sha zahoti abadiy qulflanadi. Ikkala qism ham noto'g'ri: yarim ishlangan ma'lumot yo'qoladi, yakunlangan ma'lumot esa tuzatib bo'lmaydigan bo'lib qoladi.

v2 da **Jarayonda** Leadning tekshiruv maydonlari avtomatik saqlanadi — status o'zgartirmasdan, tasdiqlash so'ramasdan. Yakunlash alohida, ongli harakat: **Tasdiqlash** yoki **Rad etish**. Qulf yo'q — istalgan Leadni qayta ochib tuzatish mumkin, faqat sabab yozib.

**Funksional talablar:**

#### FR-7: Tekshiruv maydonlari avtomatik saqlanadi

**Jarayonda** Lead egasining tekshiruv maydonlaridagi o'zgarishlari fon rejimida saqlanadi. UJ-1 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- O'zgarishdan keyin ~1 soniya ichida saqlanadi; ekranda "Saqlandi" indikatori ko'rinadi.
- Saqlash muvaffaqiyatsiz bo'lsa, ma'lumot ekranda qoladi va qayta urinish taklif qilinadi — hech qachon jimgina yo'qolmaydi.
- Qoralama saqlash **status o'zgartirmaydi** va Lead tarixiga alohida yozuv qo'shmaydi (tarixni shovqinga to'ldirmaslik uchun) — faqat `last_activity_at` yangilanadi.
- Website va LMS mustaqil: biri belgilanib, ikkinchisi belgilanmagan holda qolishi mumkin.

#### FR-8: Avtomatik bo'shatish (4 soat)

**Jarayonda** Lead 4 soat davomida hech qanday harakatsiz qolsa, tizim uni **Kutilmoqda**ga o'tkazadi.

**Natijalar (tekshiriladigan):**
- `last_activity_at` dan 4 soat o'tgan **Jarayonda** Lead hech kimga band hisoblanmaydi va "Kutilmoqda" ro'yxatida chiqadi.
- Tarixga tizim yozuvi tushadi: "Avtomatik bo'shatildi — 4 soat harakatsizlik", muallifi sifatida tizim ko'rsatiladi.
- Qoralama ma'lumot **saqlanib qoladi** — bo'shatish ma'lumotni o'chirmaydi.
- Eski egasi qaytib kelsa, uni oddiy tarzda qayta ola oladi (agar boshqa kim olib ulgurmagan bo'lsa).

#### FR-9: Yakunlash — Tasdiqlash va Rad etish

Operator **Jarayonda** Leadni **Tasdiqlangan** yoki **Rad etilgan** holatiga o'tkazib yakunlaydi. Admin tasdig'i talab qilinmaydi. UJ-1 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- **Tasdiqlash** faqat Website va LMS ikkalasi ham belgilangan bo'lsa mumkin; aks holda tugma o'chiq va sababi ko'rsatilgan bo'ladi.
- **Rad etish** har doim mumkin, lekin sabab izohi majburiy.
- Yakunlashda ega bo'shaydi va Lead tegishli tabga o'tadi.
- Ikkala o'tish ham Lead tarixiga yakunlovchi, natija va izoh bilan yoziladi.

#### FR-10: Qayta ochish — ruxsatsiz, lekin izsiz emas

Har qanday operator **Tasdiqlangan** yoki **Rad etilgan** Leadni qayta ocha oladi, sabab yozgan holda. UJ-4 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Qayta ochish sababi bo'sh bo'lishi mumkin emas.
- Qayta ochilgan Lead **Jarayonda**ga o'tadi va so'ragan operatorga biriktiriladi.
- Oldingi tekshiruv ma'lumoti saqlanib qoladi va tahrirlanadigan holatga qaytadi.
- Tarixda qayta ochish alohida hodisa sifatida ko'rinadi: kim, qachon, nega.
- **`permission_requests` orqali ruxsat so'rash oqimi umuman ishlatilmaydi** — bu FR uning o'rnini bosadi.

**Eslatma:** `[NOTE FOR PM]` Bu PRD dagi eng jiddiy savdo. Qulf ma'lumot sifatini *oldindan* himoya qilar edi — hech kim tegolmasa, hech kim buzolmaydi ham. Uni olib tashlash bilan tizim boshqa himoyaga o'tadi: har bir o'zgarish kim tomonidan va nega qilingani ko'rinib turadi (FR-11). Bu savdo ongli — chunki qulf amalda ma'lumotni himoya qilmas, balki *xatoni muzlatib qo'yar* edi: operator o'z xatosini ko'rib turib, kunlab tuzatolmay o'tirar edi. Lekin xavf haqiqiy va u SM-C1 orqali kuzatilishi shart: qayta ochilgan Leadlar ulushi keskin oshsa, demak yakunlash juda yengil kechyapti va bu joyga ma'lum darajada ishqalanish qaytarilishi kerak bo'ladi (masalan, boshqa operator yakunlagan Leadni qayta ochishda ogohlantirish). Birinchi oydan keyin qayta ko'rilsin.

---

### 4.4 Lead tarixi

**Tavsif.** Bu v2 ning nazorat mexanizmi. Eski tizim nazoratni qulf orqali amalga oshirar edi (hech kim tegolmaydi); v2 uni to'liq tarix orqali amalga oshiradi (hamma tegishi mumkin, lekin hech narsa yashirin qolmaydi). Handover izohi ham shu yerda yashaydi — bu alohida mexanizm emas, tarixning bir turi.

**Funksional talablar:**

#### FR-11: Har bir hodisa yoziladi

Tizim Lead ustidagi har bir muhim hodisani o'zgarmas tarix yozuvi sifatida saqlaydi. UJ-3, UJ-5 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Yoziladigan hodisa turlari: status o'zgarishi (eski va yangi status bilan), Handover izohi, erkin izoh, yakunlash, qayta ochish, avtomatik bo'shatish, admin aralashuvi.
- Har bir yozuvda: kim (yoki tizim), qachon, qaysi tur, izoh matni.
- Tarix yozuvlari **tahrirlanmaydi va o'chirilmaydi** — hech bir API bunga yo'l bermaydi.
- Lead sahifasida tarix eng yangisidan boshlab ko'rinadi.

#### FR-12: Oxirgi izoh ro'yxatda ko'rinadi

**Kutilmoqda** statusidagi Leadlar ro'yxatida har bir qator ostida oxirgi Handover izohi ko'rinadi. UJ-3 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- Operator Leadni ochmasdan turib "bu yerda nima bo'lgan" savoliga javob oladi.
- Izoh muallifi va vaqti ko'rsatiladi ("Malika, 2 soat oldin").
- Uzun izoh qisqartiriladi, to'lig'i Lead sahifasida.

#### FR-13: Erkin izoh

Operator **Jarayonda** Leadga status o'zgartirmasdan izoh qo'sha oladi.

**Natijalar (tekshiriladigan):**
- Izoh darhol tarixga tushadi va sahifa yangilanmasdan ko'rinadi.
- Bo'sh izoh qabul qilinmaydi.

---

### 4.5 Navbat va ko'rinuvchanlik

**Tavsif.** Navbat ekrani status bo'yicha tablarga bo'linadi — operator "hozir nima qilishim mumkin" savoliga bir qarashda javob oladi. Eski navbatda band qilingan Leadlar butunlay yo'qolar edi va operator ularning taqdirini bilmas edi; endi o'zining ishi va jamoaning kutilayotgan ishlari ko'rinib turadi.

**Funksional talablar:**

#### FR-14: Status bo'yicha tablar va sanoq

Navbat ekrani Leadlarni status bo'yicha tablarga ajratadi, har birida joriy soni bilan.

**Natijalar (tekshiriladigan):**
- Operator tablari: **Yangi** · **Mening ishim** (o'zining **Jarayonda** Leadi) · **Kutilmoqda** · **Tasdiqlangan** · **Rad etilgan**.
- Admin tablari: yuqoridagilar plus **Jarayonda (hammasi)** — egasi ismi bilan.
- Sanoqlar ro'yxat bilan bitta so'rovda keladi (hozirgi ikkita alohida so'rov o'rniga).
- Nomi va kategoriya bo'yicha filtrlar har bir tabda ishlaydi (mavjud xatti-harakat saqlanadi, AD-12).

#### FR-15: Navbat jonli yangilanadi

Bir operator Leadni band qilganda yoki bo'shatganda, boshqa operatorlarning ochiq navbati o'zi yangilanadi.

**Natijalar (tekshiriladigan):**
- Mavjud WebSocket kanali (AD-9) status o'zgarishlarini uzatadi — yangi infratuzilma qo'shilmaydi.
- Ulanish uzilsa, navbat davriy yangilanishga qaytadi va ishlashda davom etadi.
- Natija: operator allaqachon band qilingan Leadni bosib 409 olishi kamayadi.

#### FR-16: Admin nazorat ko'rinishi

Admin boshqaruv panelida diqqat talab qiladigan Leadlarni ko'radi. UJ-5 ni amalga oshiradi.

**Natijalar (tekshiriladigan):**
- "Uzoq turgan ishlar": 2 kundan ortiq **Kutilmoqda**da turgan Leadlar. `[ASSUMPTION: chegara 2 kun]`
- "Ko'p qo'l almashgan": 3 martadan ko'p qo'ldan qo'lga o'tgan Leadlar. `[ASSUMPTION: chegara 3 marta]`
- Admin har qanday **Jarayonda** Leadni majburan bo'shata oladi (sabab majburiy) yoki boshqa operatorga bera oladi.
- Har bir admin aralashuvi tarixga yoziladi.

---

### 4.6 Olib tashlanadigan mexanizmlar

**Tavsif.** Bu bo'lim v2 nima **qo'shishini** emas, nima **o'chirishini** belgilaydi. Downstream ish uchun bu qo'shimchalar ro'yxatidan muhimroq: har biri hozir operatorni bloklab turgan kod.

#### FR-17: Muddat va band qilish so'rovlari mashinasi o'chiriladi

Tizim endi ish muddati, uni cho'zish yoki ishdan voz kechish so'rovlarini qo'llab-quvvatlamaydi.

**Natijalar (tekshiriladigan):**
- Muddat kiritish oynasi, "muddati o'tdi" ogohlantirishi va bloklash holati mavjud emas.
- Muddat cho'zish / voz kechish so'rovlarini yaratish yoki hal qilish API'lari mavjud emas.
- Admin panelidagi "Ish so'rovlari" bo'limi olib tashlanadi.
- **Hech qanday operator harakati admin javobini kutishga majbur qilmaydi.**

#### FR-18: Yozuv qulflash va ruxsat so'rash oqimi o'chiriladi

Tizim endi tekshiruv maydonlarini qulflamaydi va ularni ochish uchun ruxsat so'ramaydi.

**Natijalar (tekshiriladigan):**
- Saqlash hech qachon maydonni qulflamaydi; qayta tahrirlash FR-10 orqali boradi.
- Ruxsat so'rash API'lari va admin panelidagi "Ruxsat so'rovlari" bo'limi mavjud emas.
- Mavjud ruxsat so'rovlari tarixi arxiv sifatida bazada qoladi (§10).

#### FR-19: Majburiy to'ldirish olib tashlanadi

Leadni ochish yoki undan chiqish hech qachon maydonlarni to'ldirishni talab qilmaydi.

**Natijalar (tekshiriladigan):**
- Operator Leadni ochib, hech narsa yozmasdan chiqa oladi (izoh berib — FR-5/FR-6).
- Bitta maydonni to'ldirib, ikkinchisini bo'sh qoldirish mumkin.
- Majburiy to'ldirish faqat bitta joyda qoladi: **Tasdiqlash** (FR-9).

---

## 5. Aniq maqsad emas (Non-Goals)

- **Bu CRM/sotuv quvuri emas.** Bitim summasi, bosqichlari, prognozi, mijoz kartochkasi — yo'q. Beshta status ishning holatini bildiradi, sotuv bosqichini emas.
- **Sozlanadigan ish oqimi emas.** Statuslar va o'tishlar kodda qattiq belgilangan. "Admin yangi status qo'sha oladi" — bu boshqa mahsulot.
- **Operator reytingi/gamifikatsiya emas.** Statistika hisobot beradi, mukofot bermaydi (mavjud UX qarori saqlanadi).
- **Skrap boshqaruvini o'z ichiga olmaydi.** Kompaniyalarni yig'ish SQLAdmin'da qoladi; OperatorDesk `companies` ni faqat o'qiydi (AD-2/AD-3 o'zgarishsiz).
- **Real vaqtda hamkorlikda tahrirlash emas.** Aksincha — eksklyuziv band qilish aynan buni oldini oladi.
- **Mobil ilova emas.** Desktop-birinchi veb saqlanadi.

---

## 6. MVP doirasi

### 6.1 Kiradi

- Beshta Lead status va o'tish mashinasi (FR-1, FR-2)
- Eksklyuziv band qilish + boshqaning ishining ko'rinmasligi (FR-3, FR-4)
- Bitta dialogli almashish + navigatsiya qo'riqchisi + majburiy Handover izohi (FR-5, FR-6)
- Qoralamani avtomatik saqlash (FR-7)
- 4 soatlik avtomatik bo'shatish (FR-8)
- Yakunlash va ruxsatsiz qayta ochish (FR-9, FR-10)
- Lead tarixi + ro'yxatda oxirgi izoh + erkin izoh (FR-11, FR-12, FR-13)
- Status tablari, jonli yangilanish, admin nazorat ko'rinishi (FR-14, FR-15, FR-16)
- Eski mexanizmlarni olib tashlash (FR-17, FR-18, FR-19)
- Ma'lumot migratsiyasi (§10)

### 6.2 MVP dan tashqarida

- **Operatorga avtomatik Lead taqsimlash** ("Keyingisini ber" tugmasi) — navbat qo'lda tanlanadi. Operatorlar tanlash erkinligini yo'qotishi kerakmi degan savol hali sinalmagan. → v2
- **Eslatma sanasi** ("ertaga 9:00 da qayta qo'ng'iroq qil" → bildirishnoma) — Handover izohida matn sifatida yozish yetarli. Chinakam eslatma tizimi kerakligi amalda ko'rinsin. `[NOTE FOR PM]` Bu UJ-2 ning tabiiy davomi; birinchi haftadan keyin qayta ko'rib chiqilsin.
- **Izohlar bo'yicha qidiruv** — tarix yoziladi, lekin qidirilmaydi. → v2
- **Operator ish yuki ko'rsatkichlari** (o'rtacha yakunlash vaqti, qo'l almashish darajasi) — ma'lumot yig'iladi, ko'rsatkich ekrani keyin.
- **Eski jadvallarni bazadan o'chirish** — bitta reliz arxiv sifatida qoladi (§10).
- **Mobil moslashuv** — mavjud desktop-birinchi qaror saqlanadi.

---

## 7. Kesib o'tuvchi sifat talablari (NFR)

- **NFR-1 — Javob tezligi.** Navbat sahifasi 300 ms ichida javob berishi kerak (250–5 000 Lead oralig'ida). Status va biriktirish maydonlari indekslangan bo'lishi shart.
- **NFR-2 — So'rovlar soni.** Lead ro'yxati va Lead sahifasi N+1 so'rov qilmasligi kerak — operator va tekshiruv maydonlari ma'lumoti to'plamli o'qilishi shart. *(Hozirgi kodda ikkalasida ham N+1 mavjud — bu tuzatish bo'limi, yangi talab emas.)*
- **NFR-3 — Tranzaksion yaxlitlik.** Ikki bosqichli o'tishlar (FR-5) bitta tranzaksiyada bajarilishi shart: yarim bajarilgan holat mumkin emas.
- **NFR-4 — Poyga holati.** Band qilish poygasi bazada hal qilinishi kerak (shartli yangilanish), ilova kodidagi tekshiruv bilan emas — aks holda ikki operator bir Leadni ola oladi.
- **NFR-5 — Ma'lumot yo'qotmaslik.** Hech bir avtomatik harakat (bo'shatish, migratsiya) operator kiritgan ma'lumotni o'chirmaydi.
- **NFR-6 — Foydalanish qulayligi (a11y).** WCAG 2.2 AA saqlanadi. Status hech qachon faqat rang bilan berilmaydi: ikonka + rang + matn. Majburiy izoh xatosi `aria-live` orqali e'lon qilinadi.
- **NFR-7 — Til.** Operatorga ko'rinadigan barcha matn o'zbek tilida; texnik identifikatorlar (`in_progress`, `waiting`) ichki qoladi va ekranga chiqmaydi.
- **NFR-8 — Testlar.** Status mashinasi va band qilish poygasi avtomatik testlar bilan qoplanishi shart. *(Hozir loyihada backend testlari umuman yo'q — bu shu ishning bir qismi.)*
- **NFR-9 — Kuzatuvchanlik.** Har bir status o'tishi tarixga yoziladi; tarix ma'lumoti hisobot uchun yetarli bo'lishi kerak (kim, qachon, qancha vaqt turdi).

---

## 8. Axborot arxitekturasi (o'zgarishlar)

| Ekran | Holati | Nima o'zgaradi |
|---|---|---|
| Navbat | O'zgaradi | Ikkita tab (`to'ldirilishi kerak`/`to'ldirilgan`) → beshta status tabi + sanoqlar. Band qilish banneri olib tashlanadi. |
| Lead sahifasi | Sezilarli o'zgaradi | Status sarlavhasi + egasi + harakatlar paneli; avtomatik saqlanadigan maydonlar; **yangi**: Lead tarixi paneli. "Saqlash → abadiy qulf" dialogi olib tashlanadi. |
| Mening so'rovlarim | Almashtiriladi | So'rovlar oqimi yo'qoladi → **"Mening ishlarim"**: operatorning joriy ishi va yaqinda yakunlagan Leadlari. |
| Admin: Ruxsat so'rovlari | Olib tashlanadi | FR-18 |
| Admin: Ish so'rovlari | Olib tashlanadi | FR-17 |
| Admin: Boshqaruv paneli | Kengayadi | Status bo'yicha taqsimot + "Uzoq turgan ishlar" + "Ko'p qo'l almashgan" bloklari (FR-16). |
| Admin: Barcha Leadlar | Yangi | Har qanday statusdagi Leadni egasi bilan ko'rish, majburan bo'shatish/qayta biriktirish. |
| Bildirishnomalar | Qisqaradi | So'rov hodisalari yo'qoladi. Qoladi: sizning ishingiz majburan bo'shatildi / sizga Lead biriktirildi. |
| Profil / Statistika | Deyarli o'zgarishsiz | Sanoqlar endi "yakunlangan Lead" bo'yicha hisoblanadi. |

---

## 9. Muvaffaqiyat ko'rsatkichlari

**Asosiy**

- **SM-1 — Bloklangan operator hodisalari: nolga.** Operator harakati "avval admin javobini kuting" bilan tugagan hollar soni. Hozir: `overdue` va `active_claim_exists` javoblari. Maqsad: **0**. FR-17, FR-18 ni tasdiqlaydi.
- **SM-2 — Handover izohi qamrovi: 100%.** **Jarayonda → Kutilmoqda** o'tishlarining necha foizida bo'sh bo'lmagan izoh bor. Maqsad: **100%** (texnik jihatdan kafolatlangan; o'lchov qoidaning ishlayotganini tasdiqlaydi). FR-5, FR-6 ni tasdiqlaydi.
- **SM-3 — Operator kutish vaqti: nol.** Operator admin qaroriga bog'liq holda kutgan umumiy vaqt. Hozir: bir necha soatdan bir necha kungacha. Maqsad: **0 daqiqa**. FR-17, FR-18 ni tasdiqlaydi.

**Ikkilamchi**

- **SM-4 — Qo'ldan olingan ishning davom etish darajasi.** Boshqa operator qoldirgan **Kutilmoqda** Leadni olgan operator uni nolga tushirmasdan yakunlagan hollar ulushi. Maqsad: **≥ 80%**. FR-12, FR-11 ni tasdiqlaydi. O'lchov usuli: birinchi haftada operatorlardan so'rov + tarix tahlili.
- **SM-5 — Qotib qolgan ish ulushi.** 2 kundan ortiq **Kutilmoqda**da turgan Leadlar ulushi. Maqsad: **< 10%**. FR-8, FR-16 ni tasdiqlaydi.

**Qarshi ko'rsatkichlar (optimallashtirmang)**

- **SM-C1 — Tasdiqlangan Leadlar sonini optimallashtirmang.** Bu son ruxsat to'siqlari olinishi bilan tabiiy o'sadi; uni maqsadga aylantirish sifatsiz tasdiqlashni rag'batlantiradi. Kuzatiladigan haqiqiy signal: **qayta ochilgan Leadlar ulushi** (FR-10). U keskin oshsa — tasdiqlash juda yengil kechyapti. SM-1 ni muvozanatlaydi.
- **SM-C2 — "Kutilmoqda"ga o'tishlar sonini kamaytirishga urinmang.** Ishni qoldirib qo'yish normal ish oqimi (mijoz javob bermadi — bu operatorning aybi emas). Xavotirli signal — soni emas, **bir Leadning 3+ marta qo'l almashishi** (FR-16). SM-2 ni muvozanatlaydi.

---

## 10. Migratsiya va ma'lumot uzluksizligi

Ishlab turgan tizim almashtirilmoqda — hech kimning ishi yo'qolmasligi kerak.

**Status ko'chirish qoidalari:**

| Hozirgi holat | Yangi status | Qo'shimcha |
|---|---|---|
| Har ikki tekshiruv maydoni to'ldirilgan (`locked`) | **Tasdiqlangan** | To'ldirgan operator va vaqti tarixga ko'chiriladi |
| Bitta maydon to'ldirilgan | **Kutilmoqda** | Tizim izohi: "Migratsiya — bitta maydon to'ldirilgan" |
| Faol band qilish (`active` claim) | **Jarayonda** | O'sha operatorga biriktiriladi; `last_activity_at` migratsiya vaqti |
| Kechiktirilgan band qilish (`deferred` claim) | **Kutilmoqda** | Eski `reason` matni Handover izohi sifatida ko'chiriladi; bo'sh bo'lsa tizim izohi qo'yiladi |
| Yakunlangan/bo'shatilgan band qilish | tekshiruv holatiga qarab | Alohida qoida yo'q |
| Qolgan barcha kompaniyalar | **Yangi** | — |

**Eski jadvallar.** `company_claims`, `claim_requests`, `permission_requests` **bitta reliz davomida bazada qoladi** — o'qish uchun arxiv sifatida, yozuvsiz. Ular bilan ishlaydigan API va ekranlar o'chiriladi. Keyingi relizda alohida migratsiya bilan o'chiriladi. Sabab: yangi model amalda ishlashiga ishonch hosil bo'lgunga qadar ortga qaytish yo'li ochiq qolsin.

**Joriy qilish.** Bir martalik almashtirish (bosqichma-bosqich yoyish emas) — foydalanuvchilar soni kichik, ikkita parallel ish oqimini bir vaqtda qo'llab-quvvatlash zarar keltiradi. Almashtirishdan oldin operatorlarga qisqa tushuntirish kerak: beshta status nimani anglatadi va izoh nega majburiy. `[ASSUMPTION: operatorlar soni 10 dan kam va bitta jamoada — bir martalik almashtirish xavfsiz]`

---

## 11. Ochiq savollar

1. **"Kutilmoqda" Leadlar tabiiy tartibi qanday?** Eng eski birinchimi, oxirgi izoh vaqti bo'yichami, yoki ilgari tegilgani birinchimi? Boshlang'ich taxmin — eng uzoq turgani birinchi, lekin amalda operatorlar buni qanday ishlatishi ko'rilsin.
2. **Rad etilgan Lead qayta skrap qilinganda nima bo'ladi?** Skrap `last_seen_at` ni yangilaydi (AD-3). Rad etilgan Lead **Yangi**ga qaytishi kerakmi, yoki rad etilganicha qolsinmi? Hozirgi taxmin: qolsin.
3. **Operator o'chirilganda (`is_active=false`) uning **Jarayonda** Leadi nima bo'ladi?** Bu eski tizimda ham hal qilinmagan muammo edi (arxitektura hujjatining "Deferred" bo'limida yozilgan). Taklif: darhol **Kutilmoqda**ga o'tsin. Tasdiqlash kerak.
4. ~~**Admin ham Lead ustida ishlay oladimi?**~~ — **hal qilindi 2026-08-20: yo'q.** Admin ishlamaydi, kuzatadi. U hech qanday Leadni band qila olmaydi, to'ldira olmaydi, yakunlay olmaydi va qayta ocha olmaydi; uning ixtiyoridagi yagona ikkita harakat — ishni **majburan bo'shatish** va **operatorga biriktirish**. Sabab: agar admin ham lead olsa, navbat sanoqlari operator yukini aks ettirmay qoladi va operator natijalari faqat tekshirib ko'rgan rahbarning raqamlari bilan aralashib ketadi. Server darajasida majburlangan (`require_operator`), faqat interfeysda yashirilgani bilan emas. **Bu UJ-5 ni ham o'zgartiradi:** Aziz Leadni o'zi rad etmaydi — uni operatorga biriktiradi yoki bo'shatadi.
5. **Tarix qancha saqlanadi?** Hozircha cheksiz. Ma'lumot hajmi o'sganda ko'rib chiqilsin.

---

## 12. Taxminlar indeksi

Har bir `[ASSUMPTION]` tasdiqlash uchun:

- **§4.5 / FR-16** — "Uzoq turgan ish" chegarasi **2 kun**. Amaliyotdan keyin sozlanishi mumkin.
- **§4.5 / FR-16** — "Ko'p qo'l almashgan" chegarasi **3 marta**.
- **§10** — Operatorlar soni 10 dan kam va bitta jamoada, shuning uchun bir martalik almashtirish xavfsiz.
- **§4.3 / FR-7** — Qoralama saqlash tarixga yozuv qo'shmaydi. Agar audit talabi qat'iylashsa, bu qayta ko'rib chiqilishi kerak (tarix shovqinga to'ladi).
- **§4.2 / FR-4** — Boshqaning **Jarayonda** Leadi uchun **404** qaytariladi (403 emas), ya'ni mavjudligi ham oshkor qilinmaydi. Ichki asbob uchun bu ortiqcha bo'lishi mumkin, lekin arzon.
- **§4.2** — Bir operatorda bir vaqtda faqat bitta **Jarayonda** Lead. Bu Handover izohini ushlab turuvchi ustun — tasdiqlash eng muhimi shu taxmin uchun.
- **§11.2** — Rad etilgan Lead qayta skrap qilinganda rad etilganicha qoladi.

---

## Bekor bo'ladigan oldingi qarorlar

Bu PRD quyidagi arxitektura qarorlarini bekor qiladi — arxitektura hujjati shunga mos yangilanishi shart:

- **AD-8** (yozuv/qulf modeli) — `locked` bayrog'i va `permission_requests` orqali ochish yo'li bekor bo'ladi. O'rniga: qulfsiz tahrirlash + Lead tarixi (FR-10, FR-11).
- **AD-11** (band qilish, muddat, admin tasdig'i) — to'liq bekor bo'ladi. O'rniga: Lead status mashinasi + eksklyuziv biriktirish + 4 soatlik avtomatik bo'shatish (FR-1…FR-8).
- **AD-9** (bildirishnomalar) — qisman: so'rov hodisalari yo'qoladi, kanal va mexanizm o'zgarishsiz qoladi va FR-15 uchun ishlatiladi.
- **AD-2, AD-3, AD-7, AD-10, AD-12, AD-13** — o'zgarishsiz.
