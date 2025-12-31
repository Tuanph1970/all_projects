import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class Actor(nn.Module):
    def __init__(self, input_size, output_size, hidden_size):
        super(Actor, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)


class Critic(nn.Module):
    def __init__(self, input_size, output_size, hidden_size):
        super(Critic, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size + output_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, 1)
    
    def forward(self, state, action):
        x = F.relu(self.fc1(state))
        x = torch.cat([x, action], dim=1)
        x = F.relu(self.fc2(x))
        return self.fc3(x)


class ActorCriticAgent(MLAgent):
    LEARNING_RATE = 0.001
    BATCH_SIZE = 32
    LAYER_SIZE = 256
    OUTPUT_SIZE = 3
    EPSILON = 0.5
    DECAY_RATE = 0.005
    MIN_EPSILON = 0.1
    GAMMA = 0.99
    MEMORY_SIZE = 300
    COPY = 1000
    T_COPY = 0
    
    def __init__(self, initial_money, window_size, trend, state_size, skip):
        super(ActorCriticAgent, self).__init__(initial_money, window_size, trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.skip = skip
        self.MEMORIES = deque()
        
        # PyTorch setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Networks
        self.actor = Actor(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.actor_target = Actor(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.critic = Critic(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.critic_target = Critic(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        
        # Copy weights to target networks
        self.actor_target.load_state_dict(self.actor.state_dict())
        self.critic_target.load_state_dict(self.critic.state_dict())
        
        # Optimizers
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=self.LEARNING_RATE)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=self.LEARNING_RATE)
        
        # Loss function
        self.criterion = nn.MSELoss()
    
    def _assign(self, from_net, to_net):
        """Copy weights from one network to another"""
        to_net.load_state_dict(from_net.state_dict())
    
    def _memorize(self, state, action, reward, new_state, dead):
        self.MEMORIES.append((state, action, reward, new_state, dead))
        if len(self.MEMORIES) > self.MEMORY_SIZE:
            self.MEMORIES.popleft()
    
    def _select_action(self, state):
        if np.random.rand() < self.EPSILON:
            action = np.random.randint(self.OUTPUT_SIZE)
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                prediction = self.actor(state_tensor)
                action = prediction.argmax().item()
        return action
    
    def _construct_memories_and_train(self, replay):
        states = torch.FloatTensor([a[0] for a in replay]).to(self.device)
        actions = torch.LongTensor([a[1] for a in replay]).to(self.device)
        rewards = torch.FloatTensor([a[2] for a in replay]).to(self.device)
        next_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        dones = torch.BoolTensor([a[4] for a in replay]).to(self.device)
        
        # Convert actions to one-hot for critic
        actions_one_hot = F.one_hot(actions, num_classes=self.OUTPUT_SIZE).float()
        
        # Critic update
        with torch.no_grad():
            next_actions = self.actor_target(next_states)
            next_q_values = self.critic_target(next_states, next_actions).squeeze()
            target_q_values = rewards + (self.GAMMA * next_q_values * ~dones)
        
        current_q_values = self.critic(states, actions_one_hot).squeeze()
        critic_loss = self.criterion(current_q_values, target_q_values)
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        # Actor update
        predicted_actions = self.actor(states)
        actor_loss = -self.critic(states, predicted_actions).mean()
        
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()
        
        return critic_loss.item()
    
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
        inventory = []
        
        state = self.get_state(0)
        for t in range(0, len(self.trend) - 1, self.skip):
            action = self._select_action(state)
            next_state = self.get_state(t + 1)
            
            if action == 1 and self.initial_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
                inventory.append(self.trend[t])
                self.initial_money -= self.trend[t]
                states_buy.append(t)
                self.exchange_history.append('day %d: buy 1 unit at price %f, total balance %f' % (t, self.trend[t], self.initial_money))
            
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
                
                if action == 1 and starting_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]
                
                elif action == 2 and len(inventory) > 0:
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]
                
                invest = ((starting_money - self.initial_money) / self.initial_money)
                self._memorize(state, action, invest, next_state, starting_money < self.initial_money)
                state = next_state
                
                if len(self.MEMORIES) > self.BATCH_SIZE:
                    replay = random.sample(list(self.MEMORIES), self.BATCH_SIZE)
                    cost = self._construct_memories_and_train(replay)
            
            if self.EPSILON > self.MIN_EPSILON:
                self.EPSILON -= self.DECAY_RATE
            
            self.T_COPY += 1
            if self.T_COPY % self.COPY == 0:
                self._assign(self.actor, self.actor_target)
                self._assign(self.critic, self.critic_target)
            
            if (i + 1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, total money: %f' % (i + 1, total_profit, starting_money))
                print('epoch: %d, total rewards: %f.3, total money: %f' % (i + 1, total_profit, starting_money))