import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResetPasswordConfirm from './ResetPasswordConfirm';

const setLocation = (search) => {
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { ...window.location, search },
  });
};

describe('ResetPasswordConfirm', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  test('shows a fatal error when no token is present', () => {
    setLocation('');
    render(<ResetPasswordConfirm />);
    expect(
      screen.getByText(/Liên kết đặt lại mật khẩu không hợp lệ/i)
    ).toBeInTheDocument();
  });

  test('rejects mismatched passwords without calling the API', () => {
    setLocation('?token=valid-token');
    global.fetch = jest.fn();

    render(<ResetPasswordConfirm />);
    const inputs = [
      screen.getByLabelText('Mật khẩu mới'),
      screen.getByLabelText('Xác nhận mật khẩu mới'),
    ];
    fireEvent.change(inputs[0], { target: { value: 'Password123' } });
    fireEvent.change(inputs[1], { target: { value: 'Different456' } });
    fireEvent.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }));

    expect(screen.getByText(/Mật khẩu xác nhận không khớp/i)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('rejects weak passwords client-side', () => {
    setLocation('?token=valid-token');
    global.fetch = jest.fn();

    render(<ResetPasswordConfirm />);
    const inputs = [
      screen.getByLabelText('Mật khẩu mới'),
      screen.getByLabelText('Xác nhận mật khẩu mới'),
    ];
    // The form's HTML5 minLength=8 will block submission below 8 chars,
    // so use 8+ chars but missing other complexity rules to exercise our
    // validatePassword JS path explicitly.
    fireEvent.change(inputs[0], { target: { value: 'lowercase1' } });
    fireEvent.change(inputs[1], { target: { value: 'lowercase1' } });
    fireEvent.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }));

    // validatePassword catches missing uppercase first.
    expect(screen.getByText(/ít nhất 1 chữ hoa/i)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('on successful submission shows success state', async () => {
    setLocation('?token=valid-token');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ message: 'Password reset successfully' }),
    });

    render(<ResetPasswordConfirm />);
    const inputs = [
      screen.getByLabelText('Mật khẩu mới'),
      screen.getByLabelText('Xác nhận mật khẩu mới'),
    ];
    fireEvent.change(inputs[0], { target: { value: 'NewPassword123' } });
    fireEvent.change(inputs[1], { target: { value: 'NewPassword123' } });
    fireEvent.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }));

    await waitFor(() => {
      expect(screen.getByText(/Đặt lại mật khẩu thành công/i)).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [, fetchOptions] = global.fetch.mock.calls[0];
    const body = JSON.parse(fetchOptions.body);
    expect(body).toEqual({ token: 'valid-token', new_password: 'NewPassword123' });
  });

  test('surfaces API error detail on failure', async () => {
    setLocation('?token=expired-token');
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Reset token has expired' }),
    });

    render(<ResetPasswordConfirm />);
    const inputs = [
      screen.getByLabelText('Mật khẩu mới'),
      screen.getByLabelText('Xác nhận mật khẩu mới'),
    ];
    fireEvent.change(inputs[0], { target: { value: 'NewPassword123' } });
    fireEvent.change(inputs[1], { target: { value: 'NewPassword123' } });
    fireEvent.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }));

    await waitFor(() => {
      expect(screen.getByText(/Reset token has expired/i)).toBeInTheDocument();
    });
  });
});
