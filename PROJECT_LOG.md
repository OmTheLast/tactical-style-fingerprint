# Project Log

This file records work actually completed, observations supported by the inspected data, and modelling decisions made so far. Planned work should not be recorded here as completed.

## 2026-08-18 — Data-source reconnaissance and project direction

### Completed

- Investigated open and commercial football event and tracking-data sources.
- Identified StatsBomb Open Data as the intended source for the hackathon project.
- Distinguished event data from continuous tracking data and StatsBomb 360 freeze-frame data.
- Defined the project direction: an interpretable, multidimensional team style profile rather than a single tactical label.
- Recorded the project brief in `PROJECTCONTEXT.md`.

### What we learned

- Located event data can support measurements related to possession, territory, passing progression, directness, pressing proxies, transitions, attacking width, and set-piece tendencies.
- Event data cannot directly establish true defensive-line height, compactness, team shape, marking systems, off-ball movement, or rest defence. Those require tracking-style positional data.
- Tactical style and tactical effectiveness are different questions. Goals, wins, league position, and finishing quality should not drive the eventual style similarity calculation.
- A transparent feature vector and a simple similarity method are appropriate for the first version. More complicated ML is not automatically more useful.

### Decisions and rationale

- **Use StatsBomb Open Data:** it provides timestamped, located events in a documented JSON structure and avoids spending hackathon time on scraping.
- **Use event data only for V1:** this keeps the scope achievable and prevents unsupported tracking-based claims.
- **Start with the 2015/16 Premier League:** it provides a complete 20-team league season and is a manageable starting point before considering the other Big Five leagues.
- **Do not finalize tactical metric definitions yet:** the underlying schema must be understood before deciding exactly how concepts such as directness or counterpressing will be measured.

## 2026-08-19 — Competition and match loading

### Completed

- Downloaded StatsBomb's `competitions.json` to `data/raw/statsbomb/competitions.json`.
- Confirmed that the 2015/16 Premier League uses `competition_id = 2` and `season_id = 27`.
- Downloaded its match metadata to `data/raw/statsbomb/matches/2-27.json`.
- Verified that the file contains 380 matches, the expected number for a 20-team double round-robin league.
- Selected the chronologically first listed fixture as an inspection example:
  - Manchester United 1–0 Tottenham Hotspur
  - 2015-08-08
  - StatsBomb match ID `3754097`
- Downloaded its raw event data to `data/raw/statsbomb/events/3754097.json`.
- Verified that the match file contains 3,780 event objects.

### What we learned

- A StatsBomb event file is a JSON list whose elements are event objects.
- Events share common top-level fields such as `id`, `index`, `period`, `timestamp`, `type`, `possession`, `possession_team`, `play_pattern`, `team`, `player`, and `location`.
- Event objects are heterogeneous: fields can be optional, and event-specific information may appear inside a nested object named for the event type.
- Python's built-in `json` module is sufficient for loading and inspecting the raw structure; pandas has not been needed or introduced yet.

## 2026-08-19 — Inspection of representative event types

### Completed

- Inspected one raw example each of `Pass`, `Carry`, `Pressure`, `Ball Recovery`, `Shot`, `Dispossessed`, and `Miscontrol` from match `3754097`.
- Displayed shortened versions containing common identifiers and the most important type-specific fields.

### Important observations

- **Pass:** contains a nested `pass` object that can hold the recipient, length, angle, height, destination, body part, type, outcome, and other qualifiers. In the inspected completed pass, `pass.outcome` was absent.
- **Carry:** contains a small nested `carry` object with `end_location`; the same player controls the ball between the start and end locations.
- **Pressure:** the inspected event had no nested `pressure` object. Its `team` was the defending team applying pressure, while `possession_team` was the opponent with the ball. A pressure event does not by itself mean the ball was won.
- **Ball Recovery:** the inspected event was represented mostly by common top-level fields and marked the player and location of the recovery. Optional recovery-specific fields may occur in other events.
- **Shot:** contains a detailed nested `shot` object with xG, outcome, technique, body part, shot type, end location, an optional key-pass link, and a shot freeze frame.
- **Shot end location:** may contain three values rather than two because the third value represents goal height.
- **Shot freeze frame:** records visible player locations at the instant of the shot. It is event-specific context, not continuous tracking and not permission to infer team shape throughout the match.
- **Dispossessed:** records a player losing the ball through an opponent's challenge and may link to the corresponding defensive action through `related_events`.
- **Miscontrol:** records a failed control rather than an opponent directly dispossessing the player.
- **Optional fields matter:** code that assumes every event has the same keys will fail or misinterpret the data. The eventual loader must access optional and nested fields safely.

### Current implementation status

- Raw competition, match, and one-match event files have been downloaded and inspected.
- No tactical metrics, feature vectors, normalization, similarity calculation, AI explanation, or application interface have been implemented.

## 2026-08-19 — Project documentation policy

### Completed

- Kept `PROJECT_LOG.md` as the repository's tracked chronological development record.
- Moved the personal revision checklist to `private_notes/OM_REVIEW.md`.
- Added `private_notes/` to `.gitignore` so personal learning notes remain local and are not included in future commits.
- Expanded the local review document to separate concepts to understand, exercises to practise, and project questions to defend.

### Decision and rationale

- **Separate the public project record from private learning notes:** implementation history and modelling decisions belong in the repository, while personal revision prompts should remain editable locally without being published.
