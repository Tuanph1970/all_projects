// src/components/Auth/LoginForm.js
import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import LanguageSwitcher from '../Layout/LanguageSwitcher';

const LoginForm = () => {
  const { t } = useTranslation();
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
          setMessage(t('login.error_password_mismatch'));
          return;
        }
        const result = await register(formData.username, formData.email, formData.password);
        // Explicitly set success message from result
        const successMsg = result.message || t('login.success_register');
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
          setMessage(t('login.error_new_password_mismatch'));
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
        <div className="auth-lang-corner">
          <LanguageSwitcher />
        </div>
        <div className="auth-header">
          <div className="auth-logo">
            <TrendingUp />
          </div>
          <h1 className="auth-title">{t('login.app_title')}</h1>
          <p className="auth-subtitle">
            {formType === 'login' && t('login.subtitle_login')}
            {formType === 'register' && t('login.subtitle_register')}
            {formType === 'forgot' && t('login.subtitle_forgot')}
            {formType === 'changePassword' && t('login.subtitle_change')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {(formType === 'login' || formType === 'register') && (
            <div className="form-group">
              <label htmlFor="lf-username" className="form-label">{t('login.label_username')}</label>
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
              <label htmlFor="lf-email" className="form-label">{t('login.label_email')}</label>
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
              <label htmlFor="lf-password" className="form-label">{t('login.label_password')}</label>
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
              <label htmlFor="lf-confirmPassword" className="form-label">{t('login.label_confirm_password')}</label>
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
                <label htmlFor="lf-currentPassword" className="form-label">{t('login.label_current_password')}</label>
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
                <label htmlFor="lf-newPassword" className="form-label">{t('login.label_new_password')}</label>
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
                <label htmlFor="lf-confirmPassword" className="form-label">{t('login.label_confirm_new_password')}</label>
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
                {t('login.submit_loading')}
              </>
            ) : (
              formType === 'login' ? t('login.submit_login') :
              formType === 'register' ? t('login.submit_register') :
              formType === 'changePassword' ? t('login.submit_change') :
              t('login.submit_forgot')
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
                {t('login.link_forgot')}
              </button>
              <div>
                <span>{t('login.link_no_account')} </span>
                <button
                  onClick={() => handleFormTypeChange('register')}
                  className="auth-link"
                >
                  {t('login.link_register')}
                </button>
              </div>
              <div>
                <button
                  onClick={() => handleFormTypeChange('changePassword')}
                  className="auth-link"
                >
                  {t('login.link_change_password')}
                </button>
              </div>
            </>
          )}

          {(formType === 'register' || formType === 'forgot' || formType === 'changePassword') && (
            <button
              onClick={() => handleFormTypeChange('login')}
              className="auth-link"
            >
              {t('login.link_back_to_login')}
            </button>
          )}
        </div>

        <div className="auth-demo">
          <p className="auth-demo-text">
            {t('login.demo_account')}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;