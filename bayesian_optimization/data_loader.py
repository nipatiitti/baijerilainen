"""
Data Loader Module
Parses processed MoTeC CSV files from the data folder
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


def load_csv_file(filepath: Path, columns: List[str]) -> Optional[Dict[str, np.ndarray]]:
    """
    Load a single CSV file and extract specified columns.
    
    Args:
        filepath: Path to the CSV file
        columns: List of column names to extract
        
    Returns:
        Dictionary mapping column names to numpy arrays, or None if file is invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Row 1: Headers (may be quoted)
            headers = next(reader)
            headers = [h.strip().strip('"') for h in headers]
            
            # Row 2: Units (skip for now, but could be useful)
            units = next(reader)
            
            # Find column indices
            col_indices = {}
            for col in columns:
                if col in headers:
                    col_indices[col] = headers.index(col)
                else:
                    print(f"Warning: Column '{col}' not found in {filepath.name}")
                    return None
            
            # Read data rows
            data = {col: [] for col in columns}
            for row in reader:
                if not row or all(cell.strip() == '' for cell in row):
                    continue
                    
                for col, idx in col_indices.items():
                    try:
                        value = float(row[idx]) if row[idx].strip() else np.nan
                        data[col].append(value)
                    except (ValueError, IndexError):
                        data[col].append(np.nan)
            
            # Convert to numpy arrays
            return {col: np.array(values) for col, values in data.items()}
            
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def load_csv_files(filepaths: List[Path], columns: List[str]) -> Dict[str, np.ndarray]:
    """
    Load multiple CSV files and combine their data.
    
    Args:
        filepaths: List of paths to CSV files
        columns: List of column names to extract
        
    Returns:
        Dictionary mapping column names to combined numpy arrays
    """
    all_data = {col: [] for col in columns}
    
    for filepath in filepaths:
        file_data = load_csv_file(filepath, columns)
        if file_data is not None:
            for col in columns:
                all_data[col].extend(file_data[col])
            print(f"Loaded {filepath.name}: {len(file_data[columns[0]])} rows")
    
    # Convert to numpy arrays
    combined = {col: np.array(values) for col, values in all_data.items()}
    
    # Remove rows with any NaN values
    valid_mask = np.ones(len(combined[columns[0]]), dtype=bool)
    for col in columns:
        valid_mask &= ~np.isnan(combined[col])
    
    filtered = {col: combined[col][valid_mask] for col in columns}
    
    removed = len(combined[columns[0]]) - len(filtered[columns[0]])
    if removed > 0:
        print(f"Removed {removed} rows with missing values")
    
    return filtered


def filter_valid_data(
    data: Dict[str, np.ndarray],
    bsfc_column: str,
    min_bsfc: float = 0.0
) -> Dict[str, np.ndarray]:
    """
    Filter out rows with invalid BSFC values (zero or below threshold).
    
    Args:
        data: Dictionary mapping column names to numpy arrays
        bsfc_column: Name of the BSFC column
        min_bsfc: Minimum valid BSFC value (rows at or below this are filtered out)
        
    Returns:
        Filtered data dictionary
    """
    if bsfc_column not in data:
        return data
    
    valid_mask = data[bsfc_column] > min_bsfc
    filtered = {col: arr[valid_mask] for col, arr in data.items()}
    
    removed = len(data[bsfc_column]) - len(filtered[bsfc_column])
    if removed > 0:
        print(f"Filtered out {removed} rows with BSFC <= {min_bsfc}")
    
    return filtered


def load_all_data(data_folder: Path, columns: List[str]) -> Dict[str, np.ndarray]:
    """
    Load all CSV files from a data folder.
    
    Args:
        data_folder: Path to the data folder
        columns: List of column names to extract
        
    Returns:
        Dictionary mapping column names to combined numpy arrays
    """
    csv_files = sorted(data_folder.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_folder}")
    
    print(f"Found {len(csv_files)} CSV file(s) in {data_folder}")
    return load_csv_files(csv_files, columns)
