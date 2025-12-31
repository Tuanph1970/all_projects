from Agents.Agent import MLAgent
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np


class PolicyNetwork(nn.Module):
    def __init__(self, state_size, output_size, hidden_size):
        super(PolicyNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        return F.softmax(self.fc2(x), dim=-1)


class GradientAgent(MLAgent):
    LEARNING_RATE = 1e-4
    LAYER_SIZE = 256
    GAMMA = 0.9
    OUTPUT_SIZE = 3
    
    def __init__(self, initial_money, window_size, trend, state_size, skip):
        super(GradientAgent, self).__init__(initial_money, window_size, trend)
        self.state_size = state_size
        self.half_window = self.window_size // 2
        self.skip = skip
        
        # PyTorch setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net = PolicyNetwork(self.state_size, self.OUTPUT_SIZE, self.LAYER_SIZE).to(self.device)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.LEARNING_RATE)
    
    def predict(self, inputs):
        with torch.no_grad():
            inputs_tensor = torch.FloatTensor(inputs).to(self.device)
            return self.policy_net(inputs_tensor).cpu().numpy()
    
    def get_state(self, t):
        window_size = self.window_size + 1
        d = t - window_size + 1
        block = self.trend[d: t + 1] if d >= 0 else -d * [self.trend[0]] + self.trend[0: t + 1]
        res = []
        for i in range(window_size - 1):
            res.append(block[i + 1] - block[i])
        return np.array([res])
    
    def discount_rewards(self, r):
        discounted_r = np.zeros_like(r)
        running_add = 0
        for t in reversed(range(0, r.size)):
            running_add = running_add * self.GAMMA + r[t]
            discounted_r[t] = running_add
        return discounted_r
    
    def get_predicted_action(self, sequence):
        prediction = self.predict(np.array(sequence))[0]
        return np.argmax(prediction)
    
    def train(self, iterations, checkpoint):
        for i in range(iterations):
            ep_history = []
            total_profit = 0
            inventory = []
            state = self.get_state(0)
            starting_money = self.initial_money
            
            for t in range(0, len(self.trend) - 1, self.skip):
                action = self.get_predicted_action(state)
                next_state = self.get_state(t + 1)
                
                if action == 1 and starting_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
                    inventory.append(self.trend[t])
                    starting_money -= self.trend[t]
                elif action == 2 and len(inventory):
                    bought_price = inventory.pop(0)
                    total_profit += self.trend[t] - bought_price
                    starting_money += self.trend[t]
                
                ep_history.append([state, action, starting_money, next_state])
                state = next_state
            
            # Convert to PyTorch tensors
            states = torch.FloatTensor([h[0][0] for h in ep_history]).to(self.device)
            actions = torch.LongTensor([h[1] for h in ep_history]).to(self.device)
            rewards = np.array([h[2] for h in ep_history])
            
            # Discount rewards
            discounted_rewards = self.discount_rewards(rewards)
            discounted_rewards = torch.FloatTensor(discounted_rewards).to(self.device)
            
            # Policy gradient update
            action_probs = self.policy_net(states)
            selected_action_probs = action_probs.gather(1, actions.unsqueeze(1)).squeeze()
            
            # Policy gradient loss (negative log likelihood weighted by rewards)
            loss = -torch.mean(torch.log(selected_action_probs + 1e-8) * (discounted_rewards + 1))
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            cost = loss.item()
            
            if (i + 1) % checkpoint == 0:
                self.train_history.append('epoch: %d, total rewards: %f.3, cost: %f, total money: %f' % (i + 1, total_profit, cost, starting_money))
                print('epoch: %d, total rewards: %f.3, cost: %f, total money: %f' % (i + 1, total_profit, cost, starting_money))
    
    def buy(self):
        starting_money = self.initial_money
        states_sell = []
        states_buy = []
        state = self.get_state(0)
        
        for t in range(0, len(self.trend) - 1, self.skip):
            action = self.get_predicted_action(state)
            next_state = self.get_state(t + 1)
            
            if action == 1 and self.initial_money >= self.trend[t] and t < (len(self.trend) - self.half_window):
                self.inventory.append(self.trend[t])
                self.initial_money -= self.trend[t]
                states_buy.append(t)
                self.exchange_history.append('day %d: buy 1 unit at price %f, total balance %f' % (t, self.trend[t], self.initial_money))
            
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
            
            state = next_state
        
        invest = ((self.initial_money - starting_money) / starting_money) * 100
        total_gains = self.initial_money - starting_money
        return states_buy, states_sell, total_gains, invest