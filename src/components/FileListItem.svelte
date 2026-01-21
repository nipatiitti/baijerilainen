<script lang="ts">
  import Icon from '@iconify/svelte';
  import Button from './Button.svelte';
  import type { MotecFileMetadata } from '$lib/csv-parser';

  interface Props {
    name: string;
    metadata?: MotecFileMetadata | null;
    error?: string;
    onremove: () => void;
  }

  let { name, metadata, error, onremove }: Props = $props();
</script>

<div
  class="flex items-center justify-between rounded-lg p-4 {error
    ? 'border border-red-700 bg-red-900/30'
    : 'bg-gray-800'}"
>
  <div class="flex items-center gap-4">
    {#if error}
      <Icon icon="material-symbols:error-outline" class="h-6 w-6 text-red-500" />
    {:else}
      <Icon icon="material-symbols:check-circle-outline" class="h-6 w-6 text-green-500" />
    {/if}
    <div>
      <p class="font-medium">{name}</p>
      {#if error}
        <p class="text-sm text-red-400">{error}</p>
      {:else if metadata}
        <p class="text-sm text-gray-400">
          {metadata.rowCount} data points • {metadata.columns.length} columns •
          {metadata.metadata.duration}s duration
        </p>
      {/if}
    </div>
  </div>
  <Button variant="icon" aria-label="Remove file {name}" onclick={onremove}>
    <Icon icon="material-symbols:close" class="h-5 w-5" />
  </Button>
</div>
