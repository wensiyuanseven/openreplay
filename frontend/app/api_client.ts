import store from 'App/store';
import { queried } from './routes';
import { setJwt } from 'Duck/user';

const siteIdRequiredPaths = new Set([
  '/dashboard',
  '/sessions',
  '/events',
  '/filters',
  '/alerts',
  '/targets',
  '/metadata',
  '/integrations/sentry/events',
  '/integrations/slack/notify',
  '/integrations/msteams/notify',
  '/assignments',
  '/integration/sources',
  '/issue_types',
  '/saved_search',
  '/rehydrations',
  '/sourcemaps',
  '/errors',
  '/funnels',
  '/assist',
  '/heatmaps',
  '/custom_metrics',
  '/dashboards',
  '/cards',
  '/unprocessed',
  '/notes',
  '/feature-flags',
  '/check-recording-status'
]);

export const clean = (obj: any, forbiddenValues: any[] = [undefined, '']): any => {
  const keys = Array.isArray(obj)
    ? new Array(obj.length).fill().map((_, i) => i)
    : Object.keys(obj);
  const retObj = Array.isArray(obj) ? [] : {};
  keys.map(key => {
    const value = obj[key];
    if (typeof value === 'object' && value !== null) {
      retObj[key] = clean(value);
    } else if (!forbiddenValues.includes(value)) {
      retObj[key] = value;
    }
  });

  return retObj;
};

export default class APIClient {
  private readonly siteId: string | undefined;
  private readonly headers: Headers;

  constructor() {
    this.siteId = store.getState().getIn(['site', 'siteId']);
    this.headers = new Headers({
      Accept: 'application/json',
      'Content-Type': 'application/json'
    });
    this.updateJwtHeader();
  }

  private updateJwtHeader(): void {
    const jwt = store.getState().getIn(['user', 'jwt']);
    if (jwt) {
      this.headers.set('Authorization', `Bearer ${jwt}`);
    }
  }

  private getInit(method: string, params?: any): RequestInit {
    return {
      method,
      headers: this.headers,
      body: ['GET', 'HEAD'].includes(method) ? undefined : JSON.stringify(params)
    };
  }

  private async makeRequest(path: string, method: string, params?: any, options: {
    clean?: boolean
  } = { clean: true }): Promise<Response> {
    this.updateJwtHeader();
    const jwt = store.getState().getIn(['user', 'jwt']);
    if (!path.includes('/refresh') && jwt && this.isTokenExpired(jwt)) {
      await this.handleTokenRefresh();
    }

    const cleanedParams = options.clean && params ? clean(params) : params;
    const init = this.getInit(method, cleanedParams);

    let edp = this.determineEndpoint(path);
    return window.fetch(edp + path, init).then(this.handleResponse);
  }

  private determineEndpoint(path: string): string {
    let edp = window.env.API_EDP || window.location.origin + '/api';

    // Check if the path already contains siteId to prevent double appending
    if (this.needsSiteId(path) && !path.includes(`/${this.siteId}`)) {
      edp = `${edp}/${this.siteId}`;
    }

    return edp;
  }

  private needsSiteId(path: string): boolean {
    if (!this.siteId) {
      return false;
    }

    for (const requiredPath of siteIdRequiredPaths) {
      if (path.includes(requiredPath)) {
        return true;
      }
    }

    return false;
  }

  private handleResponse(response: Response): Promise<Response> {
    if (!response.ok) {
      throw new Error(`! ${response.status} error on ${response.url}`);
    }
    return Promise.resolve(response);
  }

  get(path: string, params?: any, options?: any): Promise<Response> {
    return this.makeRequest(queried(path, params), 'GET', undefined, options);
  }

  post(path: string, params?: any, options?: any): Promise<Response> {
    return this.makeRequest(path, 'POST', params);
  }

  put(path: string, params?: any, options?: any): Promise<Response> {
    return this.makeRequest(path, 'PUT', params);
  }

  delete(path: string, params?: any, options?: any): Promise<Response> {
    return this.makeRequest(path, 'DELETE', params);
  }

  private decodeJwt(jwt: string): any {
    const base64Url = jwt.split('.')[1];
    const base64 = base64Url.replace('-', '+').replace('_', '/');
    return JSON.parse(window.atob(base64));
  }

  isTokenExpired(token: string): boolean {
    const decoded: any = this.decodeJwt(token);
    const currentTime = Date.now() / 1000;
    return decoded.exp < currentTime;
  }

  private async handleTokenRefresh(): Promise<string> {
    // If we are already refreshing the token, return the existing promise
    if (!this.refreshingTokenPromise) {
      this.refreshingTokenPromise = this.refreshToken().finally(() => {
        // Once the token has been refreshed, reset the promise
        this.refreshingTokenPromise = null;
      });
    }
    return this.refreshingTokenPromise;
  }

  async refreshToken(): Promise<string> {
    try {
      const response = await this.makeRequest('/refresh', {
        headers: this.headers
      }, 'GET', { clean: false });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      const refreshedJwt = data.jwt;
      store.dispatch(setJwt(refreshedJwt));
      return refreshedJwt;
    } catch (error) {
      console.error('Error refreshing token:', error);
      store.dispatch(setJwt(null));
      throw error;
    }
  }
}