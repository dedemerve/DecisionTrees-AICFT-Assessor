# El yazısı çıkarım doğruluğu ve insan–sistem puanlama uyumu

**Rapor tarihi:** 12 Kasım 2026  
**Veri inceleme tarihi:** 9–12 Kasım 2026  
**Kapsam:** WS1–WS15, 15 öğrenci  
**Önceki sürüm:** v5 (10 Kasım 2026) — WS1–WS12 kapsıyordu  
**Bu sürümde eklenen:** WS13, WS14, WS15  
**Amaç:** Makalenin Findings bölümüne temel olacak bulguları, hesaplama kapsamını ve sınırlılıklarını birlikte sunmak.

---

## 1. Temel sonuçlar

İki analiz farklı süreçleri ölçmektedir. El yazısı çıkarım analizi, LLM'nin öğrencinin yazısını doğru okuyup çıkarabilmesini; puanlama uyumu analizi ise insanın öğrenci cevabına verdiği kategoriyle yayımlanmış sistem kararının eşleşmesini değerlendirmektedir.

- **El yazısı çıkarım doğruluğu (WS1–WS15):** 2739 doğru ve 32 yanlış çıkarım; 2771 değerlendirilmiş öğrenci–madde kaydı üzerinden **%98,85**.
- **İnsan–sistem puanlama uyumu (WS1–WS15):** karşılaştırılabilir 1324 kayıt; **%88,97 ham uyum** (95% CI: %85,42–%91,99), ağırlıksız **Cohen's κ = 0,7783** (95% CI: 0,7154–0,8355).

**v5 → v6 karşılaştırması:**

| | v5 (WS1–12) | v6 (WS1–15) |
|---|---|---|
| OCR doğruluğu | %97,32 (1164/1196) | **%98,85** (2739/2771) |
| Puanlama N | 556 | **1324** |
| Ham uyum | %95,50 | **%88,97** |
| Cohen's κ | 0,8598 | **0,7783** |

OCR kapsamı WS13–15 eklenmesiyle arttı ve doğruluk yükseldi. Puanlama uyumu ise WS13 (%78,61) ve WS14 (%63,53) genel ortalamayı aşağı çektiğinden düştü. Bu fark WS13–14'te açık uçlu yorumlayıcı madde oranının yüksek olmasından kaynaklanmaktadır.

---

## 2. Kaynaklar ve eşleştirme

İnsan değerlendirmeleri kod kitabının **Cevap Anahtarı** sayfasından alınmıştır (xlsx SHA-256: `0cc4911d9fb1fbc65d0a75bd7a17eefd70e00fd4ea4e67d20dc247db0f350b08`; okuma öncesi ve sonrası özet aynıdır). Sistem kararları 10 Kasım 2026 site görüntüsünden alınan `comparison_all_groups.csv` (`system_label` sütunu) dosyasına dayanmaktadır.

İnsan ve sistem kayıtları öğrenci adı, worksheet kimliği ve madde konumu üzerinden eşleştirilmiştir. Birden fazla satırı kapsayan T-strand grupları AND-birleşimi ile tek birime dönüştürülmüştür. Toplam kayıt sayısı 197 kaynak satır × 15 öğrenci = 2955 bileşen hücresi, 2760 AND-grubu birimidir.

---

## 3. Dışlamalar

Her birim aşağıdaki hiyerarşik önceliğe göre tek bir nedene atanmıştır.

| Dışlama | Birim | Kaynak hücre |
|---|---:|---:|
| 1. Worksheet yok | 323 | 349 |
| 2. İnsan +0,5 (silip doğru) | 419 | 437 |
| 3. İnsan \| (ağacı uzatmaya gerek yok) | 98 | 98 |
| 4. Birim uyuşmazlığı | 312 | 312 |
| 5. Sistem doğrulanmamış / karar yok | 28 | 28 |
| 6. Sistem Partial | 256 | 258 |
| **Dahil edilen** | **1324** | **1473** |

Uzlaşma: 1324 dahil + 1436 dışlanan = 2760 AND birimi. İnsan grupların >1 site hücresine karşılık geldiği 26 birimde sistem etiketleri de AND-birleşimi ile oluşturulmuştur.

---

## 4. El yazısı çıkarım doğruluğu

| Worksheet | Satır | Doğru | Yanlış | Payda | Doğruluk | WS yok |
|---|---:|---:|---:|---:|---:|---:|
| WS1 | 11 | 143 | 0 | 143 | %100,00 | 22 |
| WS3 | 8 | 100 | 4 | 104 | %96,15 | 16 |
| WS4 | 5 | 57 | 8 | 65 | %87,69 | 10 |
| WS5 | 25 | 324 | 1 | 325 | %99,69 | 50 |
| WS6 | 13 | 161 | 8 | 169 | %95,27 | 26 |
| WS7 | 7 | 84 | 7 | 91 | %92,31 | 14 |
| WS10 | 8 | 104 | 0 | 104 | %100,00 | 16 |
| WS12 | 15 | 191 | 4 | 195 | %97,95 | 30 |
| WS13 | 25 | 375 | 0 | 375 | %100,00 | 0 |
| WS14 | 33 | 495 | 0 | 495 | %100,00 | 0 |
| WS15 | 47 | 705 | 0 | 705 | %100,00 | 0 |
| **Toplam** | **197** | **2739** | **32** | **2771** | **%98,85** | — |

AND-birleşimi sonrası OCR doğruluğu: 2571/2602 = **%98,81** (158 yokluk grubu hariç).

Hata yoğunluğu: WS6 (8 hata, %25,0), WS4 (8 hata, %25,0), WS7 (7 hata, %21,9) — üçü birlikte 32 hatanın %71,9'unu oluşturmaktadır. WS13–WS15 için çıkarım hatası sıfırdır. Tek değerlendirici kullanıldığından Cohen's κ hesaplanmamıştır.

**Koşullu OCR tablosu** (AND-birleşimi sonrası, her iki sayfada mevcut birimler):

| İnsan kodu | n | OCR=+1 | OCR=−1 | P(OCR=+1) |
|---|---:|---:|---:|---:|
| +1 (doğru) | 1424 | 1408 | 16 | %98,88 |
| −1 (yanlış) | 89 | 81 | 8 | %91,01 |
| 0 (boş) | 407 | 405 | 2 | %99,51 |
| +0,5 (silip doğru) | 419 | 417 | 2 | %99,52 |
| \| (yapısal dur) | 98 | 95 | 3 | %96,94 |
| **Toplam** | **2437** | **2406** | **31** | **%98,73** |

---

## 5. İnsan–sistem puanlama uyumu (WS1–WS15)

### 5.1. Genel karışıklık matrisi (n=1324)

| İnsan / Sistem | correct | wrong | blank | Toplam |
|---|---:|---:|---:|---:|
| correct | 796 | 77 | 39 | 912 |
| wrong | 5 | 56 | 0 | 61 |
| blank | 15 | 10 | 326 | 351 |
| **Toplam** | **816** | **143** | **365** | **1324** |

**Sınıf metrikleri:**

| Sınıf | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| correct | 0,9755 | 0,8728 | 0,9213 | 912 |
| wrong | 0,3916 | 0,9180 | 0,5490 | 61 |
| blank | 0,8932 | 0,9288 | 0,9106 | 351 |
| **Makro F1** | | | **0,7936** | |

**Percent agreement = %88,97 (95% CI: %85,42–%91,99)**  
**Unweighted Cohen's κ = 0,7783 (95% CI: 0,7154–0,8355)**  
Bootstrap: 10.000 küme yeniden örneklemesi (15 öğrenci), tohum 20261110, yüzdelik CI.

### 5.2. Worksheet düzeyi uyum

| Worksheet | n | Uyum | Uyuşmazlıklar |
|---|---:|---:|---|
| WS1 | 142 | %97,89 | correct→wrong: 2, wrong→correct: 1 |
| WS3 | 104 | %96,15 | correct→wrong: 4 |
| WS4 | 61 | %78,69 | correct→wrong: 7, wrong→correct: 2, correct→blank: 2, blank→correct: 1, blank→wrong: 1 |
| WS5 | 109 | %97,25 | correct→wrong: 3 |
| WS6 | 35 | %94,29 | correct→wrong: 2 |
| WS7 | 52 | %100,00 | — |
| WS10 | 24 | %95,83 | blank→wrong: 1 |
| WS12 | 37 | %100,00 | — |
| WS13 | 187 | %78,61 | correct→wrong: 12, correct→blank: 19, blank→wrong: 6, blank→correct: 2, wrong→correct: 1 |
| WS14 | 170 | %63,53 | correct→wrong: 47, correct→blank: 9, blank→wrong: 2, blank→correct: 3, wrong→correct: 1 |
| WS15 | 403 | %95,53 | correct→blank: 9, blank→correct: 9 |

WS13 ve WS14 en düşük uyum göstermektedir. WS14'te en yaygın hata correct→wrong (n=47): sistem insan değerlendirmesinin doğru saydığı yanıtları yanlış olarak işaretliyor.

### 5.3. Duyarlılık analizleri

| Analiz | n | κ | Uyum |
|---|---:|---:|---:|
| S1 — AND-birleşimi (ana analiz) | 1324 | 0,7783 | %88,97 |
| S1b — AND-birleşimsiz (madde bazlı) | 1409 | 0,7913 | %89,35 |
| S2 — İnsan-blank dışarıda | 973 | 0,4343 | %87,56 |
| S3 — Backend skor tekrarı giderildi | 1262 | 0,7748 | %88,51 |

S2'de blank birimlerin çıkarılması κ'yı −0,344 düşürüyor; blank uyumunun genel κ'ya katkısı büyüktür.

---

## 6. Hesaplama ve doğrulama

Ham uyum Pₒ = aynı kategori sayısı / karşılaştırılan kayıt sayısı. Beklenen uyum Pₑ = her kategori için insan ve sistem marjinal oranlarının çarpımlarının toplamı. Ağırlıksız çok kategorili Cohen's κ = (Pₒ − Pₑ) / (1 − Pₑ). Üç sınıf nominaldir; +0,5 bir süreç kodu, | yapısal bir durdurma işaretidir — ordinal ölçek bulunmadığından ağırlıklı κ kullanılmamıştır.

**Doğrulama (hepsi PASS):**
- V1: OCR sayımı uzlaşır (2955 bileşen); AND birimleri uzlaşır (2760).
- V2: Her kaynak satır tam olarak bir AND grubuna dahildir.
- V3: Manuel κ=0,778307 = sklearn κ=0,778307 (4 hesaplamanın tümü <1e-12 fark).
- V4: xlsx SHA-256 okuma öncesi ve sonrası aynıdır; sistem kararı CSV değişmemiştir.
- V5: AND grubu boyutu × grup sayısı her worksheet için doğrulanmıştır.

---

## 7. Makalenin Findings bölümüne uyarlanabilir metin

### El yazısı çıkarımı

WS1–WS15 kapsamında 197 madde satırı ve 15 öğrenci için toplam 2771 değerlendirilebilir öğrenci–madde kaydında el yazısı çıkarım doğruluğu %98,85 bulunmuştur. WS13–WS15 için çıkarım hatası gözlenmemiştir. En düşük doğruluk WS4'te (%87,69), ardından WS7'de (%92,31) görülmüş; bu iki worksheet ile WS6 toplam 32 hatanın %71,9'unu oluşturmuştur. Tek bağımsız değerlendirici kullanıldığından değerlendiriciler arası κ hesaplanmamıştır.

### İnsan–sistem puanlama uyumu

İnsan kodu kitabı ile yayımlanmış sistem kararları AND-birleşimi uygulanmış birimler üzerinden eşleştirilmiştir. Dışlamalar hiyerarşik olarak uygulandıktan sonra (worksheet yok, +0,5, yapısal |, birim uyuşmazlığı, sistem kararı yok/doğrulanmamış, sistem Partial) 1324 birim karşılaştırılabilmiştir. Ham uyum %88,97 (95% CI: %85,42–%91,99) ve ağırlıksız Cohen's κ ise 0,7783 (95% CI: 0,7154–0,8355) bulunmuştur. Bootstrap CI'lar 10.000 küme yeniden örneklemesi (15 öğrenci) ile hesaplanmıştır. Worksheet düzeyinde uyum %63,53 (WS14) ile %100,00 (WS7, WS12) arasında değişmektedir. WS14'te en yaygın uyuşmazlık insan doğru iken sistemin yanlış demesidir (n=47). Sistem Partial kararları (n=256 birim) metodolojik gerekçeyle dışlanmış; bu dışlama analizin koşullu niteliğini pekiştirmektedir.

---

## 8. Kaynakların yeniden bulunması

- İnsan kaynak dosyası: Cevap Anahtarı sayfası (xlsx SHA-256: `0cc4911d9fb1fbc65d0a75bd7a17eefd70e00fd4ea4e67d20dc247db0f350b08`)
- Sistem kararları: `comparison_all_groups.csv` — 10 Kasım 2026 site görüntüsü
- Yayımlanmış site: https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/#/findings

Bu rapor yeni bir kör doğrulama çalışması veya dergi kabulüne ilişkin bir kalite onayı değildir. Makalede kullanılacak iddiaların kapsamı, burada açıklanan veri sürümü, referans etiketler ve karşılaştırılabilir kayıtlarla sınırlıdır.
