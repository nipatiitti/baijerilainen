import { json } from '@sveltejs/kit';
import { existsSync } from 'fs';
import { readdir, stat, unlink } from 'fs/promises';
import { join } from 'path';

const DATA_DIR = 'data';

export interface FileInfo {
  name: string;
  size: number;
  createdAt: string;
}

/**
 * GET /api/files - List all uploaded CSV files
 */
export const GET = async () => {
  try {
    if (!existsSync(DATA_DIR)) {
      return json({ files: [] });
    }

    const entries = await readdir(DATA_DIR);
    const csvFiles = entries.filter((f: string) => f.endsWith('.csv'));

    const files: FileInfo[] = await Promise.all(
      csvFiles.map(async (name: string) => {
        const filePath = join(DATA_DIR, name);
        const stats = await stat(filePath);
        return {
          name,
          size: stats.size,
          createdAt: stats.birthtime.toISOString()
        };
      })
    );

    // Sort by creation date, newest first
    files.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return json({ files });
  } catch (error) {
    console.error('Error listing files:', error);
    return json({ files: [], error: 'Failed to list files' }, { status: 500 });
  }
};

/**
 * DELETE /api/files - Delete a specific file
 */
export const DELETE: RequestHandler = async ({ request }) => {
  try {
    const { filename } = await request.json();

    if (!filename || typeof filename !== 'string') {
      return json({ error: 'Filename is required' }, { status: 400 });
    }

    // Security: prevent directory traversal
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      return json({ error: 'Invalid filename' }, { status: 400 });
    }

    const filePath = join(DATA_DIR, filename);

    if (!existsSync(filePath)) {
      return json({ error: 'File not found' }, { status: 404 });
    }

    await unlink(filePath);

    return json({ success: true, message: `Deleted ${filename}` });
  } catch (error) {
    console.error('Error deleting file:', error);
    return json({ error: error instanceof Error ? error.message : 'Failed to delete file' }, { status: 500 });
  }
};
