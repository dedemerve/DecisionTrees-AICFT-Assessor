Aşağıdaki kalibrasyon/validasyon paketini Q1 gate review olarak değerlendir.
Yalnızca system prompt'taki JSON şemasını döndür; markdown veya açıklama ekleme.

## İncelenecek iddia kapsamı
Bu paket Q1 dergide şu iddiaları taşıyabilir mi? (C1–C6 ayrı ayrı)

## Dosyalar

### 1) calibration/2025_calibration_dataset.json
{{CALIBRATION_DATASET_JSON_OR_SUMMARY}}

### 2) calibration/validation_raw_scores.json
{{VALIDATION_RAW_SCORES_JSON_OR_SUMMARY}}

### 3) calibration/validation_metrics.json
{{VALIDATION_METRICS_JSON}}

### 4) calibration/fewshot_examples.json
{{FEWSHOT_EXAMPLES_JSON_OR_SUMMARY}}

### Opsiyonel
{{VALIDATION_REPORT_JSON_OR_NULL}}
{{RUBRIC_V4_SCOPE_NOTE_OR_NULL}}

## Zorunlu özet istatistikler (doğrulanmış olarak kullan; çelişirse dosyayı esas al)
- calibration frames: {{N_CALIB_FRAMES}}
- students: {{N_STUDENTS}}
- validation frames: {{N_VAL_FRAMES}}
- model: {{MODEL_NAME}}
- macro_f1: {{MACRO_F1}}
- macro_kappa: {{MACRO_KAPPA}}
- metrics_verdict: {{METRICS_VERDICT}}
- proceed_threshold_f1: {{THR_F1}}
- proceed_threshold_kappa: {{THR_KAPPA}}

## Özellikle denetle
1. label_source = nearest_gold_silver_anchor ise C1 overclaim mi?
2. B15/B16/B17 construct içinde mi?
3. macro_f1≈0.21 / macro_kappa≈0.10 ve verdict=REFINE iken C2/C5 mümkün mü?
4. few-shot absolute path + öğrenci sızıntısı?
5. Bu paket main AI-CFT scoring paper için yeterli mi, yoksa yalnızca internal refine sinyali mi?

Kararı bağlayıcı kurallara göre ver; şüphede düşük savunulabilir seçeneği seç.
