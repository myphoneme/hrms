import {
  CanActivate,
  createParamDecorator,
  ExecutionContext,
  Inject,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { sign, verify } from 'jsonwebtoken';
import { ServiceConfig } from './config';
import { isUuid } from './tenancy';
import { SERVICE_CONFIG } from './tokens';

export const USER_ROLES = ['platform_admin', 'tenant_admin', 'manager', 'recruiter_hr'] as const;
export type UserRole = (typeof USER_ROLES)[number];

/** Who is calling, as proven by a verified access token (TDD §3). */
export interface AuthContext {
  userId: string;
  /** Null only for a Phoneme Platform Admin, who is not scoped to any tenant. */
  tenantId: string | null;
  role: UserRole;
}

const ISSUER = 'teamora-auth';
const AUDIENCE = 'teamora';
const ACCESS_TOKEN_TTL_SECONDS = 15 * 60; // TDD §3.3: short-lived 15-minute access tokens

interface AccessTokenClaims {
  sub: string;
  tenant_id: string | null;
  role: UserRole;
}

/** Issues an access token. Used by auth-service at login, and by tests. */
export function signAccessToken(secret: string, auth: AuthContext, ttlSeconds = ACCESS_TOKEN_TTL_SECONDS): string {
  const claims: Omit<AccessTokenClaims, 'sub'> = { tenant_id: auth.tenantId, role: auth.role };
  return sign(claims, secret, {
    algorithm: 'HS256',
    subject: auth.userId,
    issuer: ISSUER,
    audience: AUDIENCE,
    expiresIn: ttlSeconds,
  });
}

/** Verifies signature, issuer, audience and expiry, then the claim shapes. Throws on anything invalid. */
export function verifyAccessToken(secret: string, token: string): AuthContext {
  const payload = verify(token, secret, { algorithms: ['HS256'], issuer: ISSUER, audience: AUDIENCE });
  if (typeof payload === 'string') throw new Error('unexpected token payload');
  const { sub, tenant_id: tenantId, role } = payload as Partial<AccessTokenClaims>;
  if (!isUuid(sub)) throw new Error('invalid sub claim');
  if (!(USER_ROLES as readonly string[]).includes(role as string)) throw new Error('invalid role claim');
  if (role === 'platform_admin' ? tenantId !== null : !isUuid(tenantId)) throw new Error('invalid tenant_id claim');
  return { userId: sub, tenantId: tenantId ?? null, role: role as UserRole };
}

/** Rejects any request without a valid `Authorization: Bearer <access token>` with 401. */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(@Inject(SERVICE_CONFIG) private readonly config: ServiceConfig) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<{ headers: Record<string, string | undefined>; auth?: AuthContext }>();
    const header = request.headers['authorization'];
    if (!header?.startsWith('Bearer ')) {
      throw new UnauthorizedException({ reason: 'missing_token', message: 'A Bearer access token is required.' });
    }
    try {
      request.auth = verifyAccessToken(this.config.authJwtSecret, header.slice('Bearer '.length).trim());
    } catch {
      throw new UnauthorizedException({ reason: 'invalid_token', message: 'The access token is invalid or expired.' });
    }
    return true;
  }
}

/** Controller parameter decorator for the verified caller; use together with `@UseGuards(AuthGuard)`. */
export const Auth = createParamDecorator((_data: unknown, context: ExecutionContext): AuthContext => {
  return context.switchToHttp().getRequest<{ auth: AuthContext }>().auth;
});
