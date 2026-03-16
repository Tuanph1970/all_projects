/**
 * Chain-of-Responsibility error handler for API errors.
 *
 * Each handler inspects the error and either:
 *   - Throws a user-facing Error (terminates the chain), or
 *   - Calls super.handle(error) to pass to the next handler.
 *
 * Adding a new error type = add a new class, insert it into the chain in
 * buildErrorHandlerChain(). No existing handler needs to change.
 */

// ─── Base ────────────────────────────────────────────────────────────────────

class ErrorHandler {
  setNext(handler) {
    this._next = handler;
    return handler; // allows fluent chaining: a.setNext(b).setNext(c)
  }

  handle(error) {
    if (this._next) {
      return this._next.handle(error);
    }
    // End of chain — re-throw the raw error
    throw error;
  }
}

// ─── Concrete handlers ────────────────────────────────────────────────────────

/**
 * If the server included a human-readable message in its JSON body, use it
 * directly instead of a generic string. This runs before status-based handlers
 * so backend validation messages are always surfaced verbatim.
 */
class ServerMessageHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.data?.message) {
      throw new Error(error.response.data.message);
    }
    return super.handle(error);
  }
}

/**
 * No HTTP response received — connection refused, timeout, offline, etc.
 */
class NetworkErrorHandler extends ErrorHandler {
  handle(error) {
    if (!error.response && error.request) {
      throw new Error('Network error. Please check your internet connection.');
    }
    return super.handle(error);
  }
}

/** HTTP 400 — malformed request */
class BadRequestHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status === 400) {
      throw new Error('Bad request. Please check your input.');
    }
    return super.handle(error);
  }
}

/** HTTP 401 — unauthenticated (token expired / invalid) */
class AuthErrorHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status === 401) {
      throw new Error('Authentication failed. Please log in again.');
    }
    return super.handle(error);
  }
}

/** HTTP 403 — authenticated but not authorised */
class ForbiddenErrorHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status === 403) {
      throw new Error('You do not have permission to perform this action.');
    }
    return super.handle(error);
  }
}

/** HTTP 404 — resource not found */
class NotFoundErrorHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status === 404) {
      throw new Error('The requested resource was not found.');
    }
    return super.handle(error);
  }
}

/** HTTP 422 — validation error (unprocessable entity) */
class ValidationErrorHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status === 422) {
      const errors = error.response.data?.errors;
      if (errors && typeof errors === 'object') {
        const messages = Object.values(errors).flat().join(' ');
        throw new Error(messages || 'Validation failed. Please check your input.');
      }
      throw new Error('Validation failed. Please check your input.');
    }
    return super.handle(error);
  }
}

/** HTTP 5xx — server-side failure */
class ServerErrorHandler extends ErrorHandler {
  handle(error) {
    if (error.response?.status >= 500) {
      throw new Error('Server error. Please try again later.');
    }
    return super.handle(error);
  }
}

/** Catch-all for any other HTTP status or unexpected error shape */
class DefaultErrorHandler extends ErrorHandler {
  handle(error) {
    const status = error.response?.status;
    if (status) {
      throw new Error(`Request failed with status ${status}`);
    }
    throw new Error(error.message || 'An unexpected error occurred.');
  }
}

// ─── Chain builder ────────────────────────────────────────────────────────────

/**
 * Builds and returns the head of the handler chain.
 * Order matters: ServerMessage → Network → 400 → 401 → 403 → 404 → 422 → 5xx → Default
 */
function buildErrorHandlerChain() {
  const serverMessage = new ServerMessageHandler();
  const network       = new NetworkErrorHandler();
  const badRequest    = new BadRequestHandler();
  const auth          = new AuthErrorHandler();
  const forbidden     = new ForbiddenErrorHandler();
  const notFound      = new NotFoundErrorHandler();
  const validation    = new ValidationErrorHandler();
  const server        = new ServerErrorHandler();
  const fallback      = new DefaultErrorHandler();

  serverMessage
    .setNext(network)
    .setNext(badRequest)
    .setNext(auth)
    .setNext(forbidden)
    .setNext(notFound)
    .setNext(validation)
    .setNext(server)
    .setNext(fallback);

  return serverMessage;
}

export const errorHandlerChain = buildErrorHandlerChain();
