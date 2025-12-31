from Agents.Agent import Agent, StockExchange
import pandas as pd
import numpy as np

class AbcdStrategyAgent(Agent):
    def __init__(self,initial_money,df_series,max_buy,max_sell):

        super(AbcdStrategyAgent, self).__init__(initial_money,df_series,max_buy,max_sell)
        self.skip_loop = 4
        self.ma = 7
    def generate_signals(self):
        super(AbcdStrategyAgent, self).generate_signals()
        self.real_movement = self.signal['trend']
        ma = pd.Series(self.signal['trend']).rolling(self.ma).mean().values
        x = []
        for a in range(ma.shape[0]):
            for b in range(a, ma.shape[0], self.skip_loop):
                for c in range(b, ma.shape[0], self.skip_loop):
                    for d in range(c, ma.shape[0], self.skip_loop):
                        if ma[b] > ma[a] and \
                                (ma[c] < ma[b] and ma[c] > ma[a]) \
                                and ma[d] > ma[b]:
                            x.append([a, b, c, d])
        x_np = np.array(x)
        ac = x_np[:, 0].tolist() + x_np[:, 2].tolist()
        bd = x_np[:, 1].tolist() + x_np[:, 3].tolist()
        ac_set = set(ac)
        bd_set = set(bd)
        signal = np.zeros(len(self.signal['trend']))
        buy = list(ac_set - bd_set)
        sell = list(list(bd_set - ac_set))
        signal[buy] = 1.0
        signal[sell] = -1.0
        self.abcd_signal = signal


    def exchange_stock(self):
        starting_money = self.initial_money
        self.exchange_obj = StockExchange(self.initial_money, self.max_buy, self.max_sell)
        for i in range(self.real_movement.shape[0]):
            state = self.abcd_signal[i]
            if state == 1:
                self.exchange_obj.buy(self.signal['trend'].values[i], i)
            elif state == -1:
                self.exchange_obj.sell(self.signal['trend'].values[i], i)

        invest = ((self.initial_money - starting_money) / starting_money) * 100
        total_gains = self.initial_money - starting_money
