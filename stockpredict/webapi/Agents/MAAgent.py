from Agents.Agent import Agent, StockExchange
import numpy as np
class MovingAverageAgent(Agent):
    def __init__(self,initial_money,df_series,max_buy,max_sell,short_window,long_window):
        super(MovingAverageAgent, self).__init__(initial_money,df_series,max_buy,max_sell)
        self.short_window = short_window
        self.long_window = long_window
    def generate_signals(self):
        super(MovingAverageAgent, self).generate_signals()
        self.signal['short_ma'] = self.signal['trend'].rolling(window=self.short_window, min_periods=1,
                                                                center=False).mean()
        self.signal['long_ma'] = self.signal['trend'].rolling(window=self.long_window, min_periods=1,
                                                               center=False).mean()

        self.signal['signal'][self.short_window:] = np.where(self.signal['short_ma'][self.short_window:]
                                                              > self.signal['long_ma'][self.short_window:], 1.0, 0.0)
        self.signal['position'] = self.signal['signal'].diff()
    def exchange_stock(self):
        self.exchange_obj = StockExchange(self.initial_money, self.max_buy, self.max_sell)
        for i in range(len(self.signal['position'])):
            state = self.signal['position'].values[i]
            if state == 1:
                self.exchange_obj.buy(self.signal['trend'].values[i],i)
            elif state == -1:
                self.exchange_obj.sell(self.signal['trend'].values[i],i)
    def get_sell_states(self):
        return super(MovingAverageAgent, self).get_sell_states()
    def get_buy_states(self):
        return super(MovingAverageAgent, self).get_buy_states()
