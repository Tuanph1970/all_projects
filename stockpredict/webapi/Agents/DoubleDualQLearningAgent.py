import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class Model(nn.Module):
    def __init__(self, input_size, output_size, layer_size):
        super(Model, self).__init__()
        self.fc1 = nn.Linear(input_size, layer_size)
        self.fc_action = nn.Linear(layer_size // 2, output_size)
        self.fc_value = nn.Linear(layer_size // 2, 1)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        action_part, value_part = torch.split(x, x.size(1) // 2, dim=1)
        action_values = self.fc_action(action_part)
        state_value = self.fc_value(value_part)
        q_values = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        return q_values
class DoubleDualQLearningAgent(MLAgent):
    LEARNING_RATE = 0.003
    BATCH_SIZE = 32
    LAYER_SIZE = 500
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
        super(DoubleDualQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.half_window = window_size // 2
        self.state_size = state_size
        self.skip = skip
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.model_negative = Model(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.LEARNING_RATE)
        self.criterion = nn.MSELoss()
    def _assign(self):
        self.model_negative.load_state_dict(self.model.state_dict())

    def _memorize(self, state, action, reward, new_state, done):
        self.MEMORIES.append((state, action, reward, new_state, done))
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
            Q = self.model(states)
            Q_new = self.model(new_states)
            Q_new_negative = self.model_negative(new_states)
        
        targets = Q.clone()
        for i, (state_r, action_r, reward_r, new_state_r, done_r) in enumerate(replay):
            targets[i][action_r] = reward_r
            if not done_r:
                best_action = Q_new[i].argmax()
                targets[i][action_r] += self.GAMMA * Q_new_negative[i][best_action]
        
        return states, targets

    def predict(self, inputs):
        inputs_tensor = torch.FloatTensor(inputs).to(self.device)
        with torch.no_grad():
            return self.model(inputs_tensor)

    def get_predicted_action(self, sequence):
        prediction = self.predict(np.array(sequence))[0]
        return prediction.argmax().item()

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
        for t in range(0, len(self.trend) - 1, self.skip):
            action = self._select_action(state)
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
                if (self.T_COPY + 1) % self.COPY == 0:
                    self._assign()

                action = self._select_action(state)
                next_state = self.get_state(t + 1)

                if action == 1 and starting_money >= self.trend[t]:
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]

                elif action == 2 and len(inventory) > 0:
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]

                invest = ((starting_money - self.initial_money) / self.initial_money)

                self._memorize(state, action, invest, next_state, starting_money < self.initial_money)
                batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                state = next_state
                replay = random.sample(self.MEMORIES, batch_size)
                states, targets = self._construct_memories(replay)

                self.optimizer.zero_grad()
                predictions = self.model(states)
                loss = self.criterion(predictions, targets)
                loss.backward()
                self.optimizer.step()
                self.T_COPY += 1
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, loss.item(),
                                                                                  starting_money))



