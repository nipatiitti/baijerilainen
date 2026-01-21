export const RESULTS_FOLDER = 'results';

export interface OptimizationResults {
  metadata: {
    timestamp: string;
    n_training_samples: number;
    training_bounds: {
      lambda: [number, number];
      timing: [number, number];
      rpm: [number, number];
    };
  };
  data_summary: {
    n_bins: number;
    rpm_range: [number, number];
    total_samples: number;
    avg_samples_per_bin: number;
    lambda_range: [number, number];
    timing_range: [number, number];
    bsfc_range: [number, number];
  };
  optimal_map: {
    format: string;
    axis: {
      name: string;
      values: number[];
      unit: string;
    };
    tables: {
      lambda: { name: string; unit: string; values: number[] };
      timing: { name: string; unit: string; values: number[] };
      predicted_bsfc: { name: string; unit: string; values: number[] };
    };
  };
  suggested_experiments: Array<{
    rpm: number;
    lambda: number;
    timing: number;
    predicted_bsfc: number;
    uncertainty: number;
    expected_improvement: number;
  }>;
  current_best: {
    overall_bsfc: number;
    per_rpm: Record<string, number>;
  };
}

export interface ResultFileSummary {
  filename: string;
  timestamp: string;
  n_bins: number;
  best_bsfc: number;
  rpm_range: [number, number];
}
