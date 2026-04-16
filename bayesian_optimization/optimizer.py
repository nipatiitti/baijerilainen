"""
Bayesian Optimizer Module
Finds optimal Lambda and Timing parameters for each RPM bin independently
"""

import warnings
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from dataclasses import dataclass

from .gp_model import BSFCGaussianProcess
from .rpm_binning import BinnedData, RPMBin

# Minimum variance required in input dimensions to perform optimization
# If variance is below this, we use the observed best instead of optimizing
MIN_VARIANCE_THRESHOLD = 0.01


@dataclass
class OptimizationResult:
    """Container for optimization results"""
    # Optimal map: RPM -> optimal parameters
    optimal_map: Dict[float, Dict[str, float]]

    # Suggested next experiments for feedback loop
    suggested_experiments: List[dict]

    # Model info per bin
    gp_models: Dict[float, BSFCGaussianProcess]
    training_bounds: dict
    n_training_samples: int

    # Convergence info
    best_bsfc_per_rpm: Dict[float, float]
    best_bsfc_overall: float


class BSFCOptimizer:
    """
    Bayesian optimizer for BSFC minimization.
    Fits a separate GP model per RPM bin and optimizes each independently.
    """

    def __init__(
        self,
        lambda_bounds: Optional[Tuple[float, float]] = None,
        timing_bounds: Optional[Tuple[float, float]] = None,
        n_suggestions: int = 5,
        noise_level: float = 0.1,
    ):
        """
        Initialize the optimizer.

        Args:
            lambda_bounds: (min, max) bounds for lambda optimization
            timing_bounds: (min, max) bounds for timing optimization
            n_suggestions: Number of next experiments to suggest
            noise_level: GP noise level
        """
        self.lambda_bounds = lambda_bounds
        self.timing_bounds = timing_bounds
        self.n_suggestions = n_suggestions
        self.noise_level = noise_level

        # Will store fitted GP models per RPM bin
        self.gp_models: Dict[float, BSFCGaussianProcess] = {}

    def _fit_gp_for_bin(self, rpm_bin: RPMBin) -> BSFCGaussianProcess:
        """
        Fit a GP model for a single RPM bin.

        Args:
            rpm_bin: The RPM bin data

        Returns:
            Fitted GP model
        """
        gp = BSFCGaussianProcess(noise_level=self.noise_level, n_restarts=5)

        # Suppress convergence warnings - they're expected with low-variance data
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=Warning)
            gp.fit(rpm_bin.X, rpm_bin.y)

        return gp

    def _check_variance(self, rpm_bin: RPMBin) -> Tuple[bool, bool]:
        """
        Check if there's sufficient variance in lambda and timing to optimize.

        Returns:
            Tuple of (lambda_has_variance, timing_has_variance)
        """
        lambda_var = np.var(rpm_bin.lambda_values)
        timing_var = np.var(rpm_bin.timing_values)

        return (lambda_var > MIN_VARIANCE_THRESHOLD, timing_var > MIN_VARIANCE_THRESHOLD)

    def _get_bounds_for_bin(self, rpm_bin: RPMBin) -> Tuple[Tuple[float, float], Tuple[float, float], bool, bool]:
        """
        Get optimization bounds for a bin.
        If variance is too low in a dimension, constrain to observed range.

        Returns:
            Tuple of (lambda_bounds, timing_bounds, lambda_optimizable, timing_optimizable)
        """
        lambda_has_var, timing_has_var = self._check_variance(rpm_bin)

        # Lambda bounds
        l_min_obs, l_max_obs = rpm_bin.lambda_range
        if lambda_has_var and self.lambda_bounds is not None:
            # Use configured bounds but don't go beyond observed range too much
            margin = (l_max_obs - l_min_obs) * 0.2
            l_bounds = (
                max(self.lambda_bounds[0], l_min_obs - margin),
                min(self.lambda_bounds[1], l_max_obs + margin)
            )
        elif lambda_has_var:
            margin = (l_max_obs - l_min_obs) * 0.1
            l_bounds = (l_min_obs - margin, l_max_obs + margin)
        else:
            # No variance - constrain to observed range
            l_bounds = (l_min_obs, l_max_obs)

        # Timing bounds
        t_min_obs, t_max_obs = rpm_bin.timing_range
        if timing_has_var and self.timing_bounds is not None:
            margin = (t_max_obs - t_min_obs) * 0.2
            t_bounds = (
                max(self.timing_bounds[0], t_min_obs - margin),
                min(self.timing_bounds[1], t_max_obs + margin)
            )
        elif timing_has_var:
            margin = (t_max_obs - t_min_obs) * 0.1
            t_bounds = (t_min_obs - margin, t_max_obs + margin)
        else:
            # No variance - constrain to observed range
            t_bounds = (t_min_obs, t_max_obs)

        return l_bounds, t_bounds, lambda_has_var, timing_has_var

    def _expected_improvement(
        self,
        gp: BSFCGaussianProcess,
        X: np.ndarray,
        best_y: float,
        xi: float = 0.01,
    ) -> np.ndarray:
        """
        Compute Expected Improvement acquisition function.

        Args:
            gp: The GP model for this bin
            X: Query points, shape (n_points, 2) for [lambda, timing]
            best_y: Current best (minimum) observed BSFC
            xi: Exploration-exploitation trade-off parameter

        Returns:
            EI values, shape (n_points,)
        """
        mean, std = gp.predict(X, return_std=True)

        # Improvement is when we find values LOWER than best (minimization)
        improvement = best_y - mean - xi

        # Handle numerical issues
        std = np.maximum(std, 1e-9)

        Z = improvement / std
        ei = improvement * norm.cdf(Z) + std * norm.pdf(Z)

        # Set EI to 0 where std is essentially 0
        ei[std < 1e-9] = 0.0

        return ei

    def _optimize_for_bin(
        self,
        gp: BSFCGaussianProcess,
        rpm_bin: RPMBin,
        n_restarts: int = 10,
    ) -> Tuple[float, float, float, float, str]:
        """
        Find optimal (lambda, timing) for a specific RPM bin.

        Args:
            gp: Fitted GP model for this bin
            rpm_bin: The RPM bin data
            n_restarts: Number of optimization restarts

        Returns:
            Tuple of (optimal_lambda, optimal_timing, predicted_bsfc, uncertainty, notes)
        """
        l_bounds, t_bounds, lambda_has_var, timing_has_var = self._get_bounds_for_bin(
            rpm_bin)

        # Check if we have enough variance to optimize meaningfully
        if not lambda_has_var and not timing_has_var:
            # No variance in either dimension - just return best observed
            best_idx = np.argmin(rpm_bin.y)
            return (
                rpm_bin.lambda_values[best_idx],
                rpm_bin.timing_values[best_idx],
                rpm_bin.y[best_idx],
                0.0,
                "observed (no variance)"
            )

        bounds = [l_bounds, t_bounds]

        def objective(x):
            X = np.array([[x[0], x[1]]])
            mean, _ = gp.predict(X, return_std=False)
            return mean[0]

        best_result = None
        best_value = np.inf

        for _ in range(n_restarts):
            # Random starting point
            x0 = [
                np.random.uniform(*l_bounds),
                np.random.uniform(*t_bounds),
            ]

            result = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                bounds=bounds,
            )

            if result.fun < best_value:
                best_value = result.fun
                best_result = result

        # Get uncertainty at optimal point
        opt_X = np.array([[best_result.x[0], best_result.x[1]]])
        _, std = gp.predict(opt_X, return_std=True)

        # Build notes about what was optimized
        notes = []
        if not lambda_has_var:
            notes.append("λ constrained")
        if not timing_has_var:
            notes.append("timing constrained")
        note_str = ", ".join(notes) if notes else "optimized"

        return best_result.x[0], best_result.x[1], best_value, std[0], note_str

    def _find_best_experiments_for_bin(
        self,
        gp: BSFCGaussianProcess,
        rpm_bin: RPMBin,
        n_candidates: int = 500,
    ) -> Optional[dict]:
        """
        Find the best next experiment for a single RPM bin using EI.

        Args:
            gp: Fitted GP model for this bin
            rpm_bin: The RPM bin data
            n_candidates: Number of random candidates to evaluate

        Returns:
            Single suggested experiment dict, or None if no variance
        """
        l_bounds, t_bounds, lambda_has_var, timing_has_var = self._get_bounds_for_bin(
            rpm_bin)

        # If neither has variance, skip suggestions for this bin
        if not lambda_has_var and not timing_has_var:
            return None

        # Generate random candidates
        lambdas = np.random.uniform(l_bounds[0], l_bounds[1], n_candidates)
        timings = np.random.uniform(t_bounds[0], t_bounds[1], n_candidates)
        X = np.column_stack([lambdas, timings])

        # Compute EI
        best_bsfc = rpm_bin.min_bsfc
        ei = self._expected_improvement(gp, X, best_bsfc)

        # Get top candidate (best EI)
        best_idx = np.argmax(ei)
        mean, std = gp.predict(X[best_idx:best_idx+1], return_std=True)

        return {
            "rpm": round(rpm_bin.rpm_center, 0),
            "lambda": round(float(X[best_idx, 0]), 4),
            "timing": round(float(X[best_idx, 1]), 2),
            "predicted_bsfc": round(float(mean[0]), 4),
            "uncertainty": round(float(std[0]), 4),
            "expected_improvement": round(float(ei[best_idx]), 6),
        }

    def optimize(self, binned_data: BinnedData) -> OptimizationResult:
        """
        Run full optimization: fit GP per bin and find optimal parameters.

        Args:
            binned_data: RPM-binned training data

        Returns:
            OptimizationResult with optimal map and suggestions
        """
        print(
            f"\nOptimizing for {binned_data.n_bins} RPM bins (fitting separate GP per bin)...")

        optimal_map = {}
        best_bsfc_per_rpm = {}
        all_suggestions = []

        for rpm_bin in binned_data.bins:
            rpm = rpm_bin.rpm_center

            print(f"\n  RPM {rpm:.0f}: {rpm_bin.n_samples} samples, "
                  f"λ=[{rpm_bin.lambda_range[0]:.3f}-{rpm_bin.lambda_range[1]:.3f}], "
                  f"timing=[{rpm_bin.timing_range[0]:.1f}-{rpm_bin.timing_range[1]:.1f}]")

            # Fit GP for this bin
            gp = self._fit_gp_for_bin(rpm_bin)
            self.gp_models[rpm] = gp

            # Optimize for this bin
            opt_lambda, opt_timing, pred_bsfc, uncertainty, notes = self._optimize_for_bin(
                gp, rpm_bin)

            optimal_map[float(rpm)] = {
                "lambda": round(opt_lambda, 4),
                "timing": round(opt_timing, 2),
                "predicted_bsfc": round(pred_bsfc, 4),
                "uncertainty": round(uncertainty, 4),
                "notes": notes,
            }

            best_bsfc_per_rpm[rpm] = float(rpm_bin.min_bsfc)

            print(f"    Optimal: λ={opt_lambda:.3f}, timing={opt_timing:.1f}°, "
                  f"BSFC={pred_bsfc:.4f} ± {uncertainty:.4f} ({notes})")

            # Get suggestion for this bin (1 per bin)
            suggestion = self._find_best_experiments_for_bin(gp, rpm_bin)
            if suggestion is not None:
                all_suggestions.append(suggestion)

        # Sort suggestions by RPM for consistent ordering
        all_suggestions.sort(key=lambda x: x["rpm"])

        # Compute overall best BSFC
        overall_best = min(best_bsfc_per_rpm.values()
                           ) if best_bsfc_per_rpm else 0.0

        print(f"\n  Best observed BSFC across all bins: {overall_best:.4f}")

        # Build training bounds from all data
        all_lambda = np.concatenate(
            [b.lambda_values for b in binned_data.bins])
        all_timing = np.concatenate(
            [b.timing_values for b in binned_data.bins])

        training_bounds = {
            "lambda": (float(all_lambda.min()), float(all_lambda.max())),
            "timing": (float(all_timing.min()), float(all_timing.max())),
            "rpm": (float(binned_data.rpm_centers.min()), float(binned_data.rpm_centers.max())),
        }

        return OptimizationResult(
            optimal_map=optimal_map,
            suggested_experiments=all_suggestions,
            gp_models=self.gp_models,
            training_bounds=training_bounds,
            n_training_samples=binned_data.total_samples,
            best_bsfc_per_rpm=best_bsfc_per_rpm,
            best_bsfc_overall=overall_best,
        )
