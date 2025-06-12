<script lang="ts">
  import Discussion from "$lib/components/Discussion.svelte";
  import ChatInput from "$lib/components/ChatInput.svelte";
  import Icon from "@iconify/svelte";
  import { v4 as uuidv4 } from "uuid";
  import type { Message } from "$lib/types";
  import { handleRagstralFlow } from "$lib/utils/ragstral";
  import { handleSimpleChat } from "$lib/utils/simpleChat";

  // Messages state
  let messages: Message[] = [];

  // Dynamic metadata - will be set from ChatInput
  let metadata = {
    repo_name: "modal-client",
    version: "v1.0.3",
    endpoint: "ragstral",
  };

  // Loading state
  let isLoading = false;

  // Handle sending messages with routing based on endpoint
  async function handleSendMessage(event: CustomEvent) {
    const { message: userMessage, metadata: newMetadata } = event.detail;

    // Update metadata from the dropdowns
    metadata = newMetadata;

    messages = [...messages, userMessage];
    isLoading = true;

    try {
      let newMessages: Message[] = [];

      // Route to different endpoints based on selected endpoint
      switch (metadata.endpoint) {
        case "ragstral":
          newMessages = await handleRagstralFlow(userMessage.text, messages, {
            repo_name: metadata.repo_name,
            version: metadata.version,
          });
          break;
        case "gpt4o":
          newMessages = await handleSimpleChat(
            "/api/gpt_simple",
            userMessage.text,
            messages
          );
          break;
        case "mistral_medium":
          newMessages = await handleSimpleChat(
            "/api/mistral_simple",
            userMessage.text,
            messages
          );
          break;
        default:
          throw new Error(`Unknown endpoint: ${metadata.endpoint}`);
      }

      // Add the new messages to the conversation
      messages = [...messages, ...newMessages];
    } catch (error) {
      console.error("Error in message handling:", error);
      const errorMessage: Message = {
        id: uuidv4(),
        text: `Sorry, I encountered an error: ${error instanceof Error ? error.message : "Unknown error"}`,
        sender: "assistant",
        timestamp: new Date(),
      };
      messages = [...messages, errorMessage];
    } finally {
      isLoading = false;
    }
  }
</script>

<div
  class="h-screen flex items-center justify-center bg-[#fcfbf7] text-black py-8"
>
  <div
    class="w-2/3 h-full flex flex-col border border-gray-300 rounded-lg overflow-hidden relative"
  >
    <!-- Loading overlay -->
    {#if isLoading}
      <div
        class="absolute inset-0 bg-black/5 backdrop-blur-sm z-10 flex items-center justify-center"
      >
        <div class="bg-white rounded-lg p-4 shadow-lg flex items-center gap-3">
          <Icon
            icon="mdi:loading"
            class="animate-spin text-[#8a8786]"
            width="20"
            height="20"
          />
          <span class="text-sm text-gray-700">Processing your request...</span>
        </div>
      </div>
    {/if}

    <div class="flex-grow overflow-hidden p-4">
      <Discussion {messages} />
    </div>

    <div class="sidebar-footer p-4 border-t border-white/10">
      <ChatInput on:sendMessage={handleSendMessage} />
    </div>
  </div>
</div>
