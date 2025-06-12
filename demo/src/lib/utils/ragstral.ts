import { v4 as uuidv4 } from "uuid";
import type { Message } from "$lib/types";

// Handle ragstral flow (chain of thought + RAG)
export async function handleRagstralFlow(
  query: string,
  messages: Message[],
  metadata: { repo_name: string; version: string }
): Promise<Message[]> {
  try {
    // Step 1: Chain of thought gate
    const chainResponse = await fetch("/api/chain-of-thought", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    const chainResult = await chainResponse.json();

    if (!chainResult.success) {
      throw new Error(chainResult.error || "Chain of thought failed");
    }

    console.log(chainResult);

    if (!chainResult.continue) {
      // If model needs clarification - respond with the clarifying question
      const clarificationMessage: Message = {
        id: uuidv4(),
        text: chainResult.message,
        sender: "assistant",
        timestamp: new Date(),
      };
      return [clarificationMessage];
    }

    // Step 2: If all good, proceed to RAG
    const ragMessages = await performRAG(query, messages, metadata);
    return ragMessages;
  } catch (error) {
    console.error("Ragstral flow error:", error);
    const errorMessage: Message = {
      id: uuidv4(),
      text: `Sorry, I encountered an error in the ragstral flow: ${error instanceof Error ? error.message : "Unknown error"}`,
      sender: "assistant",
      timestamp: new Date(),
    };
    return [errorMessage];
  }
}

// Perform RAG search and response
export async function performRAG(
  query: string,
  messages: Message[],
  metadata: { repo_name: string; version: string }
): Promise<Message[]> {
  try {
    // Build context from previous messages (last 10 messages for context)
    const conversationContext = messages.slice(-10).map((msg) => ({
      role: msg.sender === "user" ? "user" : "assistant",
      content: msg.text,
    }));

    const ragResponse = await fetch("/api/rag", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        context: conversationContext,
        metadata: {
          repo_name: metadata.repo_name,
          version: metadata.version,
        },
      }),
    });

    const ragResult = await ragResponse.json();

    if (!ragResult.success) {
      throw new Error(ragResult.error || "RAG search failed");
    }

    // Create response message
    // TODO: Add sources info
    let responseText = ragResult.response;

    const ragMessage: Message = {
      id: uuidv4(),
      text: responseText,
      sender: "assistant",
      timestamp: new Date(),
    };

    return [ragMessage];
  } catch (error) {
    console.error("RAG error:", error);
    const errorMessage: Message = {
      id: uuidv4(),
      text: `Sorry, I encountered an error during search: ${error instanceof Error ? error.message : "Unknown error"}`,
      sender: "assistant",
      timestamp: new Date(),
    };
    return [errorMessage];
  }
} 