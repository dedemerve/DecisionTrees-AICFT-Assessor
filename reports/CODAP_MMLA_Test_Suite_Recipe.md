# CODAP Arbor MMLA Test Suite & Edge-Case Reçetesi

## Kapsam ve karar ilkesi

Bu reçete, seçilmiş video kareleri, transkript parçaları ve CODAP/Arbor log olaylarını birleştiren pipeline için hazırlanmıştır. Test oracle'ının temel kuralı şudur:

> Arayüz durumu yalnızca kanıtın mevcut olduğunu gösterir. Bilişsel davranış ancak öğrenciye atfedilebilir eylem, ilgili semantik ifade ve doğru zamansal bağ aynı episode içinde doğrulandığında kodlanabilir.

Frame, log veya metadata tek başına AI-CFT/B0–B13 düzeyi üretmemelidir. Teknik belirsizlik öğrenci başarısızlığına çevrilmemeli; `not_measurable`, `not_observed` ve `observed` ayrı tutulmalıdır.

---

# 1. Zafiyet Analizi Özet Tablosu

Etkileşimli risk tablosu ve test filtreleri companion Canvas içinde sunulmuştur. Kritik zafiyet kayıtları aşağıdadır.

## R-01 — Log olayı ile görsel render aynı zaman kabul ediliyor

- **Katman:** zaman hizalama
- **Mevcut durum:** log penceresi ±10 saniyedir; olayın UI tarafından henüz render edilip edilmediğini gösteren durum alanı yoktur.
- **Hata modu:** `emit_tree_data` görüldüğü anda confusion matrix okuma veya accuracy yorumlama davranışı tetiklenebilir.
- **Risk:** kritik false positive
- **Gerekli kontrol:** `event_time`, `frame_time`, `render_state` ve `render_latency_ms` ayrı tutulmalı; render doğrulanana kadar bilişsel gösterge bastırılmalıdır.

## R-02 — Aktif katılım ile görünür arayüz durumu ayrılmıyor

- **Katman:** semantik füzyon
- **Mevcut durum:** frame şeması bilişsel göstergeleri `observed: boolean` olarak tutarken session prompt'u `true|null` kullanır. Aynı “kanıt yok” durumu iki farklı biçimde temsil edilir.
- **Hata modu:** görünür confusion matrix, öğrenci yorumlamış gibi kodlanabilir veya `false` yanlış anlama gibi yorumlanabilir.
- **Risk:** kritik false positive ve şema drift'i
- **Gerekli kontrol:** `observation_status = observed | not_observed | not_measurable | conflict` kullanılmalıdır.

## R-03 — Session prompt niyet çıkarmayı zorunlu kılıyor

- **Katman:** LLM prompt
- **Mevcut durum:** `why_inferred` boş bırakılamaz; transkript yoksa log örüntüsünden neden çıkarılması istenir.
- **Hata modu:** hızlı tıklama, tekrar veya sıra bilgisi “strateji”, “panik” ya da “keşif” olarak uydurulabilir.
- **Risk:** kritik construct contamination
- **Gerekli kontrol:** `why_source = none` ve `why_status = unavailable` geçerli olmalı; log yalnızca ne ve ne zaman sorusunu yanıtlamalıdır.

## R-04 — Transkript yalnızca en yakın zamana göre bağlanıyor

- **Katman:** transcript alignment
- **Mevcut durum:** en yakın öğrenci ifadesi ±5 saniyede alınır; ifadenin geçmişe, mevcut ana veya gelecekteki eyleme atıf yaptığı kodlanmaz.
- **Hata modu:** “az önceki ağaç” ifadesi mevcut frame'e aktarılır.
- **Risk:** yüksek bağlam kayması
- **Gerekli kontrol:** `temporal_reference = prior | concurrent | future | unclear` ve `referenced_episode_id` zorunlu olmalıdır.

## R-05 — OCR ham değer, normalize değer ve güven ayrılmıyor

- **Katman:** görsel çıkarım
- **Mevcut durum:** `accuracy_value` doğrudan sayı veya null'dır.
- **Hata modu:** `0.B` yanlışlıkla `0.8` yapılabilir; hangi dönüşümün uygulandığı denetlenemez.
- **Risk:** yüksek veri fabrikasyonu
- **Gerekli kontrol:** ham metin korunmalı; parse başarısızsa normalize değer null kalmalıdır.

## R-06 — İmkânsız ekran durumları için deterministik invariant yok

- **Katman:** şema sonrası doğrulama
- **Mevcut durum:** JSON Schema alan tiplerini doğrular; `tree_has_nodes=false` ile `node_count_visible=5` arasındaki mantıksal çelişkiyi engellemez.
- **Hata modu:** yapısal olarak geçerli fakat anlamsız JSON skora katılır.
- **Risk:** kritik false positive
- **Gerekli kontrol:** alanlar arası invariant motoru ve fatal `invariant_violations` listesi.

## R-07 — Şema hataları çıktıyı durdurmuyor

- **Katman:** runtime QA
- **Mevcut durum:** frame analizindeki validation hataları kayda eklenir fakat sonuç yine yazılır.
- **Hata modu:** geçersiz çıktı downstream aggregation'a ulaşabilir.
- **Risk:** kritik veri bütünlüğü
- **Gerekli kontrol:** schema/invariant hatasında `quarantined=true`; skor ve aggregation yasak.

## R-08 — Frame bütçesi kritik kareleri düşürebilir

- **Katman:** sampling
- **Mevcut durum:** zorunlu ve yüksek hareketli kareler seçildikten sonra `max_frames` uygulanırsa uniform downsampling yapılır.
- **Hata modu:** emit veya split olayına ait zorunlu kare bütçe nedeniyle kaybolabilir.
- **Risk:** yüksek false negative
- **Gerekli kontrol:** zorunlu kareler bütçe dışı korunmalı; bütçe yalnızca ikincil karelere uygulanmalıdır.

## R-09 — Tek-frame AI-CFT skoru şemada yer alıyor

- **Katman:** ölçme
- **Mevcut durum:** frame çıktısı LO3 puanı ister.
- **Hata modu:** anlık UI durumu yeterlik puanına dönüşür.
- **Risk:** kritik construct-invalid scoring
- **Gerekli kontrol:** frame çıktısı yalnızca detection/evidence üretmeli; davranış ve düzey episode aşamasında belirlenmelidir.

## R-10 — CODAP değişken adları için kanonikleştirme sözleşmesi yok

- **Katman:** normalizasyon
- **Mevcut durum:** Unicode, yüzde işareti, birim, boşluk ve büyük/küçük harf davranışı açık değildir.
- **Hata modu:** aynı değişken farklı ad sanılabilir veya farklı değişkenler yanlış birleştirilebilir.
- **Risk:** orta-yüksek false negative/positive
- **Gerekli kontrol:** görünen ad korunmalı; eşleme için Unicode NFKC + trim + whitespace collapse + locale-aware casefold uygulanmalıdır.

---

# 2. Katı Test Senaryoları — Test Cases

## TC-TS-01 — Log önden gidiyor, UI render bekliyor

- **Test düzeyi:** unit + integration + fusion
- **Expected Screen State:** `tree_visible=true`, `accuracy_visible=false`, `confusion_matrix_visible=false`.
- **Expected Log:** frame zamanından 150 ms önce geçerli bir `emit_tree_data`; accuracy ve TP/TN/FP/FN logda mevcut.
- **Transcript:** null.
- **Beklenen assertion'lar:**
  - Teknik eylem `emit_received` olarak kaydedilir.
  - `log_screen_match="partial"` veya eşdeğer durum üretilir.
  - `render_state="pending"` olur.
  - `accuracy_interpretation` ve `confusion_matrix_reading` observed olamaz.
  - LO3/B8/B13 yükselmez.
  - Render-timeout dolmadan insan inceleme bayrağı gerekmez; timeout sonrasında `needs_human_review=true`.
- **Başarısızlık koşulu:** log metriğinin görsel veya semantik yorum kanıtı gibi kullanılması.

## TC-TS-02 — Beş saniyede üç split değişikliği

- **Test düzeyi:** unit + integration
- **Expected Screen State:** yalnızca son eşik değeri görünür; ara iki değer için frame yoktur.
- **Expected Log:** `t=100000 value=10`, `t=102000 value=12`, `t=104500 value=11.6`.
- **Transcript:** null veya semantik olmayan konuşma.
- **Beklenen assertion'lar:**
  - Üç log olayı sırası ve event ID'leri korunur.
  - Tek episode içinde üç ayrı teknik değişiklik kaydedilir.
  - `threshold_change_count=3` yalnızca metadata'dır.
  - `threshold_reasoning` observed olmaz.
  - `pixel_change_pct` eksik ara frame'leri üretmek için kullanılmaz.
  - Son görsel değer yalnızca üçüncü log olayıyla eşlenir.
- **Başarısızlık koşulu:** değişiklik sayısından sistematik arama, deneme-yanılma veya Deepen çıkarılması.

## TC-TS-03 — Confusion matrix görünür, semantik atıf yok

- **Test düzeyi:** fusion regression
- **Expected Screen State:** `confusion_matrix_visible=true`, accuracy ve tüm hücreler okunaklı.
- **Expected Log:** geçerli `emit_tree_data`.
- **Transcript:** “Hocam bitti mi?” veya “Şimdi buna bakıyorum.”
- **Beklenen assertion'lar:**
  - Transcript `is_task_relevant=false` veya `cognitive_signal=none`.
  - `confusion_matrix_reading` observed olmaz.
  - `accuracy_interpretation` observed olmaz.
  - Görsel yalnızca `evidence_available=true` üretir.
  - B8/B13 Acquire veya Deepen tetiklenmez.
- **Başarısızlık koşulu:** metrik görünürlüğünün aktif katılım sayılması.

## TC-TS-04 — Geçmişteki ağaca retrospektif atıf

- **Test düzeyi:** transcript alignment + fusion
- **Expected Screen State:** grafik sekmesi açık; ağaç ve matrix görünür değil.
- **Expected Log:** mevcut zaman penceresinde `codap_component_change`; önceki episode'da emit.
- **Transcript:** “Az önceki ağaçta tuz değişkeni çok iyi ayırmıştı.”
- **Beklenen assertion'lar:**
  - `temporal_reference="prior"`.
  - `referenced_episode_id` önceki ağaç episode'una bağlanır.
  - Mevcut frame'in LO3/B8/B6 kararı yükselmez.
  - İfade önceki episode'un reasoning kriterini destekleyebilir fakat eylemin o gerekçeyle yapıldığını tek başına kanıtlamaz.
- **Başarısızlık koşulu:** semantik ifadenin en yakın frame'e otomatik taşınması.

## TC-TS-05 — Accuracy alanı popup ile örtülü

- **Test düzeyi:** vision unit + schema/invariant
- **Expected Screen State:** accuracy bölgesi kısmen kapalı; OCR ham değer `0.B`.
- **Expected Log:** accuracy `0.8`.
- **Beklenen assertion'lar:**
  - `occlusion_present=true`.
  - `ocr_raw_value="0.B"`.
  - `accuracy_value=null`; log değeri OCR tahmini olarak yazılmaz.
  - `analysis_confidence="low"`.
  - `field_visibility="partial"`.
  - Log değeri teknik değer olarak ayrı tutulur.
- **Başarısızlık koşulu:** `0.B` değerinin sessizce `0.8` yapılması.

## TC-TS-06 — Unicode ve özel karakterli değişken adı

- **Test düzeyi:** normalization unit
- **Expected Screen State:** `split_attribute_visible="Şeker_%_Oranı"`.
- **Expected Log:** aynı adın Unicode olarak eşdeğer fakat farklı kod noktaları veya ekstra boşluk içeren biçimi.
- **Beklenen assertion'lar:**
  - `display_name` aynen korunur.
  - `canonical_name` deterministik NFKC/trim/casefold işleminden geçer.
  - Eşdeğer Unicode biçimler aynı variable ID'ye bağlanır.
  - Yüzde işareti veya Türkçe karakter kaybolmaz.
  - Bilinmeyen isim domain knowledge ile tahmin edilmez.
- **Başarısızlık koşulu:** ASCII'ye çevirme nedeniyle değişken çakışması veya eşleşme kaybı.

## TC-TS-07 — İmkânsız ağaç durumu

- **Test düzeyi:** invariant unit + integration
- **Expected Screen State:** `tree_has_nodes=false`, `node_count_visible=5`, `accuracy_visible=true`.
- **Expected Log:** yok veya bu durumu açıklamıyor.
- **Beklenen assertion'lar:**
  - `invariant_violations` en az `TREE_NODE_CONTRADICTION` ve `ACCURACY_WITHOUT_MODEL` içerir.
  - `needs_human_review=true`.
  - `quarantined=true`.
  - Cognitive indicator ve LO/B0–B13 aggregation çalışmaz.
- **Başarısızlık koşulu:** tip-valid JSON'un doğrudan skora katılması.

## TC-TS-08 — Log-video desynchronization

- **Test düzeyi:** alignment integration
- **Expected Screen State:** split değişikliği frame'de `t=120 s`.
- **Expected Log:** eşleşen olay `t=165 s`; tahmin edilen offset hata sınırını aşar.
- **Beklenen assertion'lar:**
  - `sync_quality="failed"`.
  - `sync_error_ms` hesaplanır.
  - Olaylar aynı episode'a zorla bağlanmaz.
  - Zamansal bağlantı gerektiren B11/iterative refinement `not_measurable` olur.
- **Başarısızlık koşulu:** ±10 saniyelik pencerenin offset hatasına rağmen güvenilir kabul edilmesi.

## TC-TS-09 — Duplicate emit

- **Test düzeyi:** log unit + aggregation
- **Expected Screen State:** değişmeyen ağaç.
- **Expected Log:** 500 ms arayla aynı target/features/thresholds/classes/depth/metrics ile iki emit.
- **Beklenen assertion'lar:**
  - İki ham olay korunur.
  - Tek normalize model sonucu üretilir.
  - `duplicate_event=true`.
  - `iterative_refinement` ve `comparison_cycles` artmaz.
- **Başarısızlık koşulu:** çift tıklamanın iki bağımsız model denemesi sayılması.

## TC-TS-10 — Kritik frame kayıp, log mevcut

- **Test düzeyi:** missing-modality fusion
- **Expected Screen State:** `frame_provided=false`.
- **Expected Log:** `change_split_values`.
- **Transcript:** null.
- **Beklenen assertion'lar:**
  - Split değişikliği teknik eylem olarak kaydedilir.
  - Görsel inspection, threshold reasoning ve cross-representational transfer çıkarılmaz.
  - Görsel geçiş load-bearing ise ilgili davranış `not_measurable`.
- **Başarısızlık koşulu:** logdan bilişsel niyet üretilmesi.

## TC-TS-11 — Arka plan konuşması

- **Test düzeyi:** speaker attribution + fusion
- **Expected Screen State:** öğrenci Arbor ekranında.
- **Expected Log:** normal eylem.
- **Transcript:** başka konuşmacı “FP çok yüksek” diyor; speaker role belirsiz.
- **Beklenen assertion'lar:**
  - Utterance learner evidence listesine girmez.
  - `speaker_attribution="unresolved"`.
  - B8/B13 veya confusion-matrix reading tetiklenmez.
- **Başarısızlık koşulu:** yakın zamandaki herhangi bir konuşmanın öğrenciye yazılması.

## TC-TS-12 — Kayıt başlangıcında hazır ağaç

- **Test düzeyi:** provenance integration
- **Expected Screen State:** ilk frame'de tamamlanmış ağaç ve accuracy görünür.
- **Expected Log:** yapılandırma olayları kayıt başlangıcından önce veya hiç yok.
- **Transcript:** null.
- **Beklenen assertion'lar:**
  - `artifact_provenance="preloaded_or_unknown"`.
  - B7 model construction `not_observed`; capture öncesi fırsat gerekiyorsa `not_measurable`.
  - Görünür model LO3/B7/B8 puanı üretmez.
- **Başarısızlık koşulu:** son durumun öğrenci yapımı kabul edilmesi.

## TC-TS-13 — Log ve ekran değeri tolerans dışında

- **Test düzeyi:** numeric normalization + conflict
- **Expected Screen State:** split `11.6`.
- **Expected Log:** split `12.4`.
- **Beklenen assertion'lar:**
  - `evidence_conflict=true`.
  - `sync_error` veya stale-log ihtimali kaydedilir.
  - Semantik değerlendirmede öğrenciye görünen legible değer korunur.
  - B11 value-match başarısız olur.
  - Güven düşürülür.
- **Başarısızlık koşulu:** değerlerin ortalaması veya tolerans dışı otomatik eşleşme.

## TC-TS-14 — Aktif bakış var, semantik yok

- **Test düzeyi:** Option B false-positive regression
- **Expected Screen State:** matrix açık; cursor FP ve FN hücreleri arasında hareket ediyor.
- **Expected Log:** emit sonrası dwell ve scroll.
- **Transcript:** null.
- **Beklenen assertion'lar:**
  - Inspection metadata kaydedilir.
  - `confusion_matrix_reading` ve `accuracy_interpretation` observed olmaz.
  - Confidence veya attention metadata davranış düzeyini yükseltmez.
- **Başarısızlık koşulu:** cursor hareketinden yorumlama çıkarılması.

## TC-TS-15 — Semantik ifade var, eylem görünmüyor

- **Test düzeyi:** Option B false-negative/role separation
- **Expected Screen State:** kritik eylem başka monitörde veya capture dışında.
- **Expected Log:** eksik.
- **Transcript:** “FN, kaçırdığımız olumlu örnekler; burada daha maliyetli.”
- **Beklenen assertion'lar:**
  - Semantik ifade B5/B8/B13 reasoning evidence olarak korunur.
  - Eylem gerektiren kriter otomatik karşılanmaz.
  - Gerekli doing modality yoksa birleşik davranış `not_measurable`; ifade `not_observed` olarak silinmez.
- **Başarısızlık koşulu:** ya salt konuşmadan eylem varsayılması ya da geçerli semantik kanıtın tamamen atılması.

## TC-TS-16 — Frame bütçesi kritik anchor'ı düşürüyor

- **Test düzeyi:** sampling unit
- **Fixture:** 50 seçilmiş frame; 5 tanesi forced emit/split/target anchor; `max_frames=10`.
- **Beklenen assertion'lar:**
  - Beş forced frame'in tamamı sonuç kümesindedir.
  - Kalan beş yer ikincil karelerden deterministik seçilir.
  - Aynı fixture ve seed aynı frame ID sırasını verir.
- **Başarısızlık koşulu:** forced frame'lerden herhangi birinin uniform downsampling ile kaybolması.

## TC-TS-17 — Geçiş frame'i

- **Test düzeyi:** vision/schema regression
- **Expected Screen State:** yükleme animasyonu; ağaç yarım render edilmiş.
- **Expected Log:** geçerli eylem olabilir.
- **Beklenen assertion'lar:**
  - `is_transition=true`, `usable=false`.
  - Screen-state OCR alanları null veya quarantined olur.
  - Eylem logda korunur fakat görsel doğrulanmış sayılmaz.
  - Skor/behavior üretilmez.
- **Başarısızlık koşulu:** yarım render edilmiş değerlerin kalıcı ekran durumu kabul edilmesi.

## TC-TS-18 — Semantik negation

- **Test düzeyi:** transcript semantic unit
- **Expected Screen State:** matrix görünür.
- **Transcript:** “FP ile FN'nin ne olduğunu bilmiyorum.”
- **Beklenen assertion'lar:**
  - Transcript task-relevant ve explicit misconception/uncertainty olarak sınıflanır.
  - `confusion_matrix_reading` pozitif observed olmaz.
  - Misconception flag ile gösterge durumu tutarlı olur.
- **Başarısızlık koşulu:** yalnızca “FP” ve “FN” anahtar kelimelerinden pozitif okuma çıkarılması.

---

# 3. İyileştirme ve Regresyon Önerileri

## 3.1 Şemaya eklenecek doğrulama alanları

### Kanıt ve karar durumu

```json
{
  "observation_status": "observed | not_observed | not_measurable | conflict",
  "evidence_available": true,
  "criterion_ids_met": [],
  "criterion_ids_failed": [],
  "decision_gate_trace": [
    "opportunity_pass",
    "provenance_pass",
    "semantic_gate_fail"
  ],
  "score_suppressed": true,
  "suppression_reason": "semantic evidence absent"
}
```

### Zaman ve render

```json
{
  "event_id": "log-uuid",
  "event_time_ms": 100000,
  "frame_time_ms": 100150,
  "render_state": "pending | rendered | stale | unknown",
  "render_latency_ms": 150,
  "temporal_relation": "prior | concurrent | future | unclear",
  "referenced_episode_id": "EP-004"
}
```

### OCR ve görünürlük

```json
{
  "field_visibility": "full | partial | hidden | absent",
  "ocr_raw_value": "0.B",
  "normalized_value": null,
  "ocr_confidence": 0.41,
  "normalization_rule_id": "NUMERIC_DECIMAL_V1"
}
```

### Füzyon, çatışma ve provenance

```json
{
  "evidence_refs": [
    {"modality": "video", "ref": "frame_0018"},
    {"modality": "log", "ref": "event_443"},
    {"modality": "transcript", "ref": "segment_91"}
  ],
  "evidence_conflict": false,
  "conflict_type": null,
  "artifact_provenance": "learner | teacher | peer | preloaded | copied | unknown",
  "speaker_attribution": "learner | peer | teacher | unresolved",
  "sync_quality": "verified | estimated | failed",
  "sync_error_ms": 0
}
```

### Runtime karantina

```json
{
  "schema_valid": true,
  "invariant_violations": [],
  "quarantined": false,
  "eligible_for_episode_aggregation": true
}
```

## 3.2 Deterministik invariant kuralları

1. `tree_has_nodes=false` ise `node_count_visible` yalnızca `0|null` olabilir.
2. `tree_visible=false` ise tree-derived accuracy/matrix OCR alanları pozitif kanıt olamaz.
3. `accuracy_visible=false` ise `accuracy_value=null` olmalıdır.
4. `confusion_matrix_visible=false` ise matrix hücreleri null olmalıdır.
5. `frame_quality.usable=false` ise screen-state alanları aggregation'a giremez.
6. `schema_valid=false` veya invariant ihlali varsa `eligible_for_episode_aggregation=false`.
7. Semantik kriter isteyen davranışta yalnızca video/log varsa `observed` üretilemez.
8. `why_source=log_pattern` bilişsel gerekçe olarak kabul edilemez.
9. Duplicate emit, model-comparison veya iterative-refinement sayısını yükseltemez.
10. Confidence hiçbir durumda level veya observation status değiştiremez.

## 3.3 Regresyon test paketi

- **Golden fixtures:** Her test case için frame görseli, log JSONL/CSV satırları, transcript segmentleri ve beklenen normalize JSON birlikte versionlanmalıdır.
- **Katmanlı oracle:** Extraction, normalization, alignment, fusion ve behavior decision için ayrı expected dosyalar tutulmalıdır. Tek bir dev snapshot hatanın hangi katmanda olduğunu gizler.
- **Semantic JSON compare:** Timestamp üretim zamanı ve model açıklama metni gibi değişken alanlar hariç tutulmalı; karar alanları exact karşılaştırılmalıdır.
- **Prompt/schema hashing:** Her sonuç provider, exact model, prompt SHA-256, schema SHA-256, preprocessing version ve fixture hash taşımalıdır.
- **Repeated stability:** Aynı fixture model başına en az 5 kez çalıştırılmalı; `observation_status`, criterion ID'leri ve review kararında %100 stabilite aranmalıdır.
- **Provider parity:** GPT, Claude ve Gemini için aynı fixture seti çalıştırılmalı; ortak deterministic post-validator aynı sonuç sözleşmesini zorlamalıdır.
- **Mutation tests:** `true↔false`, ±1 frame offset, transcript negation silme, Unicode normalization ve duplicate log enjeksiyonları test edilmelidir.
- **CI gate:** Critical false positive, schema-invalid persistence veya forced-frame loss oluşursa build doğrudan başarısız olmalıdır.

## 3.4 Otomatik pass/fail eşikleri

- Kritik Option B false-positive sayısı: **0**
- İmkânsız state'in aggregation'a geçişi: **0**
- Schema veya invariant-invalid kaydın karantina dışı kalması: **0**
- Forced anchor frame kaybı: **0**
- Golden fixture karar alanlarında nondeterminism: **0**
- Teknik missingness'in öğrenci skoru olarak sıfıra çevrilmesi: **0**
- Retrospektif ifadenin yanlış episode'a bağlanması: **0**

## 3.5 Öncelikli uygulama sırası

1. Tek kanonik `observation_status` ve fatal schema/invariant gate.
2. Tek-frame LO3 skorunun kaldırılması veya downstream'de zorunlu bastırılması.
3. Transcript temporal-reference ve speaker-attribution alanları.
4. Render-pending/log-ahead state machine.
5. OCR raw/normalized/confidence ayrımı.
6. Forced-frame-preserving budget algoritması.
7. Golden multimodal fixtures ve CI regresyon paketi.

