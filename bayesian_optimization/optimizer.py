"""
Bayesian Optimizer Module
Finds optimal Lambda and Timing parameters using Expected Improvement
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from dataclasses import dataclass

from .gp_model import BSFCGaussianProcess
from .rpm_binning import BinnedData


@dataclass
class OptimizationResult:
    """Container for optimization results"""
    # Optimal map: RPM -> optimal parameters
    optimal_map: Dict[float, Dict[str, float]]
    
    # Suggested next experiments for feedback loop
    suggested_experiments: List[dict]
    
    # Model info
    training_bounds: dict
    n_training_samples: int
    
    # Convergence info
    best_bsfc_per_rpm: Dict[float, float]
    best_bsfc_overall: float


class BSFCOptimizer:
    """
    Bayesian optimizer for BSFC minimization.
    Uses Expected Improvement acquisition function.
    """
    
    def __init__(
        self,
        gp_model: BSFCGaussianProcess,
        lambda_bounds: Optional[Tuple[float, float]] = None,
        timing_bounds: Optional[Tuple[float, float]] = None,
        n_suggestions: int = 5,
    ):
        """
        Initialize the optimizer.
        
        Args:
            gp_model: Fitted GP model
            lambda_bounds: (min, max) bounds for lambda optimization
            timing_bounds: (min, max) bounds for timing optimization
            n_suggestions: Number of next experiments to suggest
        """
        self.gp = gp_model
        self.n_suggestions = n_suggestions
        
        # Get bounds from training data if not specified
        training_bounds = gp_model.get_training_bounds()
        
        if lambda_bounds is None:
            # Expand bounds slightly beyond training data
            l_min, l_max = training_bounds["lambda"]
            margin = (l_max - l_min) * 0.1
            self.lambda_bounds = (l_min - margin, l_max + margin)
        else:
            self.lambda_bounds = lambda_bounds
            
        if timing_bounds is None:
            t_min, t_max = training_bounds["timing"]
            margin = (t_max - t_min) * 0.1
            self.timing_bounds = (t_min - margin, t_max + margin)
        else:
            self.timing_bounds = timing_bounds
    
    def _expected_improvement(
        self,
        X: np.ndarray,
        best_y: float,
        xi: float = 0.01,
    ) -> np.ndarray:
        """
        Compute Expected Improvement acquisition function.
        
        Args:
            X: Query points, shape (n_points, 3)
            best_y: Current best (minimum) observed BSFC
            xi: Exploration-exploitation trade-off parameter
            
        Returns:
            EI values, shape (n_points,)
        """
        mean, std = self.gp.predict(X, return_std=True)
        
        # Improvement is when we find values LOWER than best (minimization)
        improvement = best_y - mean - xi
        
        # Handle numerical issues
        std = np.maximum(std, 1e-9)
        
        Z = improvement / std
        ei = improvement * norm.cdf(Z) + std * norm.pdf(Z)
        
        # Set EI to 0 where std is essentially 0
        ei[std < 1e-9] = 0.0
        
        return ei
    
    def _optimize_for_rpm(
        self,
        rpm: float,
        best_bsfc: float,
        n_restarts: int = 10,
    ) -> Tuple[float, float, float]:
        """
        Find optimal (lambda, timing) for a specific RPM.
        
        Args:
            rpm: Fixed RPM value
            best_bsfc: Current best BSFC for this RPM
            n_restarts: Number of optimization restarts
            
        Returns:
            Tuple of (optimal_lambda, optimal_timing, predicted_bsfc)
        """
        bounds = [self.lambda_bounds, self.timing_bounds]
        
        def objective(x):
            X = np.array([[x[0], x[1], rpm]])
            mean, _ = self.gp.predict(X, return_std=False)
            return mean[0]
        
        best_result = None
        best_value = np.inf
        
        for _ in range(n_restarts):
            # Random starting point
            x0 = [
                np.random.uniform(*self.lambda_bounds),
                np.random.uniform(*self.timing_bounds),
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
        
        return best_result.x[0], best_result.x[1], best_value
    
    def _find_best_experiments(
        self,
        rpm_values: np.ndarray,
        current_best_bsfc: float,
        n_candidates: int = 1000,
    ) -> List[dict]:
        """
        Find the most promising next experiments using EI.
        
        Args:
            rpm_values: Array of RPM values to consider
            current_best_bsfc: Overall best BSFC observed
            n_candidates: Number of random candidates to evaluate
            
        Returns:
            List of suggested experiments sorted by EI (descending)
        """
        # Generate random candidates across the search space
        candidates = []
        
        for rpm in rpm_values:
            n_per_rpm = n_candidates // len(rpm_values)
            
            lambdas = np.random.uniform(
                self.lambda_bounds[0], self.lambda_bounds[1], n_per_rpm
            )
            timings = np.random.uniform(
                self.timing_bounds[0], self.timing_bounds[1], n_per_rpm
            )
            rpms = np.full(n_per_rpm, rpm)
            
            X = np.column_stack([lambdas, timings, rpms])
            candidates.append(X)
        
        X_all = np.vstack(candidates)
        
        # Compute EI for all candidates
        ei = self._expected_improvement(X_all, current_best_bsfc)
        
        # Get predictions for top candidates
        top_indices = np.argsort(ei)[-self.n_suggestions * 3:][::-1]
        
        suggestions = []
        seen_rpms = set()
        
        for idx in top_indices:
            if len(suggestions) >= self.n_suggestions:
                break
                
            rpm = X_all[idx, 2]
            
            # Try to suggest experiments across different RPM bins
            # (optional: remove this constraint if you want all suggestions from same RPM)
            if rpm in seen_rpms and len(suggestions) < self.n_suggestions // 2:
                continue
            
            mean, std = self.gp.predict(X_all[idx:idx+1], return_std=True)
            
            suggestions.append({
                "rpm": round(float(rpm), 0),
                "lambda": round(float(X_all[idx, 0]), 4),
                "timing": round(float(X_all[idx, 1]), 2),
                "predicted_bsfc": round(float(mean[0]), 4),
                "uncertainty": round(float(std[0]), 4),
                "expected_improvement": round(float(ei[idx]), 6),
            })
            
            seen_rpms.add(rpm)
        
        return suggestions
    
    def optimize(self, binned_data: BinnedData) -> OptimizationResult:
        """
        Run full optimization to find optimal map and suggest next experiments.
        
        Args:
            binned_data: RPM-binned training data
            
        Returns:
            OptimizationResult with optimal map and suggestions
        """
        rpm_values = binned_data.rpm_centers
        
        # Find current best BSFC per RPM and overall
        best_bsfc_per_rpm = {}
        for rpm, bsfc in zip(rpm_values, binned_data.bsfc_values):
            best_bsfc_per_rpm[rpm] = float(bsfc)
        
        overall_best = float(binned_data.bsfc_values.min())
        
        print(f"\nOptimizing for {len(rpm_values)} RPM bins...")
        print(f"Current best BSFC: {overall_best:.4f}")
        
        # Optimize for each RPM bin
        optimal_map = {}
        
        for rpm in rpm_values:
            opt_lambda, opt_timing, pred_bsfc = self._optimize_for_rpm(
                rpm, best_bsfc_per_rpm[rpm]
            )
            
            optimal_map[float(rpm)] = {
                "lambda": round(opt_lambda, 4),
                "timing": round(opt_timing, 2),
                "predicted_bsfc": round(pred_bsfc, 4),
            }
            
            print(f"  RPM {rpm:.0f}: λ={opt_lambda:.3f}, timing={opt_timing:.1f}°, BSFC={pred_bsfc:.4f}")
        
        # Find suggested next experiments
        print(f"\nFinding {self.n_suggestions} suggested next experiments...")
        suggestions = self._find_best_experiments(rpm_values, overall_best)
        
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. RPM={s['rpm']:.0f}, λ={s['lambda']:.3f}, timing={s['timing']:.1f}° (EI={s['expected_improvement']:.4f})")
        
        return OptimizationResult(
            optimal_map=optimal_map,
            suggested_experiments=suggestions,
            training_bounds=self.gp.get_training_bounds(),
            n_training_samples=len(binned_data.y),
            best_bsfc_per_rpm=best_bsfc_per_rpm,
            best_bsfc_overall=overall_best,
        )
