# # scripts/annotation/test_batterybert.py
# from transformers import pipeline

# ner = pipeline(
#     "ner",
#     model="batterydata/batterybert-uncased",
#     aggregation_strategy="simple"
# )

# test_sentences = [
#     "The NaMnO2 cathode delivered 185 mAh/g at 0.1C after 300 cycles.",
#     "Hard carbon anode synthesized at 1300°C showed 87% ICE.",
#     "P2-type Na0.67MnO2 was characterized by XRD and TEM.",
#     "NASICON-type Na3Zr2Si2PO12 electrolyte was prepared by sol-gel.",
#     "Prussian blue analogue showed excellent sodium storage capacity."
# ]

# for sent in test_sentences:
#     print(f"\nSentence: {sent}")
#     entities = ner(sent)
#     for e in entities:
#         print(f"  [{e['entity_group']}] '{e['word']}' (score: {e['score']:.2f})")

