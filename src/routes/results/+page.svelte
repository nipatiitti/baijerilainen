<script lang="ts">
  import Icon from '@iconify/svelte';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  function extractDateFromFilename(filename: string): string {
    // Extract date from filename like: optimization_results_20260117_220436.json or optimization_results_2026-01-21_22-53-11.json
    const match1 = filename.match(/optimization_results_(\d{8})_(\d{6})\.json/);
    if (match1) {
      const date = match1[1];
      const time = match1[2];
      return `${date.slice(6, 8)}.${date.slice(4, 6)}.${date.slice(0, 4)} ${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`;
    }
    const match2 = filename.match(/optimization_results_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.json/);
    if (match2) {
      return `${match2[3]}.${match2[2]}.${match2[1]} ${match2[4]}:${match2[5]}:${match2[6]}`;
    }
    return filename;
  }
</script>

<div class="min-h-screen bg-gray-900 p-8 text-white">
  <div class="mx-auto max-w-4xl">
    <!-- Header -->
    <header class="mb-8">
      <div class="flex items-center gap-3">
        <a href="/" class="rounded-lg p-2 text-gray-400 hover:bg-gray-800 hover:text-white">
          <Icon icon="material-symbols:arrow-back-rounded" width="24" height="24" />
        </a>
        <div>
          <h1 class="text-3xl font-bold text-blue-400">Optimization Results</h1>
          <p class="mt-1 text-gray-400">Select a result file to view details</p>
        </div>
      </div>
    </header>

    {#if data.results.length === 0}
      <div class="rounded-lg border border-gray-700 bg-gray-800 p-8 text-center">
        <Icon icon="material-symbols:folder-off-outline" width="64" height="64" class="mx-auto mb-4 text-gray-600" />
        <h2 class="mb-2 text-xl font-semibold text-gray-300">No Results Found</h2>
        <p class="mb-4 text-gray-500">
          Run the Bayesian optimization to generate results, then come back here to view them.
        </p>
        <a
          href="/"
          class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-500"
        >
          <Icon icon="material-symbols:upload-file" width="20" height="20" />
          Upload Data
        </a>
      </div>
    {:else}
      <div class="space-y-3">
        {#each data.results as result (result.filename)}
          <a
            href="/results/{encodeURIComponent(result.filename.replace('.json', ''))}"
            class="group flex items-center justify-between rounded-lg bg-gray-800 p-4 transition-colors hover:bg-gray-700"
          >
            <div class="flex items-center gap-4">
              <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600/20">
                <Icon icon="material-symbols:analytics" width="24" height="24" class="text-blue-400" />
              </div>
              <div>
                <h3 class="font-medium text-white group-hover:text-blue-400">
                  {extractDateFromFilename(result.filename)}
                </h3>
                <p class="text-sm text-gray-400">
                  {result.n_bins} RPM bins • {result.rpm_range[0]} - {result.rpm_range[1]} RPM
                </p>
              </div>
            </div>
            <div class="flex items-center gap-6">
              <div class="text-right">
                <p class="text-sm text-gray-400">Best BSFC</p>
                <p class="font-medium text-green-400">{result.best_bsfc.toFixed(1)}</p>
              </div>
              <Icon
                icon="material-symbols:chevron-right"
                width="24"
                height="24"
                class="text-gray-500 group-hover:text-white"
              />
            </div>
          </a>
        {/each}
      </div>
    {/if}
  </div>
</div>
