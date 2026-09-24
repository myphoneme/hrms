import { ArgumentsHost, Catch, ExceptionFilter, HttpException, HttpStatus, Logger } from '@nestjs/common';

/** The one JSON error shape every Teamora API returns (Readiness doc §2.3). */
export interface ErrorBody {
  reason: string;
  message: string;
  details?: unknown;
}

const REASON_BY_STATUS: Record<number, string> = {
  400: 'bad_request',
  401: 'unauthorized',
  403: 'forbidden',
  404: 'not_found',
  409: 'conflict',
  422: 'validation_failed',
  429: 'too_many_requests',
};

/**
 * Normalises every error into `{ reason, message, details? }`:
 * - exceptions thrown with an object that already has `reason` pass through unchanged;
 * - exceptions thrown with a custom object without `statusCode` (e.g. /health/ready) pass through;
 * - Nest's default `{ statusCode, message, error }` bodies are converted;
 * - anything unexpected becomes a 500 with no internals in the response (logged instead).
 */
@Catch()
export class HttpErrorFilter implements ExceptionFilter {
  private readonly logger = new Logger('HttpErrorFilter');

  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<{ status(code: number): { json(body: unknown): void } }>();

    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const body = exception.getResponse();
      if (typeof body === 'object' && body !== null && ('reason' in body || !('statusCode' in body))) {
        response.status(status).json(body);
        return;
      }
      const message = typeof body === 'string' ? body : String((body as { message?: unknown }).message ?? exception.message);
      response.status(status).json({ reason: REASON_BY_STATUS[status] ?? 'error', message } satisfies ErrorBody);
      return;
    }

    this.logger.error(exception instanceof Error ? (exception.stack ?? exception.message) : String(exception));
    response
      .status(HttpStatus.INTERNAL_SERVER_ERROR)
      .json({ reason: 'internal_error', message: 'Internal server error' } satisfies ErrorBody);
  }
}
