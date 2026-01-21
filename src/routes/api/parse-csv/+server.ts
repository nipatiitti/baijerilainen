import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { extractMotecMetadata, validateMotecCSV, type MotecFileMetadata } from '$lib/csv-parser';

export interface ParseCSVResponse {
	success: true;
	filename: string;
	metadata: MotecFileMetadata;
}

export interface ParseCSVError {
	success: false;
	filename: string;
	error: string;
}

export type ParseCSVResult = ParseCSVResponse | ParseCSVError;

export const POST: RequestHandler = async ({ request }) => {
	try {
		const formData = await request.formData();
		const file = formData.get('file') as File | null;

		if (!file) {
			return json({ success: false, filename: '', error: 'No file provided' } satisfies ParseCSVError, { status: 400 });
		}

		const filename = file.name;

		// Check file extension
		if (!filename.endsWith('.csv')) {
			return json({ success: false, filename, error: 'File must be a CSV' } satisfies ParseCSVError);
		}

		// Read file content
		const content = await file.text();

		// Validate it's a MoTeC file
		const validation = validateMotecCSV(content);
		if (!validation.valid) {
			return json({ success: false, filename, error: validation.error ?? 'Invalid MoTeC CSV' } satisfies ParseCSVError);
		}

		// Extract only metadata (no data matrix)
		const metadata = extractMotecMetadata(content);

		return json({ success: true, filename, metadata } satisfies ParseCSVResponse);
	} catch (e) {
		const errorMessage = e instanceof Error ? e.message : 'Failed to parse file';
		return json({ success: false, filename: '', error: errorMessage } satisfies ParseCSVError, { status: 500 });
	}
};
