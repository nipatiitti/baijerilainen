"""
Results Exporter Module
Exports optimization results to JSON files
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .optimizer import OptimizationResult
from .rpm_binning import BinnedData, aggregate_binned_data
from .gp_model import BSFCGaussianProcess


def export_results(
    result: OptimizationResult,
    binned_data: BinnedData,
    gp_model: BSFCGaussianProcess,
    output_dir: Path,
    include_visualization_data: bool = True,
) -> Path:
    """
    Export optimization results to a new timestamped JSON file.
    
    Args:
        result: Optimization results
        binned_data: Binned training data
        gp_model: Fitted GP model
        output_dir: Directory to save results
        include_visualization_data: Whether to include GP grid predictions
        
    Returns:
        Path to the created results file
    """
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"optimization_results_{timestamp}.json"
    filepath = output_dir / filename
    
    # Build output structure
    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "n_training_samples": result.n_training_samples,
            "training_bounds": result.training_bounds,
        },
        "data_summary": aggregate_binned_data(binned_data),
        "optimal_map": _format_optimal_map(result.optimal_map),
        "suggested_experiments": result.suggested_experiments,
        "current_best": {
            "overall_bsfc": result.best_bsfc_overall,
            "per_rpm": {str(int(k)): v for k, v in result.best_bsfc_per_rpm.items()},
        },
    }
    
    # Add visualization data if requested
    if include_visualization_data:
        output["visualization"] = _generate_visualization_data(
            gp_model, binned_data, result
        )
    
    # Write to file
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {filepath}")
    
    return filepath


def _format_optimal_map(optimal_map: dict) -> dict:
    """
    Format the optimal map for ECU calibration tools.
    Creates 1D tables with RPM as the axis.
    """
    rpms = sorted(optimal_map.keys())
    
    return {
        "format": "1D_map",
        "axis": {
            "name": "RPM",
            "values": [int(rpm) for rpm in rpms],
            "unit": "rpm",
        },
        "tables": {
            "lambda": {
                "name": "Fuel Mixture Aim",
                "unit": "LA",
                "values": [optimal_map[rpm]["lambda"] for rpm in rpms],
            },
            "timing": {
                "name": "Ignition Timing Main",
                "unit": "dBTDC",
                "values": [optimal_map[rpm]["timing"] for rpm in rpms],
            },
            "predicted_bsfc": {
                "name": "Predicted BSFC",
                "unit": "",
                "values": [optimal_map[rpm]["predicted_bsfc"] for rpm in rpms],
            },
        },
    }


def _generate_visualization_data(
    gp_model: BSFCGaussianProcess,
    binned_data: BinnedData,
    result: OptimizationResult,
) -> dict:
    """
    Generate data for frontend visualization.
    """
    bounds = gp_model.get_training_bounds()
    
    # Generate surface plots for a few representative RPMs
    rpm_values = binned_data.rpm_centers
    
    # Select 3-5 RPMs spread across the range
    n_plots = min(5, len(rpm_values))
    indices = [int(i * (len(rpm_values) - 1) / (n_plots - 1)) for i in range(n_plots)]
    selected_rpms = [rpm_values[i] for i in indices]
    
    surfaces = []
    for rpm in selected_rpms:
        grid_data = gp_model.predict_grid(
            lambda_range=bounds["lambda"],
            timing_range=bounds["timing"],
            rpm=rpm,
            n_points=30,  # Lower resolution for smaller file size
        )
        surfaces.append(grid_data)
    
    # Training data points for scatter overlay
    training_points = {
        "lambda": binned_data.X[:, 0].tolist(),
        "timing": binned_data.X[:, 1].tolist(),
        "rpm": binned_data.X[:, 2].tolist(),
        "bsfc": binned_data.y.tolist(),
    }
    
    return {
        "surfaces": surfaces,
        "training_data": training_points,
        "bounds": bounds,
    }


def export_ecu_map_csv(
    result: OptimizationResult,
    output_dir: Path,
) -> Tuple[Path, Path]:
    """
    Export optimal maps as simple CSV files for ECU calibration tools.
    
    Args:
        result: Optimization results
        output_dir: Directory to save results
        
    Returns:
        Tuple of (lambda_map_path, timing_map_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    rpms = sorted(result.optimal_map.keys())
    
    # Lambda map
    lambda_path = output_dir / f"lambda_map_{timestamp}.csv"
    with open(lambda_path, "w") as f:
        f.write("RPM,Fuel Mixture Aim (LA)\n")
        for rpm in rpms:
            f.write(f"{int(rpm)},{result.optimal_map[rpm]['lambda']}\n")
    
    # Timing map
    timing_path = output_dir / f"timing_map_{timestamp}.csv"
    with open(timing_path, "w") as f:
        f.write("RPM,Ignition Timing Main (dBTDC)\n")
        for rpm in rpms:
            f.write(f"{int(rpm)},{result.optimal_map[rpm]['timing']}\n")
    
    print(f"ECU maps saved to:")
    print(f"  Lambda: {lambda_path}")
    print(f"  Timing: {timing_path}")
    
    return lambda_path, timing_path
