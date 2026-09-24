// Fixed IDs of the local demo data, shared by seed.js, token.js and requests.http.
// Local development only — never used on staging or production.
module.exports = {
  REQUISITION_API: 'http://localhost:3002',
  tenants: {
    agency: { id: '11111111-1111-4111-8111-111111111111', orgType: 'staffing_agency', name: 'Demo Staffing Agency' },
    employer: { id: '44444444-4444-4444-8444-444444444444', orgType: 'direct_employer', name: 'Demo Direct Employer' },
  },
  clients: {
    retail: { id: '22222222-2222-4222-8222-222222222222', tenant: 'agency', name: 'Retail Co (demo client)' },
    fintech: { id: '22222222-2222-4222-8222-222222222223', tenant: 'agency', name: 'Fintech Co (demo client)' },
  },
  users: {
    agency: { id: '33333333-3333-4333-8333-333333333333', tenant: 'agency', email: 'manager@agency.demo', role: 'manager' },
    employer: { id: '55555555-5555-4555-8555-555555555555', tenant: 'employer', email: 'manager@employer.demo', role: 'manager' },
  },
};
