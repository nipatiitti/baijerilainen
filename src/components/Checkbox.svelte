<script lang="ts">
    import type { Snippet } from "svelte";

    interface Props {
        checked?: boolean;
        onchange?: () => void;
        children?: Snippet;
    }

    let { checked = false, onchange, children }: Props = $props();
</script>

<label
    class="flex items-start gap-2 cursor-pointer hover:bg-gray-700/50 p-1 rounded"
>
    <input
        type="checkbox"
        {checked}
        {onchange}
        class="mt-1 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
    />
    {#if children}
        <div class="flex-1 min-w-0">
            {@render children()}
        </div>
    {/if}
</label>
