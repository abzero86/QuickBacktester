__author__ = 'zhiyuwang'
## Simple turtle strategy for ShangHai and ShenZhen 300 stocks.
## Long and Short.
## Last update Oct 15th, 2014
## Added: plot PnL / drawdown curve using matplotlib.pyplot
## Added: dynamic turtle_size modification based on drawdown

from __future__ import division
import csv
from collections import OrderedDict
from datetime import *
import matplotlib.pyplot as plt
from matplotlib.finance import candlestick_ohlc
from pylab import date2num
from matplotlib.dates import  DateFormatter, WeekdayLocator, HourLocator, \
     DayLocator, MONDAY
import math
    
class backtester():
    def __init__(self, filepaths, init_date = datetime(2009,1,1), end_date = datetime(2014, 9, 30)):
        self.equity = 0
        self.cash = 0
        self.history = OrderedDict()
        self.positions = {}
        self.bars = {}
        self.trades = {}
        self.init_date = init_date
        self.end_date = end_date
        self.pnl_by_symbol = {}
        self.trading_fee = {}
        self.actions = []
        for symbol in filepaths:
##            print(symbol)
            reader = csv.reader(open(filepaths[symbol], 'rb'))
            self.bars[symbol] = []
            headers = reader.next()
            for title in headers:
                if "Date" in title:
                    date_index = headers.index(title)
                elif "Open" in title:
                    open_index = headers.index(title)
                elif "High" in title:
                    high_index = headers.index(title)
                elif "Low" in title:
                    low_index = headers.index(title)
                elif "Close" in title:
                    close_index = headers.index(title)
                elif "Volume" in title:
                    volume_index = headers.index(title)
            for row in reader:
                tempdate = datetime.strptime(row[date_index], '%Y-%m-%d')
                if (int(float((row[volume_index]))) > 0
                    and tempdate >= init_date
                    and tempdate <= end_date):
                    self.bars[symbol].append({"D":tempdate,
                                              "O":float(row[open_index]),
                                              "H":float(row[high_index]),
                                              "L":float(row[low_index]),
                                              "C":float(row[close_index]),
                                              "V":int(float(row[volume_index]))})
##            print(symbol + ": " + str(len(self.bars[symbol])))
            self.positions[symbol] = {"Position":0, "AvgCost":0, "LastPrice":0}
            self.trades[symbol] = []
            self.pnl_by_symbol[symbol] = 0
            self.trading_fee[symbol] = 0
            
    def run(self, strategy, init_equity = 1000000, init_date = None, end_date = None):
        self.equity = init_equity
        self.cash = self.equity
        self.best = self.equity
        self.max_drawdown = 0
        if init_date == None:
            init_date = self.init_date
        if end_date == None:
            end_date = self.end_date
        current_date = init_date
        symbol_indices = {}
        for symbol in self.bars:
            symbol_indices[symbol] = 0
        while(current_date <= end_date):
            trading_fee = 0
            for symbol in self.bars:
                if (symbol_indices[symbol] < len(self.bars[symbol])
                    and current_date == self.bars[symbol][symbol_indices[symbol]]["D"]):
                    new_position = strategy(current_date,
                                            symbol,
                                            symbol_indices[symbol],
                                            self.equity,
                                            self.cash,
                                            self.positions,
                                            self.bars,
                                            self)
                    self.trade(new_position, current_date, symbol_indices[symbol])
##                    if (symbol in self.trading_fee
##                        and current_date in self.trading_fee[symbol]):
##                        trading_fee += self.trading_fee[symbol][current_date]
                    self.positions[symbol]["LastPrice"] = self.bars[symbol][symbol_indices[symbol]]["C"]
                    symbol_indices[symbol] += 1
            ## Sellshort csi300 to hedge:
##            csi_new_position, csi_index = self.csi300_hedge(current_date)
##            self.trade(, current_date, csi300_index)
            if self.equity > self.best:
                self.best = self.equity
            if self.max_drawdown < 1 - self.equity/self.best:
                self.max_drawdown = 1 - self.equity/self.best
            self.history[current_date] = {"date":current_date,
                                          "equity":self.equity,
                                          "cash":self.cash,
                                          "positions":self.positions,
                                          "drawdown":1-self.equity/self.best}
##            print(current_date.__str__()+", equity = "+self.equity.__str__()+", cash = "+self.cash.__str__())
            current_date = current_date + timedelta(days=1)
##    def csi300_hedge(self, current_date):
##        for
    def generate_trading_fee_by_date(self):
        index_actions = 0
        for date in self.history:
            self.history[date]["trading_fee"] = 0
            while(index_actions < len(self.actions)
                  and self.actions[index_actions]["Date"] <= date):
                self.history[date]["trading_fee"] += self.actions[index_actions]["Commission"]
                index_actions += 1
            
    def trade(self, position, date, index):
        equity = 0
        for action in position:
            action["Position"] = round(action["Position"])
            action["Price"] = round(action["Price"],3)    
            print(date.__str__() + " "
                  + action["Symbol"] + ": "
                  + action["Position"].__str__() + "@"
                  + action["Price"].__str__()
                  + ", ATR = " + round(self.bars[action["Symbol"]][index]["ATR"],2).__str__())
            symbol = action["Symbol"]
##            self.cash -= action["Position"]*action["Price"]
            if ((action["Entry"] and action["Position"] > 0) or
                (not action["Entry"] and action["Position"] < 0)):
                self.cash -= action["Position"]*action["Price"]
##            elif ((action["Entry"] and action["Position"] < 0) or
##                (not action["Entry"] and action["Position"] > 0)):
##                self.cash += action["Position"]*action["Price"]
##            Commissions
            comission = abs(action["Position"]*action["Price"]) * 3/10000
            self.trading_fee[action["Symbol"]] += comission if comission > 5 else 5
            self.cash -= comission if comission > 5 else 5
            action["Commission"] = comission if comission > 5 else 5
            self.actions.append(action)
            if self.positions[symbol]["Position"] + action["Position"] == 0:
                self.pnl_by_symbol[symbol] -= action["Position"]*(action["Price"]-self.positions[symbol]["AvgCost"])
                self.positions[symbol]["Position"] = 0
                self.positions[symbol]["AvgCost"] = 0
            else:
                self.positions[symbol]["AvgCost"] = \
                                                  (self.positions[symbol]["AvgCost"]*self.positions[symbol]["Position"] +\
                                                  action["Position"]*action["Price"])/(self.positions[symbol]["Position"] + action["Position"])
                self.positions[symbol]["Position"] += action["Position"]
            self.trades[action["Symbol"]].append({"Date": date,
                                                  "Price":action["Price"],
                                                  "Lots":action["Position"]})
        for symbol in self.positions:
            if self.positions[symbol]["Position"] > 0 :
                equity += self.positions[symbol]["Position"] * self.positions[symbol]["LastPrice"]
            elif self.positions[symbol]["Position"] < 0 :
                equity += self.positions[symbol]["Position"] *( self.positions[symbol]["LastPrice"] - self.positions[symbol]["AvgCost"])
        self.equity = self.cash + equity
##        print(date.__str__()+", cash = "+self.cash.__str__()+", equity = "+self.equity.__str__())
        
    def plot_trade(self, symbol, init_index = None, end_index=None, PnL=False, ATR=False):
        if init_index == None:
            init_index = 0
        init_date = b.bars[symbol][init_index]["D"]
        if end_index == None:
            end_index = len(b.bars[symbol])
        end_date = b.bars[symbol][end_index-1]["D"]
        mondays = WeekdayLocator(MONDAY)
        mondays.MAXTICKS = 2000
        alldays = DayLocator()              # minor ticks on the days
        alldays.MAXTICKS = 2000
        weekFormatter = DateFormatter('%b %d')  # e.g., Jan 12
        dayFormatter = DateFormatter('%d')      # e.g., 12
        history = [(date2num(x["D"]), x["O"], x["H"], x["L"], x["C"]) for x in b.bars[symbol][init_index:end_index]]
        if PnL or ATR:
            fig, (ax, ax2) = plt.subplots(2, sharex = True)
        else:
            fig, ax = plt.subplots()
        ax.xaxis.set_major_locator(mondays)
        ax.xaxis.set_minor_locator(alldays)
        ax.xaxis.set_major_formatter(weekFormatter)
        candlestick_ohlc(ax, history)
        buys = [(x["Date"], x["Price"]) for x in self.trades[symbol] if (x["Lots"] > 0 and x["Date"] > init_date and x["Date"]<end_date) ]
        buy_dates, buy_values = zip(*buys)
        ax.plot(buy_dates, buy_values, "^", markersize = 5, color='m')
        sells = [(x["Date"], x["Price"]) for x in self.trades[symbol] if (x["Lots"] < 0 and x["Date"] > init_date and x["Date"]<end_date)]
        sell_dates, sell_values = zip(*sells)
        ax.plot(sell_dates, sell_values, "v", markersize = 5, color='k')
        ax.xaxis_date()
        ax.autoscale_view()
        if PnL:
            equity_history = [(date, record["equity"], record["drawdown"]) for date, record in self.history.items()]
            dates, values, drawdowns = zip(*equity_history)
            ax2 = fig.add_subplot(212)
            ax2.plot(dates, values, 'b-')
        elif ATR:
            equity_history = [(x["D"], x["ATR"]) for x in self.bars[symbol][init_index:end_index]]
            dates, values = zip(*equity_history)
            ax2 = fig.add_subplot(212)
            ax2.plot(dates, values, 'b-')
            
##        ax3 = ax2.twinx()
##        ax3.plot(dates, drawdowns, 'r-')
        
        plt.show()

class turtle():
    def __init__(self,
                 donchian_exit_period = 10,
                 donchian_short_period = 20,
                 donchian_long_period = 55,
                 turtle_atr_period = 20,
                 turtle_risk_ratio = 0.01,
                 turtle_entry_interval = 1,
                 turtle_max_entry_time = 4):
        self.exit_period = donchian_exit_period
        self.short_period = donchian_short_period
        self.long_period = donchian_long_period
        self.atr_period = turtle_atr_period
        self.risk_ratio = turtle_risk_ratio
        self.pre_entry_success = {}
        self.pre_entry_price = {}
        self.entry_number = {}
        self.entry_interval = turtle_entry_interval
        self.max_entry_time = turtle_max_entry_time
    def turtle(self, date, symbol, index, equity, cash, positions, data, backtester):
##        print(symbol + " @ " + date.__str__())
        actions = []
        if index < 56:
            return actions
        day_high = data[symbol][index]["H"]
        day_low = data[symbol][index]["L"]
        day_open = data[symbol][index]["O"]
        day_max55 = data[symbol][index]["Max55"]
        day_max20 = data[symbol][index]["Max20"]
        day_min10 = data[symbol][index]["Min10"]
        day_min55 = data[symbol][index]["Min55"]
        day_min20 = data[symbol][index]["Min20"]
        day_max10 = data[symbol][index]["Max10"]
        day_atr = data[symbol][index]["ATR"]
        turtle_size_1 = self.risk_ratio*cash/day_atr
        turtle_size_2 = cash/5/day_open
        turtle_size = round(min(turtle_size_1, turtle_size_2)/100)*100
## Turtle size modification based on current drawdown
## For example, if current drawdown = 10%, then the turtle size will be 90% of original normal size.
        turtle_size = round(turtle_size * (backtester.equity/backtester.best)**2/100)*100
##        if (day_high == day_low
##            and day_high > data[symbol][index-1]["C"] * 1.098):
##            return actions
##        if symbol in self.pre_entry_success:
##            print (date.__str__()
##                   +", Pre 20 Entry Success: "+self.pre_entry_success[symbol].__str__()
##                   + ", Max20 = "+day_max20.__str__()
##                   + ", Min10 = "+day_min10.__str__())
##        if symbol in self.pre_entry_price:
##            print(date.__str__() + ", PreEntry = "+self.pre_entry_price[symbol].__str__())
        if (day_high >= day_max55
            and positions[symbol]["Position"] == 0
            and turtle_size >= 100):
            price = day_max55 if day_open < day_max55 else day_open
            actions.append({"Symbol":symbol,
                            "Date":date,
                            "Price": price,
                            "Position":turtle_size,
                            "Entry":True})
            self.entry_number[symbol] = 1
            self.pre_entry_price[symbol] = price
            print(date.__str__()+", Entry because Max55")
        elif (data[symbol][index]["PRM"] < data[symbol][index]["lnReturn"]
            and positions[symbol]["Position"] == 0
            and turtle_size >= 100):
            price = math.exp(data[symbol][index]["PRM"])*data[symbol][index-1]["C"]
            price = price if day_open < price else day_open
            actions.append({"Symbol":symbol,
                            "Date":date,
                            "Price": price,
                            "Position":turtle_size,
                            "Entry":True})
            self.entry_number[symbol] = 1
            self.pre_entry_price[symbol] = price
            print(date.__str__()+", Entry because High Return")
        elif (day_high >= day_max20
              and symbol in self.pre_entry_success
              and self.pre_entry_success[symbol]
              and positions[symbol]["Position"] == 0
              and turtle_size >= 100
              ## Filter 1:
              and day_max10 > data[symbol][index - 10]["Max10"]):
            price = day_max20 if day_open < day_max20 else day_open
            actions.append({"Symbol":symbol,
                            "Date":date,
                            "Price":price,
                            "Position":turtle_size,
                            "Entry":True})
            self.entry_number[symbol] = 1
            self.pre_entry_price[symbol] = price
            print(date.__str__()+", Entry because Max20")
        elif (symbol in self.pre_entry_price
              and day_high > self.pre_entry_price[symbol] + self.entry_interval*day_atr
              and positions[symbol]["Position"] > 0
              and self.entry_number[symbol] < self.max_entry_time
              and turtle_size >= 100):
            price = self.pre_entry_price[symbol] + self.entry_interval*day_atr
            while (price < day_high
                   and self.entry_number[symbol] < self.max_entry_time
                   and turtle_size >= 100):
                actions.append({"Symbol":symbol,
                                "Date":date,
                                "Price":price if day_open < price else day_open,
                                "Position":turtle_size,
                                "Entry":True})
                cash -= price * turtle_size
                turtle_size = turtle_size if turtle_size < self.risk_ratio*cash/day_atr else round(self.risk_ratio*cash/day_atr/100)*100
                self.entry_number[symbol] += 1
                self.pre_entry_price[symbol] = price
                price += 0.5*day_atr
        elif (symbol in positions
              and positions[symbol]["Position"] >0
              and symbol in self.pre_entry_price
              and self.pre_entry_price[symbol] - 2*day_atr > day_low):
            price = self.pre_entry_price[symbol] - 2*day_atr if self.pre_entry_price[symbol] - 2*day_atr < day_open else day_open
##              and positions[symbol]["AvgCost"] - day_low > 2*day_atr):
##            price = positions[symbol]["AvgCost"] - 2*day_atr if positions[symbol]["AvgCost"] - 2*day_atr < day_open else day_open
            actions.append({"Symbol":symbol,
                            "Date":date,
                            "Price": price,
                            "Position": -positions[symbol]["Position"],
                            "Entry":False})
            self.entry_number[symbol] = 0
            del self.pre_entry_price[symbol]
            self.pre_entry_success[symbol] = False
        elif ((symbol in positions)
              and (positions[symbol]["Position"] >0)
              and (symbol in self.pre_entry_price)
              and (day_low < day_min10)):
            price = day_min10 if day_min10 < day_open else day_open
            actions.append({"Symbol":symbol,
                            "Date":date,
                            "Price": price,
                            "Position": -positions[symbol]["Position"],
                            "Entry": False})
            self.entry_number[symbol] = 0
            del self.pre_entry_price[symbol]
            if (positions[symbol]["AvgCost"] < price):
                self.pre_entry_success[symbol] = True
            else:
                self.pre_entry_success[symbol] = False
######         LOSING       
######        elif ((symbol in positions)
######              and (positions[symbol]["Position"] >0)
######              and (symbol in self.pre_entry_price)
######              and (day_low < day_max10 - 2*day_atr)):
######            price = day_max10 - 2*day_atr if day_max10 - 2*day_atr < day_open else day_open
######            actions.append({"Symbol":symbol,
######                            "Date":date,
######                            "Price": price,
######                            "Position": -positions[symbol]["Position"],
######                            "Entry": False})
######            self.entry_number[symbol] = 0
######            del self.pre_entry_price[symbol]
######            if (positions[symbol]["AvgCost"] < price):
######                self.pre_entry_success[symbol] = True
######            else:
######                self.pre_entry_success[symbol] = False
####        print(date.__str__() + ", "
####              + (symbol in positions).__str__() + ", "
####              + (positions[symbol]["Position"] >0).__str__()+", "
####              + (symbol in self.pre_entry_price).__str__()+", "
####              + (day_low < day_min10).__str__())
##SellShort
##        if (day_high == day_low
##            and day_low < data[symbol][index-1]["C"] * 0.91):
##            return actions
        
##        if (day_low <= day_min55
##            and positions[symbol]["Position"] == 0
##            and turtle_size >= 100):
##            price = day_min55 if day_open > day_min55 else day_open
##            actions.append({"Symbol":symbol,
##                            "Price": price,
##                            "Position":-turtle_size,
##                            "Entry":True})
##            self.entry_number[symbol] = 1
##            self.pre_entry_price[symbol] = price
##        elif (day_low <= day_min20
##              and symbol in self.pre_entry_success
##              and self.pre_entry_success[symbol]
##              and positions[symbol]["Position"] == 0
##              and turtle_size >= 100
##              ## Filter 1:
##              and day_min10 < data[symbol][index - 10]["Min10"]):
##            price = day_min20 if day_open > day_min20 else day_open
##            actions.append({"Symbol":symbol,
##                            "Price":price,
##                            "Position":-turtle_size,
##                            "Entry":True})
##            self.entry_number[symbol] = 1
##            self.pre_entry_price[symbol] = price
##        elif (symbol in self.pre_entry_price
##              and day_low < self.pre_entry_price[symbol] - 0.5*day_atr
##              and positions[symbol]["Position"] < 0
##              and turtle_size >= 100
##              and self.entry_number[symbol] < 4):
##            price = self.pre_entry_price[symbol] - 0.5*day_atr
##            while (price > day_low
##                   and self.entry_number[symbol] < 4
##                   and turtle_size >= 100):
##                actions.append({"Symbol":symbol,
##                                "Price":price if day_open > price else day_open,
##                                "Position":-turtle_size,
##                                "Entry": True})
##                cash -= abs(price * turtle_size)
##                turtle_size = turtle_size if turtle_size < self.risk_ratio*cash/day_atr else round(self.risk_ratio*cash/day_atr/100)*100
##                self.entry_number[symbol] += 1
##                self.pre_entry_price[symbol] = price
##                price -= 0.5*day_atr
##        elif (symbol in positions
##              and positions[symbol]["Position"] < 0
##              and symbol in self.pre_entry_price
##              and positions[symbol]["AvgCost"] < day_high - 2*day_atr):
##            price = positions[symbol]["AvgCost"] + 2*day_atr if positions[symbol]["AvgCost"] + 2*day_atr > day_open else day_open
##            actions.append({"Symbol":symbol,
##                            "Price": price,
##                            "Position": -positions[symbol]["Position"],
##                            "Entry": False})
##            self.entry_number[symbol] = 0
##            del self.pre_entry_price[symbol]
##            self.pre_entry_success[symbol] = False
##        elif (symbol in positions
##              and positions[symbol]["Position"] < 0
##              and symbol in self.pre_entry_price
##              and day_high > day_max10):
##            price = day_max10 if day_max10 > day_open else day_open
##            actions.append({"Symbol":symbol,
##                            "Price": price,
##                            "Position": -positions[symbol]["Position"],
##                            "Entry": False})
##            self.entry_number[symbol] = 0
##            del self.pre_entry_price[symbol]
##            if (positions[symbol]["AvgCost"] > price):
##                self.pre_entry_success[symbol] = True
##            else:
##                self.pre_entry_success[symbol] = False
                
        return actions
    def prepare_indicators(self, data):
        for symbol in data:
            for index in range(0, len(data[symbol])):
                if index >= self.exit_period:
                    data[symbol][index]['Min10'] = min([x["L"] for x in data[symbol][(index - self.exit_period):index]])
                else:
                    data[symbol][index]['Min10'] = None
                if index >= self.short_period:
                    data[symbol][index]['Max20'] = max([x["H"] for x in data[symbol][(index - self.short_period):index]])
                else:
                    data[symbol][index]['Max20'] = None
                if index >= self.long_period:
                    data[symbol][index]['Max55'] = max([x["H"] for x in data[symbol][(index - self.long_period):index]])
                else:
                    data[symbol][index]['Max55'] = None
                    
                if index >= self.exit_period:
                    data[symbol][index]['Max10'] = max([x["H"] for x in data[symbol][(index - self.exit_period):index]])
                else:
                    data[symbol][index]['Max10'] = None
                if index >= self.short_period:
                    data[symbol][index]['Min20'] = min([x["L"] for x in data[symbol][(index - self.short_period):index]])
                else:
                    data[symbol][index]['Min20'] = None
                if index >= self.long_period:
                    data[symbol][index]['Min55'] = min([x["L"] for x in data[symbol][(index - self.long_period):index]])
                else:
                    data[symbol][index]['Min55'] = None
                if index >= self.atr_period:
                    temp = []
                    for i in range(index-self.atr_period, index-1):
                        temp.append(max(data[symbol][i]["H"] - data[symbol][i]["L"],
                                        abs(data[symbol][i]["H"] - data[symbol][i]["O"]),
                                        abs(data[symbol][i]["L"] - data[symbol][i]["O"])))
                    data[symbol][index]['ATR'] = sum(temp)/len(temp)
                else:
                    data[symbol][index]['ATR'] = None
                if index >= 1:
                    data[symbol][index]["lnReturn"] = math.log(data[symbol][index]["C"]/data[symbol][index-1]["C"])
                else:
                    data[symbol][index]["lnReturn"] = None
                if index > 55:
                    i = index
                    positive_lnReturn = []
                    while (i>1 and len(positive_lnReturn) < 20):
                        i -= 1
                        if data[symbol][i]["lnReturn"]>0:
                            positive_lnReturn.append(data[symbol][i]["lnReturn"])
                    data[symbol][index]["PRM"] = max(positive_lnReturn)
                else:
                    data[symbol][index]["PRM"] = None
                

                    
##symbol = "000001.sz"
##filepath = {symbol:"C:\\New folder\\s\\histories\\"+symbol+".adjusted.csv"}
##b = backtester(filepath)
##t = turtle()
##t.prepare_indicators(b.bars)
####data = [(x["D"], x["C"], x["lnReturn"]) for x in b.bars[symbol]]
####date, close, returnval = zip(*data)
####fig, (ax1, ax2) = plt.subplots(2, sharex = True)
####ax1.plot(date, close)
####ax2.plot(date, returnval)
####plt.show()
##b.run(t.turtle)
##print("End Equity = " + b.equity.__str__())
##equity_history = [(date, record["equity"], record["drawdown"]) for date, record in b.history.items()]
##dates, values, drawdowns = zip(*equity_history)
##b.plot_trade(symbol)


filepath = {}
codes = csv.reader(open(r"C:\New folder\s\histories\000300cons.csv",'rb'))
for code in codes:
    filepath[code[0]] = "C:\\New folder\\s\\histories\\" + code[0] + ".adjusted.csv"
b = backtester(filepath)
t = turtle(turtle_risk_ratio = 0.001, turtle_max_entry_time = 1)
t.prepare_indicators(b.bars)
b.run(t.turtle, init_equity = 100000000)
print("End Equity = " + b.equity.__str__())
b.generate_trading_fee_by_date()
equity_history = [(date, record["equity"], record["drawdown"],record["cash"], record["trading_fee"]) for date, record in b.history.items()]
dates, values, drawdowns, cashes, trading_fee = zip(*equity_history)
fig, (ax1,ax3) = plt.subplots(2, sharex = True)
ax1.plot(dates, values, 'b-')
ax2 = ax1.twinx()
ax2.plot(dates, cashes, 'r-')
ax3.plot(dates, trading_fee)
plt.show()
