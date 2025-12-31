from typing import Dict, List, Optional
import pandas as pd
import torch
from Agents import NeuroEvolutionAgent
from Agents.ActorCriticAgent import ActorCriticAgent
from Agents.ActorCriticDuelAgent import ActorCriticDuelAgent
from Agents.ActorCriticRecurrentAgent import ActorCriticRecurrentAgent
from Agents.Agent import DataEngine
from Agents.CuriosityQLearningAgent import CuriosityQLearningAgent
from Agents.DoubleDualQLearningAgent import DoubleDualQLearningAgent
from Agents.DoubleDualRecurrentQlearningAgent import DoubleDualRecurrentQLearningAgent
from Agents.DoubleQLearningAgent import DoubleQLearningAgent
from Agents.DoubleRecurrentQLearningAgent import DoubleRecurrentQLearningAgent
from Agents.DualQLeaeningAgent import DualQLearningAgent
from Agents.DualRecurrentQLearningAgent import DualRecurrentQLearningAgent
from Agents.DuelCuriosityQLearningAgent import DuelCuriosityQLearningAgent
from Agents.EvolutionStrategyAgent import EvovutionStrategyAgent
from Agents.GradientAgent import GradientAgent
from Agents.NeuroEvolutionAgent import NeuroEvolutionAgent, neuralnetwork
from Agents.NeuroEvolutionNoveltySeachAgent import NeuroEvolutionNoveltySearchAgent, neuralnetwork1
from Agents.QLearningAgent import QLearningAgent
from Agents.RecurrentCuriosityQLearningAgent import RecurrentCuriosityQLearningAgent
from Agents.RecurrentQLearningAgent import RecurrentQLearningAgent
from services.stock_market_service import CompanyService
from core.exceptions import AgentExecutionException, EntityNotFoundException
from core.decorators import validate_input


class MLAgentService:
    def __init__(self):
        self.company_service = CompanyService()
        tf.compat.v1.disable_eager_execution()
    
    @validate_input()
    def run_ml_stock_agent(self, params: Dict) -> Dict:
        try:
            ticker = params['ticker']
            agent_name = params['agent_name']
            initial_money = int(params['initial_money'])
            window_size = int(params['window_size'])
            iterations = params['iterations']
            checkpoint = params['checkpoint']
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
                    'tradingdate': df['time'].values[i],
                    'close': df['close'].values[i]
                }
                close_series_json.append(json_obj)
            
            result = {'time_series': close_series_json}
            trend = df['close'].tolist()
            
            # Create ML agent based on type
            agent_ml_stock = self._create_ml_agent(agent_name, initial_money, window_size, trend, params)
            
            if agent_ml_stock:
                if agent_name not in ['NeuroEvolution', 'NeuroEvolutionNoveltySearch']:
                    agent_ml_stock.train(iterations=iterations, checkpoint=checkpoint)
                    states_buy, states_sell, total_gains, invest = agent_ml_stock.buy()
                    
                    result.update({
                        'buy': states_buy,
                        'sell': states_sell,
                        'current_amount': agent_ml_stock.get_current_money(),
                        'current_inventory': agent_ml_stock.get_inventory(),
                        'total_gain': total_gains,
                        'investment': invest,
                        'exchange_history': agent_ml_stock.get_exchange_history(),
                        'train_history': agent_ml_stock.get_train_histort()
                    })
                else:
                    generations = params['generations']
                    fittest_nets = agent_ml_stock.train(generations)
                    states_buy, states_sell, total_gains, invest = agent_ml_stock.buy(fittest_nets)
                    
                    result.update({
                        'buy': states_buy,
                        'sell': states_sell,
                        'current_amount': agent_ml_stock.get_current_money(),
                        'current_inventory': agent_ml_stock.get_inventory(),
                        'total_gain': total_gains,
                        'investment': invest
                    })
            
            return result
            
        except Exception as e:
            raise AgentExecutionException(agent_name, str(e))
    
    def _create_ml_agent(self, agent_name: str, initial_money: int, window_size: int, 
                        trend: List, params: Dict):
        if agent_name == "Gradient":
            state_size = params['state_size']
            skip = params['skip']
            return GradientAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == "QLearning":
            state_size = params['state_size']
            skip = params['skip']
            batch_size = params['batch_size']
            return QLearningAgent(initial_money, window_size, trend, state_size, skip, batch_size)
        elif agent_name == "DeepEvolutionStrategy":
            skip = params['skip']
            return EvovutionStrategyAgent(initial_money, window_size, trend, skip)
        elif agent_name == "DoubleQLearning":
            skip = params['skip']
            state_size = params['state_size']
            return DoubleQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'RecurrentQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return RecurrentQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'DoubleRecurrentQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return DoubleRecurrentQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'DualQLearning':
            skip = params['skip']
            state_size = params['state_size']
            batch_size = params['batch_size']
            return DualQLearningAgent(initial_money, window_size, trend, state_size, skip, batch_size)
        elif agent_name == 'DoubleDualQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return DoubleDualQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'DualRecurrentQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return DualRecurrentQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'DoubleDualRecurrentQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return DoubleDualRecurrentQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'ActorCritic':
            skip = params['skip']
            state_size = params['state_size']
            return ActorCriticAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'ActorCriticDuel':
            skip = params['skip']
            state_size = params['state_size']
            return ActorCriticDuelAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'ActorCriticRecurrent':
            skip = params['skip']
            state_size = params['state_size']
            return ActorCriticRecurrentAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'ActorCriticDuelRecurrent':
            skip = params['skip']
            state_size = params['state_size']
            return ActorCriticRecurrentAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'CuriosityQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return CuriosityQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'RecurrentCuriosityQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return RecurrentCuriosityQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'DuelCuriosityQLearning':
            skip = params['skip']
            state_size = params['state_size']
            return DuelCuriosityQLearningAgent(initial_money, window_size, trend, state_size, skip)
        elif agent_name == 'NeuroEvolution':
            skip = params['skip']
            state_size = params['state_size']
            population_size = params['population_size']
            mutation_rate = params['mutation_rate']
            return NeuroEvolutionAgent(initial_money, window_size, trend, state_size, skip, 
                                     population_size, mutation_rate, neuralnetwork)
        elif agent_name == 'NeuroEvolutionNoveltySearch':
            skip = params['skip']
            state_size = params['state_size']
            population_size = params['population_size']
            mutation_rate = params['mutation_rate']
            return NeuroEvolutionNoveltySearchAgent(initial_money, window_size, trend, state_size, skip,
                                                  population_size, mutation_rate, neuralnetwork1)
        else:
            raise EntityNotFoundException("ML Agent", agent_name)
    
    def get_supported_ml_agents(self) -> List[str]:
        return [
            'Gradient', 'QLearning', 'DeepEvolutionStrategy', 'DoubleQLearning',
            'RecurrentQLearning', 'DoubleRecurrentQLearning', 'DualQLearning',
            'DoubleDualQLearning', 'DualRecurrentQLearning', 'DoubleDualRecurrentQLearning',
            'ActorCritic', 'ActorCriticDuel', 'ActorCriticRecurrent', 'ActorCriticDuelRecurrent',
            'CuriosityQLearning', 'RecurrentCuriosityQLearning', 'DuelCuriosityQLearning',
            'NeuroEvolution', 'NeuroEvolutionNoveltySearch'
        ]