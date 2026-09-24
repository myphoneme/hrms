// Database tests: run against a real bootstrapped + migrated `teamora` database (npm run test:db).
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testRegex: 'test/db/.*\\.db-spec\\.ts$',
};
