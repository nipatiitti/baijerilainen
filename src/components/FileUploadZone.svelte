<script lang="ts">
    import Icon from "@iconify/svelte";

    interface Props {
        dragOver?: boolean;
        onfiles: (files: File[]) => void;
    }

    let { dragOver = $bindable(false), onfiles }: Props = $props();

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        dragOver = false;

        const droppedFiles = event.dataTransfer?.files;
        if (!droppedFiles) return;

        onfiles(Array.from(droppedFiles));
    }

    function handleFileInput(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files) return;
        onfiles(Array.from(input.files));
    }
</script>

<div
    class="border-2 border-dashed rounded-lg p-8 text-center transition-colors {dragOver
        ? 'border-blue-400 bg-blue-900/20'
        : 'border-gray-600 hover:border-gray-500'}"
    ondragover={(e) => {
        e.preventDefault();
        dragOver = true;
    }}
    ondragleave={() => (dragOver = false)}
    ondrop={handleDrop}
    role="button"
    tabindex="0"
>
    <Icon
        icon="material-symbols:cloud-upload-outline"
        class="w-12 h-12 mx-auto mb-4 text-gray-500"
    />
    <p class="text-lg mb-2">Drag and drop MoTeC CSV files here</p>
    <p class="text-gray-500 mb-4">or</p>
    <label
        class="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer transition-colors"
    >
        <span>Browse Files</span>
        <input
            type="file"
            accept=".csv"
            multiple
            class="hidden"
            onchange={handleFileInput}
        />
    </label>
</div>
