"""
RPM Binning Module
Groups dyno data into discrete RPM intervals, keeping individual test points
for proper GP fitting within each bin.
"""

from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class RPMBin:
    """Container for data within a single RPM bin"""
    rpm_center: float
    rpm_min: float
    rpm_max: float

    # Raw data points within this bin (for GP training)
    lambda_values: np.ndarray
    timing_values: np.ndarray
    bsfc_values: np.ndarray

    # 2D GP training data for this bin: X = [lambda, timing], y = bsfc
    X: np.ndarray  # Shape (n_points, 2)
    y: np.ndarray  # Shape (n_points,)

    @property
    def n_samples(self) -> int:
        return len(self.y)

    @property
    def mean_bsfc(self) -> float:
        return float(np.mean(self.bsfc_values))

    @property
    def min_bsfc(self) -> float:
        return float(np.min(self.bsfc_values))

    @property
    def lambda_range(self) -> tuple:
        return (float(np.min(self.lambda_values)), float(np.max(self.lambda_values)))

    @property
    def timing_range(self) -> tuple:
        return (float(np.min(self.timing_values)), float(np.max(self.timing_values)))


@dataclass
class BinnedData:
    """Container for all RPM bins"""
    bins: List[RPMBin]
    bin_width: int

    @property
    def rpm_centers(self) -> np.ndarray:
        return np.array([b.rpm_center for b in self.bins])

    @property
    def n_bins(self) -> int:
        return len(self.bins)

    @property
    def total_samples(self) -> int:
        return sum(b.n_samples for b in self.bins)

    # For backward compatibility with old code
    @property
    def bsfc_values(self) -> np.ndarray:
        return np.array([b.mean_bsfc for b in self.bins])

    @property
    def lambda_values(self) -> np.ndarray:
        return np.array([np.mean(b.lambda_values) for b in self.bins])

    @property
    def timing_values(self) -> np.ndarray:
        return np.array([np.mean(b.timing_values) for b in self.bins])

    def get_bin_by_rpm(self, rpm: float) -> Optional[RPMBin]:
        """Find the bin containing the given RPM"""
        for b in self.bins:
            if b.rpm_min <= rpm < b.rpm_max:
                return b
        return None


def bin_by_rpm(
    data: Dict[str, np.ndarray],
    rpm_col: str = "Engine Speed",
    lambda_col: str = "Fuel Mixture Aim",
    timing_col: str = "Ignition Timing Main",
    bsfc_col: str = "Dyno Brake Specific Fuel Consumption",
    bin_width: int = 100,
    rpm_min: Optional[int] = None,
    rpm_max: Optional[int] = None,
    min_samples: int = 3,
) -> BinnedData:
    """
    Bin data by RPM intervals, averaging by test run within each bin.

    For each RPM bin, this function:
    1. Groups data points by test run (source file)
    2. Computes the average lambda, timing, and BSFC for each test run
    3. Uses these per-test-run averages as training points for the GP

    This reduces noise from high-frequency sampling while preserving
    the variance between different test runs with different parameters.

    Args:
        data: Dictionary with column arrays (must include '_test_run_id')
        rpm_col: Column name for RPM values
        lambda_col: Column name for lambda/AFR values
        timing_col: Column name for ignition timing
        bsfc_col: Column name for BSFC values
        bin_width: Width of RPM bins in RPM
        rpm_min: Minimum RPM to consider (auto-detect if None)
        rpm_max: Maximum RPM to consider (auto-detect if None)
        min_samples: Minimum test run averages required per bin

    Returns:
        BinnedData with list of RPMBin objects containing per-test-run averages
    """
    rpm = data[rpm_col]
    lambda_vals = data[lambda_col]
    timing = data[timing_col]
    bsfc = data[bsfc_col]

    # Get test run IDs if available, otherwise treat all data as one run
    if '_test_run_id' in data:
        test_run_ids = data['_test_run_id'].astype(int)
    else:
        test_run_ids = np.zeros(len(rpm), dtype=int)

    # Auto-detect RPM range if not specified
    if rpm_min is None:
        rpm_min = int(np.floor(rpm.min() / bin_width) * bin_width)
    if rpm_max is None:
        rpm_max = int(np.ceil(rpm.max() / bin_width) * bin_width)

    # Create bin edges
    bin_edges = np.arange(rpm_min, rpm_max + bin_width, bin_width)

    # Assign each data point to a bin
    bin_indices = np.digitize(rpm, bin_edges) - 1

    # Create bins with per-test-run averaged data points
    bins = []

    for i in range(len(bin_edges) - 1):
        bin_mask = bin_indices == i

        if bin_mask.sum() == 0:
            continue

        # Get unique test runs in this bin
        runs_in_bin = np.unique(test_run_ids[bin_mask])

        # Average each test run's data within this bin
        avg_lambdas = []
        avg_timings = []
        avg_bsfcs = []

        for run_id in runs_in_bin:
            run_mask = bin_mask & (test_run_ids == run_id)
            if run_mask.sum() > 0:
                avg_lambdas.append(lambda_vals[run_mask].mean())
                avg_timings.append(timing[run_mask].mean())
                avg_bsfcs.append(bsfc[run_mask].mean())

        # Number of test runs with data in this bin
        n_samples = len(avg_lambdas)

        if n_samples >= min_samples:
            bin_lambda = np.array(avg_lambdas)
            bin_timing = np.array(avg_timings)
            bin_bsfc = np.array(avg_bsfcs)

            # Create 2D training data for this bin's GP
            X = np.column_stack([bin_lambda, bin_timing])

            bins.append(RPMBin(
                rpm_center=float((bin_edges[i] + bin_edges[i + 1]) / 2),
                rpm_min=float(bin_edges[i]),
                rpm_max=float(bin_edges[i + 1]),
                lambda_values=bin_lambda,
                timing_values=bin_timing,
                bsfc_values=bin_bsfc,
                X=X,
                y=bin_bsfc,
            ))

    return BinnedData(bins=bins, bin_width=bin_width)


def aggregate_binned_data(binned: BinnedData) -> dict:
    """
    Create a summary of the binned data for reporting.

    Args:
        binned: BinnedData object

    Returns:
        Dictionary with summary statistics
    """
    if binned.n_bins == 0:
        return {
            "n_bins": 0,
            "rpm_range": [0, 0],
            "total_samples": 0,
            "avg_samples_per_bin": 0,
            "lambda_range": [0, 0],
            "timing_range": [0, 0],
            "bsfc_range": [0, 0],
        }

    all_lambda = np.concatenate([b.lambda_values for b in binned.bins])
    all_timing = np.concatenate([b.timing_values for b in binned.bins])
    all_bsfc = np.concatenate([b.bsfc_values for b in binned.bins])

    return {
        "n_bins": binned.n_bins,
        "rpm_range": [float(binned.rpm_centers.min()), float(binned.rpm_centers.max())],
        "total_samples": binned.total_samples,
        "avg_samples_per_bin": binned.total_samples / binned.n_bins,
        "lambda_range": [float(all_lambda.min()), float(all_lambda.max())],
        "timing_range": [float(all_timing.min()), float(all_timing.max())],
        "bsfc_range": [float(all_bsfc.min()), float(all_bsfc.max())],
    }
