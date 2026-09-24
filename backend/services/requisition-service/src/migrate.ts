import { join } from 'node:path';
import { runMigrationsCli } from '@teamora/platform';

// dist/migrate.js -> ../db/migrations
void runMigrationsCli('requisition', join(__dirname, '..', 'db', 'migrations'));
