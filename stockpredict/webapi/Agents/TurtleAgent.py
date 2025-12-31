from Agents.Agent import Agent, StockExchange
import pandas as pd

class TurtleAgent(Agent):
    def __init__(self,initial_money,df_series,max_buy,max_sell,window_length):
        super(TurtleAgent,self).__init__(initial_money,df_series,max_buy,max_sell)
        self.window_length = window_length
    def generate_signals(self):
        super(TurtleAgent, self).generate_signals()
        count = self.window_length

        self.signal['RollingMax'] = (self.signal['trend'].shift(1).rolling(count).max())
        self.signal['RollingMin'] = (self.signal['trend'].shift(1).rolling(count).min())
        self.signal.loc[self.signal['RollingMax'] < self.signal['trend'], 'signal'] = -1
        self.signal.loc[self.signal['RollingMin'] > self.signal['trend'], 'signal'] = 1
    def exchange_stock(self):
        self.exchange_obj = StockExchange(self.initial_money, self.max_buy, self.max_sell)
        for i in range(len(self.signal)):
            state = self.signal['signal'].values[i]
            if state == 1:
                self.exchange_obj.buy(self.signal['trend'].values[i],i)
            elif state == -1:
                self.exchange_obj.sell(self.signal['trend'].values[i],i)
    def get_buy_states(self):
        return  super(TurtleAgent, self).get_buy_states()
    def get_sell_states(self):
        return super(TurtleAgent, self).get_sell_states()




