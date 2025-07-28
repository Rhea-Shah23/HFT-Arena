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
            symbol = "AAPL"
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
            agent_id = "agent2"
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.MARKET,
            quantity = 100
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
