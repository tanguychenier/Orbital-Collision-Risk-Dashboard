import axios, { AxiosError, type AxiosInstance } from 'axios';
import type { ApiError } from './types';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' }
});

export class ApiClientError extends Error {
  public readonly status: number | undefined;
  public readonly detail: string;

  constructor(message: string, status: number | undefined, detail: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = detail;
  }
}

apiClient.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail ?? error.message ?? 'Unknown API error';
    return Promise.reject(new ApiClientError(detail, status, detail));
  }
);
