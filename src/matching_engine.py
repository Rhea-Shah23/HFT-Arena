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

from .orders import Order, Trade, MarketData, OrderSide, OrderType 
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
        
    #get current market data for a symbol 
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        if symbol in self.order_books:
            return self.order_book[symbol].get_market_data()
        return None 
    
    #get market data for all symbols 
    def get_all_market_data(self) -> Dict[str, MarketData]:
        return {
            symbol: book.get_market_data() 
            for symbol, book in self.order_book.items()
        }
    
    #get order book depth for visualization 
    def get_order_book_depth(self, symbol: str, levels: int = 5) -> Optional[Dict]: 
        if symbol in self.order_books:
            return self.order_books[symbol].get_depth(levels)
        return None 
    
    #callback for trade events 
    def add_trade_callbacks(self, callback: Callable[[Trade], None]):
        self.trade_callbacks.append(callback)

    #callback for maket data updates 
    def add_market_data_callback(self, callback: Callable[[MarketData], None]):
        self.market_data_callbacks.append(callback)

    #real-time simulation loop 
    def start_simulation(self):
        self.running = True 
        self.current_time = time.time()
        self.logger.info("matching engine simulation started")

        def simulation_loop():
            while self.running:
                start_time = time.time()

                trades = self.process_events()

                #publish market updates
                if trades: 
                    for symbol in set(trade.symbol for trade in trades):
                        market_data = self.get_market_data(symbol)
                        for callback in self.market_data_callbacks:
                            callback(market_data)

                #simulation speed 
                elapsed = time.time() - start_time 
                sleep_time = max(0, 0.001 - elapsed)
                time.sleep(sleep_time / self.simulation_speed)

        self.simulation_thread = threading.Thread(target = simulation_loop, daemon = True)
        self.simulation_thread.start()

    #stop simulation 
    def stop_simulation(self):
        self.running = False 
        self.logger.info("matching engine simulation stopped")

    #restart engine (for new simulation)
    def reset(self):
        with self.lock:
            self.event_queue.clear()
            for book in self.order_books.values():
                book.orders.clear()
                book.bids.clear()
                book.asks.clear()
                book.trades.clear()

            #reset stats 
            self.stats = {
                "total_trades": 0,
                "total_volume": 0,
                "orders_processed": 0,
                "orders_cancelled": 0,
                "agent_pnl":defaultdict(float), 
                "agent_positions": defaultdict(lambda: defaultdict(int)),
                "latency_violations": 0 
            }

            self.logger.info("matching engine reset")

    #get engine statst 
    def get_statistics(self) -> Dict[str, Any]:
        with self.lock:
            stats = dict(self.stats)
            stats["agent_pnl"] = dict(stats["agent_pnl"])
            stats["agent_positions"] = {
                agent: dict(positions)
                for agent, positions in stats["agent_positions"].items()
            }

            #performance metrics 
            stats["avg_trades_per_second"] = self.stats["total_trades"] / max(1, time.time() - self.current_time)
            stats["pending_events"] = len(self.event_queue)

            return stats 
        
#inject rnadom market ordrese (simulates external liquidity)
def inject_market_noise(self, symbol: str, intensity: float = 0.1):
    import random 
    if symbol not in self.order_books:
        return 
    market_data = self.get_market_data(symbol)
    if not market_data.best_bid or not market_data.best_ask: 
        return 
    
    #random market order 
    side = random.choice([OrderSide.BUY, OrderSide.SELL])
    quantity = random.randint(10, 100)

    #noise order (min. latency)
    noise_order = Order(
        agent_id = "market_noise", 
        symbol = symbol, 
        side = side, 
        order_type = OrderType.MARKET, 
        quantity = quantity, 
        latency_delay = 0.0001
    )

    self.submit_order(noise_order)
