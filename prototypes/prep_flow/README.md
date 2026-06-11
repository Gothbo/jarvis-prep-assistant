# Prototype: Prep Flow End-to-End

## Question

Does the end-to-end Prep package generation flow work correctly with our data models,
from natural language input through intent recognition to a structured PrepPackage output?

Specifically:
- Can we recognize industry and scenario from free-text input?
- Can we load the knowledge base (cases, methodologies, sensitivities) and match relevant ones?
- Can we assemble a PrepPackage with all 6 required modules?
- Does the rule-based fallback produce sensible output when LLM is unavailable?

## Run

```bash
cd prototypes/prep_flow
python main.py
```

## Expected Outcome

A terminal app where you can type scenarios and see the full PrepPackage output,
including matched cases, sensitivity alerts, follow-up questions, etc.
