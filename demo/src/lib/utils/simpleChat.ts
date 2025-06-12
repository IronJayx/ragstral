import { v4 as uuidv4 } from "uuid";
import type { Message } from "$lib/types";

// Handle simple chat endpoints (GPT and Mistral simple)
export async function handleSimpleChat(
  endpoint: string,
  query: string,
  messages: Message[]
): Promise<Message[]> {
  try {
    // Build context from previous messages (last 10 messages for context)
    const conversationContext = messages.slice(-10).map((msg) => ({
      role: msg.sender === "user" ? "user" : "assistant",
      content: msg.text,
    }));

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        context: conversationContext,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || "Chat request failed");
    }

    const responseMessage: Message = {
      id: uuidv4(),
      text: result.response,
      sender: "assistant",
      timestamp: new Date(),
    };

    return [responseMessage];
  } catch (error) {
    console.error("Simple chat error:", error);
    const errorMessage: Message = {
      id: uuidv4(),
      text: `Sorry, I encountered an error: ${error instanceof Error ? error.message : "Unknown error"}`,
      sender: "assistant",
      timestamp: new Date(),
    };
    return [errorMessage];
  }
} 