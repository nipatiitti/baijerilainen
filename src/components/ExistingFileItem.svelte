<script lang="ts">
  import Icon from '@iconify/svelte';
  import type { FileInfo } from '../routes/api/files/+server';
  import Button from './Button.svelte';

  interface Props {
    file: FileInfo;
    ondelete: () => void;
    isDeleting?: boolean;
  }

  let { file, ondelete, isDeleting = false }: Props = $props();

  // Format file size
  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // Format date
  function formatDate(isoString: string): string {
    const date = new Date(isoString);
    return date.toLocaleDateString('fi-FI', {
      day: 'numeric',
      month: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Extract original filename from the timestamped name
  function getDisplayName(name: string): string {
    // Format: 2026-01-30T21-30-00-000Z_original_name.csv
    const parts = name.split('_');
    if (parts.length > 1 && parts[0]?.match(/^\d{4}-\d{2}-\d{2}T/)) {
      return parts.slice(1).join('_');
    }
    return name;
  }
</script>

<div class="hover:bg-gray-750 flex items-center justify-between rounded-lg bg-gray-800 p-4 transition-colors">
  <div class="flex items-center gap-4">
    <Icon icon="material-symbols:csv-outline" class="h-6 w-6 text-blue-400" />
    <div>
      <p class="font-medium" title={file.name}>{getDisplayName(file.name)}</p>
      <p class="text-sm text-gray-400">
        {formatSize(file.size)} • Uploaded {formatDate(file.createdAt)}
      </p>
    </div>
  </div>
  <Button variant="icon" aria-label="Delete file {file.name}" onclick={ondelete} disabled={isDeleting}>
    {#if isDeleting}
      <div class="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent"></div>
    {:else}
      <Icon icon="material-symbols:delete-outline" class="h-5 w-5 text-red-400" />
    {/if}
  </Button>
</div>
