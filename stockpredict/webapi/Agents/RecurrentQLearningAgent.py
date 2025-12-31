import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from Agents.Agent import MLAgent
from collections import deque
import random


class RecurrentQNetwork(nn.Module):
    def __init__(self, state_size, output_size, layer_size):
        super(RecurrentQNetwork, self).__init__()
        self.layer_size = layer_size
        self.lstm = nn.LSTM(state_size, layer_size, batch_first=True)
        self.fc = nn.Linear(layer_size, output_size)
        
    def forward(self, x, hidden=None):
        if hidden is None:
            batch_size = x.size(0)
            hidden = (torch.zeros(1, batch_size, self.layer_size).to(x.device),
                     torch.zeros(1, batch_size, self.layer_size).to(x.device))
        
        lstm_out, hidden = self.lstm(x, hidden)
        output = self.fc(lstm_out[:, -1, :])
        return output, hidden


class RecurrentQLearningAgent(MLAgent):
    LEARNING_RATE = 0.003
    BATCH_SIZE = 32
    LAYER_SIZE = 256
    OUTPUT_SIZE = 3
    EPSILON = 0.5
    DECAY_RATE = 0.005
    MIN_EPSILON = 0.1
    GAMMA = 0.99
    MEMORIES = deque()
    MEMORY_SIZE = 300
    def __init__(self,initial_money,window_size, trend,state_size,skip):
        super(RecurrentQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.state_size = state_size
        self.skip = skip
        self.INITIAL_FEATURES = np.zeros((4, self.state_size))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = RecurrentQNetwork(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=self.LEARNING_RATE)
        self.criterion = nn.MSELoss()
        self.hidden_state = None

    def _memorize(self, state, action, reward, new_state, dead, rnn_state):
        self.MEMORIES.append((state, action, reward, new_state, dead, rnn_state))
        if len(self.MEMORIES) > self.MEMORY_SIZE:
            self.MEMORIES.popleft()

    def _construct_memories(self, replay):
        states = torch.FloatTensor([a[0] for a in replay]).to(self.device)
        new_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        
        with torch.no_grad():
            Q, _ = self.q_network(states)
            Q_new, _ = self.q_network(new_states)
        
        targets = Q.clone()
        for i, (state_r, action_r, reward_r, new_state_r, dead_r, rnn_memory) in enumerate(replay):
            targets[i][action_r] = reward_r
            if not dead_r:
                targets[i][action_r] += self.GAMMA * Q_new[i].max()
        
        return states, targets

    def get_state(self, t):
        window_size = self.window_size + 1
        d = t - window_size + 1
        block = self.trend[d: t + 1] if d >= 0 else -d * [self.trend[0]] + self.trend[0: t + 1]
        res = []
        for i in range(window_size - 1):
            res.append(block[i + 1] - block[i])
        return np.array(res)

    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []

        state = self.get_state(0)
        self.hidden_state = None
        for k in range(self.INITIAL_FEATURES.shape[0]):
            self.INITIAL_FEATURES[k, :] = state
        for t in range(0, len(self.trend) - 1, self.skip):
            state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
            with torch.no_grad():
                action_values, self.hidden_state = self.q_network(state_tensor, self.hidden_state)
            action = action_values.argmax().item()
            next_state = self.get_state(t + 1)

            if action == 1 and self.initial_money >= self.trend[t]:
                self.inventory.append(self.trend[t])
                self.initial_money -= self.trend[t]
                states_buy.append(t)
                self.exchange_history.append('day %d: buy 1 unit at price %f, total balance %f' % (t, self.trend[t], self.initial_money))

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

            new_state = np.append([self.get_state(t + 1)], self.INITIAL_FEATURES[:3, :], axis=0)
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
            self.hidden_state = None
            for k in range(self.INITIAL_FEATURES.shape[0]):
                self.INITIAL_FEATURES[k, :] = state
            for t in range(0, len(self.trend) - 1, self.skip):

                if np.random.rand() < self.EPSILON:
                    action = np.random.randint(self.OUTPUT_SIZE)
                else:
                    state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
                    with torch.no_grad():
                        action_values, self.hidden_state = self.q_network(state_tensor, self.hidden_state)
                    action = action_values.argmax().item()

                next_state = self.get_state(t + 1)

                if action == 1 and starting_money >= self.trend[t]:
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]

                elif action == 2 and len(inventory) > 0:
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]

                invest = ((starting_money - self.initial_money) / self.initial_money)
                new_state = np.append([self.get_state(t + 1)], self.INITIAL_FEATURES[:3, :], axis=0)
                self._memorize(self.INITIAL_FEATURES, action, invest, new_state,
                               starting_money < self.initial_money, None)
                self.INITIAL_FEATURES = new_state
                batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                replay = random.sample(self.MEMORIES, batch_size)
                states, targets = self._construct_memories(replay)

                self.optimizer.zero_grad()
                predictions, _ = self.q_network(states)
                loss = self.criterion(predictions, targets)
                loss.backward()
                self.optimizer.step()
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)

            if (i + 1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f' % (i + 1, total_profit, loss.item(),
                                                                                     starting_money))


