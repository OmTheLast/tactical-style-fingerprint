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

## 2026-08-20 — Directness definition investigation

### Status

- Tactical feature #1 was committed and pushed before beginning this investigation.
- Three event-data definitions of directness were proposed for discussion:
  1. distance-weighted attempted-pass verticality;
  2. progressive-action attempt share using passes and carries;
  3. possession-level net progression speed.
- No directness calculation has been implemented and no definition has been selected yet.

### Current recommendation

- **Distance-weighted attempted-pass verticality** is the recommended hackathon V1 option because it is transparent, threshold-free, inexpensive to calculate, and uses attempted rather than completed passes. This makes it primarily a measure of directional intent rather than passing success.
- Its main limitation is that it describes passing direction only and does not include ball carrying or the tempo of whole possessions.

### Decision still required

- Choose whether directness should primarily mean pass direction, frequency of large progressive actions, or speed of whole-possession progression.
- Decide how to exclude explicit restarts from the eligible action set. No implementation should begin before this definition is chosen.

## 2026-08-20 — Tactical feature #2: Pass Verticality

### Decision

- Selected the distance-weighted attempted-pass definition and named it **Pass Verticality**, rather than general directness.
- The fixed formula is:

  `sum(pass end x - pass start x) / sum(pass length)`

- The value is a dimensionless ratio. Multiplying it by 100 expresses the net forward component as a percentage of all eligible attempted passing distance.
- Included successful and unsuccessful attempts so that the feature represents directional passing intent without directly rewarding completion quality.
- Excluded passes whose explicit `pass.type.name` is `Corner`, `Free Kick`, `Goal Kick`, `Kick Off`, or `Throw-in`.
- Retained ordinary passes and passes labelled `Recovery` or `Interception`, because those are open-play origins rather than explicit restarts.
- The exclusion applies to the restart pass itself, not every later pass in a possession that began with a restart.

Fields used:

- `type.name` to select Pass events;
- `pass.type.name` to exclude explicit restarts;
- `location[0]` and `pass.end_location[0]` to calculate forward displacement;
- `pass.length` as the distance denominator;
- `team.name` for aggregation;
- `pass.outcome.name` only to validate that both completed and unsuccessful attempts are included;
- `pass.angle` for an independent trigonometric validation check.

### One-match implementation and validation

- Added `analysis/pass_verticality_one_match.py` for Manchester United vs Tottenham Hotspur, match `3754097`.
- Manchester United: 500 eligible attempts, 91 unsuccessful; 2,719.6 net forward units over 10,967.8 total pass-distance units; Pass Verticality 0.248, or 24.8%.
- Tottenham Hotspur: 492 eligible attempts, 112 unsuccessful; 3,271.5 net forward units over 11,065.7 total pass-distance units; Pass Verticality 0.296, or 29.6%.
- Confirmed that every eligible pass had its required start x, end x, length, and angle fields.
- Confirmed that none of the five excluded restart types remained.
- Recalculated each pass's forward component as `pass.length * cos(pass.angle)`. Its team-level sum matched the coordinate-derived `end_x - start_x` sum, validating the coordinate calculation and orientation assumption.
- Only after these checks passed was the unchanged calculation extended to the season.

### Full-season implementation

- Added `analysis/pass_verticality_season.py` and saved the ranked output to `data/processed/pass_verticality_2015_16.csv`.
- Aggregated numerator and denominator separately over all matches, then divided. This is a ratio of season totals, not a mean of match ratios.
- All 20 teams have complete 38/38 match coverage.
- Leicester City ranked first at 44.5%, followed by Sunderland at 44.3% and West Bromwich Albion at 42.6%.
- Manchester City ranked 19th at 28.1%, and Manchester United ranked 20th at 27.9%.
- The season coordinate and angle-derived numerators differed by at most 0.0005 pitch units per team, which is negligible floating-point/recording precision error.

### Interpretation and limitations

- A high value means a larger proportion of attempted passing distance points toward the opponent's goal; a low value means more passing distance is lateral or backward.
- Because unsuccessful attempts count, the feature does not simply reward teams for executing forward passes successfully.
- The metric is distance-weighted: a long forward attempt affects it more than a short pass, which is intentional but can make hopeful long balls influential.
- Forward and backward distances cancel in the numerator, while every eligible pass adds positive length to the denominator.
- It measures passing direction only. It does not include carries, possession tempo, time taken, pressure, zone, attack success, or continuous player/ball movement.
- It should not be described as a complete measure of general directness or attacking quality.

### Deferred option

- The earlier possession-level option has not been discarded. It remains documented as a possible later **possession progression/transition-speed** feature based on net x-progression and elapsed event time within a StatsBomb possession.
- That feature was not implemented, and no other tactical feature was started.

## 2026-08-20 — Pressing Intensity definition investigation

### Status

- Tactical feature #2 was committed and pushed as commit `121fc84` before beginning this investigation.
- Investigated two possible event-data definitions for tactical feature #3:
  1. an open-data PPDA-style reconstruction;
  2. high-zone StatsBomb Pressure events per 100 opposition pass attempts.
- No pressing feature has been selected or implemented yet.

### Data availability audit

- All 380 event files contain 368,619 Pass events, 115,402 Pressure events, 15,445 Duel events of type Tackle, 8,920 Interception events, and 9,512 Foul Committed events.
- Every event in those inspected categories has the required `location`, `team`, and `possession_team` objects. Every Pressure also has `duration`.
- The data includes 24,224 Pressure events marked `counterpress`, but this field is not required by either proposed definition.
- There are 304 Foul Committed events explicitly marked `foul_committed.offensive`; these can be excluded from a defensive-action denominator.

### Coordinate and team attribution verification

- The StatsBomb specification defines a 120 by 80 coordinate system and states that pass angle zero points toward the event team's attacking goal.
- Previous shot and pass checks confirmed that high x is toward the acting team's attacking goal.
- Related Pressure and opponent on-ball events in match `3754097` were inspected. Their coordinates approximately rotate as `(x, y)` versus `(120 - x, 80 - y)`, allowing for the pressure starting at a nearby rather than identical position.
- Therefore a defensive action at `x >= 48` from the defending/acting team's frame corresponds to an opponent pass in the same physical zone at `x <= 72` from the passer's frame.
- `team.name` identifies the team performing the event and is the correct field for attributing the action. `possession_team.name` labels StatsBomb's possession chain and must not be treated as the coordinate frame or as a guaranteed current-ball-owner test.
- The season confirms this caution: 97,509 of 115,402 Pressure events have `team != possession_team`, but 17,893 do not. Filtering pressures only where those fields differ would silently discard recorded pressures.

### Options under consideration

- **PPDA-style reconstruction:** opposition non-restart attempted passes starting at `x <= 72`, divided by the team's Tackle duels, Interceptions, and non-offensive Fouls Committed at `x >= 48`. Lower means more frequent defensive actions per allowed pass and therefore more aggressive pressing.
- **High-zone pressures per 100 passes:** 100 times the team's Pressure events at `x >= 48`, divided by opposition non-restart attempted passes starting at `x <= 72`. Higher means more recorded pressure actions per passing opportunity and therefore more aggressive pressing.
- Explicit restart types would be excluded from either pass denominator because StatsBomb represents several restarts as Pass events while the intended opportunity set is open play.
- Both options would use season ratios of totals rather than averages of match ratios.

### Sources and limitations noted

- The original PPDA concept uses passes allowed per tackle, interception, challenge, or foul in an advanced pressing zone. Hudl StatsBomb's published metric description uses tackles, interceptions, and fouls and defines the zone from 40% of the pitch length away from the defending team's goal and forward.
- The proposed PPDA calculation is an explicit open-data reconstruction, not a claim to reproduce StatsBomb's proprietary metric exactly.
- Neither option observes team shape, coordinated off-ball movement, marking, press success, or all moments when a team could have pressed.
- No implementation should begin until an option is selected.

## 2026-08-20 — Tactical feature #3: High-Zone Pressures per 100 Opposition Passes

### Decision

- Selected the Pressure-event option and named the underlying metric **High-Zone Pressures per 100 Opposition Passes**. A future interface may use the broader tactical-dimension label **Pressing Intensity**.
- The fixed formula is:

  `100 * team qualifying high-zone Pressure events / qualifying opposition pass attempts`

- A qualifying team pressure is a StatsBomb `Pressure` event starting at `x >= 48` in the pressure team's coordinate frame.
- A qualifying opposition pass is a successful or unsuccessful `Pass` event starting at `x <= 72` in the opponent passer's coordinate frame, excluding explicit `Corner`, `Free Kick`, `Goal Kick`, `Kick Off`, and `Throw-in` pass types.
- The output is a rate per 100 opposition passes, not a percentage. It is not capped and can theoretically exceed 100 when multiple pressures occur per passing opportunity.
- `team.name` attributes a Pressure to the pressing team. No `team != possession_team` filter is used.
- Numerator and denominator counts are preserved alongside every calculated rate for auditability.

### One-match implementation and validation

- Added `analysis/high_zone_pressures_one_match.py` for Manchester United vs Tottenham Hotspur, match `3754097`.
- Manchester United recorded 128 qualifying high-zone pressures against 401 qualifying Tottenham passes: 31.9 pressures per 100 opposition passes.
- Tottenham recorded 90 qualifying high-zone pressures against 358 qualifying Manchester United passes: 25.1 per 100.
- Checked concrete qualifying examples for both event sets, including Pressure coordinates above 48 and opposition Pass coordinates below 72.
- Confirmed that no excluded restart pass remained in the denominator.
- Confirmed with an example at `00:08:10.209` that a valid Manchester United Pressure can have both `team.name` and `possession_team.name` equal to Manchester United. This supports the decision not to require those fields to differ.

### Full-season implementation

- Added `analysis/high_zone_pressures_season.py` and saved its output to `data/processed/high_zone_pressures_per_100_opposition_passes_2015_16.csv`.
- Aggregated the raw pressure numerator and opposition-pass denominator over the season before dividing; match-level rates were not averaged.
- All 20 teams have complete 38/38 match coverage, a non-zero denominator, and a rank from 1 to 20.
- Liverpool ranked first with 3,777 pressures / 9,844 opposition passes = 38.4 per 100.
- Tottenham Hotspur ranked second with 3,518 / 9,186 = 38.3 per 100.
- Sunderland and West Bromwich Albion were lowest; both round to 24.8 per 100, from 3,025 / 12,192 and 3,060 / 12,350 respectively.

### Interpretation and limitations

- Higher values mean more recorded high-zone Pressure events relative to opponent passing opportunities in the corresponding physical zone.
- The metric measures pressure activity, not success. It does not require a turnover, tackle, shot prevention, or completed defensive action.
- Multiple players can pressure during one opponent action, so the rate can exceed 100 and must not be interpreted as a percentage.
- The count ignores Pressure duration and may treat one long pressure differently from several short events.
- Opponent passing style, match state, and the chosen zone boundary can affect the rate.
- It cannot measure coordinated team shape, pressing traps, compactness, defensive-line height, or off-ball movement.

### Deferred comparison

- The PPDA-style Option 1 remains documented as a possible later comparison or robustness metric.
- PPDA was not combined with this feature and has not been implemented.
- Tactical feature #4 was not started.
