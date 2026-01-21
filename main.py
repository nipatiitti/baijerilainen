#!/usr/bin/env python3
"""
ECU BSFC Optimization using Bayesian Optimization

This script optimizes Fuel Mixture Aim (Lambda) and Ignition Timing
to minimize Brake Specific Fuel Consumption (BSFC) across RPM ranges.

Usage:
    python main.py                    # Process all CSVs in data/
    python main.py file1.csv file2.csv  # Process specific files
"""

import argparse
from pathlib import Path

from bayesian_optimization import (
    load_all_data,
    load_csv_files,
    filter_valid_data,
    bin_by_rpm,
    aggregate_binned_data,
    BSFCGaussianProcess,
    BSFCOptimizer,
    export_results,
)
from bayesian_optimization.exporter import export_ecu_map_csv

# =============================================================================
# CONFIGURATION - Modify these as needed
# =============================================================================

# Column names in the CSV files
COLUMNS = [
    "Engine Speed",
    "Fuel Mixture Aim",
    "Ignition Timing Main",
    "Dyno Brake Specific Fuel Consumption",
]

# Column roles (which column serves which purpose)
RPM_COLUMN = "Engine Speed"
LAMBDA_COLUMN = "Fuel Mixture Aim"
TIMING_COLUMN = "Ignition Timing Main"
BSFC_COLUMN = "Dyno Brake Specific Fuel Consumption"

# RPM binning configuration
RPM_BIN_WIDTH = 50  # RPM per bin (smaller = more resolution, less noise)
MIN_SAMPLES_PER_BIN = 3  # Minimum data points required per bin

# Optimization bounds (None = auto-detect from data)
LAMBDA_BOUNDS = None  # e.g., (0.85, 1.15) for lambda
TIMING_BOUNDS = None  # e.g., (5.0, 35.0) for degrees BTDC

# Number of next experiments to suggest
N_SUGGESTIONS = 5

# Paths
DATA_FOLDER = Path("data")
RESULTS_FOLDER = Path("results")

# =============================================================================
# MAIN PIPELINE
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="ECU BSFC Optimization using Bayesian Optimization"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="CSV files to process (default: all files in data/)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_FOLDER,
        help="Data directory (default: data/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_FOLDER,
        help="Output directory (default: results/)",
    )
    parser.add_argument(
        "--bin-width",
        type=int,
        default=RPM_BIN_WIDTH,
        help=f"RPM bin width (default: {RPM_BIN_WIDTH})",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization data generation (faster)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ECU BSFC Optimization - Bayesian Optimizer")
    print("=" * 60)
    
    # Step 1: Load data
    print("\n[1/5] Loading data...")
    
    if args.files:
        # Load specific files
        filepaths = [Path(f) for f in args.files]
        for fp in filepaths:
            if not fp.exists():
                # Try relative to data dir
                fp_alt = args.data_dir / fp
                if fp_alt.exists():
                    filepaths[filepaths.index(fp)] = fp_alt
                else:
                    raise FileNotFoundError(f"File not found: {fp}")
        data = load_csv_files(filepaths, COLUMNS)
    else:
        # Load all files from data directory
        data = load_all_data(args.data_dir, COLUMNS)
    
    # Filter out invalid BSFC values (zeros indicate no load/invalid measurement)
    data = filter_valid_data(data, BSFC_COLUMN, min_bsfc=0.0)
    
    n_samples = len(data[COLUMNS[0]])
    print(f"Total valid samples: {n_samples}")
    
    if n_samples == 0:
        print("ERROR: No valid data loaded. Check your CSV files.")
        return 1
    
    # Step 2: Bin by RPM
    print(f"\n[2/5] Binning data by RPM (width={args.bin_width})...")
    
    binned = bin_by_rpm(
        data,
        rpm_col=RPM_COLUMN,
        lambda_col=LAMBDA_COLUMN,
        timing_col=TIMING_COLUMN,
        bsfc_col=BSFC_COLUMN,
        bin_width=args.bin_width,
        min_samples=MIN_SAMPLES_PER_BIN,
    )
    
    summary = aggregate_binned_data(binned)
    print(f"Created {summary['n_bins']} RPM bins")
    print(f"RPM range: {summary['rpm_range'][0]:.0f} - {summary['rpm_range'][1]:.0f}")
    print(f"Total samples in bins: {summary['total_samples']}")
    print(f"Avg samples per bin: {summary['avg_samples_per_bin']:.1f}")
    
    if summary['n_bins'] < 3:
        print("ERROR: Not enough RPM bins with data. Need at least 3.")
        return 1
    
    # Step 3: Fit GP model
    print("\n[3/5] Fitting Gaussian Process model...")
    
    gp = BSFCGaussianProcess(noise_level=0.1, n_restarts=10)
    gp.fit(binned.X, binned.y)
    
    # Step 4: Run optimization
    print("\n[4/5] Running Bayesian optimization...")
    
    optimizer = BSFCOptimizer(
        gp,
        lambda_bounds=LAMBDA_BOUNDS,
        timing_bounds=TIMING_BOUNDS,
        n_suggestions=N_SUGGESTIONS,
    )
    
    result = optimizer.optimize(binned)
    
    # Step 5: Export results
    print("\n[5/5] Exporting results...")
    
    results_path = export_results(
        result,
        binned,
        gp,
        args.output_dir,
        include_visualization_data=not args.no_viz,
    )
    
    # Also export simple ECU map CSVs
    export_ecu_map_csv(result, args.output_dir)
    
    # Summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"\nBest predicted BSFC: {result.best_bsfc_overall:.4f}")
    print(f"\nNext suggested experiments ({len(result.suggested_experiments)}):")
    for i, exp in enumerate(result.suggested_experiments, 1):
        print(f"  {i}. RPM={exp['rpm']:.0f}, λ={exp['lambda']:.3f}, timing={exp['timing']:.1f}°")
    
    print(f"\nResults saved to: {args.output_dir}/")
    print("\nTo continue optimization:")
    print("  1. Run dyno tests with suggested parameters")
    print("  2. Export new CSV from MoTeC")
    print("  3. Add CSV to data/ folder")
    print("  4. Re-run: python main.py")
    
    return 0


if __name__ == "__main__":
    exit(main())
