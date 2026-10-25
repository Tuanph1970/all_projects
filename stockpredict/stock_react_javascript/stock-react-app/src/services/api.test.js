import { formatApiError } from './api';

describe('formatApiError', () => {
  it('returns a string detail as-is', () => {
    expect(formatApiError({ detail: 'Invalid username/email or password' }, 'x'))
      .toBe('Invalid username/email or password');
  });

  it('flattens FastAPI 422 validation lists', () => {
    const body = {
      detail: [
        { type: 'missing', loc: ['body', 'email'], msg: 'Field required' },
        { type: 'missing', loc: ['body', 'password'], msg: 'Field required' },
      ],
    };
    expect(formatApiError(body, 'x')).toBe('email: Field required; password: Field required');
  });

  it('falls back to message, then the fallback', () => {
    expect(formatApiError({ message: 'Boom' }, 'x')).toBe('Boom');
    expect(formatApiError(null, 'Invalid credentials')).toBe('Invalid credentials');
    expect(formatApiError({ detail: [] }, 'Invalid credentials')).toBe('Invalid credentials');
  });
});
