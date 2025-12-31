import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class CuriosityModel(nn.Module):
    def __init__(self, state_size, layer_size):
        super(CuriosityModel, self).__init__()
        self.layer_size = layer_size
        self.lstm = nn.LSTM(state_size + 1, layer_size, batch_first=True)
        self.fc = nn.Linear(layer_size, state_size)
        
    def forward(self, states, actions, hidden=None):
        batch_size, seq_len, _ = states.size()
        actions = actions.unsqueeze(-1).unsqueeze(-1).expand(-1, seq_len, 1)
        state_action = torch.cat([states, actions], dim=-1)
        
        if hidden is None:
            hidden = (torch.zeros(1, batch_size, self.layer_size).to(states.device),
                     torch.zeros(1, batch_size, self.layer_size).to(states.device))
        
        lstm_out, _ = self.lstm(state_action, hidden)
        prediction = self.fc(lstm_out[:, -1, :])
        return prediction


class RecurrentQModel(nn.Module):
    def __init__(self, state_size, output_size, layer_size):
        super(RecurrentQModel, self).__init__()
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


class RecurrentCuriosityQLearningAgent(MLAgent):
    LEARNING_RATE = 0.003
    BATCH_SIZE = 32
    LAYER_SIZE = 128
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
        super(RecurrentCuriosityQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.skip = skip
        self.INITIAL_FEATURES = np.zeros((4, self.state_size))
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models
        self.curiosity_model = CuriosityModel(self.state_size, self.LAYER_SIZE).to(self.device)
        self.eval_net = RecurrentQModel(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.target_net = RecurrentQModel(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        
        # Initialize optimizers
        self.curiosity_optimizer = optim.RMSprop(self.curiosity_model.parameters(), lr=self.LEARNING_RATE)
        self.q_optimizer = optim.RMSprop(self.eval_net.parameters(), lr=self.LEARNING_RATE)
        
        # Loss functions
        self.mse_loss = nn.MSELoss(reduction='none')
        self.mse_loss_mean = nn.MSELoss()
        
        # Copy eval_net parameters to target_net
        self.target_net.load_state_dict(self.eval_net.state_dict())
        
        self.hidden_state = None
    
    def _compute_q_loss(self, states, actions, rewards, new_states):
        """Compute Q-learning loss with curiosity-driven intrinsic rewards"""
        batch_size = states.size(0)
        
        # Get current Q-values
        current_q_values, _ = self.eval_net(states)
        current_q_values = current_q_values.gather(1, actions.unsqueeze(1))
        
        # Get next Q-values from target network
        with torch.no_grad():
            next_q_values, _ = self.target_net(new_states)
            max_next_q_values = next_q_values.max(1)[0]
            
            # Compute intrinsic curiosity rewards
            intrinsic_rewards = self._compute_intrinsic_rewards(states, actions, new_states)
            
            # Combine extrinsic and intrinsic rewards
            total_rewards = rewards + 0.1 * intrinsic_rewards  # Scale intrinsic rewards
            
            # Compute target Q-values
            target_q_values = total_rewards + self.GAMMA * max_next_q_values
        
        # Compute loss
        loss = self.mse_loss_mean(current_q_values.squeeze(), target_q_values)
        return loss
    
    def _compute_curiosity_loss(self, states, actions, new_states):
        """Compute curiosity model loss - forward model prediction error"""
        # Predict next states using curiosity model
        predicted_states = self.curiosity_model(states, actions)
        
        # Use only the next state (last timestep) for loss calculation
        target_states = new_states[:, -1, :]  # Get last timestep
        
        # Compute forward model loss
        loss = self.mse_loss_mean(predicted_states, target_states)
        return loss
    
    def _compute_intrinsic_rewards(self, states, actions, new_states):
        """Compute intrinsic curiosity rewards based on prediction error"""
        with torch.no_grad():
            # Predict next states
            predicted_states = self.curiosity_model(states, actions)
            
            # Get actual next states (last timestep)
            actual_states = new_states[:, -1, :]
            
            # Compute prediction error as intrinsic reward
            prediction_errors = self.mse_loss(predicted_states, actual_states)
            intrinsic_rewards = torch.mean(prediction_errors, dim=1)  # Average over state dimension
            
        return intrinsic_rewards
    def _memorize(self, state, action, reward, new_state, done, rnn_state):
        self.MEMORIES.append((state, action, reward, new_state, done, rnn_state))
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

    def _construct_memories(self, replay):
        states = np.array([a[0] for a in replay])
        actions = np.array([a[1] for a in replay])
        rewards = np.array([a[2] for a in replay])
        new_states = np.array([a[3] for a in replay])
        init_values = np.array([a[-1] for a in replay])
        
        # Convert to PyTorch tensors
        states_tensor = torch.FloatTensor(states).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        rewards_tensor = torch.FloatTensor(rewards).to(self.device)
        new_states_tensor = torch.FloatTensor(new_states).to(self.device)
        
        # Update target network if needed
        if (self.T_COPY + 1) % self.COPY == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())
        
        # Compute Q-learning loss
        q_loss = self._compute_q_loss(states_tensor, actions_tensor, rewards_tensor, new_states_tensor)
        
        # Optimize Q-network
        self.q_optimizer.zero_grad()
        q_loss.backward()
        self.q_optimizer.step()
        
        # Compute and optimize curiosity loss
        curiosity_loss = self._compute_curiosity_loss(states_tensor, actions_tensor, new_states_tensor)
        
        if (self.T_COPY + 1) % self.COPY == 0:
            self.curiosity_optimizer.zero_grad()
            curiosity_loss.backward()
            self.curiosity_optimizer.step()
        
        return q_loss.item()

    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []
        self.inventory = []
        state = self.get_state(0)
        for k in range(self.INITIAL_FEATURES.shape[0]):
            self.INITIAL_FEATURES[k,:] = state
        
        # Initialize hidden state for LSTM
        hidden_state = None
        
        for t in range(0, len(self.trend) - 1, self.skip):
            if np.random.rand() < self.EPSILON:
                action = np.random.randint(self.OUTPUT_SIZE)
            else:
                with torch.no_grad():
                    state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
                    q_values, hidden_state = self.eval_net(state_tensor, hidden_state)
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
            for k in range(self.INITIAL_FEATURES.shape[0]):
                self.INITIAL_FEATURES[k,:] = state
            
            # Initialize hidden state for LSTM
            hidden_state = None
            cost = 0
            
            for t in range(0, len(self.trend) - 1, self.skip):
                if np.random.rand() < self.EPSILON:
                    action = np.random.randint(self.OUTPUT_SIZE)
                else:
                    with torch.no_grad():
                        state_tensor = torch.FloatTensor([self.INITIAL_FEATURES]).to(self.device)
                        q_values, hidden_state = self.eval_net(state_tensor, hidden_state)
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
                
                # Train the model if we have enough memories
                if len(self.MEMORIES) >= self.BATCH_SIZE:
                    batch_size = min(len(self.MEMORIES), self.BATCH_SIZE)
                    replay = random.sample(self.MEMORIES, batch_size)
                    cost = self._construct_memories(replay)
                    self.T_COPY += 1
                    
            # Update epsilon for exploration
            self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
            
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost,
                                                                                  starting_money))
