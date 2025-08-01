#comprehensive test suite for matching engine 
#tests latency simulation, mulit-symbol trading, and performance under load 

import pytest
import time 
import threading 
from unittest.mock import Mock, patch 

from src.matching_engine import MatchingEngine, LatencyProfile
from src.orders import Order, Ordertype, OrderSide, OrderStatus, OrderType 
from src.agents.base_agent import BaseAgent, AgentConfig 

#simple mock agent for testing 
class MockAgent(BaseAgent):
    def __init__(self, agent_id: str):
        config = AgentConfig(agent_id = agent_id)
        super().__init__(config)
        self.market_data_updates = [] 
        self.trade_notifications = [] 

    def on_market_data(self, market_data):
        self.market_data_updates.append(market_data)

    def on_trade(self, trade):
        self.trade_notifications.append(trade)

class TestMatchingEngine:
    def setup_method(self):
        self.engine = MatchingEngine(symbols = ["AAPL", "MSFT"])

        self.agent1 = MockAgent("agent1")
        self.agent2 = MockAgent("agent2")

        self.engine.register_agent("agent1", LatencyProfile(base_latency = 0.001))
        self.engine.register_agent("agent2", LatencyProfile(base_latency = 0.002)) 

    def test_engine_initialization(self):
        assert len(self.engine.symbols) == 2 
        assert "AAPL" in self.engine.order_books 
        assert "MSFT" in self.engine.order_books 
        assert len(self.engine.latency_profiles) == 2 

    def test_agent_registration(self):
        latency_profile = LatencyProfile(base_latency = 0.005, jitter = 0.001)
        self.engine.register_agent("agent3", latency_profile)

        assert "agent3" in self.engine.latency_profiles
        assert self.engine.latency_profiles["agent3"].base_latency == 0.005 

    def test_order_submission_with_latency(self):
        order = Order(
            agent_id = "agent1", 
            symbol = "AAPL",
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00 
        )

        order_id = self.engine.submit_order(order)

        assert order_id == order.order_id 
        assert len(self.engine.event_queue) == 1 
        assert order.latency_delay > 0 
        assert order.effective_timestamp > order.timestamp

    def test_event_processing(self):
        order = Order(
            agent_id = "agent1", 
            symbol = "AAPL",
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 150.00
        ) 
        order.latency_delay = 0.001 

        self.engine.submit_order(order)

        time.sleep(0.002)
        trades = self.engine.process_events()

        assert self.egnine.stats["orders_processed"] == 1 
        assert len(trades) == 0 

        market_data = self.engine.get_market_data("AAPL")
        assert market_data.best_bid == 150.0 

    def test_matching_across_agents(self):
        sell_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 150.00,
        )
        self.engine.submit_order(sell_order)

        buy_order = Order(
            agent_id = "agent2",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00
        )
        self.engine.submit_order(buy_order)

        time.sleep(0.005) 
        trades = self.engine.process_events()

        assert len(trades) == 1 
        trade = trades[0]
        assert trade.quantity == 100 
        assert trade.price == 150.00 
        assert trade.buyer_agent_id == "agent2"
        assert trade.seller_agent_id == "agent1"

        assert self.engine.stats["total_trades"] == 1
        assert self.engine.stats["total_volume"] == 100 
        assert self.engine.stats["agent_pnl"]["agent1"] == 15000.00
        assert self.engine.stats["agent_pnl"]["agent2"] == -15000.00

    def test_multi_symbol_trading(self):
        aapl_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity = 100,
            price = 150.00
        )

        msft_order = Order(
            agent_id = "agent2",
            symbol = "MSFT",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity = 50,
            price = 250.00
        )

        self.engine.submit_order(aapl_order)
        self.engine.submit_order(msft_order)

        time.sleep(0.005)
        self.engine.process_events()

        aapl_data = self.engine.get_market_data("AAPL")
        msft_data = self.engine.get_market_data("MSFT")

        all_data = self.engine.get_all_market_data()
        assert len(all_data) == 2 
        assert "AAPL" in all_data
        assert "MSFT" in all_data

    def test_latency_budget_violation(self):
        order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00 
        )
        order.max_latency = 0.001 

        order.latency_delay = 0.002 
        self.engine.submit_order(order)

        time.sleep(0.005)
        trades = self.engine.process_events()

        assert self.engine.stats["latency_violations"] >= 1 
        market_data = self.engine.get_market_data("AAPL")
        assert market_data.best_bid is None 

    def test_market_order_execution(self):
        limit_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 100,
            price = 150.00
        )
        self.engine.submit_order(limit_order)

        market_order = Order(
            agent_id = "agent2",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.MARKET,
            quantity = 100,
        )
        self.engine.submit_order(market_order)

        time.sleep(0.005)
        trades = self.engine.process_events()

        assert len(trades) == 1 
        assert trades[0].price == 150.00
        assert trades[0].quantity == 100 

    def test_partial_fill_execution(self):
        sell_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 200,
            price = 150.00 
        )
        self.engine.submit_order(sell_order)

        buy_order = Order(
            agent_id = "agent2", 
            symbol = "AAPL",
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 50, 
            price = 150.0
        )
        self.engine.submit_order(buy_order)

        time.sleep(0.005)
        trades=self.engine.process_events()

        assert len(trades) == 1
        assert trades[0].quantity == 50 

        market_data = self.engine.get_market_data("AAPL")
        assert market_data.ask_size == 150 

    def test_price_time_priority(self):
        sell1 = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 151.00
        )
        self.engine.submit_order(sell1)

        time.sleep(0.001)

        sell2 = Order(
            agent_id = "agent2",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 150.00
        )
        self.engine.submit_order(sell2)

        buy_order = Order(
            agent_id = "buyer",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity = 100,
            price = 152.00 
        )
        self.engine.submit_order(buy_order)

        time.sleep(0.005)
        trades = self.engine.process_events()

        assert len(trades) == 1
        assert trades[0].price == 150.00
        assert trades[0].seller_agent_id == "agent2"

    def test_callbacks(self):
        trade_callback_calls = []
        market_data_callback_calls = []
        
        def trade_callback(trade):
            trade_callback_calls.append(trade)

        def market_data_callback(market_data):
            market_data_callback_calls.append(market_data)
        
        self.engine.add_trade_callback(trade_callback)
        self.engine.add_market_data_callback(market_data_callback)

        sell_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 100,
            price = 150.00
        )
        self.engine.submit_order(sell_order)

        buy_order = Order(
            agent_id = "agent2",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity  = 100, 
            price = 150.00
        )
        self.engine.submit_order(buy_order)

        time.sleep(0.005)
        trades = self.engine.process_events()

        for symbol in set(trade.symbol for trade in trades):
            market_data = self.engine.get_market_data(symbol)
            for callback in self.engine.market_data_callbacks:
                callback(market_data) 

        assert len(trade_callback_calls) == 1 
        assert len(market_data_callback_calls) == 1 
        assert trade_callback_calls[0].quantity == 100 

    def test_order_book_depth(self):
        orders = [
            Order("agent1", "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 149.00),
            Order("agent1", "AAPL", OrderSide.BUY, OrderType.LIMIT, 200, 148.00),
            Order("agent1", "AAPL", OrderSide.SELL, OrderType.LIMIT, 150, 151.00),
            Order("agent1", "AAPL", OrderSide.SELL, OrderType.LIMIT, 100, 152.00),
        ]

        for order in orders:
            self.engine.submit_order(order)

        time.sleep(0.005)
        self.engine.process_events()

        depth = self.engine.get_order_book_depth("AAPL", levels = 3)

        assert depth is not None
        assert len(depth["bids"]) <= 3 
        assert len(depth["asks"]) <= 3 

        if len(depth["bids"]) > 1:
            assert depth["bids"][0][0] >= depth["bids"][1][0]
        if len(depth["asks"]) > 1:
            assert depth["asks"][0][0] <= depth["asks"][1][0] 

    def test_market_noise_injection(self):
        sell_order = Order(
            agent_id = "agent1",
            symbol = "AAPL",
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 1000,
            price = 150.00
        )
        self.engine.submit_order(sell_order)

        time.sleep(0.005)
        self.engine.process_events()

        initial_trades = len(self.engine.order_books["AAPL"].trades)
        self.engine.inject_market_noise("AAPL", intensity = 0.1)

        time.sleep(0.005)
        trades = self.engine.process_events()

        final_trades = len(self.engine.order_books["AAPL"].trades)
        assert final_trades >= initial_trades 
    
    def test_statistics_tracking(self):
        orders = [
            Order("agent1", "AAPL", OrderSide.SELL, OrderType.LIMIT, 100, 150.0),
            Order("agent2", "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 150.0),
            Order("agent1", "MSFT", OrderSide.SELL, OrderType.LIMIT, 50, 250.0),
            Order("agent2", "MSFT", OrderSide.BUY, OrderType.LIMIT, 50, 250.0)
        ]

        for order in orders:
            self.engine.submit_order(order)

        time.sleep(0.005)
        self.engine.process_events()

        stats = self.engine.get_statistics()

        assert stats["total_trades"] == 2
        assert stats["total_volume"] == 150 
        assert stats["orders_processed"] == 4 

        assert stats["agent_pnl"]["agent1"] == 27500.0
        assert stats["agent_pnl"]["agent2"] == -27500.0

        assert stats["agent_positions"]["agent1"]["AAPL"] == -100
        assert stats["agent_positions"]["agent2"]["AAPL"] == 100
        assert stats["agent_positions"]["agent1"]["MSFT"] == -50
        assert stats["agent_positions"]["agent2"]["MSFT"] == 50
    
    def test_engine_reset(self):
        sell_order = Order("agent1", "AAPL", OrderSide.SELL, OrderType.LIMIT, 100, 150.0) 
        buy_order = Order("agent2", "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 150.0)

        self.engine.submit_order(sell_order)
        self.engine.submit_order(buy_order)

        time.sleep(0.005)
        self.engine.process_events()

        assert self.engine.stats["total_trades"] > 0 
        assert len(self.engine.event_queue) >= 0 

        self.engine.reset()

        assert self.engine.stats["total_trades"] == 0 
        assert self.engine.stats["total_volume"] == 0 
        assert len(self.engine.event_queue) == 0 

        for book in self.engine.order_books.values():
            assert len(book.orders) == 0 
            assert len(book.bids) == 0 
            assert len(book.asks) == 0 
            assert len(book.trades) == 0 

    def test_simulation_loop(self):
        self.engine.start_simulation()
        assert self.engine.running

        sell_order = Order("agent1", "AAPL", OrderSide.SELL, OrderType.LIMIT, 100, 150.0)
        buy_order = Order("agent2", "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 150.0)

        self.engine.submit_order(sell_order)
        time.sleep(0.01)
        self.engine.submit_order(buy_order)

        time.sleep(0.02)

        assert self.engine.stats["total_trades"] > 0 

        self.engine.stop_simulation()
        assert not self.engine.running 

    def test_latency_profile_generation(self):
        profile = LatencyProfile(base_latency=0.001, jitter=0.0002, packet_loss_rate=0.01)
        latencies = [profile.get_latency() for _ in range(100)]

        assert all(lat > 0 for lat in latencies) 

        normal_latencies = [lat for lat in latencies if lat < 0.002]
        avg_latency = sum(normal_latencies) / len(normal_latencies) if normal_latencies else 0 

        assert 0.0008 <= avg_latency <= 0.0012

    def test_concurrent_order_submission(self):
        def submit_orders(agent_id, count):
            for i in range(count):
                order = Order(
                    agent_id=agent_id,
                    symbol = "AAPL",
                    side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    order_type = OrderType.LIMIT, 
                    quantity = 10, 
                    price = 150.00 + (i % 5)
                )
                self.engine.submit_order(order) 

        threads = [] 
        for i in range(3):
            agent_id = f"agent{i}"
            self.engine.register_agent(agent_id, LatencyProfile())
            thread = threading.Thread(target = submit_orders, args = (agent_id, 10))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        time.sleep(0.01)
        trades = self.engine.process_events()

        assert self.engine.stats["orders_processed"] >= 20 
        assert len(trades) >= 0 

if __name__ == "__main__":
    test = TestMatchingEngine()

    print("running matching engine tests...")

    try:
        test.setup_method()
        test.test_engine_initialization()
        print("engine initialization done")

        test.setup_method()
        test.test_agent_registration()
        print("agent registration done")

        test.setup_method()
        test.test_order_submission_with_latency()
        print("order submission w/ latency done")

        test.setup_method()
        test.test_event_processing()
        print("event processing done")

        test.setup_method()
        test.test_matching_across_agents()
        print("cross-agent matching")

        test.setup_method()
        test.test_multi_symbol_trading()
        print("multi-symbol trading done")

        test.setup_method()
        test.test_order_cancellation()
        print("order cancellation done")

        test.setup_method()
        test.test_market_order_execution()
        print("market order execution done")

        test.setup_method()
        test.test_partial_fill_execution()
        print("partial fill execution done")

        test.setup_method()
        test.test_price_time_priority()
        print("price-time priority done")

        test.setup_method()
        test.test_callbacks()
        print("callbacks done")

        test.setup_method()
        test.test_statistics_tracking()
        print("statistics tracking")

        test.setup_method()
        test.test_latency_profile_generation()
        print("latency profile generation")

        print("all tests passed")

    except Exception as e:
        print(f"\n test failed: {e}")
        import traceback 
        traceback.print_exc()
