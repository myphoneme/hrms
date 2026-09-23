import { ServiceDefinition } from '@teamora/platform';

export const SERVICE: ServiceDefinition = {
  serviceName: 'requisition-service',
  defaultPort: 3002,
  dbRole: 'svc_requisition',
  dbPasswordVar: 'POSTGRES_SVC_REQUISITION_PASSWORD',
};
