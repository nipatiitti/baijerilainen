/**
 * MoTeC CSV Parser
 * Parses MoTeC M1 ECU CSV exports with metadata headers
 */

export interface MotecMetadata {
	format: string;
	venue: string;
	vehicle: string;
	driver: string;
	device: string;
	comment: string;
	logDate: string;
	logTime: string;
	sampleRate: number;
	duration: number;
	session: string;
}

export interface ColumnInfo {
	name: string;
	unit: string;
	index: number;
}

/**
 * Lightweight metadata extracted from a MoTeC CSV
 * Does NOT include the data matrix - for frontend display only
 */
export interface MotecFileMetadata {
	metadata: MotecMetadata;
	columns: ColumnInfo[];
	headers: string[];
	units: string[];
	rowCount: number;
}

/**
 * Full parsed MoTeC CSV including data matrix
 * Used only server-side for processing
 */
export interface ParsedMotecCSV extends MotecFileMetadata {
	data: string[][];
}

// Default columns that should be pre-selected for optimization
export const DEFAULT_SELECTED_COLUMNS = [
	'Time',
	'Engine Speed',
	'Fuel Mixture Aim',
	'Ignition Timing Main',
	'Dyno Brake Specific Fuel Consumption',
];

/**
 * Parse a MoTeC CSV file content
 */
export function parseMotecCSV(content: string): ParsedMotecCSV {
	const lines = content.split('\n').map((line) => line.trim());

	// Parse metadata from header rows (first 12-13 rows)
	const metadata = parseMetadata(lines);

	// Find the header row (contains column names)
	// It's the first row after metadata that has many columns
	let headerRowIndex = -1;
	for (let i = 0; i < Math.min(20, lines.length); i++) {
		const cols = parseCSVLine(lines[i] ?? '');
		// Header row typically has many columns (>10) and starts with "Time"
		if (cols.length > 10 && cols[0] === 'Time') {
			headerRowIndex = i;
			break;
		}
	}

	if (headerRowIndex === -1) {
		throw new Error('Could not find header row in CSV. Expected a row starting with "Time".');
	}

	const headers = parseCSVLine(lines[headerRowIndex] ?? '');
	const units = parseCSVLine(lines[headerRowIndex + 1] ?? '');

	// Build column info
	const columns: ColumnInfo[] = headers.map((name, index) => ({
		name,
		unit: units[index] ?? '',
		index
	}));

	// Parse data rows (skip header, units, and empty line after units)
	const dataStartIndex = headerRowIndex + 3; // +1 for units, +1 for empty line, +1 for first data
	const data: string[][] = [];

	for (let i = dataStartIndex; i < lines.length; i++) {
		const line = lines[i];
		if (!line || line.trim() === '') continue;

		const row = parseCSVLine(line);
		if (row.length === headers.length) {
			data.push(row);
		}
	}

	return {
		metadata,
		columns,
		headers,
		units,
		data,
		rowCount: data.length
	};
}

/**
 * Parse metadata from the first rows of a MoTeC CSV
 */
function parseMetadata(lines: string[]): MotecMetadata {
	const getValue = (line: string, index = 1): string => {
		const parts = parseCSVLine(line);
		return parts[index] ?? '';
	};

	const getNumericValue = (line: string, index = 1): number => {
		const val = getValue(line, index);
		return parseFloat(val) || 0;
	};

	return {
		format: getValue(lines[0] ?? '', 1),
		venue: getValue(lines[1] ?? '', 1),
		vehicle: getValue(lines[2] ?? '', 1),
		driver: getValue(lines[3] ?? '', 1),
		device: getValue(lines[4] ?? '', 1),
		comment: getValue(lines[5] ?? '', 1),
		logDate: getValue(lines[6] ?? '', 1),
		logTime: getValue(lines[7] ?? '', 1),
		sampleRate: getNumericValue(lines[8] ?? '', 1),
		duration: getNumericValue(lines[9] ?? '', 1),
		session: getValue(lines[5] ?? '', 5) // Session is in a different position
	};
}

/**
 * Parse a CSV line handling quoted values
 */
function parseCSVLine(line: string): string[] {
	const result: string[] = [];
	let current = '';
	let inQuotes = false;

	for (let i = 0; i < line.length; i++) {
		const char = line[i];

		if (char === '"') {
			inQuotes = !inQuotes;
		} else if (char === ',' && !inQuotes) {
			result.push(current.trim());
			current = '';
		} else {
			current += char;
		}
	}

	result.push(current.trim());
	return result;
}

/**
 * Create a simplified CSV with only selected columns
 * Filters out rows where Engine Speed is 0 (engine not running)
 */
export function createSimplifiedCSV(
	parsed: ParsedMotecCSV,
	selectedColumns: string[]
): string {
	// Find indices of selected columns
	const indices = selectedColumns
		.map((name) => parsed.headers.indexOf(name))
		.filter((i) => i !== -1);

	if (indices.length === 0) {
		throw new Error('No valid columns selected');
	}

	// Find Engine Speed column index for filtering
	const engineSpeedIndex = parsed.headers.indexOf('Engine Speed');

	// Build CSV content
	const lines: string[] = [];

	// Add header row
	const headerRow = indices.map((i) => `"${parsed.headers[i]}"`).join(',');
	lines.push(headerRow);

	// Add units row
	const unitsRow = indices.map((i) => `"${parsed.units[i] ?? ''}"`).join(',');
	lines.push(unitsRow);

	// Add data rows (filter out rows where engine speed is 0 or empty)
	for (const row of parsed.data) {
		// Skip rows where engine is not running
		if (engineSpeedIndex !== -1) {
			const engineSpeed = parseFloat(row[engineSpeedIndex] ?? '0');
			if (engineSpeed === 0 || isNaN(engineSpeed)) {
				continue;
			}
		}

		const dataRow = indices.map((i) => row[i] ?? '').join(',');
		lines.push(dataRow);
	}

	return lines.join('\n');
}

/**
 * Validate that a file looks like a MoTeC CSV
 */
export function validateMotecCSV(content: string): { valid: boolean; error?: string } {
	const firstLine = content.split('\n')[0] ?? '';

	if (!firstLine.includes('MoTeC CSV File')) {
		return {
			valid: false,
			error: 'File does not appear to be a MoTeC CSV export. First line should contain "MoTeC CSV File".'
		};
	}

	return { valid: true };
}

/**
 * Extract only metadata from a MoTeC CSV (no data matrix)
 * This is much faster and lighter for frontend use
 */
export function extractMotecMetadata(content: string): MotecFileMetadata {
	const lines = content.split('\n').map((line) => line.trim());

	// Parse metadata from header rows
	const metadata = parseMetadata(lines);

	// Find the header row
	let headerRowIndex = -1;
	for (let i = 0; i < Math.min(20, lines.length); i++) {
		const cols = parseCSVLine(lines[i] ?? '');
		if (cols.length > 10 && cols[0] === 'Time') {
			headerRowIndex = i;
			break;
		}
	}

	if (headerRowIndex === -1) {
		throw new Error('Could not find header row in CSV. Expected a row starting with "Time".');
	}

	const headers = parseCSVLine(lines[headerRowIndex] ?? '');
	const units = parseCSVLine(lines[headerRowIndex + 1] ?? '');

	// Build column info
	const columns: ColumnInfo[] = headers.map((name, index) => ({
		name,
		unit: units[index] ?? '',
		index
	}));

	// Count data rows without parsing them fully
	const dataStartIndex = headerRowIndex + 3;
	let rowCount = 0;
	for (let i = dataStartIndex; i < lines.length; i++) {
		const line = lines[i];
		if (line && line.trim() !== '') {
			rowCount++;
		}
	}

	return {
		metadata,
		columns,
		headers,
		units,
		rowCount
	};
}

/**
 * Process a raw CSV content with selected columns and filtering
 * This is the main server-side processing function
 */
export function processMotecCSV(
	content: string,
	selectedColumns: string[]
): string {
	// Parse the full CSV
	const parsed = parseMotecCSV(content);
	
	// Use the existing simplified CSV function
	return createSimplifiedCSV(parsed, selectedColumns);
}
