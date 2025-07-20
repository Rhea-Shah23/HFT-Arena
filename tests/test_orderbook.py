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

        assert len(trades) == 1 
        assert trades[0].price == 150.00 #takes existing price 
        assert buy_order.status == OrderStatus.FILLED 
        assert sell_order.status == OrderStatus.FILLED 

    #test that latency affects order timing 
    def test_latency_delay(self):
        #add sell order w/ no latency 
        sell_order = Order(
            agent_id = "seller", 
            symbol = "AAPL", 
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT,
            quantity = 100, 
            price = 150.00, 
            latency_delay= 0.0
        )
        self.book.add_order(sell_order) 

        #buy order w/ latency 
        buy_order = Order(
            agent_id = "buyer", 
            symbol = "AAPL", 
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00,
            latency_delay = 0.001 # =1ms delay 
        )
        trades = self.book.add_order(buy_order)

        assert len(trades) == 1 
        assert trades[0].timestamp >= buy_order.effective_timestamp 

    #test order cancellation 
    def test_cancel_order(self): 
        order = Order(
            agent_id = "agent1", 
            symbol = "AAPL", 
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 150.00
        )
        self.book.add_order(order)

        #cancel order 
        success = self.book.cancel_order(order.order_id)

        assert success 
        assert order.status == OrderStatus.CANCELLED 
        assert len(self.book.order) == 0 
        assert self.book.get_test_bid() is None

    #test market data generation 
    def test_market_data(self):
        #add some orders 
        buy_order = Order( 
            agent_id = "buyer", 
            symbol = "AAPL",
            side = OrderSide.BUY, 
            order_type = OrderType.LIMIT, 
            quantity = 100, 
            price = 149.00 
        )
        self.book.add_order(buy_order) 

        sell_order = Order(
            agent_id = "seller", 
            symbol = "AAPL", 
            side = OrderSide.SELL,
            order_type = OrderType.LIMIT, 
            quantity = 200,
            price = 151.00
        )
        self.book.add_order(sell_order)

        market_data = self.book.get_market_data()
        assert market_data.best_bid == 149.00 
        assert market_data.best_ask == 151.00 
        assert market_data.bid_size == 100
        assert market_data.ask_size == 200 
        assert market_data.spread == 2.00 
        assert market_data.spread == 150.00 

if __name__ == "__main__": 
    #run basic tests 
    test = TestOrderBook()
    test.setup_method()

    print("running order book tests") 

    try: 
        test.test_add_limit_buy_order()
        print("add limit buy order: passed ")

        test.setup_method()
        test.test_add_limit_sell_order()
        print("add limit sell order: passed ")

        test.setup_method()
        test.test_matching_orders()
        print("matching orders: passed ")

        test.setup_method()
        test.test_partial_fill()
        print("partial fill: passed ")

        test.setup_method()
        test.test_price_priority()
        print("price priority: passed ")

        test.setup_method()
        test.test_market_order()
        print("market order: passed ")

        test.setup_method()
        test.test_latency_delay()
        print("latency delay: passed ")

        test.setup_method()
        test.test_cancel_order()
        print("cancel order: passed ")

        test.setup_method()
        test.test_market_data()
        print("market data: passed ")

        print("all tests passed!")
    
    except Exception as e: 
        print("test failed: ", e)
        import traceback 
        traceback.print_exc()