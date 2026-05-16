// Database factory - dynamically connects to configured provider

import type { DatabaseAdapter, DatabaseProvider } from './types';
import { MockDatabaseAdapter } from './mock-adapter';
import { PostgresAdapter } from './postgres-adapter';

// Singleton instance
let dbInstance: DatabaseAdapter | null = null;

// Determine provider from environment
function getProvider(): DatabaseProvider {
  // Check for specific database URLs
  if (process.env.DATABASE_URL) {
    const url = process.env.DATABASE_URL;
    if (url.includes('neon.tech')) return 'neon';
    if (url.includes('supabase')) return 'supabase';
    return 'postgres';
  }
  
  // Check for provider-specific env vars
  if (process.env.NEON_DATABASE_URL) return 'neon';
  if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) return 'supabase';
  if (process.env.POSTGRES_URL) return 'postgres';
  
  // Default to mock for development
  return 'mock';
}

// Get connection string based on provider
function getConnectionString(provider: DatabaseProvider): string {
  switch (provider) {
    case 'neon':
      return process.env.NEON_DATABASE_URL || process.env.DATABASE_URL || '';
    case 'supabase':
      // Supabase connection string format
      const supabaseUrl = process.env.SUPABASE_URL || '';
      const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';
      // Extract host from URL for direct Postgres connection
      if (process.env.SUPABASE_DB_URL) {
        return process.env.SUPABASE_DB_URL;
      }
      return process.env.DATABASE_URL || `postgresql://postgres:${supabaseKey}@${supabaseUrl.replace('https://', '')}.supabase.co:5432/postgres`;
    case 'postgres':
      return process.env.POSTGRES_URL || process.env.DATABASE_URL || '';
    default:
      return '';
  }
}

// Create adapter based on provider
function createAdapter(provider: DatabaseProvider): DatabaseAdapter {
  switch (provider) {
    case 'neon':
    case 'supabase':
    case 'postgres': {
      const connectionString = getConnectionString(provider);
      if (!connectionString) {
        console.warn(`No connection string found for ${provider}, falling back to mock`);
        return new MockDatabaseAdapter();
      }
      return new PostgresAdapter(connectionString);
    }
    case 'mock':
    default:
      return new MockDatabaseAdapter();
  }
}

// Get or create database instance
export async function getDatabase(): Promise<DatabaseAdapter> {
  if (dbInstance && dbInstance.isConnected()) {
    return dbInstance;
  }

  const provider = getProvider();
  console.log(`[Harpy.AI] Connecting to database provider: ${provider}`);
  
  dbInstance = createAdapter(provider);
  await dbInstance.connect();
  
  return dbInstance;
}

// Get provider info for display
export function getDatabaseInfo(): { provider: DatabaseProvider; isConnected: boolean } {
  return {
    provider: getProvider(),
    isConnected: dbInstance?.isConnected() ?? false,
  };
}

// Export types
export * from './types';
export { MockDatabaseAdapter } from './mock-adapter';
export { PostgresAdapter, INIT_SCHEMA } from './postgres-adapter';
