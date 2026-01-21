/**
 * Server load function to fetch a specific optimization result file
 */

import { error } from '@sveltejs/kit';
import { readFile } from 'fs/promises';
import { join } from 'path';
import type { PageServerLoad } from './$types';
import { RESULTS_FOLDER, type OptimizationResults } from '$lib/types';


export const load: PageServerLoad = async ({ params }) => {
  const name = decodeURIComponent(params.name);

  // Validate filename format to prevent directory traversal (name without .json)
  // Supports both formats: optimization_results_20260121_220436 and optimization_results_2026-01-21_22-53-11
  if (!name.match(/^optimization_results_(\d{8}|\d{4}-\d{2}-\d{2})_(\d{6}|\d{2}-\d{2}-\d{2})$/)) {
    throw error(400, 'Invalid filename format');
  }

  const filename = `${name}.json`;

  try {
    const filePath = join(RESULTS_FOLDER, filename);
    const content = await readFile(filePath, 'utf-8');
    const results: OptimizationResults = JSON.parse(content);

    return {
      filename,
      results
    };
  } catch (e) {
    console.error('Error reading result file:', e);
    throw error(404, 'Result file not found');
  }
};
