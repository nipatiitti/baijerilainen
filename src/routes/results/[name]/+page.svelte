<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Title,
    Tooltip,
    Legend,
    Filler
  } from 'chart.js';
  import Icon from '@iconify/svelte';
  import type { PageProps } from './$types';

  // Register Chart.js components
  Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Title, Tooltip, Legend, Filler);

  let { data }: PageProps = $props();

  let lambdaChart: Chart | null = null;
  let timingChart: Chart | null = null;
  let ecuMapChart: Chart | null = null;
  let lambdaCanvas = $state<HTMLCanvasElement | null>(null);
  let timingCanvas = $state<HTMLCanvasElement | null>(null);
  let ecuMapCanvas = $state<HTMLCanvasElement | null>(null);

  onMount(() => {
    // Wait for DOM to update, then create charts
    setTimeout(createCharts, 50);

    return () => {
      // Cleanup charts on unmount
      lambdaChart?.destroy();
      timingChart?.destroy();
      ecuMapChart?.destroy();
    };
  });

  function createCharts() {
    const results = data.results;
    if (!results) return;

    const rpmValues = results.optimal_map.axis.values;
    const lambdaValues = results.optimal_map.tables.lambda.values;
    const timingValues = results.optimal_map.tables.timing.values;

    // Suggested experiment points
    const suggestions = results.suggested_experiments ?? [];

    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index' as const
      },
      layout: {
        padding: { left: 6, right: 10, top: 6, bottom: 6 }
      },
      plugins: {
        legend: {
          labels: {
            color: '#cbd5e1',
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: '#1f2937',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 10
        }
      },
      elements: {
        line: { borderWidth: 2 },
        point: { hoverRadius: 7, hoverBorderWidth: 2 }
      },
      scales: {
        x: {
          title: { display: true, text: 'RPM', color: '#cbd5e1' },
          ticks: { color: '#94a3b8', maxTicksLimit: 10 },
          grid: { color: 'rgba(148, 163, 184, 0.14)' },
          border: { color: 'rgba(148, 163, 184, 0.25)' }
        },
        y: {
          ticks: { color: '#94a3b8' },
          grid: { color: 'rgba(148, 163, 184, 0.14)' },
          border: { color: 'rgba(148, 163, 184, 0.25)' }
        }
      }
    };

    // Lambda chart
    if (lambdaCanvas) {
      lambdaChart = new Chart(lambdaCanvas, {
        type: 'line',
        data: {
          labels: rpmValues.map(String),
          datasets: [
            {
              label: 'Optimal Lambda',
              data: lambdaValues,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: 3
            },
            {
              label: 'Suggested Tests',
              data: rpmValues.map((rpm) => {
                const suggestion = suggestions.find((s) => Math.abs(s.rpm - rpm) < 30);
                return suggestion ? suggestion.lambda : null;
              }),
              borderColor: '#f59e0b',
              backgroundColor: '#f59e0b',
              pointRadius: 8,
              pointHoverRadius: 10,
              pointStyle: 'star',
              showLine: false
            }
          ]
        },
        options: {
          ...commonOptions,
          scales: {
            ...commonOptions.scales,
            y: {
              ...commonOptions.scales.y,
              title: { display: true, text: 'Lambda (LA)', color: '#cbd5e1' }
            }
          }
        }
      });
    }

    // Timing chart
    if (timingCanvas) {
      timingChart = new Chart(timingCanvas, {
        type: 'line',
        data: {
          labels: rpmValues.map(String),
          datasets: [
            {
              label: 'Optimal Timing',
              data: timingValues,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: 3
            },
            {
              label: 'Suggested Tests',
              data: rpmValues.map((rpm) => {
                const suggestion = suggestions.find((s) => Math.abs(s.rpm - rpm) < 30);
                return suggestion ? suggestion.timing : null;
              }),
              borderColor: '#f59e0b',
              backgroundColor: '#f59e0b',
              pointRadius: 8,
              pointHoverRadius: 10,
              pointStyle: 'star',
              showLine: false
            }
          ]
        },
        options: {
          ...commonOptions,
          scales: {
            ...commonOptions.scales,
            y: {
              ...commonOptions.scales.y,
              title: { display: true, text: 'Timing (°BTDC)', color: '#cbd5e1' }
            }
          }
        }
      });
    }

    // ECU Map combined chart (BSFC, Lambda, Timing vs RPM)
    if (ecuMapCanvas) {
      const bsfcValues = results.optimal_map.tables.predicted_bsfc.values;

      ecuMapChart = new Chart(ecuMapCanvas, {
        type: 'line',
        data: {
          labels: rpmValues.map(String),
          datasets: [
            {
              label: 'BSFC',
              data: bsfcValues,
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              fill: false,
              tension: 0.3,
              pointRadius: 4,
              pointHoverRadius: 6,
              yAxisID: 'yBsfc'
            },
            {
              label: 'Lambda',
              data: lambdaValues,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              fill: false,
              tension: 0.3,
              pointRadius: 4,
              pointHoverRadius: 6,
              yAxisID: 'yLambda'
            },
            {
              label: 'Timing (°)',
              data: timingValues,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: false,
              tension: 0.3,
              pointRadius: 4,
              pointHoverRadius: 6,
              yAxisID: 'yTiming'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index' as const
          },
          layout: {
            padding: { left: 6, right: 10, top: 6, bottom: 6 }
          },
          plugins: {
            legend: {
              labels: {
                color: '#cbd5e1',
                boxWidth: 10,
                boxHeight: 10,
                usePointStyle: true,
                pointStyle: 'circle'
              }
            },
            tooltip: {
              backgroundColor: '#1f2937',
              titleColor: '#f3f4f6',
              bodyColor: '#d1d5db',
              borderColor: '#374151',
              borderWidth: 1,
              padding: 10
            }
          },
          elements: {
            line: { borderWidth: 2 },
            point: { hoverRadius: 7, hoverBorderWidth: 2 }
          },
          scales: {
            x: {
              title: { display: true, text: 'RPM', color: '#cbd5e1' },
              ticks: { color: '#94a3b8', maxTicksLimit: 10 },
              grid: { color: 'rgba(148, 163, 184, 0.14)' },
              border: { color: 'rgba(148, 163, 184, 0.25)' }
            },
            yBsfc: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'BSFC', color: '#ef4444' },
              ticks: { color: '#ef4444' },
              grid: { color: 'rgba(148, 163, 184, 0.14)' },
              border: { color: 'rgba(239, 68, 68, 0.5)' }
            },
            yLambda: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: 'Lambda', color: '#3b82f6' },
              ticks: { color: '#3b82f6' },
              grid: { drawOnChartArea: false },
              border: { color: 'rgba(59, 130, 246, 0.5)' }
            },
            yTiming: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: 'Timing (°)', color: '#10b981' },
              ticks: { color: '#10b981' },
              grid: { drawOnChartArea: false },
              border: { color: 'rgba(16, 185, 129, 0.5)' }
            }
          }
        }
      });
    }
  }

  // BSFC color scale: green (good) -> yellow -> red (bad)
  function getBsfcColor(bsfc: number, min: number, max: number): string {
    if (!Number.isFinite(bsfc) || !Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
      return 'rgba(148, 163, 184, 0.35)';
    }
    const normalized = (bsfc - min) / (max - min);
    if (normalized < 0.33) {
      return '#16a34a'; // green-600
    } else if (normalized < 0.66) {
      return '#ca8a04'; // yellow-600
    } else {
      return '#dc2626'; // red-600
    }
  }

  function formatTimestamp(ts: string): string {
    const date = new Date(ts);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}:${seconds}`;
  }

  // Derived values for the template
  const results = $derived(data.results);
  const minBsfc = $derived(Math.min(...(results?.optimal_map.tables.predicted_bsfc.values ?? [0])));
  const maxBsfc = $derived(Math.max(...(results?.optimal_map.tables.predicted_bsfc.values ?? [0])));
</script>

<div
  class="print-container min-h-screen bg-linear-to-b from-gray-950 via-gray-900 to-gray-950 p-4 text-gray-100 sm:p-8"
>
  <div class="mx-auto flex max-w-7xl flex-col gap-8">
    <!-- Header -->
    <header
      class="print-header print-section rounded-xl bg-gray-900/40 p-4 shadow-lg ring-1 ring-white/5 backdrop-blur sm:p-6"
    >
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <a
            href={resolve('/results')}
            class="print-hide inline-flex h-10 w-10 items-center justify-center rounded-lg bg-gray-800/40 text-gray-300 ring-1 ring-white/10 transition hover:bg-gray-800/70 hover:text-white"
            aria-label="Back to results"
          >
            <Icon icon="material-symbols:arrow-back-rounded" width="22" height="22" />
          </a>
          <div>
            <h1 class="print-text-dark text-2xl font-semibold tracking-tight text-blue-300 sm:text-3xl">
              Optimization Results
            </h1>
            <p class="print-text-muted mt-1 max-w-[70ch] truncate text-sm text-gray-400">{data.filename}</p>
          </div>
        </div>
      </div>
    </header>

    {#if results}
      <!-- Metadata Cards -->
      <section class="print-section rounded-xl bg-gray-900/25 p-4 ring-1 ring-white/5 sm:p-6">
        <div class="mb-4 flex items-center justify-between gap-4">
          <h2 class="print-text-dark text-lg font-semibold tracking-tight sm:text-xl">Summary</h2>
          <div class="print-text-muted hidden text-sm text-gray-400 sm:block">Run overview and key stats</div>
        </div>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-6">
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">Timestamp</p>
            <p class="print-text-dark mt-1 font-medium text-gray-100">{formatTimestamp(results.metadata.timestamp)}</p>
          </div>
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">Training Samples</p>
            <p class="print-text-dark mt-1 font-medium text-gray-100 tabular-nums">
              {results.metadata.n_training_samples}
            </p>
          </div>
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">RPM Bins</p>
            <p class="print-text-dark mt-1 font-medium text-gray-100 tabular-nums">{results.data_summary.n_bins}</p>
          </div>
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">RPM Range</p>
            <p class="print-text-dark mt-1 font-medium text-gray-100 tabular-nums">
              {results.data_summary.rpm_range[0]} – {results.data_summary.rpm_range[1]}
            </p>
          </div>
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">Best BSFC</p>
            <p class="print-text-dark mt-1 text-lg font-semibold text-green-300 tabular-nums">
              {results.current_best.overall_bsfc.toFixed(1)}
            </p>
          </div>
          <div class="print-card rounded-lg bg-gray-800/45 p-4 shadow-sm ring-1 ring-white/10">
            <p class="print-text-muted text-xs font-medium tracking-wide text-gray-400 uppercase">Suggested Tests</p>
            <p class="print-text-dark mt-1 text-lg font-semibold text-amber-300 tabular-nums">
              {results.suggested_experiments.length}
            </p>
          </div>
        </div>
      </section>

      <!-- Charts -->
      <section class="grid gap-6 lg:grid-cols-2">
        <div
          class="print-section print-chart relative overflow-hidden rounded-xl bg-gray-800/40 p-4 shadow-lg ring-1 ring-white/10 backdrop-blur sm:p-6"
        >
          <div class="mb-4 flex items-start justify-between gap-4">
            <div>
              <h3 class="print-text-dark text-base font-semibold tracking-tight sm:text-lg">Optimal Fuel Mixture</h3>
              <p class="print-text-muted mt-1 text-sm text-gray-400">Lambda setpoint across RPM bins</p>
            </div>
            <span
              class="print-badge rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-300 ring-1 ring-blue-400/20"
            >
              Lambda
            </span>
          </div>
          <div class="h-80 rounded-lg bg-gray-900/20 p-2 ring-1 ring-white/10 sm:h-96">
            <canvas bind:this={lambdaCanvas} class="h-full w-full"></canvas>
          </div>
        </div>
        <div
          class="print-section print-chart relative overflow-hidden rounded-xl bg-gray-800/40 p-4 shadow-lg ring-1 ring-white/10 backdrop-blur sm:p-6"
        >
          <div class="mb-4 flex items-start justify-between gap-4">
            <div>
              <h3 class="print-text-dark text-base font-semibold tracking-tight sm:text-lg">Optimal Ignition Timing</h3>
              <p class="print-text-muted mt-1 text-sm text-gray-400">Ignition timing across RPM bins</p>
            </div>
            <span
              class="print-badge rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300 ring-1 ring-emerald-400/20"
            >
              Timing
            </span>
          </div>
          <div class="h-80 rounded-lg bg-gray-900/20 p-2 ring-1 ring-white/10 sm:h-96">
            <canvas bind:this={timingCanvas} class="h-full w-full"></canvas>
          </div>
        </div>
      </section>

      <!-- Suggested Experiments -->
      <section class="print-section print-break-before rounded-xl bg-gray-900/25 p-4 ring-1 ring-white/5 sm:p-6">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="print-text-dark flex items-center gap-2 text-lg font-semibold tracking-tight sm:text-xl">
            <Icon icon="material-symbols:science-outline" width="22" height="22" style="color: #f59e0b;" />
            Suggested Next Experiments
          </h2>
          <span
            class="print-badge rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-200 ring-1 ring-amber-400/20"
          >
            {results.suggested_experiments.length} points
          </span>
        </div>
        <p class="print-text-muted mb-4 text-sm text-gray-400">
          Recommended test points to maximize information gain and potentially improve BSFC.
        </p>
        <div class="print-table overflow-hidden rounded-xl bg-gray-800/35 ring-1 ring-white/10">
          <div class="print-no-scroll max-h-130 overflow-auto">
            <table class="print-table w-full min-w-245 text-sm tabular-nums">
              <thead class="sticky top-0 z-10 bg-gray-900/70 backdrop-blur">
                <tr class="text-left text-xs font-semibold tracking-wide text-gray-300 uppercase">
                  <th class="px-4 py-3">RPM</th>
                  <th class="px-4 py-3">Lambda</th>
                  <th class="px-4 py-3">Timing (°BTDC)</th>
                  <th class="px-4 py-3">Pred. BSFC</th>
                  <th class="px-4 py-3">Uncertainty</th>
                  <th class="px-4 py-3">Exp. Improvement</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-700/40">
                {#each results.suggested_experiments as exp, i (exp.rpm + '-' + exp.lambda + '-' + exp.timing)}
                  <tr
                    class={i % 2 === 0 ? 'bg-gray-800/20 hover:bg-gray-700/25' : 'bg-gray-800/10 hover:bg-gray-700/25'}
                  >
                    <td class="print-text-dark px-4 py-3 font-medium whitespace-nowrap text-gray-100"
                      >{exp.rpm.toFixed(0)}</td
                    >
                    <td class="print-text-dark px-4 py-3 text-gray-100">{exp.lambda.toFixed(3)}</td>
                    <td class="print-text-dark px-4 py-3 whitespace-nowrap text-gray-100">{exp.timing.toFixed(1)}°</td>
                    <td class="print-text-dark px-4 py-3 text-gray-100">{exp.predicted_bsfc.toFixed(1)}</td>
                    <td class="print-text-muted px-4 py-3 whitespace-nowrap text-gray-300"
                      >±{exp.uncertainty.toFixed(1)}</td
                    >
                    <td class="px-4 py-3">
                      <span
                        class="inline-flex items-center rounded-lg bg-amber-500/10 px-2.5 py-1 text-amber-200 ring-1 ring-amber-400/20"
                      >
                        {exp.expected_improvement.toFixed(4)}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ECU Map Chart -->
      <section
        class="print-section print-chart print-break-before relative overflow-hidden rounded-xl bg-gray-800/40 p-4 shadow-lg ring-1 ring-white/10 backdrop-blur sm:p-6"
      >
        <div class="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 class="print-text-dark flex items-center gap-2 text-base font-semibold tracking-tight sm:text-lg">
              <Icon icon="material-symbols:show-chart" width="22" height="22" style="color: #a855f7;" />
              ECU Map Overview
            </h3>
            <p class="print-text-muted mt-1 text-sm text-gray-400">BSFC, Lambda, and Timing as functions of RPM</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span
              class="inline-flex items-center gap-1.5 rounded-full bg-red-500/10 px-2.5 py-1 text-red-300 ring-1 ring-red-400/20"
            >
              <span class="h-2 w-2 rounded-full" style="background:#ef4444"></span>
              BSFC
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-1 text-blue-300 ring-1 ring-blue-400/20"
            >
              <span class="h-2 w-2 rounded-full" style="background:#3b82f6"></span>
              Lambda
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-emerald-300 ring-1 ring-emerald-400/20"
            >
              <span class="h-2 w-2 rounded-full" style="background:#10b981"></span>
              Timing
            </span>
          </div>
        </div>
        <div class="h-80 rounded-lg bg-gray-900/20 p-2 ring-1 ring-white/10 sm:h-96">
          <canvas bind:this={ecuMapCanvas} class="h-full w-full"></canvas>
        </div>
      </section>

      <!-- BSFC Table -->
      <section class="print-section print-break-before rounded-xl bg-gray-900/25 p-4 ring-1 ring-white/5 sm:p-6">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="print-text-dark flex items-center gap-2 text-lg font-semibold tracking-tight sm:text-xl">
            <Icon icon="material-symbols:table-chart-outline" width="22" height="22" style="color: #3b82f6;" />
            Optimal ECU Map
          </h2>
          <div class="print-text-muted flex items-center gap-2 text-xs text-gray-300">
            <span class="inline-flex items-center gap-1 rounded-full bg-gray-800/40 px-2.5 py-1 ring-1 ring-white/10">
              <span class="h-2 w-2 rounded-full" style="background:#16a34a"></span>
              efficient
            </span>
            <span class="inline-flex items-center gap-1 rounded-full bg-gray-800/40 px-2.5 py-1 ring-1 ring-white/10">
              <span class="h-2 w-2 rounded-full" style="background:#ca8a04"></span>
              neutral
            </span>
            <span class="inline-flex items-center gap-1 rounded-full bg-gray-800/40 px-2.5 py-1 ring-1 ring-white/10">
              <span class="h-2 w-2 rounded-full" style="background:#dc2626"></span>
              less efficient
            </span>
          </div>
        </div>
        <p class="print-text-muted mb-4 text-sm text-gray-400">
          Cells are colored by predicted BSFC (lower is better).
        </p>

        <div class="print-ecu-table print-table overflow-hidden rounded-xl bg-gray-800/35 ring-1 ring-white/10">
          <div class="print-no-scroll relative max-h-130 overflow-auto">
            <table
              class="print-table w-max min-w-full text-sm tabular-nums"
              style="border-collapse: separate; border-spacing: 0;"
            >
              <thead class="sticky top-0 z-10 bg-gray-900/70 backdrop-blur">
                <tr class="text-xs font-semibold tracking-wide text-gray-300 uppercase">
                  <th class="sticky left-0 z-20 bg-gray-900/70 px-4 py-3 text-left">Parameter</th>
                  {#each results.optimal_map.axis.values as rpm (rpm)}
                    <th class="px-4 py-3 text-center whitespace-nowrap">{rpm}</th>
                  {/each}
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-700/40">
                <tr class="bg-gray-800/10">
                  <td class="print-text-dark sticky left-0 z-10 bg-gray-800/30 px-4 py-3 font-medium text-gray-300"
                    >Lambda</td
                  >
                  {#each results.optimal_map.tables.lambda.values as lambda, i (i)}
                    <td class="print-text-dark px-4 py-3 text-center text-gray-100">{lambda.toFixed(3)}</td>
                  {/each}
                </tr>
                <tr class="bg-gray-800/20">
                  <td class="print-text-dark sticky left-0 z-10 bg-gray-800/40 px-4 py-3 font-medium text-gray-300"
                    >Timing (°)</td
                  >
                  {#each results.optimal_map.tables.timing.values as timing, i (i)}
                    <td class="print-text-dark px-4 py-3 text-center text-gray-100">{timing.toFixed(1)}</td>
                  {/each}
                </tr>
                <tr class="bg-gray-800/10">
                  <td class="print-text-dark sticky left-0 z-10 bg-gray-800/30 px-4 py-3 font-medium text-gray-300"
                    >BSFC</td
                  >
                  {#each results.optimal_map.tables.predicted_bsfc.values as bsfc, i (i)}
                    <td class="px-4 py-3 text-center">
                      <span
                        class="inline-flex min-w-16 items-center justify-center rounded-lg px-2 py-1 font-semibold text-gray-950 shadow-sm"
                        style="background-color: {getBsfcColor(bsfc, minBsfc, maxBsfc)};"
                      >
                        {bsfc.toFixed(1)}
                      </span>
                    </td>
                  {/each}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    {/if}
  </div>
</div>

<style>
  @media print {
    /* Reset dark theme to light for printing */
    :global(body) {
      background: white !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    .print-container {
      background: white !important;
      color: #1f2937 !important;
      padding: 0 !important;
    }

    /* Hide back button in print */
    .print-hide {
      display: none !important;
    }

    /* Light backgrounds for sections */
    .print-section {
      background: #f9fafb !important;
      box-shadow: none !important;
      border: 1px solid #e5e7eb !important;
      page-break-inside: avoid;
    }

    /* Card styling for print */
    .print-card {
      background: #f3f4f6 !important;
      border: 1px solid #d1d5db !important;
      box-shadow: none !important;
    }

    /* Text colors for print */
    .print-text-dark {
      color: #1f2937 !important;
    }

    .print-text-muted {
      color: #4b5563 !important;
    }

    /* Table styling for print */
    .print-table {
      background: white !important;
      border: 1px solid #d1d5db !important;
    }

    .print-table th {
      background: #f3f4f6 !important;
      color: #1f2937 !important;
      border-bottom: 2px solid #d1d5db !important;
    }

    .print-table td {
      color: #1f2937 !important;
      border-bottom: 1px solid #e5e7eb !important;
    }

    /* Chart containers */
    .print-chart {
      background: white !important;
      border: 1px solid #e5e7eb !important;
      page-break-inside: avoid;
    }

    /* Chart canvas wrapper - remove grey backgrounds */
    .print-chart > div:last-child,
    .print-chart .rounded-lg,
    .print-chart [class*='bg-gray'] {
      background: white !important;
      border: 1px solid #e5e7eb !important;
    }

    /* Badges for print */
    .print-badge {
      background: #e5e7eb !important;
      color: #1f2937 !important;
      border: 1px solid #9ca3af !important;
    }

    /* Page breaks */
    .print-break-before {
      page-break-before: always;
    }

    /* Ensure charts are visible */
    canvas {
      max-width: 100% !important;
      background: white !important;
    }

    /* Header styling */
    .print-header {
      background: #f9fafb !important;
      border: 1px solid #e5e7eb !important;
    }

    /* Remove ring/shadow effects */
    [class*='ring-'] {
      --tw-ring-shadow: none !important;
      box-shadow: none !important;
    }

    /* Ensure scrollable areas show full content */
    .print-no-scroll {
      max-height: none !important;
      overflow: visible !important;
    }

    /* ECU Map table - ensure full visibility */
    .print-ecu-table {
      max-height: none !important;
      overflow: visible !important;
    }

    .print-ecu-table > div {
      max-height: none !important;
      overflow: visible !important;
    }

    .print-ecu-table table {
      width: 100% !important;
    }

    .print-ecu-table td,
    .print-ecu-table th {
      padding: 4px 6px !important;
      font-size: 10px !important;
    }

    /* Remove sticky positioning in print */
    .print-ecu-table .sticky {
      position: static !important;
    }

    /* Ensure all backgrounds in tables are white */
    .print-ecu-table tr,
    .print-ecu-table td,
    .print-ecu-table th,
    .print-ecu-table thead {
      background: white !important;
    }

    /* Keep BSFC colored cells visible */
    .print-ecu-table td span {
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
  }
</style>
