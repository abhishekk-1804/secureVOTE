export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.data?.detail) {
      if (typeof error.data.detail === 'string') return error.data.detail;
      if (Array.isArray(error.data.detail)) {
        return error.data.detail
          .map((e: any) => {
            if (typeof e === 'string') return e;
            if (typeof e === 'object' && e !== null) {
              return e.msg || e.message || JSON.stringify(e);
            }
            return String(e);
          })
          .join('. ');
      }
      if (typeof error.data.detail === 'object' && error.data.detail !== null) {
        if ('msg' in error.data.detail && typeof error.data.detail.msg === 'string') {
          return error.data.detail.msg;
        }
        if ('message' in error.data.detail && typeof error.data.detail.message === 'string') {
          return error.data.detail.message;
        }
        try {
          return JSON.stringify(error.data.detail);
        } catch {
          return error.message || 'An unexpected error occurred. Please try again.';
        }
      }
      const str = String(error.data.detail);
      return str === '[object Object]' ? (error.message || 'An unexpected error occurred.') : str;
    }
    if (error.data?.message && typeof error.data.message === 'string') {
      return error.data.message;
    }
    return error.message || 'An unexpected API error occurred.';
  }
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (typeof error === 'object' && error !== null) {
    try {
      const serialized = JSON.stringify(error);
      return serialized === '{}' ? 'An unexpected error occurred.' : serialized;
    } catch {
      return 'An unexpected error occurred. Please try again.';
    }
  }
  return 'An unexpected error occurred. Please try again.';
}
