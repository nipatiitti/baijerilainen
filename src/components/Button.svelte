<script lang="ts">
    import type { Snippet } from "svelte";
    import type { HTMLButtonAttributes } from "svelte/elements";

    interface Props extends HTMLButtonAttributes {
        variant?: "primary" | "success" | "ghost" | "icon";
        children: Snippet;
    }

    let {
        variant = "primary",
        children,
        class: className = "",
        ...rest
    }: Props = $props();

    const variants = {
        primary:
            "px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors",
        success:
            "px-8 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold transition-colors",
        ghost: "text-gray-400 hover:text-white transition-colors",
        icon: "p-2 hover:bg-gray-700 rounded-lg transition-colors",
    };
</script>

<button class="{variants[variant]} {className}" {...rest}>
    {@render children()}
</button>
