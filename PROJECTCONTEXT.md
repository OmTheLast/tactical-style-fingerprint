# Tactical Style Fingerprint — Project Context

## Goal

Build a football/soccer project that represents how teams play through a transparent, multidimensional tactical profile derived from match event data. The product should avoid reducing teams to vague labels such as “possession team” or “counterattacking team.”

Eventually, a user should be able to select a team, view its tactical fingerprint, find stylistically similar teams, compare two teams, and receive an AI-generated explanation grounded only in the calculated statistics.

## Initial scope

- Use StatsBomb Open Data.
- Start with the 2015/16 Premier League, then consider the other Big Five leagues from that season.
- Use event data only for V1.
- Candidate dimensions include control, territory, directness, build-up patience, attacking width, pressing, counterpressing, and attacking transitions.
- Treat metric definitions as modelling decisions to investigate and document before implementation.
- Represent each team with an interpretable feature vector; a simple method such as normalized cosine similarity is likely sufficient for V1.

Do not infer tracking-only concepts such as true defensive-line height, compactness, team shape, marking, off-ball runs, or rest defence. StatsBomb 360 and tracking-derived features are outside the initial scope.

## Modelling principles

- Measure style rather than quality: goals, wins, league position, and finishing should not drive tactical similarity.
- Prefer transparent features and simple models over unnecessary neural networks or complicated ML.
- Consider PCA, clustering, season comparisons, and manager eras only after the basic pipeline works.
- Present important metric-definition alternatives and trade-offs before making final choices.

## AI component

The project may use the Featherless AI API to explain similarities and differences. Explanations must be grounded in the calculated feature values, not generated from team names or general football knowledge. Do not use an LLM where ordinary calculations are sufficient.

## Hackathon priorities

1. Correct data pipeline
2. Defensible tactical metrics
3. Working team fingerprints
4. Team similarity
5. Functional application
6. Grounded AI explanations
7. Visual polish
8. Optional advanced analysis

Work incrementally: inspect the current state, implement the smallest useful step, verify it, and only then continue. The developer should be able to explain the pipeline and major modelling decisions, so briefly explain important Python and data-library concepts as they are introduced.
