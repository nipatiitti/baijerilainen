<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '@iconify/svelte';

  interface LogEntry {
    type: 'info' | 'stdout' | 'stderr';
    message: string;
    timestamp: Date;
  }

  let logs = $state<LogEntry[]>([]);
  let isRunning = $state(true);
  let isComplete = $state(false);
  let hasError = $state(false);
  let terminalElement: HTMLDivElement;

  // Auto-scroll to bottom when new logs arrive
  $effect(() => {
    if (logs.length > 0 && terminalElement) {
      terminalElement.scrollTop = terminalElement.scrollHeight;
    }
  });

  onMount(() => {
    const eventSource = new EventSource('/api/run-optimization');

    eventSource.addEventListener('log', (event) => {
      const data = JSON.parse(event.data);
      logs = [
        ...logs,
        {
          type: data.type,
          message: data.message,
          timestamp: new Date()
        }
      ];
    });

    eventSource.addEventListener('complete', (event) => {
      const data = JSON.parse(event.data);
      logs = [
        ...logs,
        {
          type: 'info',
          message: `✓ ${data.message}`,
          timestamp: new Date()
        }
      ];
      isRunning = false;
      isComplete = true;
      eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
      // Check if it's an actual error event with data
      if (event instanceof MessageEvent && event.data) {
        const data = JSON.parse(event.data);
        logs = [
          ...logs,
          {
            type: 'stderr',
            message: `✗ ${data.message}`,
            timestamp: new Date()
          }
        ];
      }
      isRunning = false;
      hasError = true;
      eventSource.close();
    });

    // Handle connection errors
    eventSource.onerror = () => {
      if (isRunning && !isComplete) {
        logs = [
          ...logs,
          {
            type: 'stderr',
            message: 'Connection lost to server',
            timestamp: new Date()
          }
        ];
        isRunning = false;
        hasError = true;
      }
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  });

  function getLogColor(type: LogEntry['type']): string {
    switch (type) {
      case 'stderr':
        return 'text-red-400';
      case 'info':
        return 'text-blue-400';
      default:
        return 'text-gray-300';
    }
  }

  function formatTime(date: Date): string {
    return date.toLocaleTimeString('fi-FI', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }
</script>

<div class="min-h-screen bg-gray-900 p-8 text-white">
  <div class="mx-auto max-w-4xl">
    <header class="mb-8">
      <div class="flex items-center gap-3">
        {#if isRunning}
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-blue-400 border-t-transparent"></div>
        {:else if isComplete}
          <Icon icon="material-symbols:check-circle" width="24" height="24" style="color: #4ade80" />
        {:else if hasError}
          <Icon icon="material-symbols:error" width="24" height="24" style="color: #f87171" />
        {/if}
        <h1 class="text-2xl font-bold text-blue-400">
          {#if isRunning}
            Running Optimization...
          {:else if isComplete}
            Optimization Complete
          {:else}
            Optimization Failed
          {/if}
        </h1>
      </div>
      <p class="mt-2 text-gray-400">
        {#if isRunning}
          The Bayesian optimization is processing your dyno data.
        {:else if isComplete}
          Your optimized ECU map is ready for review.
        {:else}
          An error occurred during the optimization process.
        {/if}
      </p>
    </header>

    <!-- Terminal Output -->
    <div class="rounded-lg border border-gray-700 bg-gray-950">
      <!-- Terminal Header -->
      <div class="flex items-center gap-2 border-b border-gray-700 px-4 py-3">
        <div class="flex gap-1.5">
          <div class="h-3 w-3 rounded-full bg-red-500"></div>
          <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
          <div class="h-3 w-3 rounded-full bg-green-500"></div>
        </div>
        <span class="ml-2 font-mono text-sm text-gray-400">optimization — python main.py</span>
      </div>

      <!-- Terminal Content -->
      <div bind:this={terminalElement} class="h-125 overflow-y-auto p-4 font-mono text-sm">
        {#each logs as log, i (i)}
          <div class="flex gap-3">
            <span class="shrink-0 text-gray-600">[{formatTime(log.timestamp)}]</span>
            <span class={getLogColor(log.type)}>{log.message}</span>
          </div>
        {/each}

        {#if isRunning}
          <div class="mt-2 flex items-center gap-2">
            <span class="animate-pulse text-blue-400">▌</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="mt-6 flex justify-between">
      <a
        href="/"
        class="flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-gray-300 transition-colors hover:bg-gray-700"
      >
        <Icon icon="material-symbols:arrow-back" width="20" height="20" />
        Back to Upload
      </a>

      {#if isComplete}
        <a
          href="/results"
          class="flex items-center gap-2 rounded-lg bg-green-600 px-6 py-2 font-medium text-white transition-colors hover:bg-green-500"
        >
          View Results
          <Icon icon="material-symbols:arrow-forward" width="20" height="20" />
        </a>
      {:else if hasError}
        <button
          onclick={() => window.location.reload()}
          class="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
        >
          <Icon icon="material-symbols:refresh" width="20" height="20" />
          Retry
        </button>
      {/if}
    </div>
  </div>
</div>
