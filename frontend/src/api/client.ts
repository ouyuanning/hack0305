import axios from 'axios';
import type { ErrorResponse } from '@/types';

const apiClient = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach common headers
apiClient.interceptors.request.use(
  (config) => {
    config.headers.set('Accept', 'application/json');
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor: extract error messages from ErrorResponse
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      const errData = error.response.data as ErrorResponse;
      const message = errData.message || errData.detail || '请求失败';
      // Create a custom error that preserves the response object
      const customError = new Error(message) as Error & { response?: typeof error.response };
      customError.response = error.response;
      return Promise.reject(customError);
    }
    if (error.message) {
      return Promise.reject(error);
    }
    return Promise.reject(new Error('网络错误'));
  },
);

export default apiClient;
