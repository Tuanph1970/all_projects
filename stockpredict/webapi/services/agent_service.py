from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
from Agents.AbcdStrategyAgent import AbcdStrategyAgent
from Agents.Agent import DataEngine
from Agents.MAAgent import MovingAverageAgent
from Agents.SignalRollingAgent import SignalRollingAgent
from Agents.TurtleAgent import TurtleAgent
from services.stock_market_service import CompanyService
from core.exceptions import AgentExecutionException, EntityNotFoundException
from core.decorators import validate_input, cache_result
from repositories.agent_repository import AgentRepository


class AgentService:
    def __init__(self):
        self.company_service = CompanyService()
        self.agent_repo = AgentRepository()
    
    @validate_input()
    def run_stock_agent(self, params: Dict) -> Dict:
        try:
            ticker = params['ticker']
            agent_name = params['agent_name']
            initial_money = int(params['initial_money'])
            max_buy = int(params['max_buy'])
            max_sell = int(params['max_sell'])
            start_date = params['start_date']
            end_date = params['end_date']
            
            # Get price data
            df = self.company_service.get_price_history_df(ticker, "VCI")
            df = df[['time', 'close']]
            df['time'] = pd.to_datetime(df.time, format='%Y-%m-%d')
            df = df[(df.time >= start_date) & (df.time <= end_date)]
            
            # Prepare time series data
            close_series_json = []
            for i in range(len(df.index)):
                json_obj = {
                    'time': df['time'].values[i],
                    'close': df['close'].values[i]
                }
                close_series_json.append(json_obj)
            
            result = {'time_series': close_series_json}
            
            # Create agent based on type
            agent_stock = self._create_agent(agent_name, initial_money, df, max_buy, max_sell, params)
            
            if agent_stock:
                agent_stock.generate_signals()
                agent_stock.exchange_stock()
                
                result.update({
                    'buy': agent_stock.get_buy_states(),
                    'sell': agent_stock.get_sell_states(),
                    'current_amount': agent_stock.get_current_amount(),
                    'current_inventory': agent_stock.get_current_inventory(),
                    'total_gain': agent_stock.get_total_gains(),
                    'investment': agent_stock.get_investment(),
                    'exchange_history': agent_stock.get_exchange_history(),
                    'training_history': []
                })
            
            return result
            
        except Exception as e:
            raise AgentExecutionException(agent_name, str(e))
    
    def _create_agent(self, agent_name: str, initial_money: int, df: pd.DataFrame, 
                     max_buy: int, max_sell: int, params: Dict):
        if agent_name == 'Turtle':
            window_length = int(params['window_length'])
            return TurtleAgent(initial_money, df, max_buy, max_sell, window_length)
        elif agent_name == 'MovingAverage':
            short_window = int(params['short_window'])
            long_window = int(params['long_window'])
            return MovingAverageAgent(initial_money, df, max_buy, max_sell, short_window, long_window)
        elif agent_name == 'SignalRolling':
            delay = int(params['delay'])
            initial_state = int(params['initial_state'])
            return SignalRollingAgent(initial_money, df, max_buy, max_sell, delay, initial_state)
        elif agent_name == 'AbcdStrategy':
            return AbcdStrategyAgent(initial_money, df, max_buy, max_sell)
        else:
            raise EntityNotFoundException("Agent", agent_name)
    
    def get_all_agents(self) -> List[Dict]:
        return self.agent_repo.get_all_agents()
    
    def get_supported_agents(self) -> List[str]:
        return ['Turtle', 'MovingAverage', 'SignalRolling', 'AbcdStrategy']