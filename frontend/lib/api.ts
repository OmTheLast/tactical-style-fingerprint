import type {
  Comparison,
  ExplanationResponse,
  Fingerprint,
  NeighboursResponse,
  TeamsResponse,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the status-based fallback when a provider returns non-JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  teams: () => request<TeamsResponse>("/teams"),
  fingerprint: (team: string) =>
    request<Fingerprint>(`/teams/${encodeURIComponent(team)}/fingerprint`),
  neighbours: (team: string) =>
    request<NeighboursResponse>(`/teams/${encodeURIComponent(team)}/neighbours`),
  compare: (teamA: string, teamB: string) =>
    request<Comparison>(
      `/compare?team_a=${encodeURIComponent(teamA)}&team_b=${encodeURIComponent(teamB)}`,
    ),
  explain: (teamA: string, teamB: string) =>
    request<ExplanationResponse>("/explain", {
      method: "POST",
      body: JSON.stringify({ team_a: teamA, team_b: teamB }),
    }),
};
