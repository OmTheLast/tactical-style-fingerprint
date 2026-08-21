export type Feature = {
  key: string;
  label: string;
  raw_metric_name: string;
  raw_value: number;
  raw_unit: string;
  z_score: number;
  display_value: number;
  definition: string;
  high_meaning: string;
  limitation: string;
};

export type Fingerprint = {
  team: string;
  season: string;
  features: Feature[];
  display_scale_note: string;
  model_limitations: string[];
};

export type FeatureDifference = {
  key: string;
  label: string;
  signed_z_difference: number;
  absolute_z_difference: number;
};

export type Neighbour = {
  team: string;
  euclidean_distance: number;
  closest_dimensions: string[];
  different_dimensions: string[];
  feature_differences: FeatureDifference[];
};

export type NeighboursResponse = {
  team: string;
  neighbours: Neighbour[];
  distance_note: string;
};

export type Comparison = {
  team_a: Fingerprint;
  team_b: Fingerprint;
  euclidean_distance: number;
  feature_differences: FeatureDifference[];
  distance_note: string;
};

export type TeamsResponse = {
  season: string;
  teams: string[];
  model: string;
  limitations: string[];
};

export type ExplanationResponse = {
  team_a: string;
  team_b: string;
  model: string;
  explanation: string;
  grounding_note: string;
};
