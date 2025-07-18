# order data structures to create an hft trading simulation 

from dataclasses import dataclass, field 
from enum import Enum 
from typing import Optional
import uuid
import time 

class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL_FILL = "partial_fill"

@dataclass
# represents a trading order with a latency simulation 
class Order: 
    agent_id: str
    symbol: str
    side: OrderSide 
    order_type: OrderType 
    quantity: int 
    price: Optional[float] = None #none for market orders
    latency_delay: float = 0.0 #represeents network delay in seconds
    order_id: str = field(default_factory = lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory = time.time)
    filled_quantity: int = 0 
    status = OrderStatus = OrderStatus.PENDING 

    def __post_init__(self):

        # calculates effective timestamp including latency 
        self.effective_timestamp = self.timestamp + self.latency_delay 

        #val 
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("limit orders must have a price ")
        if self.quantity <= 0: 
            raise ValueError("quantity must be positive")
        
    def remaining_quantity(self) -> int: 
        #gets remaining unfilled quantity 
        return self.quantity - self.filled_quantity 
    
    def is_buy(self) -> bool: 
        #checks if order is a buy order 
        return self.side == OrderSide.BUY 
    
    def is_sell(self) -> bool: 
        #checks if order is a sell order 
        return self.side == OrderSide.SELL 
    
    def __repr__(self):
        return (f"Order({self.order_id[:8]}..., {self.agent_id}, {self.side.value}, {self.order_type.value}, qty = {self.quantity}, price = {self.price})")

@dataclass 
# represents an executed trade between two orders 
class Trade: 
    symbol: str 
    quantity: int 
    price: float
    timestamp: float 
    buy_order_id: str 
    sell_order_id: str 
    buyer_agent_id: str 
    seller_agent_id: str
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __repr__(self) -> str: 
        return (f"trade({self.trade_id[:8]}..., {self.symbol}, qty = {self.quantity}, price = {self.price})")


