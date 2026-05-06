import React, { useEffect, useMemo, useState } from 'react';
import { TrendingUp, CheckCircle2, AlertCircle } from 'lucide-react';
import { API_ENDPOINTS } from '../../constants/api';

const STATES = {
  EDITING: 'editing',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
};

const ResetPasswordConfirm = () => {
  const token = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('token') || '';
  }, []);

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [state, setState] = useState(STATES.EDITING);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setState(STATES.ERROR);
      setMessage('Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.');
    }
  }, [token]);

  const validatePassword = (value) => {
    if (value.length < 8) return 'Mật khẩu phải có ít nhất 8 ký tự.';
    if (!/[A-Z]/.test(value)) return 'Mật khẩu phải có ít nhất 1 chữ hoa.';
    if (!/[a-z]/.test(value)) return 'Mật khẩu phải có ít nhất 1 chữ thường.';
    if (!/\d/.test(value)) return 'Mật khẩu phải có ít nhất 1 chữ số.';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');

    if (password !== confirmPassword) {
      setMessage('Mật khẩu xác nhận không khớp.');
      return;
    }
    const pwError = validatePassword(password);
    if (pwError) {
      setMessage(pwError);
      return;
    }

    setState(STATES.SUBMITTING);
    try {
      const response = await fetch(API_ENDPOINTS.AUTH_RESET_PASSWORD_CONFIRM, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Không thể đặt lại mật khẩu.');
      }

      setState(STATES.SUCCESS);
      setMessage('Đặt lại mật khẩu thành công. Bạn có thể đăng nhập với mật khẩu mới.');
    } catch (err) {
      setState(STATES.ERROR);
      setMessage(err.message || 'Không thể đặt lại mật khẩu.');
    }
  };

  const goToLogin = () => {
    // Drop the query string and head back to the app root so LoginForm renders.
    const homepage = '/stock-app';
    window.location.assign(homepage + '/');
  };

  const submitting = state === STATES.SUBMITTING;
  const success = state === STATES.SUCCESS;
  const fatalError = state === STATES.ERROR && !token;

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <TrendingUp />
          </div>
          <h1 className="auth-title">Đặt lại mật khẩu</h1>
          <p className="auth-subtitle">
            {success
              ? 'Mật khẩu đã được cập nhật.'
              : 'Nhập mật khẩu mới cho tài khoản của bạn.'}
          </p>
        </div>

        {success ? (
          <div style={{ textAlign: 'center', padding: '8px 0 16px' }}>
            <CheckCircle2 size={48} color="#16a34a" style={{ margin: '0 auto 12px' }} />
            <div className="auth-message success" style={{ marginBottom: 16 }}>
              {message}
            </div>
            <button onClick={goToLogin} className="auth-button">
              Đến trang đăng nhập
            </button>
          </div>
        ) : fatalError ? (
          <div style={{ textAlign: 'center', padding: '8px 0 16px' }}>
            <AlertCircle size={48} color="#dc2626" style={{ margin: '0 auto 12px' }} />
            <div className="auth-message error" style={{ marginBottom: 16 }}>
              {message}
            </div>
            <button onClick={goToLogin} className="auth-button">
              Quay lại đăng nhập
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label className="form-label">Mật khẩu mới</label>
              <input
                type="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input"
                autoComplete="new-password"
                required
                minLength={8}
              />
              <small style={{ color: '#6b7280' }}>
                Tối thiểu 8 ký tự, gồm chữ hoa, chữ thường và số.
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">Xác nhận mật khẩu mới</label>
              <input
                type="password"
                name="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="form-input"
                autoComplete="new-password"
                required
                minLength={8}
              />
            </div>

            {message && (
              <div className="auth-message error">{message}</div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className={`auth-button ${submitting ? 'btn-loading' : ''}`}
            >
              {submitting ? (
                <>
                  <span className="loading-spinner"></span>
                  Đang xử lý...
                </>
              ) : (
                'Đặt lại mật khẩu'
              )}
            </button>

            <div className="auth-links" style={{ marginTop: 12 }}>
              <button type="button" onClick={goToLogin} className="auth-link">
                Quay lại đăng nhập
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPasswordConfirm;
