import { GreppaApi } from './types';
import { MockGreppaApi } from './mock-api';
import { HttpGreppaApi } from './http-api';

const API_MODE = process.env.NEXT_PUBLIC_API_MODE || 'mock';

let apiInstance: GreppaApi;

if (API_MODE === 'http') {
  apiInstance = new HttpGreppaApi();
} else {
  apiInstance = new MockGreppaApi();
}

export const api = apiInstance;
export type ApiClient = typeof apiInstance;
