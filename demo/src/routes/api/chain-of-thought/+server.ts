import { json } from '@sveltejs/kit';
import { Mistral } from '@mistralai/mistralai';
import type { RequestHandler } from './$types';
import { MISTRAL_API_KEY } from '$env/static/private';

// Initialize Mistral client lazily
let mistralClient: Mistral | null = null;

function getMistralClient() {
    if (!mistralClient) {
        if (!MISTRAL_API_KEY) {
            throw new Error('MISTRAL_API_KEY environment variable is required');
        }
        mistralClient = new Mistral({ apiKey: MISTRAL_API_KEY });
    }
    return mistralClient;
}

export const POST: RequestHandler = async ({ request }) => {
    try {
        const { query, context } = await request.json();

        if (!query || typeof query !== 'string') {
            return json({ error: 'Query is required' }, { status: 400 });
        }

        console.log("GATE: context", context);
        console.log("GATE: query", query);

        const systemPrompt = `You are the gate to a RAG application answer the user query: "${query}"."

The RAG's retrieval will query a database with indexed code from different packages.

Make sure the user included enough information so the vector search will be accurate

- You dont always need to ask a question, if the user intent is explicit → respond with exactly "ALL_GOOD"
- If the user message mention clearly intent or a technology → respond with exactly "ALL_GOOD"
- If the user message is too cryptic or vague → respond with exactly "ASK: <one-sentence question>"

Your response should start with either "ALL_GOOD" or "ASK:" and nothing else.
Dont include <think> tags in your response.

`;

        const client = getMistralClient();
        const response = await client.chat.complete({
            model: 'magistral-medium-2506',
            messages: [
                {
                    role: 'system',
                    content: systemPrompt
                }
            ],
            maxTokens: 100,
            temperature: 0.1
        });

        const messageContent = response.choices?.[0]?.message?.content;
        const responseText = typeof messageContent === 'string' ? messageContent.trim() : '';

        console.log("GATE: response", responseText);
        
        // Parse the response
        if (responseText.startsWith('ALL_GOOD')) {
            console.log("GATE: all good");
            return json({
                success: true,
                continue: true,
                message: 'Query is clear, proceeding to RAG'
            });
        } else if (responseText.startsWith('ASK:')) {
            const clarificationQuestion = responseText.substring(4).trim();
            console.log("GATE: asking question", clarificationQuestion);
            return json({
                success: true,
                continue: false,
                message: clarificationQuestion
            });
        } else {
            // Fallback if response doesn't match expected format
            console.log("GATE: fallback");
            return json({
                success: true,
                continue: false,
                message: 'Could you please provide more details about your question?'
            });
        }

    } catch (error) {
        console.error('Chain of thought error:', error);
        return json({ 
            success: false, 
            continue: false, 
            error: 'Failed to process chain of thought' 
        }, { status: 500 });
    }
}; 