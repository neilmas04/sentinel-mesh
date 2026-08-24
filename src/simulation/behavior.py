# src/simulation/behavior.py
import numpy as np
import uuid
from datetime import timedelta

def generate_id(prefix: str) -> str:
    """Generates a realistic unique ID with a prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def get_lognormal_amount(mean: float, std: float) -> float:
    """
    Generates a realistic transaction amount.
    Financial data is typically log-normally distributed.
    """
    var = std**2
    if var == 0 or mean == 0:
        return round(mean, 2)
        
    mu = np.log(mean**2 / np.sqrt(var + mean**2))
    sigma = np.sqrt(np.log(var / mean**2 + 1))
    
    amount = np.random.lognormal(mean=mu, sigma=sigma)
    return round(max(1.0, amount), 2)

def get_stochastic_timedelta(mean_minutes: float, std_minutes: float) -> timedelta:
    """
    Generates a realistic time delay between transactions.
    """
    delay = np.random.normal(loc=mean_minutes, scale=std_minutes)
    delay = max(0.1, delay) # Minimum 6 seconds delay
    return timedelta(minutes=delay)