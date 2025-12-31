import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random

from Agents.Agent import MLAgent


class CuriosityModel(nn.Module):
    def __init__(self, state_size, device):
        super(CuriosityModel, self).__init__()
        self.state_size = state_size
        self.device = device
        
        self.hidden = nn.Linear(state_size + 1, 32)
        self.output = nn.Linear(32, state_size)
        
        self.to(device)
    
    def forward(self, state, action):
        action = action.unsqueeze(1)
        state_action = torch.cat([state, action], dim=1)
        hidden = F.relu(self.hidden(state_action))
        predicted_state = self.output(hidden)
        return predicted_state

class DuelQModel(nn.Module):
    def __init__(self, state_size, output_size, device):
        super(DuelQModel, self).__init__()
        self.state_size = state_size
        self.output_size = output_size
        self.device = device
        
        self.shared = nn.Linear(state_size, 128)
        self.action_layer = nn.Linear(64, output_size)
        self.value_layer = nn.Linear(64, 1)
        
        self.to(device)
    
    def forward(self, x):
        shared = F.relu(self.shared(x))
        # Split for dueling architecture
        tensor_action = shared[:, :64]
        tensor_validation = shared[:, 64:]
        
        # Dueling network computation
        action_values = self.action_layer(tensor_action)
        state_value = self.value_layer(tensor_validation)
        
        # Combine action and value
        q_values = state_value + (action_values - action_values.mean(dim=1, keepdim=True))
        
        return q_values

class DuelCuriosityQLearningAgent(MLAgent):
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
        super(DuelCuriosityQLearningAgent, self).__init__(initial_money,window_size,trend)
        self.state_size = state_size
        self.half_window = window_size // 2
        self.skip = skip
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Create models
        self.curiosity_model = CuriosityModel(state_size, self.device)
        self.eval_net = DuelQModel(state_size, self.OUTPUT_SIZE, self.device)
        self.target_net = DuelQModel(state_size, self.OUTPUT_SIZE, self.device)
        
        # Copy eval_net to target_net initially
        self.target_net.load_state_dict(self.eval_net.state_dict())
        
        # Optimizers
        self.curiosity_optimizer = optim.RMSprop(self.curiosity_model.parameters(), lr=self.LEARNING_RATE)
        self.q_optimizer = optim.RMSprop(self.eval_net.parameters(), lr=self.LEARNING_RATE)
        
        # Loss functions
        self.mse_loss = nn.MSELoss()
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
            return self.eval_net(inputs_tensor).cpu().numpy()

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
        actions = torch.FloatTensor([a[1] for a in replay]).to(self.device)
        rewards = torch.FloatTensor([a[2] for a in replay]).to(self.device)
        new_states = torch.FloatTensor([a[3] for a in replay]).to(self.device)
        
        if (self.T_COPY + 1) % self.COPY == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())

        # Compute curiosity reward
        with torch.no_grad():
            predicted_states = self.curiosity_model(states, actions)
            curiosity_reward = torch.sum((new_states - predicted_states) ** 2, dim=1)
        
        # Compute total reward
        total_reward = curiosity_reward + rewards
        
        # Compute Q-learning loss
        with torch.no_grad():
            target_q_values = self.target_net(new_states)
            max_target_q = torch.max(target_q_values, dim=1)[0]
            q_target = total_reward + self.GAMMA * max_target_q
        
        current_q_values = self.eval_net(states)
        actions_int = actions.long()
        q_values = current_q_values.gather(1, actions_int.unsqueeze(1)).squeeze(1)
        
        # Update Q-network
        self.q_optimizer.zero_grad()
        q_loss = self.mse_loss(q_values, q_target)
        q_loss.backward()
        self.q_optimizer.step()
        
        # Update curiosity model
        if (self.T_COPY + 1) % self.COPY == 0:
            self.curiosity_optimizer.zero_grad()
            predicted_states = self.curiosity_model(states, actions)
            curiosity_loss = self.mse_loss(predicted_states, new_states)
            curiosity_loss.backward()
            self.curiosity_optimizer.step()
        
        return q_loss.item()

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
                cost = self._construct_memories(replay)
                self.T_COPY += 1
                self.EPSILON = self.MIN_EPSILON + (1.0 - self.MIN_EPSILON) * np.exp(-self.DECAY_RATE * i)
            if (i+1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f'%(i + 1, total_profit, cost,
                                                                                  starting_money))
