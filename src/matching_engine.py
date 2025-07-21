# high-frequency matching engine 
# coordinates: multiple order books, latency simulation, and agent interactions 

import time 
import threading 
from typing import Dict, List, Optional, Callable, Any 
from collections import defaultdict, deque 
import heapq 
from dataclasses import dataclass, field 
import asyncio 
import logging 

from .orders import Order, Trade, OrderStatus, MarketData 
from .orderbook import OrderBook 

#simulates network latency for different agents 
@dataclass 
class LatencyProfile: 
    base_latency: float = 0.001 #1ms 
    jitter: float = 0.0002 
    packet_loss_rate: float = 0.0001 

    #generate realistic latency w/ jitter 
    def get_latency(self) -> float: 
        import random 
        if random.random() < self.packet_loss_rate: 
            return self.base_latency * 10 #retransmission delay 
        return self.base_latency + random.uniform(-self.jitter, self.jitter) 
    
#time-ordered event in matching engine 
@dataclass 
class OrderEvent: 
    timestamp: float 
    order: Order 
    event_type : str = "new_order" #options: new_order, cancel_order 

    def __lt__(self, other): 
        return self.timestamp < other.timestamp 
    
# event driven matching engine 
class MatchingEngine: 
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["AAPL", "MSFT", "GOOGL"]

        #order books for each symbol 
        self.order_books: Dict[str, OrderBook] = {
            symbol: OrderBook(symbol) for symbol in self.symbols 
        }

        #event queue 
        self.event_queue: List[OrderEvent] = []

        #agent latency profiles 
        self.latency_profiles: Dict[str, LatencyProfile] = {}

        #engine state 
        self.running = False 
        self.current_time = time.time() 
        self.simulation_speed = 1.0 #real time 

        #stats 
        self.stats = {
            "total_trades": 0, 
            "total_volume": 0, 
            "orders_processed": 0, 
            "orders_cancelled": 0, 
            "agent_pnl": defaultdict(float), 
            "agent_positions": defaultdict(lambda: defaultdict(int)),
            "latency_violations": 0 
        }

        #event callbacks 
        self.trade_callbacks: List[Callable[[Trade], None]] = []
        self.market_data_callbacks: List[Callable[[MarketData], None]] = []

        #thread saftey 
        self.lock = threading.Lock() 

        #logging 
        logging.basicConfig(level = logging.INFO)
        self.logger = logging.getLogger(__name__)

    #register agent w/ specific latency
    def register_agent(self, agent_id: str, latency_profile: LatencyProfile = None):
        if latency_profile is None:
            latency_profile = LatencyProfile()
        self.latency_profiles[agent_id] = latency_profile
        self.logger.info(f"registered agent {agent_id} with latency {latency_profile.base_latency}s")

    #submit order w/ latency simulation
    #returns order_id for tracking 
    def submit_order(self, order: Order) -> str:
        with self.lock:
            #apply latency delay 
            if order.agent_id in self.latency_profiles: 
                latency = self.latency_profiles[order.agent_id].get_latency()
                order.latency_delay = latency 

            #calc effective timestamp 
            order.effective_timestamp = order.timestamp + order.latency_delay 

            #add to event queue 
            event = OrderEvent(
                timestamp = order.effective_timestamp, 
                order = order, 
                event_type = "new_order"
            )
            heapq.heappush(self.event_queue, event)

            self.logger.debug(f"order {order.order_id[:8]} queued with {order.latnecy_delay * 1000:.2f}ms latency")
            return order.order_id 
        
    #cancel an order w/ latency 
    def cancel_order(self, agent_id: str, order_id: str) -> bool:
        with self.lock:
            if agent_id in self.latnecy_profiles:
                latency = self.latnecy_profiles[agent_id].get_latency()
                cancel_time = time.time() + latency 

                for symbol in self.symbols:
                    if self.order_books[symbol].cancel_order(order_id):
                        self.stats["orders_cancelled"] += 1 
                        self.logger.debug(f"order {order_id[:8]} cancelled by {agent_id}")
                        return True 
                    
        return False
    
    #processes events to current time 
    def process_events(self) -> List[Trade]:
        trades = []
        current_time = time.time()

        with self.lock: 
            while self.event_queue and self.event_queue[0].timestamp <= current_time:
                event = heapq.heappop(self.event_queue)

                if event.event_type == "new_order":
                    order = event.order 

                    #latency budget violation 
                    actual_delay = current_time - order.timestamp
                    if hasattr(order, "max_latency") and actual_delay > order.max_latency: 
                        self.stats["latency violation"] += 1
                        self.logger.warning(f"latency violation: {actual_delay*1000:.2f}ms > {order.max_latency*1000:.2f}ms") 
                        continue 

                    #route to order book 
                    if order.symbol in self.order_books:
                        book_trades = self.order_books[order.symbol].add_order(order)
                        trades.extend(book_trades)

                        #update stats 
                        self.stats["orders_processed"] += 1 
                        for trade in book_trades: 
                            self._update_trade_stats(trade) 

                            #callback 
                            for callback in self.trade_callbacks: 
                                callback(trade)

        return trades 
    
    #update internal stats 
    def _update_trade_stats(self, trade: Trade):
        self.stats["total_trades"] += 1 
        self.stats["total_volume"] += trade.quantity 

        #update agent pnl 
        trade_value = trade.quantity * trade.price 
        self.stats["agent_pnl"][trade.buyer_agent_id][trade.symbol] += trade.quantity
        self.stats["agent_pnl"][trade.seller_agent_id][trade.symbol] -= trade.quantity

        #update positions 
        self.stats["agent_positions"][trade.buyer_agent_id][trade.symbol] += trade.quantity
        self.stats["agent_positions"][trade.seller_agent_id][trade.symbol] -= trade.quantity
        
        
