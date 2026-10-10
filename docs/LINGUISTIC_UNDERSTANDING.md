# Linguistic Understanding Substrate

Genesis now emits a transparent, non-neural linguistic intermediate representation through `genesis.dialogue.understanding.understand(text)`.

It segments sentence/clause boundaries, records token sequence, classifies broad surface speech acts, identifies interrogative dimensions, preserves negation and modal operators, tracks coordinating conjunctions, and flags context-dependent pronouns/references. The output includes the exact cues used so an operator can inspect why a classification was made.

This is a primitive for further learning, not a completed natural-language understanding system. It does not yet reliably resolve semantic roles, long-distance dependencies, sarcasm, idioms, coreference, implied intent, or world knowledge. Surface classifications must be evaluated on held-out language examples; their confidence is not a calibrated probability. The next learning stages should learn and test grammatical constructions from observed evidence rather than silently expand a hard-coded list of topic-specific answers.
