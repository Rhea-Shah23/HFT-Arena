#base agent class for all trading agents 
#common functionality:order management, position tracking, performance measurement 

import time
import logging 
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any 
from collections import defaultdict, deque 
from dataclasses import dataclass
import uuid 

from ..orders import order, Trade, OrderType, OrderSide, OrderStatus, MarketData 

#config for trading agents 
@dataclass 
class AgentConfig:
    agent_id: str 
    max_position: int = 1000 
    max_order_size: int = 100 
    risk_limit: float = 10000.0 
    latency_budget: float = 0.005 
    symbols: List[str] = None 

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["AAPL"]

#track agent performance 
@dataclass 
class PerformanceMetrics:
    total_pnl:float = 0.0 
    realized_pnl: float = 0.0 
    unrealized_pnl: float = 0.0 
    total_trades: int = 0 
    winning_trades: int = 0 
    losing_trades: int = 0 
    max_drawdown: float = 0.0 
    sharpe_ratio: float = 0.0 
    avg_latency: float = 0.0 
    latency_violations: int = 0 

    @property 
    def win_rate(self) -> float: 
        if self.total_trades == 0: 
            return 0.0 
        return (self.winning_trades / self.total_trades) * 100 
    
    @property 
    def profit_factor(self) -> float:
        if self.losing_trades == 0:
            return float("inf") if self.winning_trades > 0 else 0.0 
        return abs(self.total_pnl) if self.total_pnl > 0 else 0.0 
    