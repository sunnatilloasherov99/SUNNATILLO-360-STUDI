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
- [ ] Chap-o'ng chegaradan o'tuvchi 360° maskani to'g'ri o'rash.
- [x] Editor preview, undo/redo va tuzatish qatlamini tozalash qo‘shildi.
- [x] Tuzatish qatlamini asl faylga tegmasdan yangi hosila media eksportiga qo‘shildi.

### 5.3 Ixtiyoriy lokal AI inpainting
- [ ] Provider-neutral adapter.
- [ ] Foydalanuvchi o'zi sozlagan lokal ComfyUI/inpainting endpoint.
- [ ] Rozilik, maskani tasdiqlash, timeout va hajm cheklovlari.
- [ ] Model mavjud bo'lmasa, AI tugmasini aniq o'chirib, manual vositalarni ishlatish.

### 5.4 Eksport va qabul sinovlari
- [ ] Tahrir tarixi va source asset bog'lanishi.
- [ ] Ruxsat/ownership, mask chegarasi, buzilgan rasm va original o'zgarmasligi testlari.
- [ ] Oldin/keyin ko'rish va JPEG eksport.
- [ ] Haqiqiy foydalanuvchi panoramalari bilan sifat sinovi.

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

1. 5.2 clone brush uchun frontend build va vizual sinovni yakunlash.
2. 360° chetlarida clone source sampling va maska xatti-harakatini mustahkamlash.
3. Tahrir qatlamini saqlash va haqiqiy panorama bilan qabul sinovlarini qo‘shish.
4. Har bir commitdan so‘ng CI natijasini qayta tekshirish.

## Reliz hisoboti

Har bir hisobotda quyidagilar yangilanadi: oxirgi commit, bajarilgan qabul mezonlari, CI holati, ochiq muammolar, foydalanuvchi tomondan zarur bo'lgan ruxsat/kirishlar va 9 bosqichdan nechta qolgani.

**Muhim:** ChatGPT suhbatdan tashqarida fonda ishlashni davom ettirmaydi. Ish faqat faol suhbat/tool chaqiruvlari davomida bajariladi; keyingi suhbatda shu hujjat va repodagi holatdan davom ettiriladi.
