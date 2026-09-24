import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Client } from 'pg';
import { ConfigError, DatabaseConfig, loadMigratorConfig } from './config';

export interface MigrationOptions {
  /** The service's own schema, e.g. `identity`. Its migrations may only create objects there. */
  schema: string;
  /** Folder of `NNNN_description.sql` files, applied in file-name order. */
  dir: string;
  connection: DatabaseConfig;
  log?: (message: string) => void;
}

const MIGRATION_FILE = /^\d{4}_[a-z0-9_]+\.sql$/;
const IDENTIFIER = /^[a-z_][a-z0-9_]*$/;

/**
 * Applies pending SQL migrations for one service schema, each in its own transaction, recording
 * them in `<schema>.schema_migrations`. Runs as teamora_migrator so every table is owned by it and
 * service roles never own (and so never bypass Row-Level Security on) a table.
 * A per-schema advisory lock makes concurrent runs (two deploys at once) safe.
 */
export async function runMigrations(opts: MigrationOptions): Promise<string[]> {
  if (!IDENTIFIER.test(opts.schema)) throw new Error(`invalid schema name "${opts.schema}"`);
  const log = opts.log ?? (() => undefined);
  const table = `"${opts.schema}".schema_migrations`;
  const files = readdirSync(opts.dir)
    .filter((f) => MIGRATION_FILE.test(f))
    .sort();

  const client = new Client({ ...opts.connection, application_name: `migrate:${opts.schema}` });
  await client.connect();
  try {
    await client.query('SELECT pg_advisory_lock(hashtext($1))', [`teamora-migrate:${opts.schema}`]);
    await client.query(
      `CREATE TABLE IF NOT EXISTS ${table} (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())`,
    );
    // Default privileges grant service roles DML on new tables; the migration history is migrator-only.
    const { rows: grantees } = await client.query<{ grantee: string }>(
      `SELECT DISTINCT grantee FROM information_schema.role_table_grants
        WHERE table_schema = $1 AND table_name = 'schema_migrations' AND grantee <> current_user`,
      [opts.schema],
    );
    for (const { grantee } of grantees) {
      if (IDENTIFIER.test(grantee) || grantee === 'PUBLIC') {
        await client.query(`REVOKE ALL ON ${table} FROM ${grantee === 'PUBLIC' ? 'PUBLIC' : `"${grantee}"`}`);
      }
    }

    const { rows } = await client.query<{ version: string }>(`SELECT version FROM ${table}`);
    const applied = new Set(rows.map((r) => r.version));
    const done: string[] = [];
    for (const file of files) {
      const version = file.replace(/\.sql$/, '');
      if (applied.has(version)) continue;
      const sql = readFileSync(join(opts.dir, file), 'utf8');
      await client.query('BEGIN');
      try {
        await client.query(sql);
        await client.query(`INSERT INTO ${table} (version) VALUES ($1)`, [version]);
        await client.query('COMMIT');
      } catch (err) {
        await client.query('ROLLBACK').catch(() => undefined);
        throw new Error(`migration ${opts.schema}/${file} failed: ${(err as Error).message}`);
      }
      log(`applied ${opts.schema}/${file}`);
      done.push(version);
    }
    if (done.length === 0) log(`${opts.schema}: up to date (${files.length} migration(s))`);
    return done;
  } finally {
    await client.query('SELECT pg_advisory_unlock_all()').catch(() => undefined);
    await client.end();
  }
}

/** Entry point for a service's `src/migrate.ts`. */
export async function runMigrationsCli(schema: string, dir: string): Promise<void> {
  try {
    const connection = loadMigratorConfig();
    await runMigrations({ schema, dir, connection, log: (m) => console.log(m) });
  } catch (err) {
    console.error(err instanceof ConfigError ? err.message : `ERROR: ${(err as Error).message}`);
    process.exit(1);
  }
}
