# Amy 432-Frame MMLA Quality Audit Report

**Rol:** Kıdemli MMLA / Computer Vision doğrulama  
**Öğrenci:** Amy  
**Set:** 432 rafine keyframe (`Amy_frames/`)  
**Tarih:** 2026-07-10  
**Araçlar:** `scripts/amy_frame_quality_audit.py`, `CodapContentAnalyzer`, pHash (hash size 320×180)

---

## Yönetici Özeti

| Boyut | Bulgu | Düzey |
|-------|--------|-------|
| **Dedup / Δ görsel bilgi** | Ardışık pHash mesafesi medyan 6.0; %70.8 > eşik (4). Uzun süreli sıfır-plateau yok. | ✅ İyi |
| **CODAP çekirdek dönem (900–3600s)** | 233 kare; yüksek içerik skoru; tipik kareler decision tree + tablo + grafik | ✅ İyi |
| **Pedagojik süreklilik** | CODAP döneminde max 281s görsel boşluk (1103→1384s); öğrenci konuşması devam ediyor | ⚠️ Orta |
| **İçerik doğrulama** | 88/432 kare yalnızca gevşek şablon eşleşmesiyle geçmiş (pHash≤16, içerik skoru düşük) | ❌ Revizyon gerekli |
| **Görev dışı sızıntı** | Örn. `frame_0009` @ 276s → Google Drive (speech anchor) | ❌ Kritik |

**Nihai karar:** **Koşullu onay** — Claude Vision Audit’a, aşağıdaki post-hoc filtre uygulanmış alt küme ile geçilebilir. Tam 432’lik set, şablon guard revizyonu olmadan “kusursuz task” olarak kilitlenmemelidir.

---

## AŞAMA 1 — pHash Delta (Zamana Bağlı Değişim)

### Metod
Kronolojik 432 kare → 431 ardışık çift için \(d_H(f_t, f_{t+1})\) (pHash, 320×180).

### Özet istatistikler

| Metrik | Değer |
|--------|-------|
| Ortalama \(d_H\) | 7.01 |
| Medyan \(d_H\) | 6.0 |
| Std | 4.80 |
| Min / Max | 0 / 24 |
| % ≤ eşik (4) | **29.2%** |
| % > eşik (4) | **70.8%** |
| % > 8 (güçlü değişim) | 26.9% |
| \(d_H = 0\) çiftleri | 62 (14.4%) |
| \(d_H = 4\) (tam eşik) | 28 (6.5%) |
| Medyan zaman aralığı | 2.73 s |
| Max zaman aralığı | **281.4 s** |

### Dönem bazlı

| Dönem | Ort. \(d_H\) | % ≤ 4 |
|-------|-------------|-------|
| Pre-CODAP (<900s) | 6.65 | 32.4% |
| CODAP (900–3600s) | 6.91 | 27.5% |
| Post-CODAP (>3600s) | 7.42 | 30.6% |

### Yorum (uzman)

1. **Merdiven/dalgalanma (ideal):** Grafikte 800–1200s, 2200–2600s, 2800–3100s ve 4300–4500s bantlarında tepe değerleri (16–24) görülüyor; bunlar CODAP’ta pencere düzenleme, attribute sürükleme ve model güncellemeleriyle uyumlu.
2. **Sıfıra yakın süreklilik (hata sinyali):** 5+ ardışık çift boyunca \(d_H \le 4\) süren **plateau yok** (`near_zero_runs: []`). Dedup katmanı işlevsel.
3. **Kalan risk:** %29 düşük-Δ çift, motion tetikleyicinin hâlâ mikro-varyasyon ürettiğini gösterir; ancak bu kareler diske yazılmamış (dedup sonrası 432 kare). Disk setinde \(d_H=0\) komşuluk yok — ardışık duplicate kalmamış.

**Görsel çıktı:** `students/Amy/mmla_quality_audit/amy_phash_delta_analysis.png`

---

## AŞAMA 2 — Human-in-the-Loop QA (n=30, her 15 karede 1)

### Örnekleme
432 kareden sistematik örnek: indeks 0, 15, 30, … + son kare → **30 kare** (`qa_sample_manifest.json`).

### Likert ölçeği (1–5)
- **Netlik:** Piksel düzeyinde okunabilirlik (eksen, tablo, marker)
- **Bağlam:** İzole karede pedagojik eylemin anlaşılırlığı (self-contained)
- **Süreklilik:** Zaman ekseninde komşu karelerle pedagojik boşluk riski

### Validasyon tablosu

| # | frame_id | t (s) | Tetikleyici | Netlik | Bağlam | Süreklilik | Not |
|---|----------|-------|-------------|--------|--------|------------|-----|
| 1 | frame_0001 | 38.5 | speech | 5 | 3 | 2 | CODAP boş canvas + karar ağacı eklentisi; kurulum fazı |
| 2 | frame_0009 | 276.1 | speech | 5 | **1** | 4 | **Google Drive** — görev dışı; şablon false-positive |
| 3 | frame_0218 | 361.1 | motion | 5 | 3 | 4 | CODAP geçiş; içerik skoru düşük |
| 4 | frame_0021 | 444.1 | speech | 5 | 4 | 4 | CODAP aktif; tablo yükleniyor |
| 5 | frame_0026 | 786.1 | speech | 5 | 5 | 5 | Tam CODAP workspace |
| 6 | frame_0243 | 905.4 | motion | 5 | 5 | 5 | CODAP dönemi başlangıcı |
| 7 | frame_0253 | 1102.9 | motion | 5 | 5 | 5 | Karar ağacı + veri tablosu |
| 8 | frame_0265 | 1605.9 | motion | 5 | 5 | 5 | Scatter + seçici + eğitim/test bölmesi |
| 9 | frame_0048 | 1692.3 | speech | 5 | 5 | 5 | Çoklu panel CODAP |
| 10 | frame_0055 | 1755.8 | speech | 5 | 5 | 4 | Model iterasyonu görünür |
| 11 | frame_0062 | 1925.2 | speech | 5 | 5 | 4 | Tablo + grafik |
| 12 | frame_0298 | 1979.3 | motion | 5 | 5 | 4 | Attribute eksen ataması bağlamı |
| 13 | frame_0305 | 2053.9 | motion | 5 | 5 | 5 | Yoğun etkileşim bölgesi |
| 14 | frame_0084 | 2180.7 | speech | 5 | 5 | 5 | Karar ağacı dallanması |
| 15 | frame_0320 | 2221.5 | motion | 5 | 4 | 5 | İçerik iyi; zayıf şablon geçişi |
| 16 | frame_0325 | 2410.3 | motion | 5 | 5 | 5 | Model kayıt tablosu |
| 17 | frame_0334 | 2714.5 | motion | 5 | 5 | 5 | TP/TN/FP/FN görünür |
| 18 | frame_0341 | 3072.6 | motion | 5 | 5 | 5 | MCR tooltip — mikro-davranış için ideal |
| 19 | frame_0123 | 3210.5 | speech | 5 | 5 | 4 | Sınıflandırma kayıtları + ağaç |
| 20 | frame_0356 | 3323.1 | motion | 5 | 5 | 5 | Derinlik/performans metrikleri |
| 21 | frame_0364 | 3447.8 | motion | 5 | 5 | 4 | Çoklu yineleme tablosu |
| 22 | frame_0147 | 3688.7 | speech | 5 | 5 | 4 | CODAP sonları; hâlâ zengin |
| 23 | frame_0378 | 3823.8 | motion | 5 | 5 | 5 | Grafik + tablo senkron |
| 24 | frame_0160 | 3997.4 | speech | 5 | 5 | 5 | Model karşılaştırma |
| 25 | frame_0395 | 4267.6 | motion | 5 | 5 | 5 | İleri model durumu |
| 26 | frame_0405 | 4345.8 | motion | 5 | 4 | 4 | Zayıf şablon bayrağı |
| 27 | frame_0178 | 4464.4 | speech | 5 | 5 | 4 | Tartışma + CODAP |
| 28 | frame_0188 | 4607.0 | speech | 5 | 5 | 5 | Tuz ekseni + kayıt tablosu |
| 29 | frame_0424 | 4844.8 | motion | 5 | 5 | 5 | Geç dönem model |
| 30 | frame_0432 | 4969.4 | motion | 5 | 5 | 5 | Oturum sonu — tam CODAP |

### QA özet skorları

| Boyut | Ortalama | Min–Max |
|-------|----------|---------|
| Netlik | **5.00** | 5–5 |
| Bağlam | **4.53** | 1–5 |
| Süreklilik | **4.37** | 2–5 |

**Zayıf şablon geçişi (içerik skoru <4):** 10/30 örneklem karesi.

---

## Kayıp Dönem / Kör Nokta Analizi

### Diarizasyon çapraz sorgu (`Amy_hybrid_diarization.json`)

**Öğrenci konuşma kümeleri** (≥12s, 3s içinde birleştirilmiş): 5 burst.

| Zaman (s) | Görsel kapsama | Tür | Pedagojik not |
|-----------|----------------|-----|----------------|
| 317–335 | 0 kare | zero_coverage | Pre-CODAP; “gelmedi hocam” — görsel yok, kabul edilebilir |
| 499–513 | 0 kare | zero_coverage | Pre-CODAP öğretmen brifingi |
| 4647–4661 | 0 kare | zero_coverage | Oturum sonu; CODAP dışı |

### CODAP döneminde büyük temporal boşluklar

| Boşluk (s) | Aralık (s) | Öğrenci segmenti (boşlukta) | Yorum |
|------------|------------|-----------------------------|-------|
| **281.4** | 1103 → 1384 | 10 segment | En kritik kör nokta; muhtemelen statik ekran + sözlü tartışma |
| 196.7 | 2410 → 2607 | 7 segment | Model değerlendirme sırasında seyrek örnekleme |
| 150.4 | 2753 → 2903 | — | Düşük hareket dönemi |
| 150.0 | 1426 → 1576 | — | Ara dinlenme / izleme |

CODAP dönemi (900–3600s): **233 kare**, ort. aralık 11.5s, max **281.4s**.

**Sonuç:** Agresif filtreleme değil, **düşük görsel entropi + uzun cooldown** birleşimi bazı yoğun konuşma pencerelerinde görsel örneklemeyi seyrekleştiriyor. Tam kör nokta (0 kare) CODAP çekirdeğinde tespit edilmedi.

---

## Kritik Bulgu: Şablon Guard Gevşekliği

`--codap-task-phash-threshold 16` ile **88 kare** yalnızca şablon eşleşmesiyle “task” sayılıyor; `CodapContentAnalyzer.is_codap_task()` **false**.

Örnek: `frame_0009` @ 276s — görsel QA’da **Google Drive**; guard nedeni: `template:amy_codap_frame_0314` @ distance=16.

**Önerilen düzeltme (kod):**
```python
# CodapTaskGuard.classify içinde:
if best_dist <= self.phash_threshold:
    signals = CodapContentAnalyzer.analyze(frame_bgr)
    if CodapContentAnalyzer.is_codap_task(signals) or best_dist <= 10:
        return CodapTaskMatch(True, ...)
```

Veya CLI: `--codap-task-phash-threshold 12` + mevcut `require_codap_content`.

---

## Karar ve Öneri

### pHash / motion / cooldown parametreleri

| Parametre | Mevcut | Değerlendirme |
|-----------|--------|---------------|
| `--phash-threshold 4` | 4 | ✅ Kilitlenebilir — plateau yok, %71 bilgi kazancı |
| `--motion-threshold 0.012` | 0.012 | ✅ Uygun — aşırı mikro-tekrar diske yansımıyor |
| `--cooldown-ms 1500` | 1500 | ⚠️ CODAP’ta 60–280s boşluklara katkı; isteğe bağlı 1000ms |

### Vision Audit onayı

| Seçenek | Öneri |
|---------|-------|
| **432 tam set → Claude Vision** | ❌ Şimdilik hayır — 88 zayıf şablon + 1+ görev dışı sızıntı |
| **CODAP çekirdek (900–3600s, içerik skoru ≥4) → Vision** | ✅ **Evet** — ~210–233 kare, yüksek utility |
| **Post-hoc filtre + revizyon sonrası tam set** | ✅ Tercih edilen yol |

### Uzman nihai görüşü

> **Koşullu onay:** Mevcut dedup ve içerik analizörü mimarisi sağlam; pHash delta profili Vision beslemesi için yeterli çeşitlilik gösteriyor. Ancak **CodapTaskGuard şablon eşiğinin gevşekliği** nedeniyle pre-CODAP ve görev dışı kareler sete sızıyor.  
>  
> **Aksiyon sırası:**  
> 1. Şablon + içerik birleşik guard revizyonu  
> 2. Mevcut 432 üzerinde post-hoc export (`content_score≥4` ∧ ¬`google_drive`)  
> 3. Claude 3.5 Sonnet Vision Audit — alt küme ile pilot  
> 4. Pilot κ / rubrik tutarlılığı sonrası tam kohort

---

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `amy_phash_delta_analysis.png` | Aşama 1 grafiği |
| `amy_frame_quality_audit_metrics.json` | Sayısal metrikler |
| `qa_sample_manifest.json` | 30 karelik QA alt kümesi |
| `amy_hitl_validation_report.md` | Bu rapor |
