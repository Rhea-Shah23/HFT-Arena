#base agent class for all trading agents 
#common functionality:order management, position tracking, performance measurement 

import time
import logging 
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any 
from collections import defaultdict, deque 
from dataclasses import dataclass
import uuid 

from ..orders import Order, Trade, OrderType, OrderSide, OrderStatus, MarketData 

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

#abstract base class (for all trading agents)
#common functionality: order management, position tracking, risk management, performance measurement 
class BaseAgent(ABC):
    def __init__(self, config:AgentConfig):
        self.config = config
        self.agent_id = config.agent_id 

        #position & order tracking 
        self.positions: Dict[str, int] = defaultdict(int)
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Trade] = []

        #performance tracking 
        self.metrics = PerformanceMetrics()
        self.pnl_history: deque = deque(maxlen = 1000)
        self.peak_pnl = 0.0 

        #market data cache
        self.market_data_cache: Dict[str, MarketData] = {}
        self.last_market_update = 0.0

        #risk management 
        self.risk_check_enabled = True 
        self.emergency_liquidation = False

        #latency 
        self.latency_samples: deque = deque(maxlen = 1000)

        #callbacks
        self.order_callback: Optional[Callable[[Order], str]] = None 
        self.cancel_callback: Optional[Callable[[str, str], bool]] = None 

        #logging 
        self.logger = logging.getLogger(f"{__name__}.{self.agent_id}")
        self.logger.info(f"agent {self.agent_id} initialized")

    #set callback for submitting orders to matching engine 
    def set_order_callback(self, callback: Callable[[Order], str]):
        self.order_callback = callback 

    #set callback for cancelling orders
    def set_cancel_callback(self, callback: Callable[[str, str], bool]): 
        self.cancel_callback = callback 

    #handle market data updates; implemented by subclasses
    @abstractmethod
    def on_market_data(self, market_data: MarketData):
        pass 

    #handle trade notif; implemented by subclass 
    @abstractmethod
    def on_trade(self, trade: Trade):
        pass 

    #handle order status updates
    def on_order_update(self, order: Order): 
        if order.order_id in self.active_orders:
            self.active_orders[order.order_id] = order 

            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                del self.active_orders[order.order_id]
                self.order_history.append(order) 

    #submits an order w/ risk checks & tracking
    #returns order_id if successful, None if not 
    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType, quantity: int, price: Optional[float] = None) -> Optional[str]: 
        #pre-trade risk checks
        if not self._pre_trade_risk_check(symbol, side, quantity, price):
            return None 
        
        order = Order(
            agent_id = self.agent_id,
            symbol = symbol,
            side = side, 
            order_type = order_type, 
            quantity = quantity, 
            price = price, 
            latency_delay = 0.0 #set by matching engine 
        )

        if self.order_callback: 
            start_time = time.time()
            order_id = self.order_callback(order)

            latency = time.time() - start_time
            self.latency_samples.append(latency)

            if latency > self.config.latency_budget:
                self.metrics.latency_violations += 1 
                self.logger.warning(f"latency violations: {latency*1000:.2f}ms > {self.config.latency_budget*1000:.2f}ms")

            if order_id:
                self.active_orders[order_id] = order 
                self.logger.debug(f"submitted order {order_id[:8]}: {side.value} {quantity} {symbol} @ {price}")

            return order_id 
        
        return None 
    
    #cancel active order 
    def cancel_all_orders(self, symbol: Optional[str] = None):
        orders_to_cancel = []

        for order_id, order in self.active_orders.item():
            if symbol is None or order.symbol == symbol:
                orders_to_cancel.append(order_id)

        for order_id in orders_to_cancel:
            self.cancel_order(order_id)

    #perform pre-trade risk checks
    def _pre_trade_risk_check(self, symbol: str, Side: OrderSide, quantity: int, price: Optional[float]) -> bool:
        if not self.risk_check_enabled:
            return True 
        
        if quantity > self.config.max_order_size:
            self.logger.warning(f"order size {quantity} exceeds limit {self.config.max_order_size}")
            return False 
        
        current_pos = self.positions[symbol]
        new_pos = current_pos + (quantity if side == OrderSide.BUY else -quantity)

        if abs(new_pos) >self.config.max_position:
            self.logger.warning(f"position limit violation: {new_pos} > {self.config.max_position}")
            return False 
        
        if self.metrics.total_pnl < -self.config.risk_limit:
            self.logger.error(f"risk limit breached: pnl {self.metrics.total_pnl} < -{self.config.risk_limit}")
            self.emergency_liquidation = True
            return False 
        
        return True 
    
    #update position 
    def update_position(self, trade: Trade):
        if trade.buyer_agent_id == self.agent_id:
            self.positions[trade.symbol] += trade.quantity 
            self.metrics.realized_pnl -= trade.quantity * trade.price 

        elif trade.seller_agent_id == self.agent_id:
            self.positions[trade.symbol] -= trade.quantity 
            self.metrics.realized_pnl += trade.quantity * trade.price 

        self.trade_history.append(trade)
        self.metrics.total_trades += 1 

        self._update_performance_metrics(trade)

    #update performance metrics from trade 
    def _update_performance_matrics(self, trade: Trade):
        trade_pnl = 0.0 
        if trade_pnl > 0:
            self.metrics.winning_trades += 1 
        else:
            self.metrics.losing_trades += 1 
        
        self.metrics.total_pnl = self.metrics.realized_pnl + self.metrics.unrealized_pnl

        if self.metrics.total_pnl > self.peak_pnl:
            self.peak_pnl = self.metrics.total_pnl
        
        current_drawdown = self.peak_pnl - self.metrics.total_pnl
        self.metrics.max_drawdown = max(self.metrics.max_drawdown, current_drawdown)

        self.pnl_history.append(self.metrics.total_pnl)

        if self.latency_samples:
            self.metrics.avg_latency = sum(self.latency_samples) / len(self.latency_samples)
            
