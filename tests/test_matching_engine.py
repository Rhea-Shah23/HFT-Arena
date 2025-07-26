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
