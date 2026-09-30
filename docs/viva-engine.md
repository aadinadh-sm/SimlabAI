# SIMLAB AI: Interactive Viva Engine

## Concept Matching & Scoring Philosophy
The Viva Engine does not rely on rigid string matching or arbitrary grading numbers. Instead, it extracts key technical concepts from the student's answer and compares them against authoritative manual expectations.

## Grading Thresholds
- **Comprehensive (Correct)**: $\ge 70\%$ of core conceptual keywords matched.
- **Partially Correct**: $35\% \text{ to } 69\%$ matched. The assistant provides constructive feedback noting which critical engineering parameters were missed.
- **Review Recommended**: $< 35\%$ matched. The student is presented with the authoritative model answer from the laboratory manual.

## Coverage
Every experiment has a dedicated question bank in `knowledge/viva/exp<N>_viva.json` covering definitions, circuit topology, theoretical calculations, and error diagnosis.
