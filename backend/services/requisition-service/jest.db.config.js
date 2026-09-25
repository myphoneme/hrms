// Database tests: run against a real bootstrapped + migrated `teamora` database (npm run test:db).
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testRegex: 'test/db/.*\\.db-spec\\.ts$',
  // Real database + app start-up: allow more than the 5 s default, and run files one at a time
  // so suites don't compete for connections on small CI runners.
  testTimeout: 30000,
  maxWorkers: 1,
};
