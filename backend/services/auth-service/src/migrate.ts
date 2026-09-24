import { join } from 'node:path';
import { runMigrationsCli } from '@teamora/platform';

// dist/migrate.js -> ../db/migrations
void runMigrationsCli('identity', join(__dirname, '..', 'db', 'migrations'));
