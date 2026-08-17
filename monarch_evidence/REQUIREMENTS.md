# Requirements for the perfect evidence system

1. embeddable into larger models (i.e. microschema)
2. The "statement" lives outside the model and is typically structured:

2.1: association style (s,p,o)

```
indication:
    drug: [...X:A]
    disease: [...Y:B]
    relationship: [...INDICATED]
    evidence: ...
```

2.2 attribute style (p is an attribute of a record about X:A)

```
drug:
    id: X:A
    indication: [
        disease: [...Y:B]
        evidence: ...
        ]
```

2.3

```
drug:
    id: X:A
    indication: Y:B
    evidence_indication: [
        - TextMiningAnalysisResult(
            # extracted a bunch of snippets from a paper
            from: [
                pmid: PMID:123
                type: CASE_STUDY
            ]
            snippet: 
                "Aspirin is and indicated for hypertension"
            
        )
        - TextMiningAnalysisResult(
            # extracted a bunch of snippets from a paper
            
        )
    ]

```

2.3. In both models, it is possible that 

3. Both attribute style statements and association style statements should be able to use the same evidence model.

TextMiningAnalysisResult instance

slots

- no overfitting to single use case


evidence:
    direction: SUPPORTS
        - snippet: 
            "Aspirin is and indicated for hypertension"
          drug_confidence: 0.9
          agent:
            
          processing:
             drug:
                - type: EXTRACTION / NER
                  output_value: "Aspirin"
                  confidence: HIGH
                - type: GROUNDING
                  outout_value: DRUGBANK:1234
                  grounded_entity_label: Asperin
                  confidence: 0.9 # Similarity
                - type: NORMALISTION
                  output_value: CHEBI:123
                  outout_value: DRUGBANK:1234
                  grounded_entity_label: Aspirin
                  confidence: 0.9 # Similarity
          found_in: PMID:123  


4. The statement itself is almost never explicit (A is an indication for B). What is explicit is the grounded triple style variant of the statement: []