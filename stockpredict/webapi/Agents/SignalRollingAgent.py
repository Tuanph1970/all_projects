from Agents.Agent import Agent, StockExchange, TARGET_NAME
import numpy as np
class SignalRollingAgent(Agent):
    def __init__(self,initial_money,df_series,max_buy,max_sell,delay=5,initial_state=1):
        super(SignalRollingAgent, self).__init__(initial_money,df_series,max_buy,max_sell)
        self.delay = delay
        self.initial_state = initial_state
    def exchange_stock(self):
        self.exchange_obj = StockExchange(self.initial_money, self.max_buy, self.max_sell)
        real_movement = self.signal['trend'].values
        starting_money = self.initial_money
        delay_change_decision = self.delay
        current_decision = 0
        state = self.initial_state
        current_val = real_movement[0]
        if state == 1:
            self.exchange_obj.buy(current_val,0)
        for i in range(1, len(real_movement), 1):
            if real_movement[i] < current_val and state == 0:
                if current_decision < delay_change_decision:
                    current_decision += 1
                else:
                    state = 1
                    self.exchange_obj.buy(real_movement[i],i)
                    current_decision = 0
            if real_movement[i] > current_val and state == 1:
                if current_decision < delay_change_decision:
                    current_decision += 1
                else:
                    state = 0
                    current_inventory = self.exchange_obj.get_current_inventory()
                    self.exchange_obj.sell(current_inventory,i)
                    current_decision = 0
            current_val = real_movement[i]
    def get_sell_states(self):
        return super(SignalRollingAgent, self).get_sell_states()
    def get_buy_states(self):
        return super(SignalRollingAgent, self).get_buy_states()
