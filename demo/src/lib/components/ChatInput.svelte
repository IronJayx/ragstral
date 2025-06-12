<script lang="ts">
  import { Textarea } from "$lib/components/ui/textarea";
  import { Button } from "$lib/components/ui/button";
  import { createEventDispatcher } from "svelte";
  import Icon from "@iconify/svelte";
  import { v4 as uuidv4 } from "uuid";

  // Message input value
  let value = "";
  const placeholder = "Ask ragstral...";

  // Dropdown values
  let selectedRepo = "modal-client";
  let selectedVersion = "v1.0.3";
  let selectedEndpoint = "ragstral";

  // Dropdown options
  const repoOptions = ["modal-client", "langchain", "fastapi", "django"];
  const versionOptions = ["v1.0.3", "v0.77.0", "v0.58.94"];
  const endpointOptions = [
    {
      value: "ragstral",
      label: "ragstral",
      description: "Chain-of-thought + RAG",
    },
    { value: "gpt4o", label: "gpt4o", description: "GPT-4 simple chat" },
    {
      value: "mistral_medium",
      label: "mistral_medium",
      description: "Mistral medium simple chat",
    },
  ];

  // Event dispatcher for sending messages
  const dispatch = createEventDispatcher();

  // Send message function
  function sendMessage() {
    if (!value.trim()) return;

    // Create message object with metadata
    const message = {
      id: uuidv4(),
      text: value,
      sender: "user",
      timestamp: new Date(),
    };

    const metadata = {
      repo_name: selectedRepo,
      version: selectedVersion,
      endpoint: selectedEndpoint,
    };

    // Dispatch event with both message and metadata
    dispatch("sendMessage", { message, metadata });

    // Clear input
    value = "";
  }

  // Handle key press
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  // Example questions
  const exampleQuestions = [
    "What is the decorator name for building apps in modal?",
    "Give me a template code for a modal endpoint",
    "What's the template code for a python endpoint using modal serverless framework?",
  ];

  // Function to handle example question click
  function handleExampleClick(question: string) {
    value = question;
  }
</script>

<div
  class="chat-input-container bg-[#f7f4ec] backdrop-blur-sm border border-black/10 rounded-lg overflow-hidden flex flex-col"
>
  <div class="flex-grow">
    <Textarea
      bind:value
      {placeholder}
      onkeydown={handleKeydown}
      rows={1}
      class="w-full bg-transparent border-none p-3 shadow-none text-black placeholder-black/50 focus:ring-0 focus:outline-none resize-none min-h-[56px]"
    />
  </div>

  <div class="actions flex items-center justify-between px-3 pb-3 mt-auto">
    <!-- Left side: Dropdown selectors -->
    <div class="flex items-center gap-2">
      <!-- Endpoint selector -->
      <select
        bind:value={selectedEndpoint}
        class="bg-transparent border border-black/20 rounded px-2 py-1 text-sm text-black focus:outline-none focus:border-black/40"
        title="Select AI endpoint"
      >
        {#each endpointOptions as endpoint}
          <option value={endpoint.value} title={endpoint.description}
            >{endpoint.label}</option
          >
        {/each}
      </select>

      <!-- Repo selector (only show for ragstral endpoint) -->
      {#if selectedEndpoint === "ragstral"}
        <select
          bind:value={selectedRepo}
          class="bg-transparent border border-black/20 rounded px-2 py-1 text-sm text-black focus:outline-none focus:border-black/40"
        >
          {#each repoOptions as repo}
            <option value={repo}>{repo}</option>
          {/each}
        </select>

        <!-- Version selector (only show for ragstral endpoint) -->
        <select
          bind:value={selectedVersion}
          class="bg-transparent border border-black/20 rounded px-2 py-1 text-sm text-black focus:outline-none focus:border-black/40"
        >
          {#each versionOptions as version}
            <option value={version}>{version}</option>
          {/each}
        </select>
      {/if}
    </div>

    <!-- Right side: Send Button -->
    <button
      on:click={sendMessage}
      class="bg-[#8a8786] hover:bg-[#7b7978] text-white rounded-full p-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
      disabled={!value.trim()}
      aria-label="Send message"
    >
      <Icon icon="mdi:send" width="16" height="16" />
    </button>
  </div>
</div>

<!-- Example Questions -->
{#if !value.trim()}
  <div class="example-questions mt-3 px-1">
    <div class="text-xs text-black/60 mb-2 font-medium">
      Try these examples:
    </div>
    <div class="flex flex-col gap-2">
      {#each exampleQuestions as question}
        <button
          on:click={() => handleExampleClick(question)}
          class="text-left text-sm text-black/70 hover:text-black bg-white/50 hover:bg-white/80 border border-black/10 hover:border-black/20 rounded-lg px-3 py-2 transition-all duration-200 cursor-pointer"
        >
          {question}
        </button>
      {/each}
    </div>
  </div>
{/if}
