<script lang="ts">
  import { deserialize } from '$app/forms';
  import { goto } from '$app/navigation';
  import { DEFAULT_SELECTED_COLUMNS, type MotecFileMetadata } from '$lib/csv-parser';
  import type { ParseCSVResult } from './api/parse-csv/+server';

  import Button from '../components/Button.svelte';
  import FileUploadZone from '../components/FileUploadZone.svelte';
  import FileListItem from '../components/FileListItem.svelte';
  import Icon from '@iconify/svelte';

  interface FileData {
    name: string;
    file: File; // Keep the original file for later submission
    metadata: MotecFileMetadata | null;
    error?: string;
  }

  let files = $state<FileData[]>([]);
  let isProcessing = $state(false);
  let isSaving = $state(false);
  let processingCount = $state(0);
  let totalToProcess = $state(0);
  let dragOver = $state(false);
  let submitError = $state<string | null>(null);
  let submitSuccess = $state<string | null>(null);

  // Compute total data points and valid files
  let validFiles = $derived(files.filter((f) => !f.error && f.metadata !== null));
  let totalDataPoints = $derived(validFiles.reduce((sum, f) => sum + (f.metadata?.rowCount ?? 0), 0));

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

      // Add hardcoded columns
      formData.append('columns', JSON.stringify(DEFAULT_SELECTED_COLUMNS));

      // Add all valid original files
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
          submitSuccess = data.message ?? 'Data saved successfully! Starting optimization...';
          submitError = null;
          // Navigate to the run page to start optimization
          goto('/run');
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

  let canSubmit = $derived(validFiles.length > 0);
</script>

<div class="min-h-screen bg-gray-900 p-8 text-white">
  <div class="mx-auto max-w-6xl">
    <header class="mb-8 flex items-start justify-between">
      <div>
        <h1 class="text-3xl font-bold text-blue-400">ECU Optimization Data Uploader</h1>
        <p class="mt-2 text-gray-400">Upload MoTeC CSV files from your dyno runs to begin the optimization process</p>
      </div>
      <a
        href="/results"
        class="flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
      >
        <Icon icon="material-symbols:analytics-outline" width="20" height="20" />
        View Results
      </a>
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

        <!-- Data Summary -->
        <div class="mb-6 rounded-lg bg-gray-800 p-4">
          <h3 class="mb-3 font-semibold">Data Summary</h3>
          <div class="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <p class="text-gray-400">Files</p>
              <p class="text-lg font-medium">{validFiles.length}</p>
            </div>
            <div>
              <p class="text-gray-400">Total Data Points</p>
              <p class="text-lg font-medium">{totalDataPoints.toLocaleString()}</p>
            </div>
            <div>
              <p class="text-gray-400">Columns to Export</p>
              <p class="text-lg font-medium">{DEFAULT_SELECTED_COLUMNS.length}</p>
            </div>
            <div>
              <p class="text-gray-400">Sample Rate</p>
              <p class="text-lg font-medium">{validFiles[0]?.metadata?.metadata.sampleRate ?? 0} Hz</p>
            </div>
          </div>
        </div>

        <form onsubmit={handleSubmit}>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-semibold">Ready to Process</h3>
              <p class="text-sm text-gray-400">Data will be filtered and prepared for optimization</p>
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
