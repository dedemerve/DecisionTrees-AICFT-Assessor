window.AGREEMENT_SUMMARY = {
  "n": 1693,
  "percent_agreement": 89.84,
  "percent_agreement_ci": [87.16, 92.17],
  "kappa": 0.798,
  "kappa_ci": [0.740, 0.845],
  "macro_f1": 0.818,
  "bootstrap_reps": 10000,
  "bootstrap_seed": 20261110,
  "total_rows": 2625,
  "excluded": 932,
  "exclusions": [
    { "reason": "System partial decisions",    "n": 663 },
    { "reason": "System unknown",              "n": 224 },
    { "reason": "System structural N/A",       "n": 23  },
    { "reason": "Human partial credit (±0.5)", "n": 8   },
    { "reason": "Human structural N/A",        "n": 8   },
    { "reason": "Absent worksheet labels",     "n": 6   }
  ],
  "classes": [
    { "label": "Correct", "precision": 0.995, "recall": 0.862, "f1": 0.924, "support": 1196 },
    { "label": "Wrong",   "precision": 0.373, "recall": 0.961, "f1": 0.537, "support": 102  },
    { "label": "Blank",   "precision": 0.995, "recall": 0.992, "f1": 0.994, "support": 395  }
  ],
  "by_worksheet": [
    { "code": "WS1",  "n": 142, "agreement": 97.9, "kappa": 0.930, "f1_correct": 0.987, "f1_wrong": 0.933, "f1_blank": 1.000, "macro_f1": 0.973 },
    { "code": "WS3",  "n": 104, "agreement": 96.2, "kappa": 0.485, "f1_correct": 0.980, "f1_wrong": 0.500, "f1_blank": null,  "macro_f1": 0.740 },
    { "code": "WS4",  "n": 61,  "agreement": 78.7, "kappa": 0.592, "f1_correct": 0.842, "f1_wrong": 0.722, "f1_blank": 0.600, "macro_f1": 0.721 },
    { "code": "WS5",  "n": 147, "agreement": 96.6, "kappa": 0.600, "f1_correct": 0.982, "f1_wrong": 0.615, "f1_blank": null,  "macro_f1": 0.799 },
    { "code": "WS6",  "n": 54,  "agreement": 88.9, "kappa": 0.206, "f1_correct": 0.940, "f1_wrong": 0.250, "f1_blank": null,  "macro_f1": 0.595 },
    { "code": "WS7",  "n": 91,  "agreement": 93.4, "kappa": 0.880, "f1_correct": 0.400, "f1_wrong": 0.933, "f1_blank": 1.000, "macro_f1": 0.778 },
    { "code": "WS10", "n": 102, "agreement": 99.0, "kappa": 0.939, "f1_correct": 1.000, "f1_wrong": 0.941, "f1_blank": null,  "macro_f1": 0.971 },
    { "code": "WS12", "n": 58,  "agreement": 100.0,"kappa": 1.000, "f1_correct": 1.000, "f1_wrong": null,  "f1_blank": 1.000, "macro_f1": 1.000 },
    { "code": "WS13", "n": 220, "agreement": 86.4, "kappa": 0.760, "f1_correct": 0.864, "f1_wrong": null,  "f1_blank": 1.000, "macro_f1": 0.932, "note": "rebuilt_key" },
    { "code": "WS14", "n": 296, "agreement": 64.9, "kappa": 0.231, "f1_correct": 0.766, "f1_wrong": 0.119, "f1_blank": 1.000, "macro_f1": 0.628, "note": "rebuilt_key" },
    { "code": "WS15", "n": 418, "agreement": 100.0,"kappa": 1.000, "f1_correct": 1.000, "f1_wrong": null,  "f1_blank": 1.000, "macro_f1": 1.000, "note": "alignment_policy" }
  ],
  "note_rebuilt_key": "Human labels for WS13–WS15 were reconstructed from rubric rules (original answer key unavailable). Metrics for these worksheets are approximate.",
  "note_alignment_policy": "WS15 agreement reflects an applied alignment policy: system = blank items were recoded as human = blank to remove CODAP formula-content noise."
};
