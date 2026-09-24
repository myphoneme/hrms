import { sign } from 'jsonwebtoken';
import { AuthContext, signAccessToken, verifyAccessToken } from './auth';

const SECRET = 'unit-test-secret-unit-test-secret-0001';
const manager: AuthContext = {
  userId: '0190a1b2-0000-7000-8000-000000000001',
  tenantId: '0190a1b2-0000-7000-8000-00000000000a',
  role: 'manager',
};

describe('access tokens', () => {
  it('round-trips a tenant user', () => {
    expect(verifyAccessToken(SECRET, signAccessToken(SECRET, manager))).toEqual(manager);
  });

  it('allows a platform admin with no tenant', () => {
    const admin: AuthContext = { userId: manager.userId, tenantId: null, role: 'platform_admin' };
    expect(verifyAccessToken(SECRET, signAccessToken(SECRET, admin))).toEqual(admin);
  });

  it('rejects a token signed with another secret', () => {
    const token = signAccessToken('another-secret-another-secret-0000001', manager);
    expect(() => verifyAccessToken(SECRET, token)).toThrow();
  });

  it('rejects an expired token', () => {
    const token = signAccessToken(SECRET, manager, -10);
    expect(() => verifyAccessToken(SECRET, token)).toThrow(/expired/);
  });

  it('rejects a tenant user without tenant_id, and a platform admin with one', () => {
    const noTenant = sign({ tenant_id: null, role: 'manager' }, SECRET, {
      subject: manager.userId, issuer: 'teamora-auth', audience: 'teamora', expiresIn: 60,
    });
    expect(() => verifyAccessToken(SECRET, noTenant)).toThrow(/tenant_id/);
    const adminWithTenant = sign({ tenant_id: manager.tenantId, role: 'platform_admin' }, SECRET, {
      subject: manager.userId, issuer: 'teamora-auth', audience: 'teamora', expiresIn: 60,
    });
    expect(() => verifyAccessToken(SECRET, adminWithTenant)).toThrow(/tenant_id/);
  });

  it('rejects an unknown role and a wrong audience', () => {
    const badRole = sign({ tenant_id: manager.tenantId, role: 'superuser' }, SECRET, {
      subject: manager.userId, issuer: 'teamora-auth', audience: 'teamora', expiresIn: 60,
    });
    expect(() => verifyAccessToken(SECRET, badRole)).toThrow(/role/);
    const badAudience = sign({ tenant_id: manager.tenantId, role: 'manager' }, SECRET, {
      subject: manager.userId, issuer: 'teamora-auth', audience: 'someone-else', expiresIn: 60,
    });
    expect(() => verifyAccessToken(SECRET, badAudience)).toThrow(/audience/);
  });

  it('rejects the "none" algorithm', () => {
    const unsigned = sign({ tenant_id: manager.tenantId, role: 'manager' }, '', {
      algorithm: 'none', subject: manager.userId, issuer: 'teamora-auth', audience: 'teamora',
    });
    expect(() => verifyAccessToken(SECRET, unsigned)).toThrow();
  });
});
