# scripts/config.py
import os

CONFIG = {
    # Data collection
    "search_years": list(range(2010, 2025)),
    "search_queries": [
        "sodium-ion battery",
        "sodium ion battery",
        "Na-ion battery",
        "SIB cathode",
        "hard carbon anode sodium",
        "Prussian blue analogue sodium"
    ],
    "min_papers": 5000,

    # Annotation targets
    "target_sentences": 1000,
    "min_iaa_kappa": 0.80,

    # Model
    "base_model": "batterydata/batterybert-uncased",
    "fallback_model": "allenai/scibert_scivocab_uncased",
    "max_seq_length": 512,
    "mlm_batch_size": 16,
    "ner_batch_size": 8,

    # Paths
    "data_dir": "data/",
    "results_dir": "results/",
}
