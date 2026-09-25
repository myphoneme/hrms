// Loads demo data into the LOCAL database for manual checks.
// Usage (requisition-service must be running: npm run start:requisition):
//   npm run dev:seed            -> seeds once; later runs report what's there
//   npm run dev:seed -- --force -> adds another set of demo requisitions
//
// 1. Demo tenants, clients and users are inserted directly (there is no admin API yet) as the
//    PostgreSQL superuser from backend/.env (PGHOST/PGPORT/PGUSER/PGPASSWORD). Safe to re-run.
// 2. Demo requisitions, JD versions and scoring matrices are created THROUGH THE API, so every
//    business rule (HR-M1-FR-007/004/006) applies to them exactly as to real data.
const { Client } = require('pg');
const { signAccessToken } = require('../packages/platform/dist');
const demo = require('./demo');

const force = process.argv.includes('--force');

async function main() {
  if (process.env.APP_ENV !== 'local') {
    throw new Error(`Refusing: demo data is for APP_ENV=local only (APP_ENV=${process.env.APP_ENV}).`);
  }

  const db = new Client({ database: 'teamora' }); // PGHOST/PGPORT/PGUSER/PGPASSWORD from backend/.env
  await db.connect();
  try {
    await seedIdentity(db);
    const { rows } = await db.query('SELECT count(*)::int AS n FROM requisition.job_requisition WHERE tenant_id = ANY($1)', [
      Object.values(demo.tenants).map((t) => t.id),
    ]);
    if (rows[0].n > 0 && !force) {
      console.log(`\nDemo requisitions already exist (${rows[0].n}). Use "npm run dev:seed -- --force" to add another set.`);
    } else {
      await assertApiUp();
      await seedRequisitions();
    }
    await printSummary(db);
  } finally {
    await db.end();
  }
}

async function seedIdentity(db) {
  for (const t of Object.values(demo.tenants)) {
    await db.query('INSERT INTO identity.tenant (id, org_type, name) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING', [t.id, t.orgType, t.name]);
  }
  for (const c of Object.values(demo.clients)) {
    await db.query('INSERT INTO identity.client (id, agency_tenant_id, name) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING', [
      c.id,
      demo.tenants[c.tenant].id,
      c.name,
    ]);
  }
  for (const u of Object.values(demo.users)) {
    await db.query(
      "INSERT INTO identity.app_user (id, tenant_id, email, auth_method, role) VALUES ($1, $2, $3, 'sso_google', $4) ON CONFLICT DO NOTHING",
      [u.id, demo.tenants[u.tenant].id, u.email, u.role],
    );
  }
  console.log('Identity: 2 tenants, 2 agency clients, 2 managers - ready.');
}

async function assertApiUp() {
  try {
    const res = await fetch(`${demo.REQUISITION_API}/health/ready`);
    if (res.ok) return;
  } catch {
    /* fall through */
  }
  throw new Error(`requisition-service is not reachable at ${demo.REQUISITION_API}. Start it first: npm run start:requisition`);
}

function apiAs(who) {
  const user = demo.users[who];
  const token = signAccessToken(process.env.AUTH_JWT_SECRET, { userId: user.id, tenantId: demo.tenants[user.tenant].id, role: user.role }, 600);
  return async (method, path, body) => {
    const res = await fetch(`${demo.REQUISITION_API}/api/v1${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const json = await res.json().catch(() => null);
    if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${JSON.stringify(json)}`);
    return json;
  };
}

/** Creates a requisition with one JD version and (optionally) matrix criteria; returns ids + revision. */
async function requisitionWithVersion(call, { tenant, client, brief, jd, variant, criteria = [] }) {
  const { requisition_id: r } = await call('POST', '/requisitions/intake', {
    tenant_id: demo.tenants[tenant].id,
    client_id: client ? demo.clients[client].id : null,
    raw_brief_text: brief,
    source: 'portal',
  });
  const v = await call('POST', `/requisitions/${r}/jd-versions`, { content: jd, variant_type: variant });
  const revision = await addCriteria(call, r, v.id, criteria);
  return { r, v: v.id, revision };
}

async function addCriteria(call, r, v, criteria) {
  let { matrix_revision: revision } = await call('GET', `/requisitions/${r}/jd-versions/${v}/scoring-matrix/draft`);
  for (const [category, criterion_name, weight_percent] of criteria) {
    ({ matrix_revision: revision } = await call('POST', `/requisitions/${r}/jd-versions/${v}/scoring-matrix/draft/criteria`, {
      matrix_revision: revision,
      category,
      criterion_name,
      weight_percent,
    }));
  }
  return revision;
}

async function seedRequisitions() {
  const agency = apiAs('agency');
  const employer = apiAs('employer');

  // 1. Agency / Retail Co: frozen v1, plus a v2 revision under review whose matrix totals only 90%.
  const analyst = await requisitionWithVersion(agency, {
    tenant: 'agency',
    client: 'retail',
    brief: 'Need a senior data analyst for Retail Co: Power BI, SQL, 5+ years, retail domain, graduate.',
    jd: 'Senior Data Analyst (Retail Co). Own sales and inventory dashboards in Power BI; write production SQL; partner with category managers. 5+ years of analytics experience in retail.',
    variant: 'formal',
    criteria: [
      ['core_skills', 'Power BI and SQL', 45],
      ['experience_seniority', '5+ years analytics', 30],
      ['domain_competency', 'Retail / category management', 20],
      ['education_fit', 'Graduate degree', 5],
    ],
  });
  await agency('POST', `/requisitions/${analyst.r}/jd-versions/${analyst.v}/submit`);
  await agency('POST', `/requisitions/${analyst.r}/freeze`, { approved_version_id: analyst.v, expected_active_version_id: null });
  const v2 = await agency('POST', `/requisitions/${analyst.r}/jd-versions`, {
    content: 'Senior Data Analyst (Retail Co) - revised: adds Python for forecasting; hybrid, 3 days on site.',
    variant_type: 'manager_edited',
    based_on_version_id: analyst.v,
  });
  await addCriteria(agency, analyst.r, v2.id, [
    ['core_skills', 'Power BI, SQL and Python', 60],
    ['experience_seniority', '5+ years analytics', 30],
  ]);

  // 2. Agency / Fintech Co: just a first draft, empty matrix.
  await requisitionWithVersion(agency, {
    tenant: 'agency',
    client: 'fintech',
    brief: 'Fintech Co wants a backend engineer - Node.js, PostgreSQL, payments experience a plus.',
    jd: 'Backend Engineer (Fintech Co). Build payment APIs in Node.js and PostgreSQL. 3+ years.',
    variant: 'candidate_friendly',
  });

  // 3. Direct employer: waiting for approval with a complete (100%) matrix - ready for you to freeze.
  const hr = await requisitionWithVersion(employer, {
    tenant: 'employer',
    client: null,
    brief: 'HR executive for our Pune office: onboarding, payroll coordination, 2-4 years.',
    jd: 'HR Executive (Pune). Run onboarding end to end and coordinate payroll inputs. 2-4 years in HR operations.',
    variant: 'formal',
    criteria: [
      ['core_skills', 'Onboarding and HR operations', 50],
      ['experience_seniority', '2-4 years HR', 25],
      ['domain_competency', 'Payroll coordination', 20],
      ['education_fit', 'MBA / PG in HR', 5],
    ],
  });
  await employer('POST', `/requisitions/${hr.r}/jd-versions/${hr.v}/submit`);
  console.log('Demo requisitions created through the API.');
}

async function printSummary(db) {
  const { rows } = await db.query(
    `SELECT t.name AS tenant, coalesce(c.name, '-') AS client, r.id, r.status,
            (SELECT count(*) FROM requisition.jd_version v WHERE v.requisition_id = r.id)::int AS versions
       FROM requisition.job_requisition r
       JOIN identity.tenant t ON t.id = r.tenant_id
       LEFT JOIN identity.client c ON c.id = r.client_id
      WHERE r.tenant_id = ANY($1)
      ORDER BY r.created_at`,
    [Object.values(demo.tenants).map((t) => t.id)],
  );
  console.log('\nDemo requisitions:');
  console.table(rows);
  console.log('Browse them: http://localhost:3002/api/docs  (Authorize with a token from "npm run dev:token")');
}

main().catch((err) => {
  console.error(`ERROR: ${err.message}`);
  process.exit(1);
});
