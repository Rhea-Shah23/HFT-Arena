# test suite for the orderbook implementation 

import pytest 
import time 
from src.orders import Order, OrderType, OrderSide, OrderStatus
from src.orderbook import OrderBook 

#test cases for orderbook functionality 
class TestOrderBook: 
    #set up test fixtures 
    def setup_method(self):
        self.book = OrderBook("AAPL")

    #test adding a limit buy order to empty book 
    def test_add_limit_buy_order(self):
        order = Order(
            agent_id = "agent1", 
            symbol = "AAPL", 
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 150.00
        )

        trades = self.book.add_order(order)

        assert len(trades) == 0 #no matching orders 
        assert self.book.get_best_bid() == 150.00 
        assert self.book.get_best_ask() is None 
        assert len(self.book.orders) == 1
    
    #test adding a limit sell order to empty book 
    def test_add_limit_sell_order(self):
        order = Order(
            agent_id = "agent1", 
            symbol = "AAPL", 
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 151.00
        )

        trades = self.book.add_order(order)

        assert len(trades) == 0 
        assert self.book.get_best_bid() is None 
        assert self.book.get_best_ask() == 151.00 
        assert len(self.book.orders) == 1 

    #test that matching orders create trades 
    def test_matching_orders(self):
        #add sell order first 
        sell_order = Order(
            agent_id = "seller", 
            symbol = "AAPL", 
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00 
        )

        self.book.add_order(sell_order) 

        #add matching buy order 
        buy_order = Order(
            agent_id = "buyer", 
            symbool = "AAPL", 
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00
        )

        trades = self.book.add_order(buy_order)

        assert len(trades) == 1 
        assert trades[0].quantity == 100 
        assert trades[0].price == 150.00 
        assert trades[0].buyer_agent_id == "buyer" 
        assert trades[0].seller_agent_id == "seller"

        #both orders should be fully filled 
        assert buy_order.status == OrderStatus.FILLED 
        assert sell_order.status == OrderStatus.FILLED 
        assert len(self.book.orders) == 0 

    #test partial order fills 
    def test_partial_fill(self): 
        #add large sell order 
        sell_order = Order( 
            agent_id = "seller", 
            symbol = "AAPL", 
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT, 
            quantity = 200, 
            price = 150.00 
        )

        self.book.add_order(sell_order) 

        #add smaller buy order 
        buy_order = Order(
            agent_id = "buyer",
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity = 50, 
            price = 150.00
        )

        trades = self.book.add_order(buy_order)

        assert len(trades) == 1 
        assert trades[0].quantity == 50 
        assert buy_order.status == OrderStatus.FILLED 
        assert sell_order.status == OrderStatus.PARTIAL_FILL
        assert sell_order.remaining_quantity() == 150 
        assert len(self.book.orders) == 1 #sell order active 

    #test that better prices get filled first 
    def test_price_priority(self):
        #adds two sell orders at different prices 
        sell_order1 = Order(
            agent_id = "seller1", 
            symbol = "AAPL", 
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 151.00
        )
        self.book.add_order(sell_order1) 

        sell_order2 = Order( 
            agent_id = "seller2", 
            symbol = "AAPL", 
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00 #better price 
        )
        self.book.add_order(sell_order2) 

        #buy order that matches both 
        buy_order = Order(
            agent_id = "buyer", 
            symbol = "AAPL", 
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 152.00 
        )
        trades = self.book.add_order(buy_order)

        assert len(trades) == 1
        assert trades[0].price == 150.00 #better price should be filled first 
        assert trades[0].seller_agent_id == "seller2"

    #test market order execution 
    def test_market_order(self):
        sell_order = Order( 
            agent_id = "seller", 
            symbol = "AAPL",
            side = OrderSide.SELL, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00
        )
        self.book.add_order(sell_order)

        #add market buy order 
        buy_order = Order( 
            agent_id = "buyer", 
            symbol = "AAPL",
            side = OrderSide.BUY,
            order_type = OrderType.MARKET, 
            quantity = 100
        )
        trades = self.book.add_order(buy_order)