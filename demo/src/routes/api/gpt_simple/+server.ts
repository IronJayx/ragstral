import { json } from '@sveltejs/kit';
import OpenAI from 'openai';
import type { RequestHandler } from './$types';
import { OPENAI_API_KEY } from '$env/static/private';

// Initialize OpenAI client lazily
let openaiClient: OpenAI | null = null;

function getOpenAIClient() {
    if (!openaiClient) {
        if (!OPENAI_API_KEY) {
            throw new Error('OPENAI_API_KEY environment variable is required');
        }
        openaiClient = new OpenAI({ apiKey: OPENAI_API_KEY });
    }
    return openaiClient;
}

export const POST: RequestHandler = async ({ request }) => {
    try {
        const { query, context } = await request.json();

        if (!query || typeof query !== 'string') {
            return json({ error: 'Query is required' }, { status: 400 });
        }

        const systemPrompt = `You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions. Be concise but thorough in your explanations.`;

        const client = getOpenAIClient();
        
        // Build messages array with context if provided
        const messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> = [
            {
                role: 'system',
                content: systemPrompt
            }
        ];

        // Add conversation context if provided
        if (context && Array.isArray(context)) {
            messages.push(...context.slice(-5)); // Last 5 messages for context
        }

        // Add current query
        messages.push({
            role: 'user',
            content: query
        });

        const response = await client.chat.completions.create({
            model: 'gpt-4o',
            messages,
            max_tokens: 1000,
            temperature: 0.1
        });

        const messageContent = response.choices?.[0]?.message?.content;
        const responseText = typeof messageContent === 'string' ? messageContent : 'I apologize, but I was unable to generate a response.';

        return json({
            success: true,
            response: responseText
        });

    } catch (error) {
        console.error('GPT simple error:', error);
        return json({ 
            success: false, 
            error: 'Failed to process GPT simple request',
            details: error instanceof Error ? error.message : 'Unknown error'
        }, { status: 500 });
    }
}; 