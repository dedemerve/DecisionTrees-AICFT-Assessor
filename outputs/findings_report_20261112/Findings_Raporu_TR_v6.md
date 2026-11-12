# El yazısı çıkarım doğruluğu ve insan–sistem puanlama uyumu

**Rapor tarihi:** 12 Kasım 2026  
**Veri inceleme tarihi:** 9–12 Kasım 2026  
**Kapsam:** WS1–WS14, 15 öğrenci  
**Önceki sürüm:** v5 (10 Kasım 2026) — WS1–WS12 kapsıyordu  
**Bu sürümde eklenen:** WS13 ve WS14 semantik inceleme sonuçları  
**Amaç:** Makalenin Findings bölümüne temel olacak bulguları, hesaplama kapsamını ve sınırlılıklarını birlikte sunmak.

---

## 1. Temel sonuçlar

İki analiz farklı süreçleri ölçmektedir. El yazısı çıkarım analizi, LLM'nin öğrencinin yazısını doğru okuyup çıkarabilmesini; puanlama uyumu analizi ise insanın öğrenci cevabına verdiği kategoriyle yayımlanmış sistem kararının eşleşmesini değerlendirmektedir.

- **El yazısı çıkarım doğruluğu (WS1–WS12):** 1164 doğru ve 32 yanlış çıkarım; 1196 değerlendirilmiş öğrenci–madde kaydı üzerinden **%97,32**.
- **İnsan–sistem puanlama uyumu (WS1–WS12):** karşılaştırılabilir 556 kaydın 531'inde aynı kategori; **%95,50 ham uyum**, ağırlıksız **Cohen's κ = 0,8598**.
- **İnsan–sistem puanlama uyumu (WS13 — Karar Ağacı / CODAP Arbor):** 373 eşleşen kayıt; **%51,21 ham uyum**, ağırlıksız **Cohen's κ = 0,2803**.
- **İnsan–sistem puanlama uyumu (WS14 — Xeno simülasyonu):** 495 eşleşen kayıt; **%76,36 ham uyum**, ağırlıksız **Cohen's κ = 0,3513**.

WS1–WS12 sonuçları insan kod kitabına (Cevap Anahtarı sayfası) dayalıdır. WS13 ve WS14 sonuçları bağımsız semantik incelemeye dayanmaktadır; bu iki analiz birbiriyle doğrudan karşılaştırılmamalıdır.

---

## 2. Kaynaklar ve eşleştirme

### WS1–WS12

İnsan değerlendirmeleri `/Users/mrved/Downloads/Copy of Code book 12092026.xlsx` dosyasının **Cevap Anahtarı** ve **LLM ve Öğrenci Yanıtları** sayfalarından alınmıştır. Sistem kararları [Findings sitesinin](https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/#/findings) 9 Kasım 2026 tarihinde erişilen yayımlanmış verilerinden hesaplanmıştır. Site daha sonra güncellenirse bu rapordaki sonuçlar yeni sürümün sonuçları olarak sunulmamalıdır.

### WS13

İnsan değerlendirmeleri `outputs/ws13_semantic_review_20261111/item_reviews.csv` dosyasından alınmıştır. Sistem kararları `students/*/WS13/scoring.json` dosyalarından, `rubrics/WS13_rubric.json`'daki `max_score` değerleri kullanılarak türetilmiştir. WS13 madde kodları (A1–G2) ile sistem item ID'leri (DT_A_Q1 vb.) arasındaki eşleştirme `ITEM_MAP` sözlüğüyle yapılmıştır. 25 madde eşleştirilmiş; `DT_E_TP` ve `DT_E_FP` semantik incelemede bulunmadığından dışarıda kalmıştır. Toplam eşleşen kayıt: 15 öğrenci × 25 madde üzerinden 373 (blank kayıtlar dahil, ancak max_score=0 olanlar hariç).

### WS14

İnsan değerlendirmeleri `outputs/ws14_semantic_review_20261111/item_reviews.csv` dosyasından alınmıştır. Sistem kararları `students/*/WS14/scoring.json` dosyalarından, `worksheets/WS14/rubric.json`'daki `max_score` değerleri kullanılarak türetilmiştir. Madde ID'leri (DTI_01–DTI_33) iki kaynak arasında doğrudan eşleşmektedir. WS14 puanlaması 12 Kasım 2026'da `score_ws14_ws15.py --force --worksheet WS14` komutuyla yeniden çalıştırılmıştır; bu çalıştırmada rubrik güncellemeleri (credit_levels) ve Xeno simülasyonuna özgü sistem prompt takviyesi uygulanmıştır.

---

## 3. WS1–WS12 Sonuçları (v5'ten aynen)

### 3.1. El yazısı çıkarım doğruluğu

| Worksheet | Doğru | Yanlış | Payda | Doğruluk | WS yok |
|---|---:|---:|---:|---:|---:|
| WS1 | 143 | 0 | 143 | %100,00 | 22 |
| WS3 | 100 | 4 | 104 | %96,15 | 16 |
| WS4 | 57 | 8 | 65 | %87,69 | 10 |
| WS5 | 324 | 1 | 325 | %99,69 | 50 |
| WS6 | 161 | 8 | 169 | %95,27 | 26 |
| WS7 | 84 | 7 | 91 | %92,31 | 14 |
| WS10 | 104 | 0 | 104 | %100,00 | 16 |
| WS12 | 191 | 4 | 195 | %97,95 | 30 |
| **Toplam** | **1164** | **32** | **1196** | **%97,32** | **184** |

### 3.2. İnsan–sistem puanlama uyumu (WS1–WS12)

| Worksheet | Karşılaştırılan | Aynı kategori | Ham uyum | Cohen's κ |
|---|---:|---:|---:|---:|
| WS1 | 139 | 136 | %97,84 | 0,9205 |
| WS3 | 104 | 100 | %96,15 | 0,4851 |
| WS4 | 56 | 45 | %80,36 | 0,5769 |
| WS5 | 13 | 13 | %100,00 | 1,0000 |
| WS6 | 13 | 13 | %100,00 | Tanımsız |
| WS7 | 50 | 44 | %88,00 | 0,3590 |
| WS10 | 102 | 101 | %99,02 | 0,9394 |
| WS12 | 79 | 79 | %100,00 | 1,0000 |
| **Toplam** | **556** | **531** | **%95,50** | **0,8598** |

---

## 4. WS13 İnsan–sistem puanlama uyumu

### 4.1. Yöntem notu

WS13, açık uçlu yorumlayıcı maddeler içeren karar ağacı worksheetidir. Semantik inceleme, 15 öğrencinin 25 maddesini dört kategoride değerlendirmiştir: correct / wrong / partial / blank. Sistem kararları aynı dört sınıfa (`correct / incorrect / partial / blank`) dönüştürülmüştür. `blank` kategorisinin sistem tarafında temsili sınırlıdır: scoring.json `not_attempted` bayrağı içermediğinden gerçekte boş bırakılan maddeler `incorrect` olarak görünmektedir.

### 4.2. Sonuçlar

**N=373, ham uyum=%51,21, Cohen's κ=0,2803**

**Karışıklık matrisi (satırlar=insan, sütunlar=sistem):**

| İnsan / Sistem | correct | incorrect | partial | blank |
|---|---:|---:|---:|---:|
| correct | 136 | 24 | 67 | 0 |
| incorrect | 0 | 2 | 1 | 0 |
| partial | 12 | 25 | 53 | 0 |
| blank | 0 | 53 | 0 | 0 |

**Sınıf metrikleri:**

| Kategori | Support | Precision | Recall |
|---|---:|---:|---:|
| correct | 227 | 0,919 | 0,599 |
| incorrect | 3 | 0,019 | 0,667 |
| partial | 90 | 0,438 | 0,589 |
| blank | 53 | N/A | 0,000 |

### 4.3. Yorum

Temel sorunlar:
- **correct → partial kayması (n=67):** Sistem insan değerlendirmesine göre çok sık kısmi kredi veriyor. Bu, yorumlayıcı maddelerde sistemin standart rubrik kriterlerini katı uygulamasından kaynaklanmaktadır.
- **blank recall=%0 (n=53):** Sisteme göre tüm blank maddeler `incorrect`. scoring.json'da `not_attempted` ayrımı bulunmamaktadır.
- **partial precision=0,438:** Sistemin partial kararlarının yarısından fazlası insanla örtüşmüyor.

---

## 5. WS14 İnsan–sistem puanlama uyumu

### 5.1. Yöntem notu

WS14, Xeno CODAP simülasyonuna dayalı worksheettir. Her öğrenci kendi simülasyon çıktısını yorumlar; sayısal değerler (vaka sayısı, yüzdeler) öğrenciye özeldir. Semantik inceleme bu özelliği göz önünde bulundurarak değerlendirme yapmıştır.

Sistem puanlaması bu analize hazırlanmak için iki güncelleme aldı:
1. **Rubrik güncellemesi (`worksheets/WS14/rubric.json`):** DTI_01–DTI_08 dahil birden fazla bileşen içeren maddeler için `credit_levels` eklendi. Öğrencinin bileşenlerden yalnızca birini doğru ifade etmesi tam kredi için yeterli sayıldı.
2. **Sistem prompt takviyesi (`worksheet_assessor.py`):** Xeno simülasyonuna özgü yorum kuralları eklendi (öğrenciye özel sayılara göre değerlendirme, kısa cevap toleransı, Xeno değişmezleri, blank tespiti).

### 5.2. Sonuçlar

**N=495, ham uyum=%76,36, Cohen's κ=0,3513**

Önceki sürümle karşılaştırma: ham uyum %41,41'den %76,36'ya, κ 0,1136'dan 0,3513'e yükseldi.

**Karışıklık matrisi (satırlar=insan, sütunlar=sistem):**

| İnsan / Sistem | correct | incorrect | partial | blank |
|---|---:|---:|---:|---:|
| correct | 345 | 32 | 22 | 0 |
| incorrect | 3 | 11 | 6 | 0 |
| partial | 31 | 11 | 22 | 0 |
| blank | 0 | 12 | 0 | 0 |

**Madde düzeyi (en düşük uyumlu 10 madde):**

| Madde | n | Doğruluk |
|---|---:|---:|
| DTI_27 | 15 | %26,7 |
| DTI_05 | 15 | %33,3 |
| DTI_30 | 15 | %40,0 |
| DTI_19 | 15 | %46,7 |
| DTI_23 | 15 | %46,7 |
| DTI_31 | 15 | %46,7 |
| DTI_28 | 15 | %53,3 |
| DTI_33 | 15 | %53,3 |
| DTI_21 | 15 | %60,0 |
| DTI_25 | 15 | %60,0 |

**Tam uyumlu maddeler:** DTI_03, DTI_08, DTI_10, DTI_13, DTI_16, DTI_18 (%100,0).

### 5.3. Kalan sorunlar

- **partial → correct kayması (n=31):** Sistemin bazı maddeler için gereksiz yere tam kredi verdiği görülüyor. Rubrik güncelleme ile correct yanlılığı arttı.
- **blank recall=%0 (n=12):** WS13 ile aynı yapısal sorun.
- DTI_27, DTI_30, DTI_31 gibi alt maddelerde hâlâ düşük uyum; bu maddelerin rubriği daha fazla dikkat gerektiriyor.

---

## 6. Worksheet karşılaştırması

| Worksheet | Yöntem | N | Ham uyum | Cohen's κ |
|---|---|---:|---:|---:|
| WS1–WS12 toplam | Kod kitabı | 556 | %95,50 | 0,8598 |
| WS13 | Semantik inceleme | 373 | %51,21 | 0,2803 |
| WS14 | Semantik inceleme | 495 | %76,36 | 0,3513 |

**Not:** WS1–WS12 ve WS13–WS14 farklı insan referans kaynakları kullandığından bu tablo doğrudan karşılaştırma için değil, kapsam özeti olarak sunulmaktadır.

---

## 7. Hesaplama ve doğrulama

WS1–WS12 için v5'teki hesaplama yöntemi aynen geçerlidir (bkz. v5 Bölüm 7).

WS13 ve WS14 metrikleri Python ile hesaplanmıştır. Ham uyum Pₒ = aynı kategori sayısı / toplam eşleşen kayıt sayısı; ağırlıksız çok kategorili Cohen's κ = (Pₒ − Pₑ) / (1 − Pₑ); Pₑ = insan ve sistem marjinal oranlarının kategori bazında çarpımlarının toplamı.

WS13 blank recall'unun %0 olması, scoring.json'da gerçek blank kayıtların `not_attempted` olarak işaretlenmediğinden kaynaklanmaktadır. Bu durum κ'yı düşürür; düzeltilmiş bir karşılaştırma için blank maddeler her iki kaynakta da dışlanabilir.

---

## 8. Makalenin Findings bölümüne uyarlanabilir metin

### WS1–WS12

WS1–WS12 kapsamında mevcut sekiz worksheet için 15 öğrencinin toplam 1196 değerlendirilebilir öğrenci–madde kaydında el yazısı çıkarım doğruluğu %97,32 bulunmuştur. Yayımlanmış nihai sistem kararlarıyla karşılaştırılabilir 556 kayıtta ham uyum %95,50, ağırlıksız Cohen's κ ise 0,86 olarak hesaplanmıştır.

### WS13

WS13'te (Karar Ağacı / CODAP Arbor) semantik inceleme yöntemiyle oluşturulan insan etiketleriyle 373 öğrenci–madde çifti karşılaştırılmıştır. Ham uyum %51,21, ağırlıksız Cohen's κ ise 0,28 olarak bulunmuştur. Temel uyuşmazlık kaynağı, insan değerlendirmesinin tam kredi verdiği durumlarda sistemin kısmi kredi atamasıdır (n=67). Blank maddeler sistemde `incorrect` olarak işaretlendiğinden blank recall %0'dır.

### WS14

WS14'te (Xeno simülasyonu) semantik inceleme yöntemiyle oluşturulan insan etiketleriyle 495 öğrenci–madde çifti karşılaştırılmıştır. Ham uyum %76,36, ağırlıksız Cohen's κ ise 0,35 olarak bulunmuştur. Rubrik ve sistem prompt güncellemesinin ardından uyum, önceki çalıştırmaya göre belirgin biçimde artmıştır (%41 → %76). Hâlâ uyuşmazlık görülen alanlar: partial insan etiketi için sistem tam kredi atıyor (n=31) ve blank maddeler sistemde incorrect görünüyor (n=12).

---

## 9. Kaynakların yeniden bulunması

- İnsan kaynak dosyası (WS1–WS12): `/Users/mrved/Downloads/Copy of Code book 12092026.xlsx`
- Semantik inceleme (WS13): `outputs/ws13_semantic_review_20261111/item_reviews.csv`
- Semantik inceleme (WS14): `outputs/ws14_semantic_review_20261111/item_reviews.csv`
- Yayımlanmış site: https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/#/findings
- WS14 rubrik: `worksheets/WS14/rubric.json` (12 Kasım 2026 güncellendi)
- WS14 scoring scripti: `scripts/score_ws14_ws15.py`, çalışma logu: `logs/score_ws13_ws14_20261112_065223.jsonl`

Bu rapor yeni bir kör doğrulama çalışması veya dergi kabulüne ilişkin bir kalite onayı değildir. Makalede kullanılacak iddiaların kapsamı, burada açıklanan veri sürümü, referans etiketler ve karşılaştırılabilir kayıtlarla sınırlıdır.
