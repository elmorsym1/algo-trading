# -*- coding: utf-8 -*-
"""
Created on Mon Mar  1 02:54:29 2021

@author: MMS
"""

# Import libraries
# from binance.enmus import *
from binance.client import Client
from binance import exceptions
from binance.exceptions import BinanceAPIException, BinanceRequestException, BinanceWithdrawException
import websocket, json, pprint
import talib
import numpy as np
import os
import config

os.chdir('D:/Canada/University/PhD/Research/Programs/Python/algonance')

# Determine the trading pair for websocket
# The base endpoint is: wss://stream.binance.com:9443
# Raw streams are accessed at /ws/<streamName>
# All symbols for streams are lowercase
# The Kline/Candlestick Stream push updates to the current klines/candlestick every second.
# intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
# <symbol>@kline_<interval>
# socket link: wss://stream.binance.com:9443/ws/<streamName><symbol>@kline_<interval>

# 1 minute candel #update speed 2 sec
candel_period = "1m"
SOCKET = "wss://stream.binance.com:9443/ws/btcusdt@kline_"+candel_period
closes = []


# RSI info
RSI_PERIOD = 14 # number of points
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# Trading pair info
TRADE_SYMBOL = 'BTCUSDT'
TRADE_QUANTITY = 0.0005 #~ $23 @ $46000 price
ORDER_TYPE = Client.ORDER_TYPE_MARKET

# set allocated wallet to be False (empty), Buy first
in_position = False
last_buy_price = 48000
last_sell_price = 50000


# load API Keys
client = Client(config.API_KEY, config.SECRET_KEY)


# define functions
def order(side, quantity, symbol, order_type=ORDER_TYPE):
    try:
        print("Sending Order")
        order = client.create_test_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        # order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    # except Exception as e:
    except exceptions as e:
        print("An exception has occurd - {}".format(e))
        return False


    return True


def on_open(ws):
    print("Open Connection")


def on_close(ws):
    print("Close Connection")


def on_message(ws, message):
    # We use global read and write a global variable inside a function
    global closes, in_position, last_buy_price, last_sell_price
    # print("Recieved Message")
    # now we read message as json so that we can access/use it
    json_message = json.loads(message)
    # pprint.pprint(json_message)

    # get the candel info
    candel = json_message['k']
    # check if the candel closed
    is_candel_closed = candel['x']
    # get the closed price
    close = candel['c']
    close = float(close)
    # print("{:0.2f}".format(close))

    if is_candel_closed:
        closes.append(close)
        if len(closes) > 1:
            c_change = ((closes[-1]-closes[-2])/closes[-2])*100
            if c_change > 0:
                c_trend = "UP"
            else:
                c_trend = "DOWN"
            
            print(">>>> {} Candel has closed at ${:0.2f}, {:0.2f}% ({})".format(candel_period, close, c_change, c_trend))

            
            if in_position:
                last_action = "buy"
                cum_change = ((close-last_buy_price)/last_buy_price)*100
            else:
                last_action = "sell"
                cum_change = ((close-last_sell_price)/last_sell_price)*100
            
            if cum_change > 0:
                cum_trend = "UP"
            else:
                cum_trend = "DOWN"
            
            print(">>> Price move since last {}: {:0.2f}% ({})".format(last_action, cum_change, cum_trend))

        if len(closes) > RSI_PERIOD:
            np_closes = np.array(closes)
            rsi = talib.RSI(np_closes, RSI_PERIOD)
            # print("all RSIs calculated")
            # print(rsi)
            last_rsi = rsi[-1]
            print(">> Current RSI is {:0.1f}\n".format(last_rsi))

            # Selling algorithm
            if last_rsi > RSI_OVERBOUGHT:
                if in_position:
                    print("\n***** SELL *****\n")
                    order_succeeded = order(side=Client.SIDE_SELL, quantity=TRADE_QUANTITY, symbol=TRADE_SYMBOL)
                    if order_succeeded:
                        print("Order Succeeded - SELL\n")
                        in_position = False
                        last_sell_price = close #change for actual sell price

                else:
                    print("** It is over-bought, but we dont have any crypto to sell **\n")

            # Buying algorithm
            if last_rsi < RSI_OVERSOLD:
                if in_position:
                    print("** It is over-sold , but we dont have any money to buy **\n")
                else:
                    print("\n***** BUY *****\n")
                    order_succeeded = order(side=Client.SIDE_BUY, quantity=TRADE_QUANTITY, symbol=TRADE_SYMBOL)
                    if order_succeeded:
                        print("Order Succeeded - BUY\n")
                        in_position = True
                        last_buy_price = close #change for actual buy price


# Now get and report stats
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()