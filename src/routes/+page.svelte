<script lang="ts">
  import { flip } from 'svelte/animate';
  import { SvelteMap, SvelteSet } from 'svelte/reactivity';
  import { deserialize } from '$app/forms';
  import { DEFAULT_SELECTED_COLUMNS, type MotecFileMetadata, type ColumnInfo } from '$lib/csv-parser';
  import type { ParseCSVResult } from './api/parse-csv/+server';

  import Icon from '@iconify/svelte';
  import Button from '../components/Button.svelte';
  import FileUploadZone from '../components/FileUploadZone.svelte';
  import FileListItem from '../components/FileListItem.svelte';
  import Checkbox from '../components/Checkbox.svelte';

  interface FileData {
    name: string;
    file: File; // Keep the original file for later submission
    metadata: MotecFileMetadata | null;
    error?: string;
  }

  let files = $state<FileData[]>([]);
  let selectedColumns = new SvelteSet<string>(DEFAULT_SELECTED_COLUMNS);
  let isProcessing = $state(false);
  let isSaving = $state(false);
  let processingCount = $state(0);
  let totalToProcess = $state(0);
  let dragOver = $state(false);
  let submitError = $state<string | null>(null);
  let submitSuccess = $state<string | null>(null);
  let columnSearch = $state('');

  // All available columns from all files (merged)
  let availableColumns = $derived.by<ColumnInfo[]>(() => {
    const columnMap = new SvelteMap<string, ColumnInfo>();
    for (const file of files) {
      if (!file.metadata) continue;
      for (const col of file.metadata.columns) {
        if (!columnMap.has(col.name)) {
          columnMap.set(col.name, col);
        }
      }
    }
    return Array.from(columnMap.values());
  });

  // Filtered and sorted columns: selected first, then filtered by search
  let filteredColumns = $derived.by(() => {
    let cols = availableColumns;

    // Filter by search
    if (columnSearch.trim()) {
      const search = columnSearch.toLowerCase();
      cols = cols.filter((col) => col.name.toLowerCase().includes(search) || col.unit.toLowerCase().includes(search));
    }

    // Sort: selected columns first, then alphabetically within each group
    return cols.toSorted((a, b) => {
      const aSelected = selectedColumns.has(a.name);
      const bSelected = selectedColumns.has(b.name);

      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      return a.name.localeCompare(b.name);
    });
  });

  /**
   * Parse a single file via the API route (metadata only)
   */
  async function parseFileViaAPI(file: File): Promise<FileData> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/parse-csv', {
        method: 'POST',
        body: formData
      });

      const result: ParseCSVResult = await response.json();

      if (result.success) {
        return {
          name: result.filename,
          file: file, // Keep original file
          metadata: result.metadata
        };
      } else {
        return {
          name: result.filename || file.name,
          file: file,
          metadata: null,
          error: result.error
        };
      }
    } catch (e) {
      return {
        name: file.name,
        file: file,
        metadata: null,
        error: e instanceof Error ? e.message : 'Failed to parse file'
      };
    }
  }

  /**
   * Process all files simultaneously via the API
   */
  async function processFiles(fileList: File[]) {
    isProcessing = true;
    submitError = null;
    submitSuccess = null;
    totalToProcess = fileList.length;
    processingCount = 0;

    // Process all files simultaneously
    const promises = fileList.map(async (file) => {
      const result = await parseFileViaAPI(file);
      processingCount++;
      return result;
    });

    const results = await Promise.all(promises);

    // Add all results to files array
    files = [...files, ...results];

    isProcessing = false;
    totalToProcess = 0;
    processingCount = 0;
  }

  function removeFile(index: number) {
    files = files.filter((_, i) => i !== index);
  }

  function toggleColumn(name: string) {
    if (selectedColumns.has(name)) {
      selectedColumns.delete(name);
    } else {
      selectedColumns.add(name);
    }
  }

  function selectAll() {
    for (const col of filteredColumns) {
      selectedColumns.add(col.name);
    }
  }

  function deselectAll() {
    for (const col of filteredColumns) {
      selectedColumns.delete(col.name);
    }
  }

  /**
   * Submit files with selected columns for server-side processing
   */
  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();

    isSaving = true;
    submitError = null;
    submitSuccess = null;

    try {
      const formData = new FormData();

      // Add selected columns
      formData.append('columns', JSON.stringify(Array.from(selectedColumns)));

      // Add all valid original files
      const validFiles = files.filter((f) => !f.error && f.metadata !== null);
      for (const fileData of validFiles) {
        formData.append('files', fileData.file);
      }

      const response = await fetch('?/saveData', {
        method: 'POST',
        body: formData
      });

      const result = deserialize(await response.text());

      if (result.type === 'success' && result.data) {
        const data = result.data as { success: boolean; message?: string; error?: string };
        if (data.success) {
          submitSuccess = data.message ?? 'Data saved successfully! Ready for optimization.';
          submitError = null;
        } else {
          submitError = data.error ?? 'Failed to save data';
          submitSuccess = null;
        }
      } else if (result.type === 'failure') {
        const data = result.data as { error?: string } | undefined;
        submitError = data?.error ?? 'Failed to save data';
        submitSuccess = null;
      } else {
        submitError = 'Unexpected response from server';
        submitSuccess = null;
      }
    } catch (e) {
      submitError = e instanceof Error ? e.message : 'Failed to save data';
      submitSuccess = null;
    } finally {
      isSaving = false;
    }
  }

  let canSubmit = $derived(files.some((f) => !f.error && f.metadata) && selectedColumns.size > 0);
</script>

<div class="min-h-screen bg-gray-900 p-8 text-white">
  <div class="mx-auto max-w-6xl">
    <header class="mb-8">
      <h1 class="text-3xl font-bold text-blue-400">ECU Optimization Data Uploader</h1>
      <p class="mt-2 text-gray-400">Upload MoTeC CSV files from your dyno runs to begin the optimization process</p>
    </header>

    <!-- File Upload Area -->
    <section class="mb-8">
      <FileUploadZone bind:dragOver onfiles={processFiles} />
    </section>

    {#if isProcessing}
      <div class="py-8 text-center">
        <div class="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-400 border-t-transparent"></div>
        <p class="mt-4 text-gray-400">
          Processing files... {processingCount}/{totalToProcess}
        </p>
      </div>
    {/if}

    <!-- Uploaded Files List -->
    {#if files.length > 0}
      <section class="mb-8">
        <h2 class="mb-4 text-xl font-semibold">Uploaded Files</h2>
        <div class="space-y-2">
          {#each files as file, i (file.name)}
            <FileListItem name={file.name} metadata={file.metadata} error={file.error} onremove={() => removeFile(i)} />
          {/each}
        </div>
      </section>
    {/if}

    <!-- Column Selection -->
    {#if availableColumns.length > 0}
      <section class="mb-8">
        <h2 class="mb-4 text-xl font-semibold">Select Columns to Export</h2>
        <p class="mb-4 text-gray-400">
          Choose the data columns you want to include in the optimization. Key columns for BSFC optimization are
          pre-selected.
        </p>

        <!-- Search and actions -->
        <div class="mb-4 flex flex-wrap items-center gap-4">
          <input
            type="text"
            placeholder="Search columns..."
            bind:value={columnSearch}
            class="min-w-50 flex-1 rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
          />
          <div class="flex gap-2">
            <Button variant="icon" type="button" onclick={selectAll} title="Select All">
              <Icon icon="material-symbols:library-add-check-outline-rounded" width="24" height="24" />
            </Button>
            <Button variant="icon" type="button" onclick={deselectAll} title="Deselect All">
              <Icon icon="material-symbols:check-box-outline-blank" width="24" height="24" />
            </Button>
          </div>
        </div>

        <!-- Column list -->
        <div class="rounded-lg bg-gray-800 p-4">
          <div class="grid max-h-96 grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
            {#each filteredColumns as col (col.name)}
              <div animate:flip={{ duration: 200 }}>
                <Checkbox checked={selectedColumns.has(col.name)} onchange={() => toggleColumn(col.name)}>
                  <span class="truncate">{col.name}</span>
                  {#if col.unit}
                    <span class="ml-1 text-xs text-gray-500">({col.unit})</span>
                  {/if}
                </Checkbox>
              </div>
            {/each}
          </div>

          {#if filteredColumns.length === 0}
            <p class="py-4 text-center text-gray-500">No columns match your search</p>
          {/if}
        </div>

        <p class="mt-4 text-sm text-gray-500">
          {selectedColumns.size} of {availableColumns.length} columns selected
        </p>
      </section>
    {/if}

    <!-- Submit Section -->
    {#if canSubmit}
      <section class="border-t border-gray-700 pt-8">
        {#if submitError}
          <div class="mb-4 rounded-lg border border-red-700 bg-red-900/30 p-4 text-red-400">
            {submitError}
          </div>
        {/if}

        {#if submitSuccess}
          <div class="mb-4 rounded-lg border border-green-700 bg-green-900/30 p-4 text-green-400">
            {submitSuccess}
          </div>
        {/if}

        <form onsubmit={handleSubmit}>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-semibold">Ready to Process</h3>
              <p class="text-sm text-gray-400">
                {files.filter((f) => !f.error).length} file(s) with
                {selectedColumns.size} columns each
              </p>
            </div>
            <Button variant="success" type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save & Continue'}
            </Button>
          </div>
        </form>
      </section>
    {/if}
  </div>
</div>
