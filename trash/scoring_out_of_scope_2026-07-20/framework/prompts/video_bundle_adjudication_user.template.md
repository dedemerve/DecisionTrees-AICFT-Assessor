Aşağıdaki JSON artefakt paketini ölçme-değerlendirme uzmanı olarak adjudike et.
Yalnızca system prompt'taki JSON şemasını döndür; markdown veya açıklama ekleme.

Öğrenci: {{STUDENT_ID}}
Kohort: {{COHORT_YEAR}}
Rubrik: codap_arbor_v4_candidate (B0–B13)
Codebook: VIDEO_PROCESS_CODEBOOK_v1 (V1–V8, process katmanı)

--- construct_scores.json ---
{{CONSTRUCT_SCORES_JSON}}

--- expert_process_narrative.json ---
{{EXPERT_PROCESS_NARRATIVE_JSON}}

--- video_analysis_bundle.json ---
{{VIDEO_ANALYSIS_BUNDLE_JSON}}

--- process_codes.json (varsa) ---
{{PROCESS_CODES_JSON}}

--- log_process_metadata.json (varsa) ---
{{LOG_PROCESS_METADATA_JSON}}

Ek bağlam:
- coverage_audit.gaps_flagged özellikle dikkatle okunacak.
- log_available=false ise Task-4 alanlarının null olması beklenen durumdur; eksiklik sayılmaz.
- behavior_level_audit için yalnızca kanıt zinciri zayıf veya çelişkili B kodlarını listele (tüm 14'ü zorunlu değil).
