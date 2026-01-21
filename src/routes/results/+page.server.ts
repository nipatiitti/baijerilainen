/**
 * Server load function to fetch all optimization result files
 */

import { readdir, readFile } from 'fs/promises';
import { join } from 'path';
import type { PageServerLoad } from './$types';
import { RESULTS_FOLDER, type OptimizationResults, type ResultFileSummary } from '$lib/types';


export const load: PageServerLoad = async () => {
  try {
    // Read all files in the results folder
    const files = await readdir(RESULTS_FOLDER);

    // Filter for optimization result JSON files and sort by name (timestamp)
    const resultFiles = files
      .filter((f) => f.startsWith('optimization_results_') && f.endsWith('.json'))
      .sort()
      .reverse(); // Most recent first

    // Load summary info for each file
    const results: ResultFileSummary[] = await Promise.all(
      resultFiles.map(async (filename) => {
        const filePath = join(RESULTS_FOLDER, filename);
        const content = await readFile(filePath, 'utf-8');
        const data: OptimizationResults = JSON.parse(content);

        return {
          filename,
          timestamp: data.metadata.timestamp,
          n_bins: data.data_summary.n_bins,
          best_bsfc: data.current_best.overall_bsfc,
          rpm_range: data.data_summary.rpm_range
        };
      })
    );

    return {
      results
    };
  } catch (e) {
    console.error('Error reading results folder:', e);
    return {
      results: []
    };
  }
};
