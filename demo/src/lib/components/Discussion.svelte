<script lang="ts">
  import Icon from "@iconify/svelte";
  import { afterUpdate } from "svelte";
  import type { Message } from "$lib/types";

  // Props
  export let messages: Message[] = [];

  // Reference to the discussion container
  let discussionContainer: HTMLElement;

  // Scroll to bottom whenever messages change
  afterUpdate(() => {
    if (discussionContainer) {
      discussionContainer.scrollTo({
        top: discussionContainer.scrollHeight,
        behavior: "smooth",
      });
    }
  });

  // Function to parse message text and format code blocks
  function parseMessage(text: string) {
    const result = [];
    const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(text)) !== null) {
      // Add text before the code block (if any)
      if (match.index > lastIndex) {
        const textContent = text.slice(lastIndex, match.index).trim();
        if (textContent) {
          result.push({
            type: "text",
            content: textContent,
          });
        }
      }

      // Add the code block
      const language = match[1] || "";
      const codeContent = match[2].trim();
      if (codeContent) {
        result.push({
          type: "code",
          language,
          content: codeContent,
        });
      }

      lastIndex = match.index + match[0].length;
    }

    // Add any remaining text after the last code block
    if (lastIndex < text.length) {
      const remainingText = text.slice(lastIndex).trim();
      if (remainingText) {
        result.push({
          type: "text",
          content: remainingText,
        });
      }
    }

    // If no code blocks were found, return the entire text as a text block
    if (result.length === 0) {
      return [{ type: "text", content: text }];
    }

    return result;
  }
</script>

<div bind:this={discussionContainer} class="discussion-container">
  {#if messages.length === 0}
    <div class="empty-state text-center py-12">
      <Icon
        icon="mdi:message-outline"
        class="text-white/30 mx-auto mb-4"
        width="48"
        height="48"
      />
      <p class="text-black/50">No messages yet</p>
    </div>
  {:else}
    {#each messages as message (message.id)}
      <div
        class="message-container mb-4 {message.sender === 'user'
          ? 'user-message'
          : 'assistant-message'}"
      >
        {#if message.sender === "assistant"}
          <div class="assistant-title flex items-center ml-1">
            <Icon icon="fluent:water-24-filled" class="mr-1 text-black" />
            <span class="text-sm font-medium"> ragstral </span>
          </div>
        {/if}
        <div
          class="message-bubble {message.sender === 'user'
            ? 'bg-[#f7f4ec] '
            : 'bg-white/10'} 
                      p-3 rounded-lg max-w-[85%] {message.sender === 'user'
            ? 'ml-auto'
            : ''}"
        >
          <div class="message-content">
            {#each parseMessage(message.text) as part}
              {#if part.type === "text"}
                <p class="text-black/80 whitespace-pre-line">
                  {part.content}
                </p>
              {:else if part.type === "code"}
                <div
                  class="code-block mt-2 mb-2 border border-gray-300 rounded-md"
                >
                  <div
                    class="code-header bg-[#dcdad4] text-black/50 text-xs px-4 py-1 rounded-t-md"
                  >
                    {part.language || "code"}
                  </div>
                  <pre
                    class="bg-[#edece7] text-black/50 p-4 rounded-b-md overflow-x-auto text-sm"><code
                      >{part.content}</code
                    ></pre>
                </div>
              {/if}
            {/each}
          </div>

          <div class="message-meta text-xs text-black/50 mt-1 text-right">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .discussion-container {
    display: flex;
    flex-direction: column;
    max-height: 100%;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
  }

  .discussion-container::-webkit-scrollbar {
    width: 6px;
  }

  .discussion-container::-webkit-scrollbar-track {
    background: transparent;
  }

  .discussion-container::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
  }

  .user-message {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .assistant-message {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .code-block {
    width: 100%;
    font-family: monospace;
    overflow: hidden;
  }

  pre {
    margin: 0;
    overflow-x: auto;
  }

  code {
    font-family: "Menlo", "Monaco", "Courier New", monospace;
  }
</style>
