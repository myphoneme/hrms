import { INestApplication } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { ServiceConfig } from './config';

export const API_DOCS_PATH = 'api/docs';

/**
 * Interactive API page (Swagger UI) for manual checks in a browser: GET /api/docs.
 * Served only when APP_ENV is local or test — never on staging or production.
 * "Authorize" takes an access token from `npm run dev:token` (backend/dev/).
 */
export function setupApiDocs(app: INestApplication, config: ServiceConfig): boolean {
  if (config.appEnv !== 'local' && config.appEnv !== 'test') return false;
  const document = SwaggerModule.createDocument(
    app,
    new DocumentBuilder()
      .setTitle(`Teamora ${config.serviceName}`)
      .setDescription(
        'Local/test only. Click **Authorize** and paste a token from `npm run dev:token` ' +
          '(backend/dev/README.md). Errors come back as `{ reason, message, details? }`.',
      )
      .setVersion('0.1.0')
      .addBearerAuth()
      .addSecurityRequirements('bearer')
      .build(),
  );
  SwaggerModule.setup(API_DOCS_PATH, app, document, { swaggerOptions: { persistAuthorization: true } });
  return true;
}
