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

## 2026-08-20 — Attacking Width definition investigation

### Status

- Tactical feature #3 was committed and pushed as commit `915c988` before beginning this investigation.
- Investigated three event-data definitions for tactical feature #4:
  1. mean lateral distance of final-third pass and carry destinations;
  2. wide-channel share of final-third entries;
  3. continuously attack-weighted mean lateral distance.
- No Attacking Width definition has been selected or implemented yet.

### Data and coordinate audit

- StatsBomb's pitch is 120 by 80 units, with the horizontal centre line at `y = 40`. The penalty-area outer edges are marked at `y = 18` and `y = 62`.
- Absolute lateral distance `abs(y - 40)` is unchanged when coordinates rotate between teams as `y -> 80 - y`, so it measures distance from the centre without treating the left and right flanks differently.
- The season contains 329,685 non-restart Pass attempts and 276,949 Carry events. Every inspected Pass has `pass.end_location`, and every Carry has `carry.end_location`.
- There are 110,587 eligible Pass endpoints and 84,876 Carry endpoints in the final third (`end_x >= 80`).
- There are 40,420 pass and 12,624 carry entries crossing from `start_x < 80` to `end_x >= 80`; 21,950 pass entries and 6,420 carry entries end outside the penalty-area-width boundaries (`y <= 18` or `y >= 62`).
- Ball Receipt locations are available but would largely repeat Pass destinations. Shots naturally concentrate centrally and can mix width with chance creation. Dribbles have a start location but no comparable movement endpoint. These events are therefore not recommended for the initial endpoint-based definitions.

### Options under consideration

- **Mean final-third destination width:** mean `abs(end_y - 40)` over non-restart Pass attempts and Carries ending at `x >= 80`. This has no arbitrary lateral channel boundary, although it retains the standard final-third threshold.
- **Wide-channel share of final-third entries:** Passes and Carries crossing from `start_x < 80` to `end_x >= 80`, with the numerator restricted to endpoints at `y <= 18` or `y >= 62`. The lateral thresholds are linked to the penalty-area edges but remain a modelling choice.
- **Attack-weighted mean lateral distance:** `sum((end_x / 120) * abs(end_y - 40)) / sum(end_x / 120)` over all eligible Pass and Carry endpoints. This has no hard x or y thresholds, but its linear attacking weight is less intuitive and is itself a modelling assumption.
- All options would include successful and unsuccessful non-restart Pass attempts to represent intended attacking direction and would include Carry endpoints to capture width created by ball carrying.
- Pass endpoints and Ball Receipt events should not both be counted, because they often describe the same movement destination.

### Current recommendation and limitations

- Mean final-third destination width is the current V1 recommendation because it directly describes attacking locations, is easy to audit, does not reduce width to crossing, and avoids an arbitrary wide/not-wide lateral cutoff.
- Pooling Pass and Carry endpoints means action mix affects the score, and each recorded action receives equal weight.
- None of the options measures the actual width of the full team, winger/full-back positioning without the ball, pitch occupation, switches that were available but not attempted, or continuous team shape.
- No implementation should begin until an option is selected.

## 2026-08-20 — Tactical feature #4: Mean Final-Third Destination Width

### Decision

- Selected the mean final-third destination option. The tactical dimension is labelled **Attacking Width**, while the underlying raw metric remains **Mean Final-Third Destination Width**.
- The claim is deliberately limited to **width of recorded final-third ball destinations**, not true team shape or formation width.
- For every eligible non-restart Pass or Carry ending at `end_x >= 80`, the event value is `abs(end_y - 40)`.
- The team score is the arithmetic mean of those event values, pooling Pass and Carry endpoints with equal event weight.
- Successful and unsuccessful Pass attempts are included to preserve attacking intent.
- Passes explicitly typed `Corner`, `Free Kick`, `Goal Kick`, `Kick Off`, or `Throw-in` are excluded.
- Ball Receipts are excluded to avoid duplicating Pass endpoints. Shots and Dribbles are not included.
- The raw score remains in StatsBomb pitch-coordinate units and has not been normalized.

### One-match implementation and validation

- Added `analysis/attacking_width_one_match.py` for Manchester United vs Tottenham Hotspur, match `3754097`.
- Manchester United: 136 qualifying Pass endpoints, 119 Carry endpoints, 255 total endpoints, mean width 23.50.
- Tottenham Hotspur: 104 qualifying Pass endpoints, 62 Carry endpoints, 166 total endpoints, mean width 18.47.
- Inspected examples from both teams and both event types, including central and touchline-adjacent endpoints, and manually verified their `abs(end_y - 40)` values.
- Confirmed that all Pass and Carry events have endpoint lists containing at least x and y coordinates.
- Confirmed that every selected endpoint has non-missing x/y values, `end_x >= 80`, and `0 <= end_y <= 80`.
- Confirmed that none of the five explicit restart Pass types survived the filter.
- Confirmed for every qualifying event that `abs(y - 40)` equals `abs((80 - y) - 40)` within floating-point tolerance. Left/right coordinate rotation therefore does not change the metric.
- Only after these checks passed was the unchanged definition extended to the season.

### Full-season implementation

- Added `analysis/attacking_width_season.py` and saved its output to `data/processed/mean_final_third_destination_width_2015_16.csv`.
- Aggregated the sum of lateral distances and endpoint counts across the season before dividing; match means were not averaged.
- The complete sample contains 110,587 qualifying Pass endpoints and 84,876 qualifying Carry endpoints, for 195,463 total endpoints.
- All 20 teams have complete 38/38 match coverage, positive Pass and Carry endpoint counts, and mean values within the valid 0-to-40 range. No team received a suspicious-data flag.
- Norwich City ranked first at 22.95, followed by Manchester United at 22.79 and AFC Bournemouth at 22.70.
- Liverpool (20.74), Tottenham Hotspur (20.59), and Sunderland (20.32) had the three lowest raw means.

### Interpretation and limitations

- A high value means the team's recorded advanced Pass/Carry destinations tend to be farther from the pitch centre and therefore wider.
- A low value means those recorded destinations tend to be more central. High is not better and low is not worse.
- This does not measure the physical width of the full formation. Event data cannot observe a winger holding a wide position without receiving the ball; continuous player-location or tracking data would be required for that claim.
- Passes and Carries receive equal event weight, so short Carry events may affect teams differently from pass-heavy teams.
- `end_x >= 80` is a hard final-third boundary.
- The metric records where selected attacking actions end, not whether they are useful, dangerous, or successful.
- It cannot observe off-ball positioning and does not distinguish productive width from harmless wide circulation.
- Tactical feature #5, similarity modelling, normalization, AI explanations, frontend work, and deployment were not started.

## 2026-08-20 — Attacking Transition definition investigation

### Status

- Tactical feature #4 was committed and pushed as commit `8e9c500` before beginning this investigation.
- Investigated three possible definitions for the fifth and final MVP tactical metric:
  1. fast final-third transition attempts after open-play possession changes;
  2. possession-level net progression speed;
  3. StatsBomb From-Counter possession rate.
- No Attacking Transition definition has been selected or implemented yet.
- There will be no tactical feature #6 for the hackathon MVP.

### Possession and play-pattern audit

- StatsBomb supplies `possession`, `possession_team`, `play_pattern`, ordered event `index`, timestamps, locations, and type-specific Pass/Carry endpoints needed for the candidate definitions.
- The 380 matches contain 71,884 raw possession IDs. Their initial play-pattern counts include 28,550 Regular Play and 1,326 From Counter possessions, alongside kick-offs, free kicks, corners, throw-ins, goal kicks, keeper starts, and Other patterns.
- The data contains 12,617 event rows tagged From Counter, but event-row count is not a defensible team tendency denominator because longer counters generate more rows.
- Play pattern can change within a StatsBomb possession: 813 possessions contain both From Counter and Regular Play. In inspected examples, the possession begins From Counter and changes to Regular Play when the initial transition phase ends.
- A provider-based possession classification should therefore use the initial meaningful possession-team on-ball event, rather than require every event in the possession to share one label.
- Of the 1,326 possessions initially labelled From Counter, 426 contain a Shot. A possession-share definition can count the many non-shot counterattacks too, avoiding a success-only feature.
- Common fields required for grouping and timing (`possession`, `possession_team`, `play_pattern`, `minute`, `second`, and `timestamp`) were present throughout the season files.

### Options under consideration

- **Fast final-third transition-attempt rate:** among open-play possession changes where the new team differs from the previous possession team and starts below `x = 80`, count the share that produces a Pass/Carry endpoint at `x >= 80` or any Shot within 10 seconds. Unsuccessful Pass attempts into the final third would count. This directly measures fast post-regain attacking intent but requires several boundary, event-resolution, and time-threshold decisions.
- **Open-play net progression speed:** over eligible non-set-piece possessions with positive measured duration, divide total net possession progression `sum(final_x - start_x)` by total possession duration in seconds. This incorporates Passes, Carries, and time, but primarily measures general possession progression tempo rather than counterattacking frequency. Restricting it to From Counter possessions would make it provider-dependent and describe speed conditional on countering, not tendency to counter.
- **From-Counter possession rate:** count possession changes whose initial meaningful on-ball event is tagged `play_pattern.name == "From Counter"`, divided by eligible open-play possession changes, expressed per 100. Every annotated counter possession counts regardless of whether it reaches the final third or produces a Shot.

### Current recommendation and cautions

- From-Counter possession rate is the current hackathon recommendation because it is transparent, fast to implement, distinct from Pass Verticality, counts failed/non-shot counters, and directly represents how often eligible possessions begin as provider-identified counters.
- Its main weakness is reliance on StatsBomb's contextual annotation and an externally defined classification rather than a fully reproducible 10-second rule.
- Fast final-third transition-attempt rate is the strongest custom alternative but is more complex and sensitive to the 10-second window, `x = 80` boundary, regain definition, and treatment of possessions beginning high up the pitch.
- All options are affected by score state and opponent behaviour: teams cannot counter frequently if opponents rarely commit players forward or lose the ball in transition-friendly situations.
- None observes off-ball sprinting, opponent defensive shape, numerical superiority, or every attempted run without tracking data.
- No implementation should begin until an option is selected. Normalization, similarity modelling, AI explanations, frontend work, and deployment remain unstarted.

## 2026-08-21 — Tactical feature #5: From-Counter Possession Rate

### Decision

- Selected the provider-annotation option. The user-facing tactical dimension is **Counterattacking Tendency**, while the underlying raw metric remains **From-Counter Possession Rate**.
- The fixed formula is:

  `100 * possessions beginning From Counter / eligible open-play possession changes`

- Each `(match_id, period, possession)` is classified once. Individual From Counter event rows are not counted.
- A meaningful possession-team on-ball event is the first event attributed to `possession_team` whose type is one of: 50/50, Ball Receipt, Ball Recovery, Carry, Clearance, Dispossessed, Dribble, Duel, Goal Keeper, Interception, Miscontrol, Pass, Shield, or Shot.
- An eligible possession is not the first possession of its period, has a different `possession_team` from the preceding possession in that period, has a meaningful possession-team on-ball event, and that event's initial play pattern is Regular Play or From Counter.
- A qualifying counter possession is an eligible possession whose initial meaningful event is tagged `play_pattern.name == "From Counter"`.
- A possession remains one counter possession if later events switch to Regular Play.
- The rate is per 100 eligible possession changes, not a generic percentage of all possessions.
- Goals, xG, shots, final-third arrival, action outcomes, and attack success do not enter the formula.

### Shared classifier and edge handling

- Added `analysis/from_counter_possessions.py` so the one-match and season scripts reuse the exact same possession classification logic.
- Possessions are ordered by event `index` within each period and keyed by match, period, and possession ID.
- First-of-period possessions, same-team possession continuations, restart/non-open-play patterns, and possessions without a meaningful on-ball event are excluded with explicit flags.
- The 93 season possessions with no meaningful on-ball event were audited. All were `Other` play pattern and involved Referee Ball-Drop sequences; none contained a From Counter event row.

### One-match implementation and validation

- Added `analysis/from_counter_rate_one_match.py` for Manchester United vs Tottenham Hotspur, match `3754097`.
- Manchester United: 42 eligible open-play possession changes, 3 From-Counter possessions, rate 7.14 per 100.
- Tottenham Hotspur: 41 eligible changes, 2 From-Counter possessions, rate 4.88 per 100.
- Inspected counter and regular examples with their preceding team, initial event, player, timestamp, location, initial play pattern, event count, and later pattern-change flag.
- Three of Manchester United/Tottenham's five counter possessions later change to Regular Play, but each is counted exactly once.
- The match contains 72 same-team continuations and 40 restart/non-open-play changes that are correctly excluded, plus the two first possessions of periods.

### Full-season implementation

- Added `analysis/from_counter_rate_season.py` and saved its output to `data/processed/from_counter_possession_rate_2015_16.csv`.
- All 20 teams have complete 38/38 match coverage, positive eligible denominators, counter counts no greater than eligible counts, and rates within the valid 0-to-100 range. No team received a suspicious validation flag.
- The classifier found 27,325 eligible open-play possession changes and 1,320 From-Counter possession starts.
- Leicester City ranked first with 93 / 1,345 = 6.91 per 100, followed by Southampton at 6.39 and Tottenham Hotspur at 5.89.
- Manchester United ranked 18th at 3.48, Stoke City 19th at 3.43, and West Bromwich Albion 20th at 3.26.

### Interpretation and limitations

- A high value means a larger share of the team's eligible open-play possession changes begin with a provider-labelled counterattacking phase. A low value means more begin as Regular Play. High is not better and low is not worse.
- Failed, aborted, and non-shot counter possessions count equally. This keeps the metric focused on style rather than attacking output.
- This feature relies on StatsBomb's provider-defined From Counter annotation. The exact classification logic is not ours, may contain contextual judgement, and may not transfer directly to another provider.
- Score state, opponent risk-taking, defensive depth, and turnover locations affect the opportunities available to counterattack.
- Event data cannot observe off-ball runs, numerical superiority, defensive shape, or transition opportunities that a team declines without an on-ball event.
- A future robustness check could implement the independent fast-transition definition from Option 1 using a fixed time window and final-third progression rule.
- This is the fifth and final tactical metric for the hackathon MVP. There is no feature #6.
- Normalization, similarity modelling, AI explanations, frontend work, and deployment were not started.

## 2026-08-21 — Combined raw fingerprint dataset and feature audit

### Combined dataset

- Added `analysis/build_raw_fingerprints.py` to read the five season-level processed CSVs, select one raw metric column from each, and merge them on `team`.
- Used pandas `merge(..., validate="one_to_one")` so the script fails if either side contains duplicate team keys.
- Verified that every input contains exactly 20 rows and 20 unique teams, that all five team-name sets are identical, and that the selected values are present and numeric.
- Saved the 20-row result to `data/processed/premier_league_2015_16_raw_tactical_fingerprints.csv` with the five raw metrics unchanged. No normalized columns or team-similarity values were created.

### Raw feature audit

- Calculated minimum, maximum, arithmetic mean, population standard deviation (`ddof=0`), and range for each raw feature.
- Attacking Territory Share: minimum 34.7000, maximum 68.6000, mean 49.5200, standard deviation 9.9560, range 33.9000.
- Pass Verticality: minimum 0.2795, maximum 0.4445, mean 0.3526, standard deviation 0.0507, range 0.1650.
- High-Zone Pressures per 100 Opposition Passes: minimum 24.7770, maximum 38.3690, mean 29.1252, standard deviation 4.0210, range 13.5920.
- Mean Final-Third Destination Width: minimum 20.3170, maximum 22.9500, mean 21.7034, standard deviation 0.7811, range 2.6330.
- From-Counter Possession Rate: minimum 3.2570, maximum 6.9140, mean 4.8239, standard deviation 1.0426, range 3.6570.
- Calculated the Pearson correlation matrix across the 20 teams. The strongest relationship is Attacking Territory versus Pass Verticality at `-0.839`. This is a meaningful overlap warning: teams with more territorial control in this season generally passed less vertically, although the two raw definitions are not identical.
- Attacking Territory and Pressing Intensity correlate at `0.689`; Pass Verticality and Pressing Intensity correlate at `-0.590`. These may reflect a broader control-versus-directness pattern, but correlation does not establish causation.
- Attacking Width has correlations close to zero with the other four features. Its raw season-level spread is comparatively narrow: a 2.633-coordinate-unit range and 0.781 standard deviation around a 21.703 mean. It is distinct, but scaling it to equal influence could amplify small or noisy width differences, so this should be revisited with a sensitivity check rather than silently removing the feature.
- From-Counter Possession Rate is also weakly correlated with the other features, supporting its role as a separate dimension.
- Using an absolute population z-score of 2 only as an audit flag, Liverpool (`38.369`, z = `2.30`) and Tottenham Hotspur (`38.297`, z = `2.28`) stand out on the pressing metric, while Leicester City (`6.914`, z = `2.00`) stands out on the counterattacking metric. These values were not removed or changed; they are plausible football results rather than evidence of broken rows.
- With only 20 teams, correlation estimates are descriptive and season-specific. The current evidence is sufficient to proceed cautiously, with the Territory–Verticality overlap and compressed Width spread explicitly retained as concerns for the modelling decision.

### Normalization and similarity proposals only

- Considered z-score standardization plus Euclidean distance as the clearest MVP approach: each metric becomes the number of league standard deviations above or below its mean, then the five squared coordinate differences are summed and square-rooted.
- Considered 0–1 min-max scaling plus Euclidean or Manhattan distance as a more bounded and visually intuitive alternative. It is sensitive to the season's minimum and maximum and stretches the narrow Width range across the full scale.
- Considered median/IQR robust scaling plus Manhattan distance as an outlier-resistant comparison. It is less immediately intuitive for a hackathon explanation and produces unbounded values.
- Equal scaling gives each stored column comparable numerical influence, but correlated columns can still double-count a shared tactical pattern. Five equal feature weights are a transparent MVP assumption, not a scientifically proven model of football style.
- Any future user-facing score should be labelled a relative similarity index, not a probability or a percentage of tactical identity. Raw distance, nearest-team rank, or a documented bounded transformation can be shown without claiming that a team is a scientifically meaningful percentage “identical” to another.
- No normalization, pairwise team distance, similarity ranking, frontend, AI explanation, or deployment work was implemented in this stage.

## 2026-08-21 — Primary tactical fingerprints and similarity engine

### Milestone before implementation

- Committed and pushed the accepted combined raw fingerprint dataset, audit, correlation analysis, and project-log changes as commit `8ebd9dd` (`Add combined raw tactical fingerprint audit`) before beginning similarity work.

### Primary fingerprint decision

- Selected five-feature population z-score standardization plus Euclidean distance as the primary MVP similarity method.
- For each raw feature across the 20 Premier League teams, calculated `z = (team_value - league_mean) / league_population_std`, using pandas population standard deviation with `ddof=0`.
- Retained all five features with equal numerical weight: Attacking Territory, Pass Verticality, Pressing Intensity, Attacking Width, and Counterattacking Tendency.
- Did not remove Attacking Territory or Pass Verticality. Their `-0.839` correlation means the model may partly double-weight a broader control-versus-directness axis even though their raw definitions differ.
- Retained Attacking Width, while preserving the concern that standardization expands its narrow raw season range to unit variance and therefore gives small Width differences the same statistical scale as broader variation in the other metrics.

### Implementation and auditable outputs

- Added `analysis/calculate_tactical_similarity.py`.
- Saved raw values beside their five z-scores in `data/processed/premier_league_2015_16_standardized_tactical_fingerprints.csv`.
- Calculated every directed other-team comparison and saved all 380 rows to `data/processed/premier_league_2015_16_pairwise_tactical_distances.csv`.
- Each pairwise row preserves total Euclidean distance plus signed and absolute z-score differences for all five features. A signed difference is the focal team's z-score minus the comparison team's z-score.
- Saved each team's five closest neighbours to `data/processed/premier_league_2015_16_nearest_5_tactical_neighbours.csv`.
- Smaller Euclidean distance means the two five-coordinate standardized fingerprints are closer. Distance is not a probability, percentage, or claim of tactical identity.

### Validation

- Every team's distance to itself is exactly zero within numerical tolerance.
- The distance matrix is symmetric: the maximum numerical difference between A-to-B and B-to-A is zero within the reported 12 decimal places.
- No distance is negative.
- The long comparison table contains 380 directed other-team comparisons, exactly 19 for each team.
- Every team has exactly five non-missing z-scores.
- Each standardized feature has mean approximately zero and population standard deviation approximately one; all printed deviations from the targets were zero to 12 decimal places.
- The closest pair is Liverpool and Tottenham Hotspur at distance `0.6199`. Their absolute gaps are only `0.1004`, `0.2072`, `0.0179`, and `0.1959` standard deviations on Territory, Verticality, Pressing, and Width respectively; their largest gap is Counterattacking Tendency at `0.5409`.

### Selected results and plausibility

- Leicester City's closest team is West Ham United at `2.0470`, followed by Newcastle United (`2.1183`) and Southampton (`2.1837`). Leicester is not especially close to any team: versus West Ham it differs by `1.5647` standard deviations in Verticality and `1.1145` in Counterattacking Tendency. This is plausible given Leicester's unusual vertical and counterattacking profile, but the “nearest” label should not be mistaken for a close match.
- Manchester United's closest team is AFC Bournemouth at `2.0224`, followed by Manchester City (`2.4702`) and Arsenal (`2.5999`). Bournemouth matches United closely on standardized Pressing and Width but differs by `1.5769` standard deviations in Territory. This result is mathematically coherent but not an obvious whole-football comparison, illustrating the limits of five equally weighted event proxies.
- Arsenal's closest team is Chelsea at `1.6965`. They are within `0.46` standard deviations on Territory, Verticality, Pressing, and Width, but differ by `1.5470` on Counterattacking Tendency. The pairing is plausible across four dimensions but contains one important tactical difference.
- Liverpool and Tottenham are mutual nearest neighbours at `0.6199`, a highly plausible result within this fingerprint because four dimensions are extremely close and the fifth differs moderately.
- Tottenham's next closest teams after Liverpool are Chelsea (`2.0686`) and Southampton (`2.7678`), leaving a large separation between the strongest match and the alternatives.

### Diagnostic sensitivity checks

- Ran 0–1 min-max scaling plus Euclidean distance only as a diagnostic. It produced the same top-three neighbour set for 19 of 20 teams, with a mean overlap of `2.95 / 3`. Arsenal was the only changed set: Everton replaced Stoke City in third place. All 20 teams retained the same nearest neighbour. This indicates the primary rankings are not highly dependent on choosing z-score rather than min-max scaling for this dataset.
- Temporarily recalculated z-score Euclidean distance without Attacking Width. Only 2 of 20 teams retained exactly the same top-three set, mean overlap fell to `1.70 / 3`, and 8 teams retained only one of their primary top-three neighbours. The nearest neighbour remained the same for 11 of 20 teams.
- The Width ablation therefore shows material sensitivity to Attacking Width. This is consistent with giving its compressed raw spread unit variance. It is not an automatic reason to remove the selected feature, but it is a substantive limitation to disclose and revisit after the MVP.
- Saved both diagnostic comparisons to `data/processed/premier_league_2015_16_similarity_sensitivity_checks.csv`. Neither diagnostic scaling is a second production model.
- The requested five-feature z-score method remains the primary model. No 0–100 similarity index was invented.
- Frontend work, Featherless integration, deployment, and Devpost materials were not started.

## 2026-08-21 — Local MVP application

### Frozen model and milestone

- Accepted the five-feature similarity engine and froze the hackathon MVP methodology: five equal-weight population z-scores and Euclidean distance.
- Committed and pushed the accepted similarity engine as commit `d0887a3` before beginning product work.
- No feature was added, removed, reweighted, or redesigned.
- Preserved all four required limitations in the API and interface: Territory/Verticality correlation, Width sensitivity, five-feature incompleteness, and the fact that nearest does not necessarily mean close.

### Architecture created

- Added a Next.js 16 App Router frontend under `frontend/` and a Python FastAPI backend under `backend/`.
- Kept the data pipeline offline. The backend loads the validated standardized fingerprint and pairwise-distance CSVs once through cached data-access functions rather than recalculating 380 matches per request.
- Added explicit CORS configuration for the local Next.js origins and a configurable deployed `FRONTEND_ORIGIN`.
- Added `.env.example` with placeholders only, ignored local environment files, Python virtual environments, Node dependencies, and build outputs.

### Backend API

- Added `GET /health`, `GET /teams`, `GET /teams/{team}/fingerprint`, `GET /teams/{team}/neighbours`, `GET /compare`, and `POST /explain`.
- Fingerprint responses preserve raw values and internal z-scores but also provide a visualization-only 0–100 league-relative min-max value. Zero is the observed season minimum and 100 the maximum; the transformation does not enter the frozen similarity model.
- Neighbour and comparison responses expose raw Euclidean distance plus signed and absolute feature-level z-score gaps so users can inspect why teams are close or different.

### Featherless integration

- Added a backend-only call to Featherless's OpenAI-compatible `/v1/chat/completions` endpoint using `httpx`.
- `FEATHERLESS_API_KEY` and `FEATHERLESS_MODEL` are read from server environment variables and are never referenced by frontend code.
- The request contains structured calculated evidence: both fingerprints, raw and z-scored values, signed differences, Euclidean distance, metric definitions, and known limitations.
- The system prompt prohibits invented player, manager, formation, match, history, or trophy facts; quality claims; and probability interpretations. It requires measured evidence to be separated from cautious interpretation.
- Missing configuration, timeouts, provider HTTP errors, network errors, malformed responses, and empty responses become contained explanation errors. The fingerprint, neighbours, and comparison continue working.
- A live Featherless response was not tested because no API key or model was supplied. The successful response path and failure isolation were tested with backend mocks.

### Frontend user journey

- Built one responsive focused analytics page with a 20-team selector, SVG tactical radar, five league-relative metric cards, nearest-neighbour cards, clickable comparison selection, overlaid comparison radar, raw values, signed z-score gaps, and a grounded explanation panel.
- The interface explicitly labels the 0–100 values as league-relative visualization values and raw Euclidean distance as neither a probability nor percentage.
- Added a limitations section visible in the product rather than leaving methodology cautions only in documentation.

### Verification completed

- Backend: 7 API/data-grounding tests pass, covering 20-team loading, five-feature payloads, display bounds, known Liverpool–Tottenham distance, invalid teams, mocked explanation success, failure isolation, and structured grounding evidence.
- Frontend: ESLint passes and the optimized Next.js production build completes with TypeScript checks.
- Local browser journey: Leicester loads by default; changing to Liverpool updates the fingerprint and correctly shows Tottenham first at `0.620`; selecting Chelsea changes the comparison distance to `1.961`; requesting an explanation without credentials shows a useful configuration error while the comparison remains visible.
- Visual checks passed at the normal desktop viewport and at a 375-pixel-wide mobile viewport with no horizontal overflow. No browser console warnings or errors were recorded.

### Current limits and deployment risks

- The complete local non-AI journey works. A real AI explanation still requires the user to supply valid Featherless credentials and an available model.
- Deployment is not yet configured. The frontend and backend require compatible Node/Python hosting, correct cross-origin configuration, bundled processed CSVs, and Featherless outbound access.
- `NEXT_PUBLIC_API_BASE_URL` is embedded at frontend build time and must point at the deployed backend.
- A public deployment should add rate limiting to `/explain` to reduce abuse and inference-cost risk.
- Demo video and Devpost work were not started.

## 2026-08-21 — Production preparation begun

### Clean local MVP milestone

- Re-ran the local verification before deployment: all 7 backend tests passed, frontend lint passed, and the optimized Next.js build completed successfully.
- Committed and pushed the complete accepted local product as commit `1c78067` (`Build local tactical fingerprint MVP`).
- Corrected the local Git remote to the repository's current URL after GitHub reported that the old misspelled URL now redirects.

### Production hardening completed locally

- Added a rolling in-memory per-client limit to `POST /explain`, configurable through `EXPLAIN_RATE_LIMIT_REQUESTS` and `EXPLAIN_RATE_LIMIT_WINDOW_SECONDS` and defaulting to 5 attempts per 10 minutes.
- The limiter returns HTTP 429 with `Retry-After`; it affects only AI explanation requests, so fingerprints, neighbours, and comparisons remain usable.
- Documented that this is intentionally modest single-instance hackathon protection: it resets when the process restarts and is not distributed across backend instances.
- Added a regression test for the limit. The expanded backend suite passes 8 tests; frontend lint and production build still pass.
- Added a Render service definition with an HTTPS health check, runtime command, secret placeholders, exact frontend-origin configuration, and the processed data available from the repository checkout.
- Expanded the README with backend-first deployment order, server-only Featherless settings, exact CORS origin, and the build-time nature of `NEXT_PUBLIC_API_BASE_URL`.

### Deployment blockers found during verification

- The Featherless key supplied for this stage is not currently present in the ignored local `.env` file or process environment. No live provider request has been claimed or performed yet.
- Render and Vercel are not currently signed in. Render reached a GitHub authorization screen and requires explicit user approval before granting the hosting service access to the GitHub account; no authorization was submitted.
- Public deployment and the requested production smoke test have therefore not yet been completed.

## 2026-08-21 — Live Featherless validation

- Merged PR #1 into `main` using a normal merge commit (`37b5c9a`) so the metric, similarity, product, and production-preparation commits remain visible in history.
- Re-ran verification on the merged `main`: 8 backend tests passed, frontend lint passed, and the optimized frontend build passed. The working tree was clean, `.env` remained ignored/untracked, and tracked Featherless assignments contained placeholders only.
- The first real Featherless request failed with HTTP 401 because the local credential/model configuration was incomplete. After the local configuration was corrected, a minimal call to `Qwen/Qwen3.8-27B` returned HTTP 200.
- A realistic first `/explain` attempt reached the model but returned empty visible content after about 20.6 seconds. The provider response showed that this Qwen reasoning model was using thinking mode for a task that only needs concise interpretation.
- Added Featherless's documented `chat_template_kwargs: {"enable_thinking": false}` request setting. This keeps the model focused on explaining the already-calculated evidence rather than spending the completion budget on hidden reasoning.
- Re-ran the real Liverpool–Tottenham `/explain` request successfully: HTTP 200 in approximately 21.2 seconds using `Qwen/Qwen3.8-27B`.
- The returned explanation named both teams, referred to all five dimensions, correctly treated the `0.620` Euclidean distance as a distance rather than a probability, identified the counterattacking gap as the largest difference, and disclosed the model's important limitations. It did not introduce obvious unsupported player, manager, formation, results, or history claims.
- The real API revealed meaningful latency but did not exceed the existing 35-second backend timeout. The non-AI routes remained healthy throughout failed provider attempts.
