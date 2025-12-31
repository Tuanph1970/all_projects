import mysql.connector as connection
import pandas as pd
TARGET_NAME = 'close'
class DataEngine:
    def __init__(self):
        host = 'localhost'
        user = 'root'
        password = "Mysql@2023"
        db = 'stock'
        port = 3306
        self.database = connection.connect(host=host, database=db, user=user, passwd=password,
                                           port=port)
    def execute_sql(self,query):
        self.df = pd.read_sql(query, self.database)
    def get_data_frame(self):
        return self.df
    def get_data_by_field(self,field_name):
        return self.df[field_name]
class StockExchange:
    def __init__(self,initial_money,max_buy,max_sell):
        self.current_inventory = 0
        self.money = initial_money

        self.max_buy = max_buy
        self.max_sell = max_sell
        self.state_buy = []
        self.state_sell = []
        self.exchange_history = []
    def buy(self,current_price,index):
        shares = self.money // current_price
        if shares < 1:
            print('not enough money to buy a stock')
        else:
            if shares > self.max_buy:
                buy_units = self.max_buy
            else:
                buy_units = shares
            self.money -= buy_units * current_price
            self.current_inventory += buy_units
            self.exchange_history.append('buy ' + str(buy_units) + ' unit at price ' + str(current_price))
            self.state_buy.append(index)
    def sell(self,current_price,index):
        if self.current_inventory == 0:
            print('ko co de ban')
            return
        if self.current_inventory > self.max_sell:
            sell_units = self.max_sell
        else:
            sell_units = self.current_inventory
        self.current_inventory -= sell_units
        sell_amount = sell_units * current_price
        self.money += sell_amount
        self.exchange_history.append('sell ' + str(sell_units) + ' unit at price ' + str(current_price))
        self.state_sell.append(index)
    def get_current_amount(self):
        return self.money
    def get_current_inventory(self):
        return self.current_inventory
    def get_exchange_history(self):
        return self.exchange_history
class Agent:
    def __init__(self,initial_money,df_series,max_buy,max_sell):
        self.initial_money = initial_money
        self.df_target = df_series
        self.max_buy = max_buy
        self.max_sell = max_sell
        self.signal = None
        self.exchange_obj = None
    def generate_signals(self):
        self.signal = pd.DataFrame(self.df_target.index)
        closes = self.df_target[TARGET_NAME].values
        self.signal['trend'] = closes
        self.signal['signal'] = 0
    def exchange_stock(self):
        pass
    def get_buy_states(self):
        return self.exchange_obj.state_buy
    def get_sell_states(self):
        return self.exchange_obj.state_sell
    def get_current_amount(self):
        return self.exchange_obj.get_current_amount()
    def get_current_inventory(self):
        return self.exchange_obj.get_current_inventory()
    def get_total_gains(self):
        return self.exchange_obj.get_current_amount() - self.initial_money
    def get_investment(self):
        return ((self.get_current_amount() - self.initial_money) / self.get_current_amount()) * 100
    def get_exchange_history(self):
        return self.exchange_obj.get_exchange_history()
class MLAgent:
    def __init__(self,initial_money,window_size,trend):
        self.inventory = []
        self.initial_money = initial_money
        self.starting_money = initial_money
        self.window_size = window_size
        self.trend = trend
        self.close = trend
        self.half_window = window_size // 2
        self.exchange_history = []
        self.train_history = []
    def predict(self,inputs):
        pass
    def train(self,iterations,checkpoint):
        pass
    def buy(self):
        pass
    def get_inventory(self):
        return len(self.inventory)
    def get_current_money(self):
        return self.initial_money
    def get_exchange_history(self):
        return self.exchange_history
    def get_train_histort(self):
        return self.train_history




