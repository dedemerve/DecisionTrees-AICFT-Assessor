Q1 gate review’e göre remediation master planını uygula.
System prompt’taki faz sırasına ve kabul kriterlerine uy.
Her faz bitince faz JSON raporu ver; en sonda final gate özetini ver.
Kullanıcı “commit” demedikçe commit/push yapma.
Research data (`data_sources_*`, `ocr_output/`, `students/`) silme/taşıma.

## Çalışma modu
{{MODE}}
# MODE seçenekleri:
# - full_auto : 0→5 tüm kodlanabilir fazları uygula; insan IRR’yi altyapıda bırak
# - phase_only : yalnız {{PHASE}} (örn. 1A)
# - plan_only : dosya yazmadan plan + kabul kriteri checklist

## Gate review özeti (bağlayıcı)
- package_sufficient_for_q1: false
- highest_defensible: internal_pilot / method_development → hedef C4 method paper
- macro_f1 ≈ 0.2063 | macro_kappa ≈ 0.1007 | verdict = REFINE
- label_source = nearest_gold_silver_anchor (%100)
- RF tetiklenen: RF01, RF02, RF03, RF05, RF06, RF07, RF08, RF09, RF10, RF11, RF12
- RF04: false (koru)

## Must-fix (öncelik sırası)
1. Bağımsız çift-kodlama altyapısı (IRR protokol + sample) — RF05
2. Few-shot pozitif örnek + Deepen ankor — G7 / C3
3. Frame≠session grain ayrımı — RF11
4. B15–B17 process quarantine — RF02
5. Relative paths — RF09
6. Model/prompt provenance — RF10
7. Student leakage-free splits — RF08

## Repo’da yeniden kullan (icat etme)
- training_datasets/2025/<id>/*_construct_scores.json
- *_expert_process_narrative.json
- *_process_codes.json + tabular/ + hf_export/
- *_log_process_metadata.json
- *_video_analysis_bundle.json
- framework/VIDEO_PROCESS_CODEBOOK_v1.md
- framework/prompts/q1_calibration_validation_gate_system.md

## Girdi artefaktları (gerekirse oku)
- calibration/2025_calibration_dataset.json
- calibration/validation_metrics.json
- calibration/validation_raw_scores.json
- calibration/fewshot_examples.json
- {{GATE_REVIEW_JSON_PATH_OR_INLINE}}

## Şimdi yap
MODE={{MODE}}; PHASE={{PHASE_OR_ALL}}

Kurallar:
- Yeni JSON’larda absolute path yasak
- v1 dosyalarını silme; v2 yanına yaz
- Frame validation’ı “ana Q1 kanıtı” diye yeniden koşturma (isteğe bağlı debug notu hariç)
- Her fazda acceptance_checks kanıtlı olsun
