"""
Gaussian Process Model Module
Surrogate model for BSFC response surface
"""

from typing import Dict, Optional, Tuple, Union
import numpy as np
from sklearn.preprocessing import StandardScaler
from skopt.learning import GaussianProcessRegressor
from skopt.learning.gaussian_process.kernels import Matern, ConstantKernel


class BSFCGaussianProcess:
    """
    Gaussian Process surrogate model for BSFC prediction.
    Models BSFC = f(Lambda, Timing, RPM)
    """
    
    def __init__(self, noise_level: float = 0.1, n_restarts: int = 10):
        """
        Initialize the GP model.
        
        Args:
            noise_level: Expected noise level in observations (alpha)
            n_restarts: Number of optimizer restarts for hyperparameter tuning
        """
        self.noise_level = noise_level
        self.n_restarts = n_restarts
        
        # Scalers for input normalization
        self.X_scaler = StandardScaler()
        self.y_scaler = StandardScaler()
        
        # GP model with Matern kernel (good for physical processes)
        kernel = ConstantKernel(1.0) * Matern(length_scale=[1.0, 1.0, 1.0], nu=2.5)
        
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=noise_level**2,
            n_restarts_optimizer=n_restarts,
            normalize_y=False,  # We normalize manually
            random_state=42,
        )
        
        self.is_fitted = False
        self.X_train = None
        self.y_train = None
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BSFCGaussianProcess":
        """
        Fit the GP model to training data.
        
        Args:
            X: Training inputs, shape (n_samples, 3) for [lambda, timing, rpm]
            y: Training targets (BSFC values), shape (n_samples,)
            
        Returns:
            self for chaining
        """
        # Store raw data
        self.X_train = X.copy()
        self.y_train = y.copy()
        
        # Normalize inputs and outputs
        X_scaled = self.X_scaler.fit_transform(X)
        y_scaled = self.y_scaler.fit_transform(y.reshape(-1, 1)).ravel()
        
        # Fit GP
        self.gp.fit(X_scaled, y_scaled)
        self.is_fitted = True
        
        print(f"GP fitted with {len(y)} samples")
        print(f"  Kernel: {self.gp.kernel_}")
        print(f"  Log-likelihood: {self.gp.log_marginal_likelihood_value_:.2f}")
        
        return self
    
    def predict(self, X: np.ndarray, return_std: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Predict BSFC at new input locations.
        
        Args:
            X: Query points, shape (n_points, 3)
            return_std: Whether to return standard deviation
            
        Returns:
            Tuple of (mean predictions, std predictions or None)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        
        X_scaled = self.X_scaler.transform(X)
        
        if return_std:
            mean_scaled, std_scaled = self.gp.predict(X_scaled, return_std=True)
            
            # Inverse transform predictions
            mean = self.y_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).ravel()
            
            # Scale std by the y scaler's scale
            std = std_scaled * self.y_scaler.scale_[0]
            
            return mean, std
        else:
            mean_scaled = self.gp.predict(X_scaled, return_std=False)
            mean = self.y_scaler.inverse_transform(mean_scaled.reshape(-1, 1)).ravel()
            return mean, None
    
    def predict_grid(
        self,
        lambda_range: Tuple[float, float],
        timing_range: Tuple[float, float],
        rpm: float,
        n_points: int = 50,
    ) -> Dict:
        """
        Predict BSFC over a grid for a fixed RPM.
        Useful for visualization.
        
        Args:
            lambda_range: (min, max) lambda values
            timing_range: (min, max) timing values
            rpm: Fixed RPM value
            n_points: Number of points per dimension
            
        Returns:
            Dictionary with grid data for plotting
        """
        lambda_vals = np.linspace(lambda_range[0], lambda_range[1], n_points)
        timing_vals = np.linspace(timing_range[0], timing_range[1], n_points)
        
        # Create meshgrid
        L, T = np.meshgrid(lambda_vals, timing_vals)
        
        # Flatten for prediction
        X_grid = np.column_stack([
            L.ravel(),
            T.ravel(),
            np.full(L.size, rpm),
        ])
        
        mean, std = self.predict(X_grid, return_std=True)
        
        return {
            "rpm": rpm,
            "lambda": lambda_vals.tolist(),
            "timing": timing_vals.tolist(),
            "bsfc_mean": mean.reshape(n_points, n_points).tolist(),
            "bsfc_std": std.reshape(n_points, n_points).tolist(),
        }
    
    def get_training_bounds(self) -> dict:
        """
        Get the bounds of the training data.
        
        Returns:
            Dictionary with min/max for each input dimension
        """
        if self.X_train is None:
            raise RuntimeError("Model must be fitted first")
        
        return {
            "lambda": (float(self.X_train[:, 0].min()), float(self.X_train[:, 0].max())),
            "timing": (float(self.X_train[:, 1].min()), float(self.X_train[:, 1].max())),
            "rpm": (float(self.X_train[:, 2].min()), float(self.X_train[:, 2].max())),
        }
