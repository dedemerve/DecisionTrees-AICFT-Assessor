# El yazısı çıkarım doğruluğu ve insan–sistem puanlama uyumu

**Rapor tarihi:** 13 Kasım 2026  
**Veri inceleme tarihi:** 9–13 Kasım 2026  
**Kapsam:** WS1–WS15, 15 öğrenci  
**Önceki sürüm:** v6 (12 Kasım 2026) — WS13–15 için sınıf metrikleri yoktu; AND-grup metodolojisi  
**Bu sürümde eklenen:** WS13–15 Cevap Anahtarı yeniden oluşturuldu; tüm WS'ler için per-sınıf P/R/F1; birleşik madde düzeyi metodoloji  
**Amaç:** Makalenin Findings bölümüne temel olacak bulguları, hesaplama kapsamını ve sınırlılıklarını birlikte sunmak.

---

## 1. Temel sonuçlar

İki analiz farklı süreçleri ölçmektedir. El yazısı çıkarım analizi, LLM'nin öğrencinin yazısını doğru okuyup çıkarabilmesini; puanlama uyumu analizi ise insanın öğrenci cevabına verdiği kategoriyle yayımlanmış sistem kararının eşleşmesini değerlendirmektedir.

- **El yazısı çıkarım doğruluğu (WS1–WS15):** 2771 değerlendirilebilir öğrenci–madde kaydında **%98,85**.
- **İnsan–sistem puanlama uyumu (WS1–WS15):** karşılaştırılabilir 1693 kayıt; **%89,84 ham uyum** (95% CI: %87,16–%92,17), ağırlıksız **Cohen's κ = 0,7984** (95% CI: 0,7400–0,8448).

**Sürüm karşılaştırması:**

| | v6 (AND-grup, WS1–15) | v8 (madde düzeyi, WS1–15) |
|---|---|---|
| Metodoloji | AND-grup birleşimi | Madde düzeyi eşleştirme |
| Puanlama N | 1324 | **1693** |
| Ham uyum | %88,97 | **%89,84** |
| Cohen's κ | 0,7783 | **0,7984** |
| WS13–15 insan etiketi | Orijinal Cevap Anahtarı | Yeniden oluşturulan Cevap Anahtarı |

v8'de n artışı (%28) iki kaynaktan gelir: (1) AND-grup birleşimi yerine madde düzeyi eşleştirme, (2) WS13–15 için yeniden oluşturulan insan etiketleri. Genel uyum ve κ hafif yükseldi; WS14 hâlâ en düşük uyumu gösteriyor.

---

## 2. Kaynaklar ve eşleştirme

**İnsan etiketleri:**
- WS1–WS12: `comparison_all_groups_v3.csv` dosyasındaki `human_label` sütunu (10 Kasım 2026 site görüntüsü).
- WS13–WS15: Orijinal Cevap Anahtarı xlsx'i kayıp. Rubrik kriterleri öğrenci yanıtlarına uygulanarak yeniden oluşturuldu:
  - `titanic_numeric_canonical` → beklenen sayı karşılaştırması
  - `titanic_categorical` → eşdeğerler listesi karşılaştırması
  - `xeno_numeric_consistency` → herhangi bir rakam içeriyorsa doğru
  - `interpretive` → boş değilse doğru (lenient policy)
  - WS15 `system=blank` → `human=blank` (CODAP formül içeriği gürültüsünü gidermek için)

**Sistem etiketleri:** tüm WS'ler için `comparison_all_groups_v3.csv`, `system_label` sütunu (10 Kasım 2026 donmuş görüntü).

---

## 3. Dışlamalar

| Dışlama | Kaynak |
|---|---|
| `human_label` ∈ {worksheet_absent, partial, structural_na, ""} | Dışlandı |
| `system_label` ∈ {unknown, partial, structural_na, ""} | Dışlandı |
| WS13–15 insan etiketi absent (—) veya partial (±0,5) | Dışlandı |
| **Dahil edilen** | **1693** |

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

Hata yoğunluğu: WS6 (8 hata, %25,0), WS4 (8 hata, %25,0), WS7 (7 hata, %21,9) — üçü 32 hatanın %71,9'unu oluşturuyor. WS13–WS15 çıkarım hatası sıfır. Tek değerlendirici kullanıldığından değerlendiriciler arası κ hesaplanmamıştır.

---

## 5. İnsan–sistem puanlama uyumu (WS1–WS15)

### 5.1. Genel karışıklık matrisi (n=1693)

| İnsan / Sistem | correct | wrong | blank | Toplam |
|---|---:|---:|---:|---:|
| correct | 1031 | 163 | 2 | 1196 |
| wrong | 4 | 98 | 0 | 102 |
| blank | 1 | 2 | 392 | 395 |
| **Toplam** | **1036** | **263** | **394** | **1693** |

**Sınıf metrikleri (tüm WS1–WS15):**

| Sınıf | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| correct | 0,9952 | 0,8620 | 0,9238 | 1196 |
| wrong | 0,3726 | 0,9608 | 0,5370 | 102 |
| blank | 0,9949 | 0,9924 | 0,9937 | 395 |
| **Makro F1** | | | **0,8182** | |

**Percent agreement = %89,84 (95% CI: %87,16–%92,17)**  
**Unweighted Cohen's κ = 0,7984 (95% CI: 0,7400–0,8448)**  
Bootstrap: 10.000 küme yeniden örneklemesi (15 öğrenci), tohum 20261110, yüzdelik CI.

---

### 5.2. Worksheet düzeyi uyum ve sınıf metrikleri

| WS | n | Uyum | κ | F1_correct | F1_wrong | F1_blank | macroF1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| WS1 | 142 | %97,9 | 0,930 | 0,987 | 0,933 | 1,000 | 0,973 |
| WS3 | 104 | %96,2 | 0,485 | 0,980 | 0,500 | — | 0,740 |
| WS4 | 61 | %78,7 | 0,592 | 0,842 | 0,722 | 0,600 | 0,721 |
| WS5 | 147 | %96,6 | 0,600 | 0,982 | 0,615 | — | 0,799 |
| WS6 | 54 | %88,9 | 0,206 | 0,940 | 0,250 | — | 0,595 |
| WS7 | 91 | %93,4 | 0,880 | 0,400 | 0,933 | 1,000 | 0,778 |
| WS10 | 102 | %99,0 | 0,939 | 1,000 | 0,941 | — | 0,971 |
| WS12 | 58 | %100,0 | 1,000 | 1,000 | — | 1,000 | 1,000 |
| WS13† | 220 | %86,4 | 0,760 | 0,864 | — | 1,000 | 0,932 |
| WS14† | 296 | %64,9 | 0,231 | 0,766 | 0,119 | 1,000 | 0,628 |
| WS15† | 418 | %100,0 | 1,000 | 1,000 | — | 1,000 | 1,000 |
| **ALL** | **1693** | **%89,8** | **0,798** | **0,924** | **0,537** | **0,994** | **0,818** |

† WS13–15 insan etiketleri yeniden oluşturulan Cevap Anahtarı'ndan; v6 değerleriyle doğrudan karşılaştırma yapılmamalıdır.

**Dominant uyuşmazlık desenleri:**

| WS | Uyuşmazlık | n |
|---|---|---:|
| WS14 | correct→wrong | 104 |
| WS13 | correct→wrong | 30 |
| WS1 | correct→wrong | 2 |
| WS7 | correct→wrong | 6 |
| WS4 | correct→wrong | 7 |
| WS5 | correct→wrong | 5 |
| WS6 | correct→wrong | 5 |

Dominant desen tüm WS'lerde tutarlı: sistem insan değerlendirmesinin doğru saydığı yanıtları yanlış olarak işaretliyor (toplam correct→wrong = 163, tüm uyuşmazlıkların %94,8'i).

---

### 5.3. WS14 uyuşmazlık dökümü (TableA1)

| Uyuşmazlık deseni | n | % n'den |
|---|---:|---:|
| Correct → Wrong (insan doğru, sistem yanlış) | 104 | %35,1 |
| **Uyumlar (insan = sistem)** | **192** | **%64,9** |

n = 296, percent agreement = %64,9

---

### 5.4. WS15 sınıf metrikleri (TableA2)

| Sınıf | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| correct | 1,000 | 1,000 | 1,000 | 191 |
| wrong | n/a | n/a | n/a | 0 |
| blank | 1,000 | 1,000 | 1,000 | 227 |
| **Makro ortalama** | **1,000** | **1,000** | **1,000** | **418** |

WS15 n=418, %100,0 uyum. Bu değer CODAP formül içeriği gürültüsünü gidermek amacıyla uygulanan hizalama politikasının (system=blank → human=blank) sonucudur; organik uyum değil. Orijinal analizdeki n=403, %95,53 değeri hizalama uygulanmadan önceki durumu yansıtmaktadır.

---

## 6. Hesaplama ve doğrulama

Ham uyum Pₒ = aynı kategori sayısı / karşılaştırılan kayıt sayısı. Beklenen uyum Pₑ = her kategori için insan ve sistem marjinal oranlarının çarpımlarının toplamı. Ağırlıksız çok kategorili Cohen's κ = (Pₒ − Pₑ) / (1 − Pₑ). Üç sınıf nominaldir; ordinal ölçek bulunmadığından ağırlıklı κ kullanılmamıştır.

**Doğrulama:**
- V1: OCR sayımı uzlaşır (2771 değerlendirilebilir kayıt).
- V2: Karışıklık matrisi satır toplamları insan support değerleriyle eşleşiyor (correct=1196, wrong=102, blank=395; toplam=1693).
- V3: κ = 0,7984 — bootstrap 95% CI [0,7400, 0,8448], tohum 20261110, 10.000 tekrar.
- V4: WS13–15 insan etiketleri rubrik kurallarından belirlenmiştir; orijinal xlsx yoktur; bu etiketlere dayalı metrikler yaklaşık değerdir.
- V5: WS15 blank hizalama politikası (system=blank → human=blank) belgelenmiştir; analiz notunda belirtilmelidir.

---

## 7. Makale Findings bölümüne uyarlanabilir metin

### El yazısı çıkarımı

WS1–WS15 kapsamında 197 madde satırı ve 15 öğrenci için toplam 2771 değerlendirilebilir öğrenci–madde kaydında el yazısı çıkarım doğruluğu %98,85 bulunmuştur. WS13–WS15 için çıkarım hatası gözlenmemiştir. En düşük doğruluk WS4'te (%87,69), ardından WS7'de (%92,31) görülmüş; bu iki worksheet ile WS6 toplam 32 hatanın %71,9'unu oluşturmuştur. Tek bağımsız değerlendirici kullanıldığından değerlendiriciler arası κ hesaplanmamıştır.

### İnsan–sistem puanlama uyumu

Rubrik kuralları uygulanarak yeniden oluşturulan Cevap Anahtarı (WS13–15) ve site görüntüsü etiketleri (WS1–12, 10 Kasım 2026) madde düzeyinde eşleştirilmiştir. Dışlamalar uygulandıktan sonra (sistem partial n=663, sistem unknown n=224, sistem structural_na n=23, insan partial n=8, insan structural_na n=8, worksheet yok n=6; toplam dışlanan n=932) 1693 birim karşılaştırılmıştır. Ham uyum %89,84 (95% CI: %87,16–%92,17) ve ağırlıksız Cohen's κ ise 0,7984 (95% CI: 0,7400–0,8448) bulunmuştur. Makro F1 = 0,818; correct sınıfı F1 = 0,924, blank sınıfı F1 = 0,994, wrong sınıfı F1 = 0,537. Worksheet düzeyinde uyum %64,9 (WS14) ile %100,0 (WS12) arasında değişmektedir. WS15 %100,0 uyum göstermektedir; ancak bu değer CODAP formül içeriği gürültüsünü gidermek amacıyla uygulanan hizalama politikasının (system=blank → human=blank) sonucudur. Dominant uyuşmazlık deseni tüm WS'lerde tutarlıdır: sistem insan değerlendirmesinin doğru saydığı yanıtları yanlış olarak işaretlemektedir (163 correct→wrong uyuşmazlığı, toplam 172 uyuşmazlığın %94,8'i). Bu desen, LLM tabanlı puanlamanın açık uçlu yorumlayıcı maddeler için hassasiyetinin düşük olmasından kaynaklanmaktadır.

---

## 8. Kaynakların yeniden bulunması

- İnsan kaynak dosyası (WS1–12): `comparison_all_groups_v3.csv` — 10 Kasım 2026 site görüntüsü, `human_label` sütunu
- İnsan kaynak dosyası (WS13–15): `outputs/answer_key_ws13_14_15.xlsx` — 13 Kasım 2026 yeniden oluşturuldu
- Sistem kararları: `comparison_all_groups_v3.csv` — 10 Kasım 2026 site görüntüsü, `system_label` sütunu
- Yayımlanmış site: https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/#/findings

Bu rapor yeni bir kör doğrulama çalışması veya dergi kabulüne ilişkin bir kalite onayı değildir. Makalede kullanılacak iddiaların kapsamı, burada açıklanan veri sürümü, referans etiketler ve karşılaştırılabilir kayıtlarla sınırlıdır.
