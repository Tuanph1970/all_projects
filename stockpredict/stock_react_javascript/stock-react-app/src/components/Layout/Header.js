// src/components/Layout/Header.js
import React from 'react';
import { LogOut, Menu, User, ChevronRight, ChevronLeft } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import NotificationBell from './NotificationBell';

const Header = ({ onToggleSidebar, isSidebarCollapsed }) => {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          {/* Mobile menu toggle */}
          <button
            onClick={() => document.dispatchEvent(new CustomEvent('toggleSidebar'))}
            className="menu-toggle mobile-only"
            title="Mở menu di động"
          >
            <Menu />
          </button>

          {/* Desktop sidebar expand/collapse toggle */}
          <button
            onClick={onToggleSidebar}
            className="sidebar-expand-toggle desktop-only"
            title={isSidebarCollapsed ? 'Mở rộng menu' : 'Thu gọn menu'}
          >
            {isSidebarCollapsed ? <ChevronRight /> : <ChevronLeft />}
          </button>
        </div>

        <div className="header-right">
          <NotificationBell />

          <div className="user-section">
            <div className="user-avatar">
              <User />
            </div>
            <span className="user-name">{user?.username}</span>
          </div>

          <button onClick={logout} className="logout-button">
            <LogOut />
            <span className="logout-text">Đăng xuất</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;