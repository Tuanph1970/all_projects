// src/components/Auth/LoginForm.js
import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const LoginForm = () => {
  const [formType, setFormType] = useState('login');
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    currentPassword: '',
    newPassword: ''
  });
  const { login, register, resetPassword, changePassword, loading } = useAuth();
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');

    try {
      if (formType === 'login') {
        await login(formData.username, formData.password);
      } else if (formType === 'register') {
        if (formData.password !== formData.confirmPassword) {
          setMessage('Mật khẩu không khớp');
          return;
        }
        const result = await register(formData.username, formData.email, formData.password);
        // Explicitly set success message from result
        const successMsg = result.message || 'Đăng ký thành công! Vui lòng đăng nhập.';
        setMessage(successMsg);
        // Switch to login form after showing message
        setTimeout(() => {
          setFormType('login');
        }, 2000);
      } else if (formType === 'forgot') {
        const result = await resetPassword(formData.email);
        setMessage(result.message);
        setFormType('login');
      } else if (formType === 'changePassword') {
        if (formData.newPassword !== formData.confirmPassword) {
          setMessage('Mật khẩu mới không khớp');
          return;
        }
        const result = await changePassword(formData.currentPassword, formData.newPassword);
        setMessage(result.message);
        setFormType('login');
      }
    } catch (error) {
      setMessage(error.message);
    }
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const resetForm = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      currentPassword: '',
      newPassword: ''
    });
    setMessage('');
  };

  const handleFormTypeChange = (newType) => {
    setFormType(newType);
    resetForm();
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <TrendingUp />
          </div>
          <h1 className="auth-title">Nền tảng Phân tích Cổ phiếu</h1>
          <p className="auth-subtitle">
            {formType === 'login' && 'Đăng nhập vào tài khoản của bạn'}
            {formType === 'register' && 'Tạo tài khoản mới'}
            {formType === 'forgot' && 'Đặt lại mật khẩu'}
            {formType === 'changePassword' && 'Đổi mật khẩu'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {(formType === 'login' || formType === 'register') && (
            <div className="form-group">
              <label htmlFor="lf-username" className="form-label">Tên đăng nhập</label>
              <input id="lf-username"
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="form-input"
                required
              />
            </div>
          )}

          {(formType === 'register' || formType === 'forgot') && (
            <div className="form-group">
              <label htmlFor="lf-email" className="form-label">Email</label>
              <input id="lf-email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="form-input"
                required
              />
            </div>
          )}

          {(formType === 'login' || formType === 'register') && (
            <div className="form-group">
              <label htmlFor="lf-password" className="form-label">Mật khẩu</label>
              <input id="lf-password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="form-input"
                required
              />
            </div>
          )}

          {formType === 'register' && (
            <div className="form-group">
              <label htmlFor="lf-confirmPassword" className="form-label">Xác nhận mật khẩu</label>
              <input id="lf-confirmPassword"
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="form-input"
                required
              />
            </div>
          )}

          {formType === 'changePassword' && (
            <>
              <div className="form-group">
                <label htmlFor="lf-currentPassword" className="form-label">Mật khẩu hiện tại</label>
                <input id="lf-currentPassword"
                  type="password"
                  name="currentPassword"
                  value={formData.currentPassword}
                  onChange={handleChange}
                  className="form-input"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="lf-newPassword" className="form-label">Mật khẩu mới</label>
                <input id="lf-newPassword"
                  type="password"
                  name="newPassword"
                  value={formData.newPassword}
                  onChange={handleChange}
                  className="form-input"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="lf-confirmPassword" className="form-label">Xác nhận mật khẩu mới</label>
                <input id="lf-confirmPassword"
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="form-input"
                  required
                />
              </div>
            </>
          )}

          {message && (
            <div className={`auth-message ${message.includes('successful') || message.includes('sent') || message.includes('thành công') ? 'success' : 'error'}`}>
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className={`auth-button ${loading ? 'btn-loading' : ''}`}
          >
            {loading ? (
              <>
                <span className="loading-spinner"></span>
                Đang xử lý...
              </>
            ) : (
              formType === 'login' ? 'Đăng nhập' :
              formType === 'register' ? 'Đăng ký' :
              formType === 'changePassword' ? 'Đổi mật khẩu' :
              'Đặt lại mật khẩu'
            )}
          </button>
        </form>

        <div className="auth-links">
          {formType === 'login' && (
            <>
              <button
                onClick={() => handleFormTypeChange('forgot')}
                className="auth-link"
              >
                Quên mật khẩu?
              </button>
              <div>
                <span>Chưa có tài khoản? </span>
                <button
                  onClick={() => handleFormTypeChange('register')}
                  className="auth-link"
                >
                  Đăng ký
                </button>
              </div>
              <div>
                <button
                  onClick={() => handleFormTypeChange('changePassword')}
                  className="auth-link"
                >
                  Đổi mật khẩu
                </button>
              </div>
            </>
          )}

          {(formType === 'register' || formType === 'forgot' || formType === 'changePassword') && (
            <button
              onClick={() => handleFormTypeChange('login')}
              className="auth-link"
            >
              Quay lại đăng nhập
            </button>
          )}
        </div>

        <div className="auth-demo">
          <p className="auth-demo-text">
            Tài khoản demo: tên đăng nhập "demo", mật khẩu "password"
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;