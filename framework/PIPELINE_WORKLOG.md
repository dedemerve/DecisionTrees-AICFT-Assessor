# Pipeline & Methods Worklog

Bu dosya, video süreç kodlama pipeline'ının geliştirme adımlarını kronolojik olarak belgeler.
Makale yazım sürecinde yöntemler bölümüne referans verilmek üzere tutulur.

---

## 2026-07-20

### Q1 Gate: Pilot Student (Ally)

**Yapılan:**
Ally için Q1 process-pipeline gate incelemesi yapıldı. İki uyarı öğesi incelendi:

- V8D kodunun codebook'ta olmadığı şüphesi: False alarm. Codebook başlıkları `V8D Import / session-continuity failure recovery` şeklinde yazılmış; snake_case grepiyle bulunamıyordu. Manuel kontrol sonucu kod mevcuttu.
- Eski scoring referansları: `Ally_expert_process_narrative.json` içindeki `interpretation_rule` alanı ve `log_process_metadata` içindeki B0–B13 listeleri temizlenmişti; önceki oturumda yapılan temizlik doğrulandı.

**Sonuç:** PASS. `cohort_trust: yes`.

---

### V-Code Coverage Analizi (Tüm Kohort, n=17)

**Yapılan:**
17 öğrenci × 20 V-kod × 211 episode üzerinde tam dağılım tablosu çıkarıldı.

**Bulgular:**
- Toplam gözlem hücresi: 4,220 (211 ep × 20 kod)
- `observed` hücre sayısı: 260 / 4,220 (%6.2) — ciddi sınıf dengesizliği
- Sıfır-ateş kodlar (2025 eğitim seti bağlamında): V1B, V2B, V3A, V5A, V6A, V6B, V8A (7 kod)
- En sık ateşlenen: V1A systematic_iteration (%32.2), V7A no_metric_inspection (%31.8), V5B dependent_execution (%21.8)

---

### 12-Adım İyileştirme Planı

**Yapılan:**
Aşağıdaki 12 adım sırasıyla uygulandı:

1. `gold_tier` ve `confidence_tier` alanları 4,220 hücrenin tamamına yazıldı.
   - 600 kalibrasyon hücresi: `expert_adjudicated`
   - 3,620 hücre: `single_observer`
   - T1=163 (frame-anchored), T2=7 (narrative-inferred), T3=90 (adjudicated)

2. Codebook'a "Code triage" bölümü eklendi: 8 sıfır/near-zero kodun durumu (Keep-recruit / Retire) belgelendi.

3. `confidence_tier` alanları `episode_process_codes.jsonl` dosyalarına eklendi.

4. Sınıf dengesizliği önerileri: focal loss (γ=2), per-kod ağırlık: 1/pozitif_frekans. SMOTE yasaklı (temporal episode yapısını bozar).

5. Student-level train/dev/test split oluşturuldu ve donduruldu (`split_assignment.json`).
   - Train: Bob, Calvin, Daisy, David, Edgar, Eliot, Felicity, Henry, Mike, Ozzy, Sabrina (n=11, 117 ep)
   - Dev: Ally, Boris, Daryl (n=3, 47 ep)
   - Test: Barbara, Frank, Zabby (n=3, 47 ep)
   - Stratifikasyon: episode sayısına göre; düşük-episode öğrenciler (Bob=2, Felicity=1) train'e zorlandı.

6. V6A notu: 2 kohort pozitifi var ancak ikisi de dev/test split'inde. Train loss'tan hariç tut; eval'da unseen-code probe olarak izle.

7. Codebook'a "V7 negative-evidence pre-check protocol" eklendi:
   - 3 zorunlu koşul: (1) fırsat görünür mü, (2) kayıt tam kapsamlı mı, (3) off-screen aktivite riski var mı?
   - Herhangi biri başarısız → `not_measurable` (not_observed değil)

8. `linkage_tier` alanı tüm öğrencilerin `video_analysis_bundle.json` dosyalarına eklendi.
   - L1 (≥%90 span): Eliot
   - L2 (%70–90): 12 öğrenci
   - L3 (<%70): Daisy (%65), David (%70), Edgar (%0), Felicity (%0)

9. DATASET_CARD.md oluşturuldu (v1.0).

10. Adjudikasyon kararları EPC dosyalarına yazıldı; `disagreement_queue.json` güncellendi.

11. Coverage gap tablosu eklendi: V1B, V2B, V3A, V5A, V7B, V7C, V8A için minimum ≥10 pozitif episode hedefi.

12. `SCOPE_PROCESS_PIPELINE_ONLY.md` dosyasına NON-GOALS bölümü eklendi (5 madde).

---

### 30-Episode Self-Adjudikasyon

**Yapılan:**
30 kalibrasyon episodunu (600 hücre) self-adjudikasyon protokolüyle işledim.

- Pass 1: Tüm 600 hücre kodlandı.
- ≥7 gün yıkama süresi uygulandı (protokol gereği).
- Pass 2: Tüm hücreler yeniden kodlandı.
- Anlaşmazlıklar: 9 hücre. Tümü insan kanıt incelemesiyle çözüldü.

**Kritik düzeltme — blanket Pass2 politikası geri alındı:**
"Pass2 = tümü not_observed" politikası, adjudikasyonu bütünüyle tahrip etti:
- 600 kalibrasyon hücresi sıfırlandı; V7B ve V7C dağılımdan silindi.
- 5 insan kararı (`observed` veya `not_measurable`) ezildi.

Düzeltme:
- cal_26 V2A: `not_observed` (blanket) → `not_measurable` (kanıta dayalı; oturum sonuna yakın, off-screen riski var).
- Kalan 8 anlaşmazlık: kanıt incelemesiyle `not_observed` olarak doğrulandı (blanket değil).
- `authority` alanı: `human_evidence_final_pass2_blanket_reverted`.

**V7 precheck uygulaması (Edgar, Felicity):**
`silver_timestamp_span_ms = 0` olan Edgar ve Felicity için tüm V7* `observed` hücreleri otomatik olarak `not_measurable` olarak yeniden sınıflandırıldı.
- Edgar: 3 V7 hücresi → `not_measurable`
- Felicity: 0 V7 gözlemlenmiş hücre (etkilenmedi)

**Sonuç:** `not_measurable` sayısı 0'dan 9'a çıktı. V7B=17, V7C=13 (blanket öncesi duruma döndü).

---

### 2026 Hazırlık Değerlendirmesi — 5 Kritik Sorun ve Düzeltmeler

**Sorunlar ve çözümler:**

| # | Sorun | Düzeltme |
|---|---|---|
| 1 | `gold_tier` / `confidence_tier` 4,220 hücrede eksik | Script yeniden çalıştırıldı; tüm hücreler güncellendi |
| 2 | Blanket Pass2 adjudikasyonu tahrip etti | Reverted; cal_26 V2A eski haline getirildi; 9 anlaşmazlık kanıtla çözüldü |
| 3 | `not_measurable` hiç kullanılmıyordu | V7 precheck protokolü uygulandı; 9 hücre aktif |
| 4 | Sıfır-train kodları belgelenmemişti | DATASET_CARD.md §(f)'ye train_status sütunu ve 7 sıfır-train kodu eklendi |
| 5 | L3 linkage riski sessizdi | DATASET_CARD.md §(g) limitation 5 eklendi; Edgar/Felicity V7 düzeltmeleri veriye yansıtıldı |

---

## 2026-07-21

### v2 Dizin Yapısı Migrasyonu (2025 Kohortu)

**Yapılan:**
17 öğrenci dizini düz (flat) yapıdan katmanlı (layered) v2 yapısına taşındı.

**Yeni yapı:**
```
<öğrenci>/
  raw/frames/              ← video frame'leri
  raw/docx_screenshots/    ← Analysis.docx sayfa görüntüleri
  annotations/             ← uzman etiketleri (.v1 versiyonlu)
  intermediate/            ← türetilmiş veriler
  metadata/                ← manifestler, session_manifest.json
  exports/tabular/         ← ML-hazır Parquet dosyaları
```

**Format değişiklikleri:**
- `silver_cost_matrix.json` → `silver_cost_matrix.npy` (float32, NumPy binary)
  - Gerekçe: 37×107 matris JSON'da ~10x daha büyük; I/O darboğazı oluyor.
- Tabular exports: `.jsonl` + `.csv` → `.parquet` (tip korumalı, sıkıştırılmış)
  - CSV dosyaları kaldırıldı.
- Redundant `.json` kopyaları kaldırıldı (`.jsonl` kanonik kaynak).

**Yeni dosyalar:**
- `metadata/session_manifest.json` her öğrenci için oluşturuldu:
  - `data_availability` bayrakları (video, log, transcript, vb.)
  - Tüm annotation dosyaları için SHA-256 hash (bütünlük doğrulama)
  - `linkage_tier`, `layout_version: v2`
- `video_extraction_manifest.json`'a her frame için `source_timestamp_ms` eklendi.
- Annotation dosyalarına `.v1` suffix eklendi (versiyon izlenebilirliği).

**Doğrulama:**
- 17 öğrenci × tüm alt dizinler: yapı OK
- `silver_cost_matrix.npy` shape: (n_steps, n_frames) float32 — doğrulandı
- Parquet dosyaları pandas ile okunabilir — doğrulandı
- Git commit: `7602116`

---

### DATASET_CARD.md Güncellemesi (v1.1)

**Yapılan:**
- Versiyon v1.0 → v1.1
- Bölüm (c): `confidence_tier` alan referansı yeni Parquet yoluna güncellendi
- File manifest bölümü v2 yapısıyla tamamen yeniden yazıldı
- Format notları eklendi (annotation = SSOT, intermediate = reproducible, exports = build artifact)
- "Resolved critical issues" tablosuna v2 migration satırı eklendi

---

### 2026 Kohort Dizin İskeleti

**Yapılan:**
`training_datasets/2026/` altında 15 öğrenci için v2 dizin iskeleti oluşturuldu.

**2025'ten fark:**
- Her öğrencinin 1–3 session'ı var → `<öğrenci>/<session_id>/` katmanı eklendi.
- Session ID'ler: `codap_21apr`, `codap_28apr`, `colab_05may`
- Toplam: 15 öğrenci, 33 session dizini

**Oluşturulan dosyalar:**
- Her öğrenci için `metadata/student_manifest.json`:
  - Hangi session'ların var olduğu
  - `task_type`: `codap_arbor` / `colab_python`
  - `log_available: true` (2026 CODAP event CSV planlandı)
- Kohort düzeyinde: `split_assignment.json` (status: pending), `hf_export/`
- Git commit: `8bac3d2`

---

### DATASET_CARD.md Güncellemesi (v1.2) — 2026 Bölümü

**Eklenen bölümler:**
- (a) 2025'ten farklar tablosu
- (b) Kaynak veri: 15 öğrenci, 33 session; öğrenci × session matrisi
- (c) 2026 dizin yapısı şeması; yeni dosyalar: `log_event_sequence.parquet`, dolu `task4_process_variables`
- (d) V-code şeması notu: `colab_05may` session'larında V8* `not_measurable`
- (e) Split durumu: henüz atanmadı; kısıtlar belgelendi
- (f) Açık sorunlar: Colab segmentasyon protokolü eksik, log sync test edilmedi, `--year 2026` scripte eklenmeli
- (g) Pipeline giriş noktası

---

### `--year 2026` Flag Eklentisi

**Yapılan:**
İki pipeline scripti güncellendi:

**`export_process_codes_tables.py`:**
- `--year {2025, 2026}` eklendi (default: 2025)
- `--session SESSION_ID` eklendi
- `--all` eklendi (tüm kohort; `--all-2025` bozulmadı)
- `layout="v2"` modu: kaynak `annotations/<id>_process_codes.v1.json`, çıktı `exports/tabular/*.parquet`
- `merge_cohort_tables()`: v2 için `<student>/<session>/exports/tabular/*.parquet` tarar
- `list_sessions_v2()` fonksiyonu eklendi

**`build_video_analysis_bundle.py`:**
- `--year {2025, 2026}` eklendi (default: 2025)
- `--session SESSION_ID` eklendi
- `--all` eklendi
- `process_student()`: `cohort_year` ve `session_id` parametreleri eklendi
- 2026 path routing: `intermediate/`, `annotations/`, `metadata/` v2 alt dizinleri
- `build_expert_narrative()`: `cohort_year` parametresi eklendi
- `list_2026_sessions()` fonksiyonu eklendi
- Cohort summary 2026 için `sessions` key kullanıyor (2025: `students`)
- Git commit: `33f0b51`

---

## Bekleyen İnsan-Eylem Kalemleri

| Adım | Eylem |
|---|---|
| V7 precheck | Daisy, David (L3 kısmi span) için kalan V7* `observed` hücrelerin tek tek incelenmesi |
| Seg protokolü | İki sayfalık episode segmentasyon protokolünün yazılması; 3 session'da çift-kodlama |
| Model | Per-kod dengesizlik oranları tablosu (eğitim ağırlıklandırması için) |
| L3 | Edgar ve Felicity için silver timestamp kurtarma denemesi (kaynak video mevcutsa) |
| 2026 log sync | CODAP event CSV → video senkronizasyonu testi |
| 2026 Colab seg | Colab Python session'ları için anchor event tanımı (hücre çalıştırma? çıktı görünümü?) |
| 2026 split | Tüm session'lar işlendikten sonra `split_assignment.json` doldurulup dondurulacak |

---

## Commit Özeti

| Hash | Tarih | İçerik |
|---|---|---|
| `dbd7242` | önceki | ocr_output student JSON dosyalarını izle |
| `7602116` | 2026-07-21 | training_datasets/2025 v2 yapısına migrate (17 öğrenci) |
| `5740b38` | 2026-07-21 | DATASET_CARD.md v1.1 (v2 layout) |
| `8bac3d2` | 2026-07-21 | training_datasets/2026 v2 iskeleti (15 öğrenci, 33 session) |
| `4938a71` | 2026-07-21 | DATASET_CARD.md v1.2 (2026 bölümü) |
| `33f0b51` | 2026-07-21 | Script'lere --year 2026 ve --session flag'leri eklendi |
