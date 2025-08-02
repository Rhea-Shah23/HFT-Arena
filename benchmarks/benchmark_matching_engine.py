# performance benchmarks for matching engine 
# tests: throughput, latency, scalability under load conditions 

import time 
import random 
import statistics
import threading
from typing import List, Dict, Any 
from concurrent.futures import ThreadPoolExecutor
import sys
import os 

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..."))

from src.matching_engine import MatchingEngine, LatencyProfile
from src.orders import Order, OrderType, OrderSide 

#comprehensive benchmarking class for matching engine 
class MatchingEngineBenchmark:
    def __init__(self):
        self.results: Dict[str, Any] = {}

    def setup_engine(self, symbols: List[str] = None, agents: int = 10) -> MatchingEngine:
        if symbols is None:
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

        engine = MatchingEngine(symbols = symbols)

        for i in range(agents):
            latency_profile = LatencyProfile(
                base_latency = random.uniform(0.0005, 0.005)
                jitter = random.uniform(0.0001, 0.001)
                packet_loss_rate = random.uniform(0.0001, 0.001)
            )
            engine.register_agent(f"agent_{i}", latency_profile)

        return engine 
    
    def generate_random_orders(self, count: int, symbols: List[str], agents: List[str]) -> List[Order]:
        orders = []
        for _ in range(count):
            symbol = random.choice(symbols)
            agent = random.choice(agents)
            side = random.choice([OrderSide.BUY, OrderSide.SELL])
            order_type = random.choice([OrderType.LIMIT, OrderType.MARKET])
            quantity = random.randint(10, 1000)

            base_prices = {"AAPL": 150, "MSFT": 250, "GOOGL": 2500, "TSLA": 800, "AMZN": 3000}
            base_price = base_prices.get(symbol, 100)

            if order_type == OrderType.LIMIT:
                price_variation = random.uniform(0.95, 1.05)
                price = base_price * price_variation
            else:
                price = None 

            order = Order(
                agent_id = agent, 
                symbol = symbol, 
                side = side,
                order_type = order_type, 
                quantity = quantity,
                price = price
            )
            orders.append(order)

            return orders 
        
    def benchmark_order_submission_throughput(self, order_counts: List[int]) -> Dict[str, Any]:
        print("benchamarking order submission throughput")
        
        results = {}

        for count in order_counts:
            engine = self.setup_engine()
            agents = [f"agent_{i}" for i in range(10)]
            symbols = engine.symbols 

            orders = self.generate_random_orders(count, symbols, agents)

            start_time = time.time()

            for order in orders:
                engine.submit_order(order)

            submission_time = time.time() - start_time

            process_start = time.time()
            trades = engine.process_events()
            process_time = time.time() - process_start 

            total_orders = agent_count * orders_per_agent 
            throughput = total_orders / (submission_time + process_time)

            results[agent_count] = {
                "total_orders": total_orders,
                "submission_time": submission_time,
                "processing_time": process_time,
                "total_time": submission_time + process_time, 
                "throughput": throughput,
                "trades_generated": len(trades),
                "orders_processed": engine.stats["orders_processed"],
                "latency_violations": engine.stats["latency_violations"]
            }

            print(f" {agent_count} agents: {throughput:,.0f} orders/sec, {len(trades)} trades, {engine.stats["latency_violations"]} violations")

        return results 
    
    def benchmark_market_depth_impact(self, depth_levels: List[int]) -> Dict[str, Any]:
        print("benchmarking market depth impact")

        results = []

        for depth in depth_levels:
            engine = self.setup_engine()

            for i in range(depth):
                buy_order = Order(
                    agent_id = "depth_builder",
                    symbol = "AAPL",
                    side = OrderSide.BUY,
                    order_type = OrderType.LIMIT,
                    quantity = 100,
                    price = 150.00 - (i * 0.1)
                )
                engine.submit_order(buy_order)

                sell_order = Order(
                    agent_id = "depth_builder",
                    symbol = "AAPL",
                    side = OrderSide.SELL,
                    order_type = OrderType.LIMIT,
                    quantity = 100,
                    price = 150.00 +(i * 0.1)
                )
                engine.submit_order(sell_order)
            engine.process_events()

            test_orders = 1000
            market_orders = []

            for _ in range(test_orders):
                order = Order(
                    agent_id = "tester",
                    symbol = "AAPL",
                    side = random.choice([OrderSide.BUY, OrderSide.SELL]),
                    order_type = OrderType.MARKET,
                    quantity = random.randint(10, 50)
                )
                market_orders.append(order)

            start_time = time.time()

            for order in market_orders:
                engine.submit_order(order)

            trades = engine.process_events()
            execution_time = time.time() - start_time

            throughput = test_orders / execution_time if execution_time > 0 else 0 

            results[depth] = {
                "market_depth": depth * 2,
                "test_orders": test_orders,
                "execution_time": execution_time,
                "throughput": throughput,
                "trades_generated": len(trades),
                "avg_trade_size": sum(t.quantity for t in trades) / len(trades) if trades else 0 
            }

            print(f" depth {depth * 2}: {throughput:,.0f} orders/sec, {len(trades)} trades")

            return results 