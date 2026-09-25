// Prints an access token for a demo manager, for manual API checks (Swagger "Authorize", requests.http).
// Usage:  npm run dev:token                   -> Demo Staffing Agency manager, valid 8 hours
//         npm run dev:token -- employer       -> Demo Direct Employer manager
//         npm run dev:token -- agency 2       -> valid 2 hours
const { signAccessToken } = require('../packages/platform/dist');
const demo = require('./demo');

const who = process.argv[2] ?? 'agency';
const hours = Number(process.argv[3] ?? 8);
const user = demo.users[who];

if (process.env.APP_ENV !== 'local' && process.env.APP_ENV !== 'test') {
  console.error(`Refusing: dev tokens are for APP_ENV=local/test only (APP_ENV=${process.env.APP_ENV}).`);
  process.exit(1);
}
if (!user) {
  console.error(`Unknown demo user "${who}". Use one of: ${Object.keys(demo.users).join(', ')}`);
  process.exit(1);
}
if (!process.env.AUTH_JWT_SECRET) {
  console.error('AUTH_JWT_SECRET is not set (backend/.env).');
  process.exit(1);
}

const token = signAccessToken(
  process.env.AUTH_JWT_SECRET,
  { userId: user.id, tenantId: demo.tenants[user.tenant].id, role: user.role },
  Math.round(hours * 3600),
);
console.error(`# ${user.email} (${demo.tenants[user.tenant].name}), valid ${hours} h`);
console.log(token);
