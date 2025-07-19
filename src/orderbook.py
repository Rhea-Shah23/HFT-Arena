# order book implementation, uses heaps for efficient price-time priority matching 

import heapq 
from typing import Dict, List, Optional, Tuple 
from collections import defaultdict 
from .orders import Order, Trade, OrderSide, OrderStatus, OrderType, MarketData 

#order book for a single symbol 

# price-time priority: 
# - higher bids get priority (max heap using negative prices) 
# - lower asks get priority (min heap using positive prices) 
# - same price orders are processed by timestamp (FIFO) 
class OrderBook: 
    def __init__(self, symbol: str):
        self.symbol = symbol 

        #format: (-price, timestamp, order) 
        self.bids: List[Tuple[float, float, Order]] = [] 

        #format: (price, timstamp, order) 
        self.askks: List[Tuple[float, float, Order]] = [] 

        #actively looks up orders 
        self.orders: Dict[str, Order] = {}

        #trade history 
        self.trades: List[Trade] = []

        #market data tracking 
        self.last_trade_price: Optional[float] = None 
        self.last_trade_quantity: int = 0 

    #adds an order to the book and returns any resulting trades
    def add_order(self, order: Order) -> List[Trade]: 
        trades = [] 
        if order.order_type == OrderType.MARKET:
            trades = self._execute_market_order(order) 
        else: 
            trades = self._execute_limit_order(order)

        #store trades 
        self.trades.extend(trades)
        
        #update market data
        if trades: 
            last_trade = trades[-1]
            self.last_trade_price = last_trade.price
            self.last_trade_quantity = last_trade.quantity

        return trades 
    
    #executes a market order against the best available prices 
    def _execute_market_order(self, order: Order) -> List[Trade]:
        trades = [] 
        remaining_qty = order.quantity

        if order.is_buy():
            # buy market order; matches against asks (lowest price first) 
            while remaining_qty > 0 and self.asks: 
                ask_price, _, ask_order = self.asks[0] 

                #skip cancelled/filled orders 
                if ask_order.status != OrderStatus.PENDING: 
                    heapq.heappop(self.asks)
                    continue

                #execute trade 
                trade_qty = min(remaining_qty, ask_order.remaining_quantity())
                trade = self._create_trade(order, ask_order, trade_qty, ask_price) 
                trades.append(trade)

                #update order status 
                self._update_order_fill(order, trade_qty) 
                self._update_order_fill(ask_order, trade_qty)
                remaining_qty -= trade_qty

                #removes fully filled orders
                if ask_order.remaining_quantity() == 0: 
                    heapq.heappop(self.asks)
                    del self.orders[ask_order.order_id] 

        else: 
            # sell market order; matches against bids (highest price first) 
            while remaining_qty > 0 and self.bids:
                neg_bid_price, _, bid_order = self.bids[0]
                bid_price = -neg_bid_price 

                #skip cancelled/filled orders
                if bid_order.status != OrderStatus.PENDING:
                    heapq.heappop(self.bids)
                    continue

                #execute trade
                trade_qty = min(remaining_qty, bid_order.remaining_quantity())
                trade = self._create_trade(bid_order, order, trade_qty, bid_price)
                trades.append(trade)

                #update order status
                self._update_order_fill(order, trade_qty)
                self._update_order_fill(bid_order, trade_qty)
                remaining_qty -= trade_qty

                #removes fully filled orders
                if bid_order.remaining_quantity() == 0:
                    heapq.heappop(self.bids)
                    del self.orders[bid_order.order_id]

        return trades 
    
    #executes a limit order; matches what's possible then adds to book 
    def _execute_limit_order(self, order: Order) -> List[Trade]: 
        trades = [] 
        if order.is_buy():
            # buy limit order if matches against asks at or below our price 
            while order.remaining_quantity() > 0 and self.asks:
                ask_price, _, ask_order = self.asks[0]

                #skip cancelled/filled orders 
                if ask_order.status != OrderStatus.PENDING: 
                    heapq.heappop(self.asks)
                    continue 

                #stop if no more profitable matches 
                if ask_price > order.price: 
                    break 

                #execute trade
                trade_qty = min(order.remaining_quantity(), ask_order.remaining_quantity())
                trade = self._create_trade(order, ask_order, trade_qty, ask_price)
                trades.append(trade)

                #update order status
                self._update_order_fill(order, trade_qty)
                self._update_order_fill(ask_order, trade_qty)

                #removes fully filled orders
                if ask_order.remaining_quantity() == 0:
                    heapq.heappop(self.asks)
                    del self.orders[ask_order.order_id]
        
        else: 
            # sell limit order; matches against bids at or above our price 
            while order.remaining_quantity() > 0 and self.bids:
                neg_bid_price, _, bid_order = self.bids[0]
                bid_price = -neg_bid_price 

                #skip cancelled/filled orders 
                if bid_order.status != OrderStatus.PENDING: 
                    heapq.heappop(self.bids)
                    continue 

                #stop if no more profitable matches 
                if bid_price < order.price: 
                    break 

                #execute trade
                trade_qty = min(order.remaining_quantity(), bid_order.remaining_quantity())
                trade = self._create_trade(bid_order, order, trade_qty, bid_price)
                trades.append(trade)

                #update order status
                self._update_order_fill(order, trade_qty)
                self._update_order_fill(bid_order, trade_qty)

                #removes fully filled orders
                if bid_order.remaining_quantity() == 0:
                    heapq.heappop(self.bids)
                    del self.orders[bid_order.order_id]
        
        #add remaining qty to book 
        if order.remaining_quantity() > 0: 
            self.orders[order.order_id] = order 
            if order.is_buy():
                heapq.heappush(self.bids, (-order.price, order.timestamp, order))
            else:
                heapq.heappush(self.asks, (order.price, order.timestamp, order))
        
        return trades
    
    #creates a trade between two orders 
    def _create_trade(self, buy_order: Order, sell_order: Order, quantity: int, price: float) -> Trade: 
        return Trade(
            symbol = self.symbol, 
            quantity = quantity, 
            price = price, 
            timestamp = max(buy_order.effective_timestamp, sell_order.effective_timestamp),
            buy_order_id = buy_order.order_id,
            sell_order_id = sell_order.order_id, 
            buyer_agent_id = buy_order.agent_id, 
            seller_agent_id = sell_order.agent_id 
        )
    
    #update order fill quantity and status 

