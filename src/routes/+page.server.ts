import { fail } from '@sveltejs/kit';
import { writeFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import type { Actions } from './$types';
import { processMotecCSV, validateMotecCSV } from '$lib/csv-parser';

const DATA_DIR = 'data';

export const actions = {
	saveData: async ({ request }) => {
		try {
			const formData = await request.formData();
			
			// Get selected columns
			const columnsStr = formData.get('columns');
			if (!columnsStr || typeof columnsStr !== 'string') {
				return fail(400, { error: 'No columns selected' });
			}

			let selectedColumns: string[];
			try {
				selectedColumns = JSON.parse(columnsStr);
			} catch {
				return fail(400, { error: 'Invalid columns format' });
			}

			if (!Array.isArray(selectedColumns) || selectedColumns.length === 0) {
				return fail(400, { error: 'No columns selected' });
			}

			// Get all uploaded files
			const files = formData.getAll('files') as File[];
			
			if (files.length === 0) {
				return fail(400, { error: 'No files provided' });
			}

			// Ensure data directory exists
			if (!existsSync(DATA_DIR)) {
				await mkdir(DATA_DIR, { recursive: true });
			}

			const savedFiles: string[] = [];
			const errors: string[] = [];

			for (const file of files) {
				if (!(file instanceof File) || !file.name) {
					continue;
				}

				try {
					// Read the original file content
					const content = await file.text();

					// Validate it's a MoTeC file
					const validation = validateMotecCSV(content);
					if (!validation.valid) {
						errors.push(`${file.name}: ${validation.error}`);
						continue;
					}

					// Process the CSV (filter columns, remove Engine Speed 0 rows)
					const processedCSV = processMotecCSV(content, selectedColumns);

					// Sanitize filename
					const safeName = file.name
						.replace(/[^a-zA-Z0-9._-]/g, '_')
						.replace(/_{2,}/g, '_');

					// Add timestamp prefix to avoid overwrites
					const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
					const finalName = `${timestamp}_${safeName}`;
					const filePath = join(DATA_DIR, finalName);

					await writeFile(filePath, processedCSV, 'utf-8');
					savedFiles.push(finalName);
				} catch (e) {
					const errorMsg = e instanceof Error ? e.message : 'Unknown error';
					errors.push(`${file.name}: ${errorMsg}`);
				}
			}

			if (savedFiles.length === 0) {
				return fail(400, { 
					error: errors.length > 0 
						? `Failed to process files: ${errors.join('; ')}` 
						: 'No files were saved'
				});
			}

			return {
				success: true,
				savedFiles,
				errors: errors.length > 0 ? errors : undefined,
				message: `Successfully saved ${savedFiles.length} file(s)${errors.length > 0 ? ` (${errors.length} failed)` : ''}`
			};
		} catch (error) {
			console.error('Error saving data:', error);
			return fail(500, {
				error: error instanceof Error ? error.message : 'Failed to save data'
			});
		}
	}
} satisfies Actions;
