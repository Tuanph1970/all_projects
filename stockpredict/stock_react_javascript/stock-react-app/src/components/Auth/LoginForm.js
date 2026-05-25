// src/components/Auth/LoginForm.js
import React, { useState } from 'react';
import { KeyRound, User, Mail, Eye, EyeOff } from 'lucide-react';
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
  // Per-field password visibility. Each entry maps the input `name` to
  // a boolean (true = plaintext, false = masked). Keeping the state by
  // field name lets every password input (login, register, current,
  // new, confirm…) have an independent toggle.
  const [visibility, setVisibility] = useState({});

  const toggleVisibility = (name) => {
    setVisibility((prev) => ({ ...prev, [name]: !prev[name] }));
  };

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
        const successMsg = result.message || t('login.success_register');
        setMessage(successMsg);
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
    setVisibility({});
  };

  const handleFormTypeChange = (newType) => {
    setFormType(newType);
    resetForm();
  };

  // Helper that renders a labelled text input with a left-side icon.
  // Keeps the JSX below readable when there are 6 possible fields.
  const renderInput = ({ id, name, type, label, autoComplete, Icon }) => (
    <div className="form-group">
      <label htmlFor={id} className="form-label">{label}</label>
      <div className="form-input-wrapper">
        <Icon className="form-input-icon" aria-hidden="true" />
        <input
          id={id}
          type={type}
          name={name}
          value={formData[name]}
          onChange={handleChange}
          className="form-input has-icon"
          autoComplete={autoComplete}
          required
        />
      </div>
    </div>
  );

  // Password variant — adds the right-side eye toggle.
  const renderPassword = ({ id, name, label, autoComplete }) => {
    const shown = !!visibility[name];
    return (
      <div className="form-group">
        <label htmlFor={id} className="form-label">{label}</label>
        <div className="form-input-wrapper">
          <KeyRound className="form-input-icon" aria-hidden="true" />
          <input
            id={id}
            type={shown ? 'text' : 'password'}
            name={name}
            value={formData[name]}
            onChange={handleChange}
            className="form-input has-icon has-trailing"
            autoComplete={autoComplete}
            required
          />
          <button
            type="button"
            onClick={() => toggleVisibility(name)}
            className="form-input-eye"
            aria-label={shown ? t('login.hide_password') : t('login.show_password')}
            aria-pressed={shown}
            tabIndex={-1}
          >
            {shown ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-lang-corner">
          <LanguageSwitcher />
        </div>
        <div className="auth-header">
          <div className="auth-logo">
            <KeyRound />
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
          {(formType === 'login' || formType === 'register') && renderInput({
            id: 'lf-username',
            name: 'username',
            type: 'text',
            label: t('login.label_username'),
            autoComplete: 'username',
            Icon: User,
          })}

          {(formType === 'register' || formType === 'forgot') && renderInput({
            id: 'lf-email',
            name: 'email',
            type: 'email',
            label: t('login.label_email'),
            autoComplete: 'email',
            Icon: Mail,
          })}

          {(formType === 'login' || formType === 'register') && renderPassword({
            id: 'lf-password',
            name: 'password',
            label: t('login.label_password'),
            autoComplete: formType === 'register' ? 'new-password' : 'current-password',
          })}

          {formType === 'register' && renderPassword({
            id: 'lf-confirmPassword',
            name: 'confirmPassword',
            label: t('login.label_confirm_password'),
            autoComplete: 'new-password',
          })}

          {formType === 'changePassword' && (
            <>
              {renderPassword({
                id: 'lf-currentPassword',
                name: 'currentPassword',
                label: t('login.label_current_password'),
                autoComplete: 'current-password',
              })}
              {renderPassword({
                id: 'lf-newPassword',
                name: 'newPassword',
                label: t('login.label_new_password'),
                autoComplete: 'new-password',
              })}
              {renderPassword({
                id: 'lf-confirmPassword',
                name: 'confirmPassword',
                label: t('login.label_confirm_new_password'),
                autoComplete: 'new-password',
              })}
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
      </div>
    </div>
  );
};

export default LoginForm;
