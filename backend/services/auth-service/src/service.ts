import { ServiceDefinition } from '@teamora/platform';

export const SERVICE: ServiceDefinition = {
  serviceName: 'auth-service',
  defaultPort: 3001,
  dbRole: 'svc_auth',
  dbPasswordVar: 'POSTGRES_SVC_AUTH_PASSWORD',
};
