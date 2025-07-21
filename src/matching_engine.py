#hft matching engine w/ latency simulation and market microstructure features 

import time 
import heapq 
from typing import List, Dict, Optional, Tuple, Callable 
from dataclasses import dataclass 
from collections import defaultdict 
import threading 
from queue import PriorityQueue
import random 

from .orders import Order, OrderSide, OrderType 
from .orderbook import OrderBook 

#represents completed trade 
@dataclass 
class TradeExecution: 
    trade_id: str 
    timestamp: float
    buyer_id: str 
    seller_id: str 
    price: float 
    quantity: int 
    agressor_side: OrderSide 

#event scheduled for later execution; simulates latency 
@dataclass 
class LatencyEvent: 
    timestamp: float 
    order: Order 
    agent_id: str 

    def __lt__(self, other): 
        return self.timestamp < other.timestamp 
    
#matching engine w/ latency simulation, slippage, and market microstructure 
class MatchingEngine: 
    def __init__(self, symbol: str, tick_size: float = 0.01, latency_config: Optional[Dict] = None): 
        self.symbol = symbol 
        self.tick_size = tick_size 
        self.order_book = OrderBook(symbol, tick_size) 

        #latency config 
        self.latency_config = latency_config or { 
            "base_latency_ms" : 0.1, 
            "latency_variance_ms" : 0.05, 
            "processing_latency_ms": 0.02, 
            "network_congestion_factor" : 1.0
        }

        #event scheduling 
        self.event_queue: List[LatencyEvent] = []
        self.current_time = time.time() 

        #trade tracking 
        self.trade_id_counter = 0 
        self.completed_trades: List[TradeExecution] = [] 
        self.trade_callbacks: List[Callable[[TradeExecution], None]] = [] 

        #agent latency profiles 
        self.agent_latencies: List[Callable] = [] 

        #threading for real-time simulation 
        self.running = False 
        self.engine_thread: Optional[threading.Thread] = None 

    #register latency profile for agent 
    def register_agent_latency(self, agent_id: str, latency_profile: Dict): 
        self.agent_latencies[agent_id] = latency_profile

    #add callback for trade notification 
    def add_trade_callback(self, callback: Callable[[TradeExecution], None]): 
        self.trade_callbacks.append(callback) 

    #add callback for market data updates 
    def add_market_data_callback(self, callback: Callable): 
        self.market_data_callbacks.append(callback) 

    #calc realistic latency 
    def calculate_latency(self, agent_id: str) -> float: 
        base_config = self.latency_config 
        agent_config = self.agent_latencies.get(agent_id, {})

        #latency calc 
        base_latency = agent_config.get("base_latency_ms", base_config["base_latency_ms"])
        variance = agent_config.get("latency_variance_ms", base_config["latency_variance_ms"])
        latency = base_latency + random.uniform(-variance, variance) 

        #co-location adjustment
        if agent_config.get("co_located", False): 
            latency *= 0.1 #co-located agents have lower latency

        #netowrk congestion 
        congestion = base_config.get("network_congestion_factor", 1.0)
        latency *= congestion 

        return max(0.001, latency / 1000.0) #converted to seconds; min value: 1ms
    
#submit order w/ latency simulation 
def submit_order(self, order: Order, agent_id: str) -> bool: 
    latency = self.calculate_latency(agent_id)
    arrival_time = self.current_time + latency 

    #schedule order 
    event = LatencyEvent(arrival_time, order, agent_id) 
    heapq.heappush(self.event_queue, event) 

    return True 

#process all events up to current time 
def process_pending_events(self) -> List[TradeExecution]: 
    trades = [] 

    while self.event_queue and self.event_queue[0].timestamp <= self.current_time: 
        event = heapq.heappop(self.event_queue) 
        trade_results = self._execute_order(event.order, event.agent_id) 
        trades.extend(trade_results) 

    return trades 

#execute order against order book 
def _execute_order(self, order: Order, agent_id: str) -> List[TradeExecution]: 
    trades = [] 

    if order.order_type == OrderType.MARKET: 
        trades = self._execute_market_order(order, agent_id) 
    elif order.order_type == OrderType.LIMIT: 
        trades = self._execute_limit_order(order, agent_id) 
    elif order.order_type == OrderType.CANCEL: 
        

        