import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class Actor(nn.Module):
    def __init__(self, input_size, output_size, size_layer):
        super(Actor, self).__init__()
        self.size_layer = size_layer
        self.lstm = nn.LSTM(input_size, size_layer, batch_first=True)
        # Dueling architecture: split into action and value streams
        self.action_head = nn.Linear(size_layer // 2, output_size)
        self.value_head = nn.Linear(size_layer // 2, 1)
    
    def forward(self, x, hidden=None):
        # x shape: (batch_size, seq_len, input_size)
        rnn_out, hidden = self.lstm(x, hidden)
        # Take the last output from the sequence
        rnn_last = rnn_out[:, -1, :]
        
        # Split into action and value streams for dueling architecture
        action_stream = rnn_last[:, :self.size_layer // 2]
        value_stream = rnn_last[:, self.size_layer // 2:]
        
        action_values = self.action_head(action_stream)
        state_value = self.value_head(value_stream)
        
        # Dueling DQN combination: V(s) + (A(s,a) - mean(A(s,a)))
        logits = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        
        return logits, hidden

class Critic(nn.Module):
    def __init__(self, input_size, output_size, size_layer):
        super(Critic, self).__init__()
        self.size_layer = size_layer
        self.lstm = nn.LSTM(input_size, size_layer, batch_first=True)
        # Dueling architecture for critic as well
        self.action_head = nn.Linear(size_layer // 2, output_size)
        self.value_head = nn.Linear(size_layer // 2, 1)
        self.fc1 = nn.Linear(output_size + output_size, size_layer // 2)
        self.fc2 = nn.Linear(size_layer // 2, 1)
    
    def forward(self, x, action, hidden=None):
        # x shape: (batch_size, seq_len, input_size)
        rnn_out, hidden = self.lstm(x, hidden)
        rnn_last = rnn_out[:, -1, :]
        
        # Split into action and value streams
        action_stream = rnn_last[:, :self.size_layer // 2]
        value_stream = rnn_last[:, self.size_layer // 2:]
        
        action_values = self.action_head(action_stream)
        state_value = self.value_head(value_stream)
        
        # Dueling combination
        dueling_out = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        dueling_out = F.relu(dueling_out)
        
        # Combine with action input
        combined = torch.cat([dueling_out, action], dim=1)
        x = F.relu(self.fc1(combined))
        logits = self.fc2(x)
        
        return logits, hidden
class ActorCriticDuelRecurrentAgent(MLAgent):
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
        super(ActorCriticDuelRecurrentAgent, self).__init__(initial_money, window_size, trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.INITIAL_FEATURES = np.zeros((4, self.state_size))
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

    def _memorize(self, state, action, reward, new_state, dead, rnn_state):
        self.MEMORIES.append((state, action, reward, new_state, dead, rnn_state))
        if len(self.MEMORIES) > self.MEMORY_SIZE:
            self.MEMORIES.popleft()

    def _select_action(self, state, hidden=None):
        if np.random.rand() < self.EPSILON:
            action = np.random.randint(self.OUTPUT_SIZE)
            return action, hidden
        else:
            # Convert state to tensor and add batch dimension
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                prediction, new_hidden = self.actor(state_tensor, hidden)
                action = prediction.argmax().item()
            return action, new_hidden

    def _construct_memories_and_train(self, replay):
        states = torch.FloatTensor([a[0] for a in replay]).to(self.device)
        actions = torch.LongTensor([a[1] for a in replay]).to(self.device)
        rewards = torch.FloatTensor([a[2] for a in replay]).to(self.device)
        next_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        dones = torch.BoolTensor([a[4] for a in replay]).to(self.device)
        
        # Convert actions to one-hot for critic
        actions_one_hot = F.one_hot(actions, num_classes=self.OUTPUT_SIZE).float()
        
        # Actor forward pass
        actor_out, _ = self.actor(states)
        
        # Critic update
        with torch.no_grad():
            next_actions, _ = self.actor_target(next_states)
            next_q_values, _ = self.critic_target(next_states, next_actions)
            target_q_values = rewards.unsqueeze(1) + (self.GAMMA * next_q_values * ~dones.unsqueeze(1))
        
        current_q_values, _ = self.critic(states, actions_one_hot)
        critic_loss = self.criterion(current_q_values, target_q_values)
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        # Actor update
        predicted_actions, _ = self.actor(states)
        actor_loss, _ = self.critic(states, predicted_actions)
        actor_loss = -actor_loss.mean()
        
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()
        
        return critic_loss.item()

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
        hidden = None
        
        for k in range(self.INITIAL_FEATURES.shape[0]):
            self.INITIAL_FEATURES[k,:] = state
            
        for t in range(0, len(self.trend) - 1, self.skip):
            # Prepare state tensor for LSTM
            state_tensor = torch.FloatTensor(self.INITIAL_FEATURES).unsqueeze(0).to(self.device)
            action, hidden = self._select_action(state_tensor, hidden)

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
                    invest = ((self.trend[t] - bought_price) / bought_price) * 100
                except:
                    invest = 0
                self.exchange_history.append(
                    'day %d, sell 1 unit at price %f, investment %f %%, total balance %f,'
                    % (t, self.trend[t], invest, self.initial_money)
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
            hidden = None
            
            for k in range(self.INITIAL_FEATURES.shape[0]):
                self.INITIAL_FEATURES[k,:] = state
                
            for t in range(0, len(self.trend) - 1, self.skip):
                if (self.T_COPY + 1) % self.COPY == 0:
                    self._assign(self.actor, self.actor_target)
                    self._assign(self.critic, self.critic_target)

                # Prepare state tensor for LSTM
                state_tensor = torch.FloatTensor(self.INITIAL_FEATURES).unsqueeze(0).to(self.device)
                action, hidden = self._select_action(state_tensor, hidden)

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
                
                # Store hidden state as numpy array for memory
                hidden_state = None
                if hidden is not None:
                    hidden_state = (hidden[0].cpu().numpy(), hidden[1].cpu().numpy())
                
                self._memorize(self.INITIAL_FEATURES, action, invest, new_state,
                               starting_money < self.initial_money, hidden_state)
                
                if len(self.MEMORIES) >= self.BATCH_SIZE:
                    batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                    replay = random.sample(list(self.MEMORIES), batch_size)
                    cost = self._construct_memories_and_train(replay)
                
                self.INITIAL_FEATURES = new_state
                self.T_COPY += 1
                
            if self.EPSILON > self.MIN_EPSILON:
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
                
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost,
                                                                                  starting_money))
                print('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost, starting_money))




