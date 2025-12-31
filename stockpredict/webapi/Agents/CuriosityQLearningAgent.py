import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class CuriosityNetwork(nn.Module):
    def __init__(self, state_size, action_size, hidden_size=32):
        super(CuriosityNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size + 1, hidden_size)  # +1 for action
        self.fc2 = nn.Linear(hidden_size, state_size)
    
    def forward(self, state, action):
        # Combine state and action
        action = action.unsqueeze(1) if action.dim() == 1 else action
        x = torch.cat([state, action], dim=1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)


class QNetwork(nn.Module):
    def __init__(self, state_size, action_size, hidden_size=128):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, action_size)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)


class CuriosityQLearningAgent(MLAgent):
    LEARNING_RATE = 0.003
    BATCH_SIZE = 32
    LAYER_SIZE = 500
    OUTPUT_SIZE = 3
    EPSILON = 0.5
    DECAY_RATE = 0.005
    MIN_EPSILON = 0.1
    GAMMA = 0.99
    COPY = 1000
    T_COPY = 0
    MEMORY_SIZE = 300
    
    def __init__(self, initial_money, window_size, trend, state_size, skip):
        super(CuriosityQLearningAgent, self).__init__(initial_money, window_size, trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.skip = skip
        self.MEMORIES = deque()
        
        # PyTorch setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Networks
        self.curiosity_net = CuriosityNetwork(self.state_size, self.OUTPUT_SIZE).to(self.device)
        self.q_network = QNetwork(self.state_size, self.OUTPUT_SIZE, 128).to(self.device)
        self.q_network_target = QNetwork(self.state_size, self.OUTPUT_SIZE, 128).to(self.device)
        
        # Copy weights to target network
        self.q_network_target.load_state_dict(self.q_network.state_dict())
        
        # Optimizers
        self.curiosity_optimizer = optim.RMSprop(self.curiosity_net.parameters(), lr=self.LEARNING_RATE)
        self.q_optimizer = optim.RMSprop(self.q_network.parameters(), lr=self.LEARNING_RATE)
        
        # Loss functions
        self.criterion = nn.MSELoss()
    
    def _assign(self):
        """Copy weights from main network to target network"""
        self.q_network_target.load_state_dict(self.q_network.state_dict())
    
    def _memorize(self, state, action, reward, new_state, done):
        self.MEMORIES.append((state, action, reward, new_state, done))
        if len(self.MEMORIES) > self.MEMORY_SIZE:
            self.MEMORIES.popleft()
    
    def get_state(self, t):
        window_size = self.window_size + 1
        d = t - window_size + 1
        block = self.trend[d : t + 1] if d >= 0 else -d * [self.trend[0]] + self.trend[0 : t + 1]
        res = []
        for i in range(window_size - 1):
            res.append(block[i + 1] - block[i])
        return np.array(res)
    
    def predict(self, inputs):
        with torch.no_grad():
            inputs_tensor = torch.FloatTensor(inputs).to(self.device)
            return self.q_network(inputs_tensor).cpu().numpy()
    
    def get_predicted_action(self, sequence):
        prediction = self.predict(np.array(sequence))[0]
        return np.argmax(prediction)
    
    def _select_action(self, state):
        if np.random.rand() < self.EPSILON:
            action = np.random.randint(self.OUTPUT_SIZE)
        else:
            action = self.get_predicted_action([state])
        return action
    
    def _construct_memories(self, replay):
        states = torch.FloatTensor([a[0] for a in replay]).to(self.device)
        actions = torch.LongTensor([a[1] for a in replay]).to(self.device)
        rewards = torch.FloatTensor([a[2] for a in replay]).to(self.device)
        next_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        dones = torch.BoolTensor([a[4] for a in replay]).to(self.device)
        
        # Update target network periodically
        if (self.T_COPY + 1) % self.COPY == 0:
            self._assign()
        
        # Curiosity-driven intrinsic reward
        predicted_next_states = self.curiosity_net(states, actions.float())
        curiosity_rewards = torch.sum((next_states - predicted_next_states) ** 2, dim=1)
        
        # Total reward = extrinsic + intrinsic (curiosity)
        total_rewards = rewards + curiosity_rewards
        
        # Q-learning update
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        with torch.no_grad():
            next_q_values = self.q_network_target(next_states).max(1)[0]
            target_q_values = total_rewards + (self.GAMMA * next_q_values * ~dones)
        
        q_loss = self.criterion(current_q_values.squeeze(), target_q_values)
        
        # Update Q-network
        self.q_optimizer.zero_grad()
        q_loss.backward()
        self.q_optimizer.step()
        
        # Update curiosity network periodically
        if (self.T_COPY + 1) % self.COPY == 0:
            curiosity_loss = torch.mean(curiosity_rewards)
            self.curiosity_optimizer.zero_grad()
            curiosity_loss.backward()
            self.curiosity_optimizer.step()
        
        return q_loss.item()
    
    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []
        inventory = []
        state = self.get_state(0)
        
        for t in range(0, len(self.trend) - 1, self.skip):
            action = self._select_action(state)
            next_state = self.get_state(t + 1)

            if action == 1 and self.initial_money >= self.trend[t]:
                inventory.append(self.trend[t])
                self.initial_money -= self.trend[t]
                states_buy.append(t)
                self.exchange_history.append('day %d: buy 1 unit at price %f, total balance %f'% (t, self.trend[t], self.initial_money))

            elif action == 2 and len(inventory):
                bought_price = inventory.pop(0)
                self.initial_money += self.trend[t]
                states_sell.append(t)
                try:
                    invest = ((self.trend[t] - bought_price) / bought_price) * 100
                except:
                    invest = 0
                self.exchange_history.append(
                    'day %d, sell 1 unit at price %f, investment %f %%, total balance %f,'
                    % (t, self.trend[t], invest, self.initial_money)
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
                
                if len(self.MEMORIES) >= self.BATCH_SIZE:
                    batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                    replay = random.sample(list(self.MEMORIES), batch_size)
                    cost = self._construct_memories(replay)
                
                state = next_state
                self.T_COPY += 1
                
            if self.EPSILON > self.MIN_EPSILON:
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
                
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost, starting_money))
                print('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost, starting_money))