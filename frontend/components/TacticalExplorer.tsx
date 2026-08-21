"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  ChevronRight,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { RadarChart } from "@/components/RadarChart";
import { api } from "@/lib/api";
import type {
  Comparison,
  ExplanationResponse,
  Fingerprint,
  Neighbour,
  NeighboursResponse,
  TeamsResponse,
} from "@/lib/types";

function formatRaw(value: number, unit: string) {
  if (unit === "forward share") return value.toFixed(3);
  if (unit === "% share") return `${value.toFixed(1)}%`;
  return value.toFixed(2);
}

function signed(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}σ`;
}

function MetricStrip({ fingerprint }: { fingerprint: Fingerprint }) {
  return (
    <div className="metric-strip">
      {fingerprint.features.map((feature) => (
        <article className="metric-card" key={feature.key}>
          <div className="metric-card-top">
            <span>{feature.label}</span>
            <strong>{Math.round(feature.display_value)}</strong>
          </div>
          <div className="metric-track" aria-hidden="true">
            <i style={{ width: `${feature.display_value}%` }} />
          </div>
          <div className="metric-meta">
            <span>{formatRaw(feature.raw_value, feature.raw_unit)}</span>
            <span>{feature.raw_metric_name}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function NeighbourCard({
  neighbour,
  active,
  onSelect,
}: {
  neighbour: Neighbour;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`neighbour-card ${active ? "active" : ""}`}
      onClick={onSelect}
      type="button"
    >
      <span className="neighbour-rank">Distance {neighbour.euclidean_distance.toFixed(3)}</span>
      <span className="neighbour-name">
        {neighbour.team} <ChevronRight size={18} />
      </span>
      <span className="neighbour-detail">
        <b>Closest</b> {neighbour.closest_dimensions.join(" · ")}
      </span>
      <span className="neighbour-detail muted">
        <b>Different</b> {neighbour.different_dimensions.join(" · ")}
      </span>
    </button>
  );
}

function ComparisonPanel({ comparison }: { comparison: Comparison }) {
  return (
    <section className="comparison-grid">
      <div className="comparison-radar panel">
        <div className="panel-kicker">Head-to-head fingerprint</div>
        <RadarChart
          series={[
            { label: comparison.team_a.team, color: "#89f7b5", features: comparison.team_a.features },
            { label: comparison.team_b.team, color: "#f1b86b", features: comparison.team_b.features },
          ]}
        />
      </div>
      <div className="comparison-table panel">
        <div className="comparison-heading">
          <div>
            <div className="panel-kicker">Raw tactical distance</div>
            <strong>{comparison.euclidean_distance.toFixed(3)}</strong>
          </div>
          <div className="distance-scale">
            <span>Closer</span>
            <i />
            <span>Further</span>
          </div>
        </div>
        <p className="small-note">{comparison.distance_note}</p>
        <div className="comparison-rows">
          {comparison.feature_differences.map((difference, index) => {
            const featureA = comparison.team_a.features[index];
            const featureB = comparison.team_b.features[index];
            return (
              <article className="comparison-row" key={difference.key}>
                <header>
                  <span>{difference.label}</span>
                  <b>{signed(difference.signed_z_difference)}</b>
                </header>
                <div className="dual-bars">
                  <div>
                    <i className="bar-a" style={{ width: `${featureA.display_value}%` }} />
                  </div>
                  <div>
                    <i className="bar-b" style={{ width: `${featureB.display_value}%` }} />
                  </div>
                </div>
                <footer>
                  <span>{formatRaw(featureA.raw_value, featureA.raw_unit)}</span>
                  <span>absolute gap {difference.absolute_z_difference.toFixed(2)}σ</span>
                  <span>{formatRaw(featureB.raw_value, featureB.raw_unit)}</span>
                </footer>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export function TacticalExplorer() {
  const [teamsData, setTeamsData] = useState<TeamsResponse | null>(null);
  const [selectedTeam, setSelectedTeam] = useState("Leicester City");
  const [fingerprint, setFingerprint] = useState<Fingerprint | null>(null);
  const [neighbours, setNeighbours] = useState<NeighboursResponse | null>(null);
  const [comparisonTeam, setComparisonTeam] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explanationError, setExplanationError] = useState("");
  const [loading, setLoading] = useState(true);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .teams()
      .then(setTeamsData)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  useEffect(() => {
    let current = true;
    Promise.all([api.fingerprint(selectedTeam), api.neighbours(selectedTeam)])
      .then(([nextFingerprint, nextNeighbours]) => {
        if (!current) return;
        setFingerprint(nextFingerprint);
        setNeighbours(nextNeighbours);
        setComparisonTeam((previous) => {
          const stillAvailable = nextNeighbours.neighbours.some(
            (item) => item.team === previous,
          );
          return stillAvailable ? previous : nextNeighbours.neighbours[0].team;
        });
      })
      .catch((requestError: Error) => current && setError(requestError.message))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [selectedTeam]);

  useEffect(() => {
    if (!comparisonTeam || comparisonTeam === selectedTeam) return;
    let current = true;
    api
      .compare(selectedTeam, comparisonTeam)
      .then((result) => current && setComparison(result))
      .catch((requestError: Error) => current && setError(requestError.message));
    return () => {
      current = false;
    };
  }, [selectedTeam, comparisonTeam]);

  const activeNeighbour = useMemo(
    () => neighbours?.neighbours.find((item) => item.team === comparisonTeam),
    [neighbours, comparisonTeam],
  );

  async function explainMatchup() {
    if (!comparisonTeam) return;
    setExplaining(true);
    setExplanation(null);
    setExplanationError("");
    try {
      setExplanation(await api.explain(selectedTeam, comparisonTeam));
    } catch (requestError) {
      setExplanationError(
        requestError instanceof Error ? requestError.message : "Explanation failed.",
      );
    } finally {
      setExplaining(false);
    }
  }

  function chooseTeam(team: string) {
    setLoading(true);
    setError("");
    setExplanation(null);
    setExplanationError("");
    setComparison(null);
    setComparisonTeam("");
    setSelectedTeam(team);
  }

  function chooseComparison(team: string) {
    setExplanation(null);
    setExplanationError("");
    setComparisonTeam(team);
  }

  return (
    <main>
      <header className="topbar">
        <a href="#top" className="brand">
          <span className="brand-mark"><Activity size={20} /></span>
          <span>Tactical<span>Fingerprint</span></span>
        </a>
        <div className="season-pill">Premier League · 2015/16</div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><ShieldCheck size={15} /> Event-data tactical analysis</div>
          <h1>See the style.<br /><em>Not the badge.</em></h1>
          <p>
            Compare how teams occupied territory, moved the ball, pressed, used width,
            and transitioned—using five transparent StatsBomb-derived measures.
          </p>
        </div>
        <div className="selector-card">
          <label htmlFor="team-select">Build a fingerprint for</label>
          <select
            id="team-select"
            value={selectedTeam}
            onChange={(event) => chooseTeam(event.target.value)}
            disabled={!teamsData}
          >
            {(teamsData?.teams ?? [selectedTeam]).map((team) => (
              <option value={team} key={team}>{team}</option>
            ))}
          </select>
          <span>20 teams · 380 matches · five frozen MVP dimensions</span>
        </div>
      </section>

      {error && <div className="global-error"><AlertTriangle size={18} /> {error}</div>}
      {loading && !fingerprint && (
        <div className="loading-state"><LoaderCircle className="spin" /> Loading fingerprint…</div>
      )}

      {fingerprint && (
        <>
          <section className="section-shell fingerprint-section">
            <div className="section-heading">
              <div>
                <span className="section-number">01</span>
                <div>
                  <div className="panel-kicker">Selected team</div>
                  <h2>{fingerprint.team}</h2>
                </div>
              </div>
              <p>League-relative display scale</p>
            </div>
            <div className="fingerprint-layout">
              <div className="panel radar-panel">
                <RadarChart
                  series={[{ label: fingerprint.team, color: "#89f7b5", features: fingerprint.features }]}
                />
              </div>
              <div>
                <MetricStrip fingerprint={fingerprint} />
                <div className="display-note">
                  <BarChart3 size={18} />
                  <p><b>How to read the 0–100 display:</b> {fingerprint.display_scale_note}</p>
                </div>
              </div>
            </div>
          </section>

          <section className="section-shell neighbours-section">
            <div className="section-heading">
              <div>
                <span className="section-number">02</span>
                <div>
                  <div className="panel-kicker">Model output</div>
                  <h2>Nearest tactical neighbours</h2>
                </div>
              </div>
              <p>Smaller raw distance means closer</p>
            </div>
            <div className="neighbour-list">
              {neighbours?.neighbours.map((neighbour) => (
                <NeighbourCard
                  key={neighbour.team}
                  neighbour={neighbour}
                  active={neighbour.team === comparisonTeam}
                  onSelect={() => chooseComparison(neighbour.team)}
                />
              ))}
            </div>
            <p className="small-note neighbour-note">{neighbours?.distance_note}</p>
          </section>

          {comparison && activeNeighbour && (
            <section className="section-shell compare-section">
              <div className="section-heading">
                <div>
                  <span className="section-number">03</span>
                  <div>
                    <div className="panel-kicker">Explain the distance</div>
                    <h2>{selectedTeam} <ArrowRight size={24} /> {comparisonTeam}</h2>
                  </div>
                </div>
                <select
                  className="compare-select"
                  aria-label="Comparison team"
                  value={comparisonTeam}
                  onChange={(event) => chooseComparison(event.target.value)}
                >
                  {neighbours?.neighbours.map((item) => (
                    <option value={item.team} key={item.team}>{item.team}</option>
                  ))}
                </select>
              </div>
              <ComparisonPanel comparison={comparison} />

              <section className="ai-panel">
                <div className="ai-heading">
                  <div className="ai-icon"><Sparkles size={22} /></div>
                  <div>
                    <div className="panel-kicker">Grounded interpretation</div>
                    <h3>Explain this matchup</h3>
                  </div>
                  <button type="button" onClick={explainMatchup} disabled={explaining}>
                    {explaining ? <><LoaderCircle className="spin" size={17} /> Analysing</> : <><Sparkles size={17} /> Generate explanation</>}
                  </button>
                </div>
                {!explanation && !explanationError && (
                  <p className="ai-placeholder">
                    Featherless receives only the calculated metrics, signed differences,
                    definitions, distance, and limitations—not an invitation to improvise club history.
                  </p>
                )}
                {explanation && (
                  <div className="explanation-copy">
                    {explanation.explanation.split("\n").filter(Boolean).map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                    <small>{explanation.grounding_note} Model: {explanation.model}</small>
                  </div>
                )}
                {explanationError && (
                  <div className="ai-error">
                    <AlertTriangle size={18} />
                    <div><b>Explanation unavailable</b><p>{explanationError}</p><span>The fingerprint and comparison above still work.</span></div>
                  </div>
                )}
              </section>
            </section>
          )}

          <section className="method-band">
            <div>
              <span className="section-number">04</span>
              <div><div className="panel-kicker">Read the fine print</div><h2>Transparent by design</h2></div>
            </div>
            <div className="limitations-grid">
              {fingerprint.model_limitations.map((limitation, index) => (
                <article key={limitation}><span>0{index + 1}</span><p>{limitation}</p></article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
