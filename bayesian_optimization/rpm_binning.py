"""
RPM Binning Module
Groups dyno data into discrete RPM intervals and aggregates BSFC
"""

from typing import Dict, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class BinnedData:
    """Container for RPM-binned aggregated data"""
    rpm_centers: np.ndarray  # Center of each RPM bin
    lambda_values: np.ndarray  # Mean lambda per bin
    timing_values: np.ndarray  # Mean timing per bin
    bsfc_values: np.ndarray  # Mean BSFC per bin
    bsfc_std: np.ndarray  # Std dev of BSFC per bin (for uncertainty)
    sample_counts: np.ndarray  # Number of samples per bin
    
    # Aggregated data for GP training (one point per bin)
    X: np.ndarray  # Shape (n_bins, 3): [lambda, timing, rpm] means
    y: np.ndarray  # Shape (n_bins,): mean BSFC per bin
    y_std: np.ndarray  # Shape (n_bins,): std BSFC per bin (noise estimate)


def bin_by_rpm(
    data: Dict[str, np.ndarray],
    rpm_col: str = "Engine Speed",
    lambda_col: str = "Fuel Mixture Aim",
    timing_col: str = "Ignition Timing Main",
    bsfc_col: str = "Dyno Brake Specific Fuel Consumption",
    bin_width: int = 50,
    rpm_min: Optional[int] = None,
    rpm_max: Optional[int] = None,
    min_samples: int = 3,
) -> BinnedData:
    """
    Bin data by RPM intervals and compute aggregated statistics.
    
    Args:
        data: Dictionary with column arrays
        rpm_col: Column name for RPM values
        lambda_col: Column name for lambda/AFR values
        timing_col: Column name for ignition timing
        bsfc_col: Column name for BSFC values
        bin_width: Width of RPM bins in RPM
        rpm_min: Minimum RPM to consider (auto-detect if None)
        rpm_max: Maximum RPM to consider (auto-detect if None)
        min_samples: Minimum samples required per bin
        
    Returns:
        BinnedData with aggregated statistics
    """
    rpm = data[rpm_col]
    lambda_vals = data[lambda_col]
    timing = data[timing_col]
    bsfc = data[bsfc_col]
    
    # Auto-detect RPM range if not specified
    if rpm_min is None:
        rpm_min = int(np.floor(rpm.min() / bin_width) * bin_width)
    if rpm_max is None:
        rpm_max = int(np.ceil(rpm.max() / bin_width) * bin_width)
    
    # Create bin edges
    bin_edges = np.arange(rpm_min, rpm_max + bin_width, bin_width)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Assign each data point to a bin
    bin_indices = np.digitize(rpm, bin_edges) - 1
    
    # Aggregate per bin
    rpm_centers = []
    lambda_means = []
    timing_means = []
    bsfc_means = []
    bsfc_stds = []
    counts = []
    
    for i, center in enumerate(bin_centers):
        mask = bin_indices == i
        n_samples = mask.sum()
        
        if n_samples >= min_samples:
            rpm_centers.append(center)
            lambda_means.append(lambda_vals[mask].mean())
            timing_means.append(timing[mask].mean())
            bsfc_means.append(bsfc[mask].mean())
            bsfc_stds.append(bsfc[mask].std() if n_samples > 1 else 50.0)  # Default std if single sample
            counts.append(n_samples)
    
    # Convert to arrays
    rpm_centers = np.array(rpm_centers)
    lambda_means = np.array(lambda_means)
    timing_means = np.array(timing_means)
    bsfc_means = np.array(bsfc_means)
    bsfc_stds = np.array(bsfc_stds)
    counts = np.array(counts)
    
    # Build GP training data from bin means (one point per bin)
    X = np.column_stack([lambda_means, timing_means, rpm_centers])
    y = bsfc_means
    
    return BinnedData(
        rpm_centers=rpm_centers,
        lambda_values=lambda_means,
        timing_values=timing_means,
        bsfc_values=bsfc_means,
        bsfc_std=bsfc_stds,
        sample_counts=counts,
        X=X,
        y=y,
        y_std=bsfc_stds,
    )


def aggregate_binned_data(binned: BinnedData) -> dict:
    """
    Create a summary of the binned data for reporting.
    
    Args:
        binned: BinnedData object
        
    Returns:
        Dictionary with summary statistics
    """
    return {
        "n_bins": len(binned.rpm_centers),
        "rpm_range": [float(binned.rpm_centers.min()), float(binned.rpm_centers.max())],
        "total_samples": int(binned.sample_counts.sum()),
        "avg_samples_per_bin": float(binned.sample_counts.mean()),
        "lambda_range": [float(binned.lambda_values.min()), float(binned.lambda_values.max())],
        "timing_range": [float(binned.timing_values.min()), float(binned.timing_values.max())],
        "bsfc_range": [float(binned.bsfc_values.min()), float(binned.bsfc_values.max())],
    }
