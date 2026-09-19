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
  if (
    error instanceof ApiError ||
    (typeof error === 'object' && error !== null && ('data' in error || (error as any).name === 'ApiError'))
  ) {
    const apiErr = error as any;
    if (apiErr.data?.detail) {
      if (typeof apiErr.data.detail === 'string') return apiErr.data.detail;
      if (Array.isArray(apiErr.data.detail)) {
        return apiErr.data.detail
          .map((e: any) => {
            if (typeof e === 'string') return e;
            if (typeof e === 'object' && e !== null) {
              return e.msg || e.message || JSON.stringify(e);
            }
            return String(e);
          })
          .join('. ');
      }
      if (typeof apiErr.data.detail === 'object' && apiErr.data.detail !== null) {
        if ('msg' in apiErr.data.detail && typeof apiErr.data.detail.msg === 'string') {
          return apiErr.data.detail.msg;
        }
        if ('message' in apiErr.data.detail && typeof apiErr.data.detail.message === 'string') {
          return apiErr.data.detail.message;
        }
        try {
          return JSON.stringify(apiErr.data.detail);
        } catch {
          return apiErr.message || 'An unexpected error occurred. Please try again.';
        }
      }
      const str = String(apiErr.data.detail);
      return str === '[object Object]' ? (apiErr.message || 'An unexpected error occurred.') : str;
    }
    if (apiErr.data?.message && typeof apiErr.data.message === 'string') {
      return apiErr.data.message;
    }
    return apiErr.message || 'An unexpected API error occurred.';
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
