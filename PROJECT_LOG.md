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

## 2026-08-20 — First one-match tactical feature: attacking-territory share

### Completed

- Verified the StatsBomb pitch convention before applying a territorial threshold:
  - event coordinates use a 120-by-80 grid;
  - the halfway line is `x = 60`;
  - attacking actions are normalized toward the high-`x` goal at `x = 120`;
  - therefore the attacking third begins at `x = 80` for both teams;
  - as an additional match-level sanity check, shots by both teams in both halves occurred near the high-`x` goal.
- Loaded match `3754097` into pandas with `pd.json_normalize`.
- Implemented one transparent event-based territorial feature in `analysis/field_tilt_one_match.py`.
- Validated the intermediate counts and confirmed that the two team shares sum to 100%.

### Definition

For this first version, **attacking-territory share** is:

`team completed passes starting at x >= 80 / both teams' completed passes starting at x >= 80`

The calculation includes all play patterns. A pass is treated as completed when its `pass.outcome.name` value is missing, following the StatsBomb event specification.

Fields used:

- `type.name` to keep Pass events;
- `pass.outcome.name` to keep completed passes;
- `location[0]` as the pass-start x-coordinate;
- `team.name` to group the selected passes by team.

### Result for Manchester United vs Tottenham Hotspur

- Manchester United: 89 completed final-third passes, 65.0% attacking-territory share.
- Tottenham Hotspur: 48 completed final-third passes, 35.0% attacking-territory share.
- Total qualifying passes: 137.

### Decision and rationale

- **Begin with completed passes starting in the attacking third:** repeated completed passing in advanced areas is a simple, auditable proxy for sustained territorial presence. It avoids claiming to measure continuous ball or player position.
- **Include all play patterns for the first calculation:** this keeps the first implementation small and transparent. Excluding set-piece phases remains an explicit later definition choice rather than a silent assumption.
- **Call the feature attacking-territory share:** “field tilt” is used with several provider-specific definitions, so the descriptive name makes this implementation's exact meaning clearer.

### Limitations

- It ignores carries, dribbles, touches, and passes that enter the final third from just outside it.
- It rewards pass-heavy circulation and ignores incomplete attacking-third passes, so it partly reflects retention and passing execution as well as territory.
- Including corners, throw-ins, free kicks, and other restarts can increase a team's count without representing settled territorial control.
- It does not measure how long the ball remained in the final third or how dangerous the possession was.
- It is a zero-sum match share: one team's increase necessarily lowers the opponent's value.
- One match is noisy and affected by score state, opponent, red cards, and game plan; this result is not yet a stable team fingerprint.
- It cannot support tracking-based claims about defensive lines, compactness, shape, or off-ball positioning.
- No other tactical features have been calculated.

## 2026-08-20 — Full-season attacking-territory aggregation

### Completed

- Extended the unchanged attacking-territory-share filter from one match to all 380 matches in the 2015/16 Premier League.
- Added `scripts/download_season_events.py` to download and locally cache missing StatsBomb event files.
- Added `analysis/attacking_territory_share_season.py` to process the cached matches one at a time and aggregate team and opponent counts.
- Added `requirements.txt` with the two dependencies currently used: pandas and certifi.
- Added `data/raw/` to `.gitignore`; downloaded provider data is treated as a reproducible local cache rather than repository source.
- Downloaded 379 missing event files and reused the one previously inspected file, producing complete coverage of 380 matches.
- Saved the ranked result to `data/processed/attacking_territory_share_2015_16.csv`.

### Download issue and resolution

- The first standard-library HTTPS attempt failed certificate verification because the local Python installation did not locate a trusted CA certificate bundle.
- SSL verification was not disabled. The downloader was updated to use the installed certifi CA bundle through an explicit `ssl.SSLContext`, after which all missing files downloaded successfully.
- Downloads are written to a temporary file and atomically renamed after the response parses as a JSON list. Existing valid files are reused; invalid cached files are downloaded again.

### Season aggregation method

For each team, the season value is:

`sum of the team's qualifying passes / (sum of the team's qualifying passes + sum of its opponents' qualifying passes in those fixtures)`

This is a ratio of season totals, not the arithmetic mean of match-level percentages. A ratio of totals weights matches according to the amount of qualifying event evidence they contain; a simple mean would give a low-event match and a high-event match equal influence.

The qualifying event definition was not changed:

- event type is Pass;
- pass outcome is missing, meaning completed;
- pass starts at `x >= 80`;
- all play patterns remain included.

### Coverage validation

- Match metadata contains 380 matches and 20 teams.
- Every team is expected to play 38 matches.
- Every team was represented in 38 processed event files.
- No team received an incomplete-coverage flag.
- The sum of team qualifying counts equals the sum of opponent qualifying counts, because every qualifying pass belongs to one team and is an opponent event for the other team in that match.

### Ranked result

The top five teams were Manchester United (68.6%), Manchester City (67.8%), Arsenal (63.3%), Chelsea (61.3%), and Liverpool (58.7%). The bottom five were Watford (41.6%), Crystal Palace (40.8%), Newcastle United (39.0%), West Bromwich Albion (36.7%), and Sunderland (34.7%).

Manchester City had the largest raw qualifying team-pass count (5,173), but Manchester United ranked first in share because United combined 4,516 team passes with only 2,068 opponent passes. This confirms that the feature measures the relative balance of advanced passing in a team's matches, not simply its own attacking-third pass volume.

Tottenham's value changed from 35.0% in the inspected Manchester United match to 57.7% over the complete season, demonstrating why a single match should not be treated as a stable team fingerprint.

### Methodological cautions

- Aggregating 38 matches reduces random one-match variation but does not remove score-state, opponent, set-piece, or passing-completion effects.
- A ratio of totals can be influenced more by matches with many qualifying passes. That is intentional for this version but should remain documented.
- Opponent counts are specific to the 38 fixtures played by each team; they are not a generic league-average denominator.
- Complete file coverage confirms that the pipeline processed the expected matches. It does not prove that every provider event is perfectly collected or classified.
- No new tactical metric was introduced.
