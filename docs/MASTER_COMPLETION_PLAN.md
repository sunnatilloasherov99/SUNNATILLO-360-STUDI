# SUNNATILLO 360° STUDIO — yagona yakunlash rejasi

Ushbu hujjat loyihani bitta uzluksiz reliz dasturi sifatida boshqaradi. Har bir yo'nalish alohida mustaqil topshiriq emas: keyingi ish avvalgi bosqichning qabul mezonlari bajarilgandan keyin boshlanadi.

## Yakuniy maqsad

O'zbek (asosiy), rus va ingliz tillarida ishlaydigan, o'z serveriga ko'chirish mumkin bo'lgan, 360° foto/video tahrirlash, virtual tur yaratish, AI yordamchisi va rasmiy imkoniyatlar doirasida xaritalarga nashr qilishni ta'minlaydigan barqaror web-platformani ommaviy ishga tushirish.

## Ishlash qoidalari

- Har bir o'zgarish GitHub'ga kichik, izohli commit bilan yoziladi.
- Har bir muhim commitdan so'ng frontend build, backend testlari, migratsiya va infratuzilma tekshiruvlari bajariladi.
- CI muvaffaqiyati real serverdagi ishga tushirish yoki haqiqiy panorama bilan vizual sifat tekshiruvi o'rnini bosmaydi.
- Original media hech qachon tahrirlangan nusxa bilan almashtirilmaydi.
- Pullik AI yoki xarita xizmati majburiy qilinmaydi; pullik/akkauntga bog'liq imkoniyatlar alohida belgilanadi.
- Google, Yandex va 2GIS nashri faqat rasmiy API, hududiy mavjudlik va akkaunt ruxsatlari imkon bergan holatda amalga oshiriladi. Qo'llab-quvvatlanmagan joyda eksport va aniq qo'lda joylash ko'rsatmasi beriladi.
- Maxfiy kalitlar, parollar va OAuth tokenlari repoga yozilmaydi.
- Har bir bosqich "kod yozildi" bilan emas, qabul mezonlari va testlar bilan yopiladi.

## Umumiy holat

- 1–3-bosqichlar: muhim funksional poydevor mavjud; production darajasida to'liq tasdiqlangan deb hisoblanmaydi.
- 4-bosqich: GitHub Actions frontend, backend va infratuzilma tekshiruvlari 2026-11-16 dagi 43916242412 run'da muvaffaqiyatli o'tdi; real qurilmalar va serverda qo'lda sinov hali kerak.
- 5-bosqich: faol ish.
- 6–9-bosqichlar: bajarilishi kerak.

## 5-bosqich — Professional panorama tiklash

### 5.1 Diagnostika
- [x] 2:1 equirectangular rasm uchun ichki vertikal kontrast nomzodlarini hisoblash.
- [x] 360° chap-o'ng chegarani hisobga olish.
- [x] Past ishonch darajasini va taxminiy natija ekanini qaytarish.
- [x] Sintetik tasvirlar uchun unit testlar qo'shish.
- [x] Sifat hisobotiga diagnostika natijasini ulash.
- [x] GitHub Actions tekshiruvlari: run 43916242412 muvaffaqiyatli.
- [ ] Haqiqiy telefon panoramalari bilan vizual tekshirish.
- [x] API javobining integratsion testi qo'shildi (`test_quality_report_includes_heuristic_vertical_discontinuity_candidates`).

### 5.2 Qo'lda tuzatish
- [x] Brauzerda nuqson maydonini belgilash va yumshoq chetli clone brush qo‘shildi.
- [x] Clone/patch vositasi va manba maydonini tanlash, cho‘tka o‘lchami hamda stroke bo‘ylab manba siljishi qo‘shildi.
- [x] Clone cho‘tkasining nishon nuqtasi va manba namunasiga chap-o‘ng 360° o‘rash qo‘shildi (commit `7fd5adf`).
- [x] Editor preview, undo/redo va tuzatish qatlamini tozalash qo‘shildi.
- [x] Tuzatish qatlamini asl faylga tegmasdan yangi hosila media eksportiga qo‘shildi.
- [x] Panorama almashtirilganda clone brush manbasi, undo/redo tarixi va faol pointer chizishi tozalanadi; pointer capture yo‘qolganda ham chizish holati yopiladi (commit `3b9b5e6`).
- [x] AI maska cho‘tkasida pointer capture yo‘qolsa, faol chizish holati ham darhol yopiladi (commit `3b005c3`).
- [x] AI maska cho‘tkasi tez harakatda uzilib qolmasligi uchun pointer nuqtalari orasidagi chiziqlar interpolatsiya qilinadi; pointer tugaganda yoki yo‘qolganda yo‘l holati tozalanadi (commit `5227dc5`).
- [x] Keshlangan rasm tez yuklanganda ham clone canvas o‘lchamlari to‘g‘ri boshlanishi uchun `complete/naturalWidth` holati tekshiriladi (commit `c8d61ae`).
- [x] CI run 43918087957: frontend build, backend testlari va Docker/infratuzilma tekshiruvlari muvaffaqiyatli.

### 5.3 Ixtiyoriy lokal AI inpainting
- [x] Server-side provider adapterining dastlabki HTTP multipart shartnomasi qo‘shildi (`image`, `mask`, `prompt`; natija bir xil o‘lchamdagi JPEG/PNG/WebP).
- [x] Provider URL faqat server konfiguratsiyasidan olinadi; foydalanuvchi so‘rovi orqali ixtiyoriy URL chaqirishga yo‘l qo‘yilmaydi.
- [x] Login talabi, 20 MB fayl cheklovi, 40 MP rasm cheklovi, maska o‘lchami tekshiruvi, timeout, provider xatolari va natija formati tekshiruvi qo‘shildi.
- [x] AI capabilities javobida provider mavjudligi va foydalanuvchi tasdig‘i talab qilinishi ko‘rsatiladi.
- [x] `.env.example` da ixtiyoriy `INPAINTING_ENDPOINT_URL`, `INPAINTING_API_KEY`, `INPAINTING_TIMEOUT_SECONDS` sozlamalari hujjatlashtirildi.
- [ ] Foydalanuvchi o‘zi sozlagan ComfyUI workflow uchun mos HTTP bridge va real model sinovi. To‘g‘ridan-to‘g‘ri ComfyUI workflow API hali ulanmagan.
- [x] Frontend’da oq maska cho‘tkasi, AI yuborishdan oldin rozilik oynasi, oldin/keyin preview va natijani qabul/rad etish qo‘shildi (commit `5d6b50b`, `44d87b6`).
- [x] AI providerga yuboriladigan maska qora fon + oq belgilangan hudud ko‘rinishiga normallashtirildi (commit `3df92da`).
- [x] `/api/ai/capabilities` orqali provider mavjudligi tekshiriladi; AI tugmasi provider sozlanmagan bo‘lsa o‘chiq, qo‘lda tuzatish vositasi alohida ishlashda davom etadi.
- [x] Panorama yoki token almashganda avvalgi AI so‘rovining kechikib kelgan javobi yangi rasm holatini bosib ketmasligi uchun request-version guard qo‘shildi (commit `a769b83`).
- [x] AI natijasini qabul qilish paytida panorama almashtirilsa, eski natija yangi panorama ustiga qo‘llanmasligi uchun qabul amali ham request-version bilan himoyalandi (commit `3318445`).
- [x] AI maska muharririda konteyner balandligi bilan rasm nisbatini buzib, maskani tasvirga nisbatan siljitishi mumkin bo‘lgan `max-height` cheklovi olib tashlandi (commit `ba4c32e`).
- [x] Yangi panorama yuklanayotganda avvalgi rasmning o‘lchamlari va maska canvas’i vaqtincha o‘chirilib, eski maskaning yangi rasmga yuborilishi oldi olindi (commit `7893742`).

### 5.4 Eksport va qabul sinovlari
- [x] AI natijasi → rang/yorug‘lik → clone brush qatlamasi → chok sozlamalari → JPEG eksport yagona render pipeline orqali bajariladi.
- [x] AI natijasini qabul qilishdan oldin preview qilish va qabul qilingan AI qatlamasini bekor qilib original manbaga qaytish boshqaruvi qo‘shildi.
- [x] Tahrirlangan nusxa source_asset_id orqali asl media bilan bog‘lanadi; 0002_media_source_asset migratsiyasi va API validatsiyasi qo‘shildi.
- [x] Original media baytlari o‘zgarmasligi, source asset ownership, noto‘g‘ri MIME/signature va hosila media bog‘lanishi uchun backend testlari qo‘shildi.
- [x] GitHub Actions frontend/backend/infrastructure tekshiruvlari yangi o‘zgarishlar bilan muvaffaqiyatli yakunlandi (run `43933375111`; barcha 3 job `success`).
- [ ] Haqiqiy foydalanuvchi panoramalari bilan preview, clone brush, AI natijasi va JPEG eksport sifatini vizual sinash. Sinov tartibi: [PANORAMA_BROWSER_ACCEPTANCE.md](./PANORAMA_BROWSER_ACCEPTANCE.md).

**5-bosqichni yopish mezoni:** foydalanuvchi panoramani xavfsiz tekshirib, nuqsonni qo'lda tuzata oladi, kerak bo'lsa ixtiyoriy lokal AI natijasini ko'rib tasdiqlaydi va original faylni saqlagan holda yangi nusxa eksport qiladi.

## 6-bosqich — Xaritalarga nashr qilish
- [ ] Google Street View rasmiy API/OAuth imkoniyatlari va talablarini tekshirish.
- [ ] Google nashr adapteri va ulanish holati; mavjud bo'lmagan API/akkaunt imkoniyatini soxta ko'rsatmaslik.
- [ ] Yandex Maps rasmiy nashr yo'li va cheklovlarini tekshirish.
- [ ] 2GIS rasmiy nashr yo'li va cheklovlarini tekshirish.
- [ ] Platformaga qarab eksport paketi, metama'lumotlar va qo'lda yuklash yo'riqnomasi.
- [ ] Har bir integratsiya uchun xatolar, token muddati va qayta urinish holatlari.
- [ ] Faqat sandbox/test yoki ruxsatli akkaunt bilan tasdiqlangan nashr sinovi.

**6-bosqichni yopish mezoni:** qo'llab-quvvatlangan platformaga haqiqiy nashr sinovi muvaffaqiyatli; qo'llab-quvvatlanmagan platforma uchun foydalanuvchi ishlata oladigan eksport va aniq ko'rsatma bor.

## 7-bosqich — Xavfsizlik va ishonchlilik
- [ ] Email tasdiqlash va parolni tiklash.
- [ ] Production secret/config tekshiruvlari, xavfsiz cookie/token siyosati va CORS.
- [ ] Fayl turi, hajmi, rasm dekodlash va upload abuse himoyasi.
- [ ] Loyiha/media ownership va public share tokenlarini tekshirish.
- [ ] Redis rate limit production sozlamasi.
- [ ] Rejali avtomatik DB + media backup.
- [ ] Backup yaxlitligi va avtomatik restore drill.
- [ ] Loglarda maxfiy ma'lumotlar chiqmasligini tekshirish.

**7-bosqichni yopish mezoni:** xavfsizlik testlari, backup va tiklash sinovi hujjatlashtirilgan; production konfiguratsiya tekshiruvlari o'tgan.

## 8-bosqich — Oflayn va desktop
- [ ] PWA offline strategiyasi: faqat xavfsiz, ruxsat etilgan statik resurslar.
- [ ] Virtual turni offline paket sifatida eksport qilish.
- [ ] Paket ichidagi panorama, hotspot va navigatsiyani internetsiz tekshirish.
- [ ] Desktop packaging (masalan, Tauri/Electron) bo'yicha eng yengil mos yo'lni tanlash.
- [ ] Desktop build, yangilanish va fayl import/eksport sinovlari.

**8-bosqichni yopish mezoni:** eksport qilingan tur internetsiz ochiladi; desktop build o'rnatilib, asosiy ish oqimlari sinovdan o'tgan.

## 9-bosqich — Production va ommaviy ishga tushirish
- [ ] VPS/hosting talablari va narxini aniqlash; arzon/free tier cheklovlarini yashirmaslik.
- [ ] Domen va DNS (foydalanuvchi domen/akkauntiga kirish talab qilinishi mumkin).
- [ ] HTTPS, production environment, DB va persistent media volume.
- [ ] Migratsiya, backup, restore va monitoring.
- [ ] Production smoke test: ro'yxatdan o'tish, loyiha, media upload, panorama, virtual tur, share, eksport.
- [ ] Telefon va desktop brauzerlarida yakuniy tekshiruv.
- [ ] O'zbek/rus/ingliz matnlarini ko'rib chiqish.
- [ ] Ommaviy URL va ishga tushirish yo'riqnomasini e'lon qilish.

**9-bosqichni yopish mezoni:** domen orqali HTTPS bilan ishlaydigan production sayt, tiklanishi sinovdan o'tgan ma'lumotlar va tasdiqlangan asosiy foydalanuvchi oqimlari mavjud.

## Hozirgi navbatdagi ishlar

1. AI maska tuzatishi va source_asset_id migratsiyasi, API hamda backend testlari CI natijasini tasdiqlash — bajarildi (run `43933375111`).
2. So‘nggi kod commitidagi asinxron holat yangilanishi tuzatishi uchun frontend/backend/infrastructure CI — bajarildi, barcha 3 job success (run `43934039556`).
3. Browser darajasidagi qo‘lda qabul sinovlari uchun bosqichma-bosqich checklist yaratildi: [PANORAMA_BROWSER_ACCEPTANCE.md](./PANORAMA_BROWSER_ACCEPTANCE.md).
4. AI inpainting panelidagi eskirgan so‘rov va qabul amallarini bekor qilish himoyasi qo‘shildi (commit `a769b83`, `3318445`); oxirgi commitlar uchun CI tekshiruvi davom etmoqda.
5. 5.3 uchun ComfyUI HTTP bridge va haqiqiy lokal model bilan integratsion sinov.
6. 5.4 uchun checklist asosida browser darajasida eksport qatlamalari va AI rollback vizual sinovi.
7. Haqiqiy telefon panoramasi bilan yakuniy qabul sinovi.

## Reliz hisoboti

Har bir hisobotda quyidagilar yangilanadi: oxirgi commit, bajarilgan qabul mezonlari, CI holati, ochiq muammolar, foydalanuvchi tomondan zarur bo'lgan ruxsat/kirishlar va 9 bosqichdan nechta qolgani.

**Muhim:** ChatGPT suhbatdan tashqarida fonda ishlashni davom ettirmaydi. Ish faqat faol suhbat/tool chaqiruvlari davomida bajariladi; keyingi suhbatda shu hujjat va repodagi holatdan davom ettiriladi.
