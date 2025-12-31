import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class Model(nn.Module):
    def __init__(self, input_size, output_size, layer_size, learning_rate, name, device):
        super(Model, self).__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.layer_size = layer_size
        self.name = name
        self.device = device
        
        # LSTM layer
        self.lstm = nn.LSTM(input_size, layer_size, batch_first=True)
        
        # Dueling network layers
        self.action_layer = nn.Linear(layer_size // 2, output_size)
        self.value_layer = nn.Linear(layer_size // 2, 1)
        
        # Optimizer and loss
        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
        self.to(device)
    
    def forward(self, x, hidden=None):
        batch_size = x.size(0)
        if hidden is None:
            hidden = self.init_hidden(batch_size)
        
        lstm_out, hidden_out = self.lstm(x, hidden)
        # Take the last output
        last_output = lstm_out[:, -1, :]
        
        # Split for dueling architecture
        tensor_action = last_output[:, :self.layer_size // 2]
        tensor_validation = last_output[:, self.layer_size // 2:]
        
        # Dueling network computation
        action_values = self.action_layer(tensor_action)
        state_value = self.value_layer(tensor_validation)
        
        # Combine action and value
        q_values = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        
        return q_values, hidden_out
    
    def init_hidden(self, batch_size):
        h0 = torch.zeros(1, batch_size, self.layer_size).to(self.device)
        c0 = torch.zeros(1, batch_size, self.layer_size).to(self.device)
        return (h0, c0)
class DoubleDualRecurrentQLearningAgent(MLAgent):
    LEARNING_RATE = 0.003
    BATCH_SIZE = 32
    LAYER_SIZE = 256
    OUTPUT_SIZE = 3
    EPSILON = 0.5
    DECAY_RATE = 0.005
    MIN_EPSILON = 0.1
    GAMMA = 0.99
    MEMORIES = deque()
    COPY = 1000
    T_COPY = 0
    MEMORY_SIZE = 300
    def __init__(self,initial_money,window_size,trend,state_size,skip):
        super(DoubleDualRecurrentQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.skip = skip
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.INITIAL_FEATURES = np.zeros((4, self.state_size))
        self.model = Model(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE, self.LEARNING_RATE,
                           'real_model', self.device)
        self.model_negative = Model(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE, self.LEARNING_RATE,
                                    'negative_model', self.device)
    def _assign(self, from_model, to_model):
        to_model.load_state_dict(from_model.state_dict())

    def _memorize(self, state, action, reward, new_state, dead, rnn_state):
        self.MEMORIES.append((state, action, reward, new_state, dead, rnn_state))
        if len(self.MEMORIES) > self.MEMORY_SIZE:
            self.MEMORIES.popleft()

    def _select_action(self, state):
        if np.random.rand() < self.EPSILON:
            action = np.random.randint(self.OUTPUT_SIZE)
        else:
            action = self.get_predicted_action([state])
        return action

    def _construct_memories(self, replay):
        states = torch.FloatTensor([a[0] for a in replay]).to(self.device)
        new_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        
        with torch.no_grad():
            Q, _ = self.model(states)
            Q_new, _ = self.model(new_states)
            Q_new_negative, _ = self.model_negative(new_states)
        
        replay_size = len(replay)
        X = torch.empty((replay_size, 4, self.state_size)).to(self.device)
        Y = torch.empty((replay_size, self.OUTPUT_SIZE)).to(self.device)
        
        for i in range(replay_size):
            state_r, action_r, reward_r, new_state_r, dead_r, rnn_memory = replay[i]
            target = Q[i].clone()
            target[action_r] = reward_r
            if not dead_r:
                target[action_r] += self.GAMMA * Q_new_negative[i, torch.argmax(Q_new[i])]
            X[i] = torch.FloatTensor(state_r)
            Y[i] = target
        
        return X, Y

    def get_state(self, t):
        window_size = self.window_size + 1
        d = t - window_size + 1
        block = self.trend[d : t + 1] if d >= 0 else -d * [self.trend[0]] + self.trend[0 : t + 1]
        res = []
        for i in range(window_size - 1):
            res.append(block[i + 1] - block[i])
        return np.array(res)

    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []
        self.inventory = []
        state = self.get_state(0)
        init_value = np.zeros((1, 2 * self.LAYER_SIZE))
        for k in range(self.INITIAL_FEATURES.shape[0]):
            self.INITIAL_FEATURES[k,:] = state
        for t in range(0, len(self.trend) - 1, self.skip):
            with torch.no_grad():
                state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
                q_values, hidden_state = self.model(state_tensor)
                action = torch.argmax(q_values[0]).item()
            next_state = self.get_state(t + 1)

            if action == 1 and self.initial_money >= self.trend[t]:
                self.inventory.append(self.trend[t])
                self.initial_money -= self.trend[t]
                states_buy.append(t)
                self.exchange_history.append('day %d: buy 1 unit at price %f, total balance %f'% (t, self.trend[t], self.initial_money))

            elif action == 2 and len(self.inventory):
                bought_price = self.inventory.pop(0)
                self.initial_money += self.trend[t]
                states_sell.append(t)
                try:
                    invest = ((self.close[t] - bought_price) / bought_price) * 100
                except:
                    invest = 0
                self.exchange_history.append(
                    'day %d, sell 1 unit at price %f, investment %f %%, total balance %f,'
                    % (t, self.close[t], invest, self.initial_money)
                )

            new_state = np.append([self.get_state(t + 1)], self.INITIAL_FEATURES[:3, :], axis = 0)
            self.INITIAL_FEATURES = new_state
        invest = ((self.initial_money - starting_money) / starting_money) * 100
        total_gains = self.initial_money - starting_money
        return states_buy, states_sell, total_gains, invest


    def train(self, iterations, checkpoint):
        for i in range(iterations):
            total_profit = 0
            inventory = []
            state = self.get_state(0)
            starting_money = self.initial_money
            init_value = np.zeros((1, 2 * self.LAYER_SIZE))
            for k in range(self.INITIAL_FEATURES.shape[0]):
                self.INITIAL_FEATURES[k,:] = state
            for t in range(0, len(self.trend) - 1, self.skip):
                if (self.T_COPY + 1) % self.COPY == 0:
                    self._assign(self.model, self.model_negative)

                if np.random.rand() < self.EPSILON:
                    action = np.random.randint(self.OUTPUT_SIZE)
                else:
                    with torch.no_grad():
                        state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
                        q_values, hidden_state = self.model(state_tensor)
                        action = torch.argmax(q_values[0]).item()

                next_state = self.get_state(t + 1)

                if action == 1 and starting_money >= self.trend[t]:
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]

                elif action == 2 and len(inventory) > 0:
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]

                invest = ((starting_money - self.initial_money) / self.initial_money)
                new_state = np.append([self.get_state(t + 1)], self.INITIAL_FEATURES[:3, :], axis = 0)

                self._memorize(self.INITIAL_FEATURES, action, invest, new_state,
                               starting_money < self.initial_money, np.zeros(2 * self.LAYER_SIZE))
                self.INITIAL_FEATURES = new_state
                batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                replay = random.sample(self.MEMORIES, batch_size)
                X, Y = self._construct_memories(replay)

                self.model.optimizer.zero_grad()
                q_values, _ = self.model(X)
                loss = self.model.criterion(q_values, Y)
                loss.backward()
                self.model.optimizer.step()
                cost = loss.item()
                self.T_COPY += 1
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost,
                                                                                  starting_money))


