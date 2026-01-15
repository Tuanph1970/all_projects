import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { useSelector } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Types removed for JavaScript
// import { RootState } from '../store/index.js';
import { UserRole } from '../types/auth.js';
import { ErrorBoundary } from '../components/common/ErrorBoundary.jsx';

// Customer Screens
import { HomeScreen } from '../screens/customer/HomeScreen.jsx';
import { SearchScreen } from '../screens/customer/SearchScreen.jsx';
import { CartScreen } from '../screens/customer/CartScreen.jsx';
import { ProfileScreen } from '../screens/customer/ProfileScreen.jsx';
import { OrderHistoryScreen } from '../screens/customer/OrderHistoryScreen.jsx';
import { CustomerOrderDetailsScreen } from '../screens/customer/CustomerOrderDetailsScreen.jsx';

// Seller Screens
import { SellerDashboardScreen } from '../screens/seller/SellerDashboardScreen.jsx';
import { ProductManagementScreen } from '../screens/seller/ProductManagementScreen.jsx';
import { OrderManagementScreen } from '../screens/seller/OrderManagementScreen.jsx';
import { OrderDetailsScreen } from '../screens/seller/OrderDetailsScreen.jsx';
import { AnalyticsScreen } from '../screens/seller/AnalyticsScreen.jsx';
import { AddProductScreen } from '../screens/seller/AddProductScreen.jsx';
import { ProductFormScreen } from '../screens/seller/ProductFormScreen.jsx';

// Common Screens
import { ChatListScreen } from '../screens/chat/ChatListScreen.jsx';
import { ChatScreen } from '../screens/chat/ChatScreen.jsx';
import { ProductDetailsScreen } from '../screens/product/ProductDetailsScreen.jsx';
import { ProductListScreen } from '../screens/customer/ProductListScreen.jsx';
import { CheckoutScreen } from '../screens/checkout/CheckoutScreen.jsx';
import { ChangePasswordScreen } from '../screens/auth/ChangePasswordScreen.jsx';



const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

const CustomerTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ color, size }) => {
          let iconName = '';

          switch (route.name) {
            case 'Home':
              iconName = 'home';
              break;
            case 'Search':
              iconName = 'search';
              break;
            case 'Cart':
              iconName = 'shopping-cart';
              break;
            case 'Chat':
              iconName = 'chat';
              break;
            case 'Profile':
              iconName = 'person';
              break;
            default:
              iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007bff',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
        tabBarTestID: `tab-${route.name.toLowerCase()}`,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Search" component={SearchScreen} />
      <Tab.Screen name="Cart" component={CartScreen} />
      <Tab.Screen name="Chat" component={ChatListScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
};

const SellerTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ color, size }) => {
          let iconName = '';

          switch (route.name) {
            case 'Dashboard':
              iconName = 'dashboard';
              break;
            case 'Products':
              iconName = 'inventory';
              break;
            case 'Orders':
              iconName = 'receipt';
              break;
            case 'Analytics':
              iconName = 'analytics';
              break;
            case 'Chat':
              iconName = 'chat';
              break;
            default:
              iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007bff',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
        tabBarTestID: `tab-${route.name.toLowerCase()}`,
      })}
    >
      <Tab.Screen name="Dashboard" component={SellerDashboardScreen} />
      <Tab.Screen name="Products" component={ProductManagementScreen} />
      <Tab.Screen name="Orders" component={OrderManagementScreen} />
      <Tab.Screen name="Analytics" component={AnalyticsScreen} />
      <Tab.Screen name="Chat" component={ChatListScreen} />
    </Tab.Navigator>
  );
};

const DualUserTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ color, size }) => {
          let iconName = '';

          switch (route.name) {
            case 'Home':
              iconName = 'home';
              break;
            case 'Search':
              iconName = 'search';
              break;
            case 'Cart':
              iconName = 'shopping-cart';
              break;
            case 'Dashboard':
              iconName = 'dashboard';
              break;
            case 'Chat':
              iconName = 'chat';
              break;
            default:
              iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007bff',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
        tabBarTestID: `tab-${route.name.toLowerCase()}`,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Search" component={SearchScreen} />
      <Tab.Screen name="Cart" component={CartScreen} />
      <Tab.Screen name="Dashboard" component={SellerDashboardScreen} />
      <Tab.Screen name="Chat" component={ChatListScreen} />
    </Tab.Navigator>
  );
};

const MainTabs = () => {
  const { user } = useSelector((state) => state.auth);

  switch (user?.role) {
    case UserRole.SELLER:
      return <SellerTabs />;
    case UserRole.DUAL:
      return <DualUserTabs />;
    default:
      return <CustomerTabs />;
  }
};

export const MainNavigator  = () => {
  return (
    <ErrorBoundary>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="MainTabs" component={MainTabs} />
        <Stack.Screen name="ProductDetails" component={ProductDetailsScreen} />
        <Stack.Screen name="ProductList" component={ProductListScreen} />
        <Stack.Screen name="ChatScreen" component={ChatScreen} />
        <Stack.Screen name="Checkout" component={CheckoutScreen} />
        <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} />
        <Stack.Screen name="OrderHistory" component={OrderHistoryScreen} />
        <Stack.Screen name="CustomerOrderDetails" component={CustomerOrderDetailsScreen} />
        <Stack.Screen name="OrderDetails" component={OrderDetailsScreen} />
        <Stack.Screen name="AddProduct" component={AddProductScreen} />
        <Stack.Screen
          name="ProductForm"
          component={ProductFormScreen}
          options={{ headerShown: true }}
        />
      </Stack.Navigator>
    </ErrorBoundary>
  );
};