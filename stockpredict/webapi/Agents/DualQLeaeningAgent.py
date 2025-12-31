import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class DualQNetwork(nn.Module):
    def __init__(self, state_size, action_size):
        super(DualQNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, 512)
        self.fc_action = nn.Linear(256, action_size)
        self.fc_value = nn.Linear(256, 1)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        action_part, value_part = torch.split(x, 256, dim=1)
        action_values = self.fc_action(action_part)
        state_value = self.fc_value(value_part)
        q_values = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        return q_values


class DualQLearningAgent(MLAgent):
    def __init__(self,initial_money,window_size,trend,state_size,skip,batch_size):
        super(DualQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.state_size = state_size
        self.skip = skip
        self.batch_size = batch_size
        self.action_size = 3
        self.memory = deque(maxlen=1000)
        self.inventory = []

        self.gamma = 0.95
        self.epsilon = 0.5
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.999
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = DualQNetwork(self.state_size, self.action_size).to(self.device)
        self.optimizer = optim.SGD(self.q_network.parameters(), lr=1e-5)
        self.criterion = nn.MSELoss()
    def act(self, state):
        if random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        state_tensor = torch.FloatTensor(state).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
        return q_values.argmax().item()

    def get_state(self, t):
        window_size = self.window_size + 1
        d = t - window_size + 1
        block = self.trend[d : t + 1] if d >= 0 else -d * [self.trend[0]] + self.trend[0 : t + 1]
        res = []
        for i in range(window_size - 1):
            res.append(block[i + 1] - block[i])
        return np.array([res])

    def replay(self, batch_size):
        mini_batch = []
        l = len(self.memory)
        for i in range(l - batch_size, l):
            mini_batch.append(self.memory[i])
        
        states = torch.FloatTensor([a[0][0] for a in mini_batch]).to(self.device)
        new_states = torch.FloatTensor([a[3][0] for a in mini_batch]).to(self.device)
        
        with torch.no_grad():
            Q = self.q_network(states)
            Q_new = self.q_network(new_states)
        
        targets = Q.clone()
        for i, (state, action, reward, next_state, done) in enumerate(mini_batch):
            targets[i][action] = reward
            if not done:
                targets[i][action] += self.gamma * Q_new[i].max()
        
        self.optimizer.zero_grad()
        loss = self.criterion(Q, targets)
        loss.backward()
        self.optimizer.step()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        return loss.item()

    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []

        state = self.get_state(0)
        for t in range(0, len(self.trend) - 1, self.skip):
            action = self.act(state)
            next_state = self.get_state(t + 1)

            if action == 1 and self.initial_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
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

            state = next_state
        invest = ((self.initial_money - starting_money) / starting_money) * 100
        total_gains = self.initial_money - starting_money
        return states_buy, states_sell, total_gains, invest

    def train(self, iterations, checkpoint):
        for i in range(iterations):
            total_profit = 0
            inventory = []
            state = self.get_state(0)
            starting_money = self.initial_money
            for t in range(0, len(self.trend) - 1, self.skip):
                action = self.act(state)
                next_state = self.get_state(t + 1)

                if action == 1 and starting_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]

                elif action == 2 and len(inventory) > 0:
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]

                invest = ((starting_money - self.initial_money) / self.initial_money)
                self.memory.append((state, action, invest,
                                    next_state, starting_money < self.initial_money))
                state = next_state
                batch_size = min(self.batch_size, len(self.memory))
                cost = self.replay(batch_size)
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost,
                                                                                  starting_money))

