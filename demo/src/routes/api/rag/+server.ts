import { json } from '@sveltejs/kit';
import { Mistral } from '@mistralai/mistralai';
import { Pinecone } from '@pinecone-database/pinecone';
import type { RequestHandler } from './$types';
import { MISTRAL_API_KEY, PINECONE_API_KEY } from '$env/static/private';

// Initialize clients lazily
let mistralClient: Mistral | null = null;
let pineconeClient: Pinecone | null = null;
let pineconeIndex: any = null;

function getMistralClient() {
    if (!mistralClient) {
        if (!MISTRAL_API_KEY) {
            throw new Error('MISTRAL_API_KEY environment variable is required');
        }
        mistralClient = new Mistral({ apiKey: MISTRAL_API_KEY });
    }
    return mistralClient;
}

function getPineconeIndex() {
    if (!pineconeClient) {
        if (!PINECONE_API_KEY) {
            throw new Error('PINECONE_API_KEY environment variable is required');
        }
        pineconeClient = new Pinecone({ apiKey: PINECONE_API_KEY });
        pineconeIndex = pineconeClient.index('ragstral-code-index');
    }
    return pineconeIndex;
}

// Convert GitHub blob URL to raw content URL
function convertToRawGitHubUrl(githubUrl: string): string {
    // Convert from: https://github.com/modal-labs/modal-client/blob/v0.77.0/conftest.py
    // To: https://raw.githubusercontent.com/modal-labs/modal-client/refs/tags/v0.77.0/conftest.py
    
    if (!githubUrl.includes('github.com/') || !githubUrl.includes('/blob/')) {
        return githubUrl; // Return as-is if not a GitHub blob URL
    }
    
    const url = new URL(githubUrl);
    const pathParts = url.pathname.split('/');
    
    // Extract: owner, repo, version, filepath
    const owner = pathParts[1];
    const repo = pathParts[2];
    const blobIndex = pathParts.indexOf('blob');
    const version = pathParts[blobIndex + 1];
    const filepath = pathParts.slice(blobIndex + 2).join('/');
    
    // Build raw URL
    return `https://raw.githubusercontent.com/${owner}/${repo}/refs/tags/${version}/${filepath}`;
}

export const POST: RequestHandler = async ({ request }) => {
    try {
        const { query, context, metadata } = await request.json();

        if (!query || typeof query !== 'string') {
            return json({ error: 'Query is required' }, { status: 400 });
        }

        // Default metadata if not provided
        const searchMetadata = metadata || {
            repo_name: "modal-client",
            version: "v0.77.0"
        };

        // Step 1: Generate embedding for the query
        const mistral = getMistralClient();
        const embeddingResponse = await mistral.embeddings.create({
            model: 'codestral-embed',
            inputs: [query]
        });

        const queryEmbedding = embeddingResponse.data?.[0]?.embedding;
        
        if (!queryEmbedding) {
            throw new Error('Failed to generate embedding');
        }

        console.log("EMBEDDING OK");

        // Step 2: Search Pinecone with vector + metadata filters
        const index = getPineconeIndex();
        const searchResponse = await index.query({
            vector: queryEmbedding,
            topK: 5,
            includeMetadata: true,
            filter: {
                repo_name: { $eq: searchMetadata.repo_name },
                version: { $eq: searchMetadata.version }
            }
        });

        console.log("SEARCH OK");
        console.log(searchResponse);

        // Step 3: Extract relevant documents
        const relevantDocs = searchResponse.matches?.map((match: any) => ({
            score: match.score,
            content: match.metadata?.text || '',
            file: match.metadata?.file || '',
            chunk_id: match.id,
            original_file: match.metadata?.original_file || ''
        })) || [];

        // Step 3.5: Remove duplicates based on original_file, ignoring score
        const deduplicatedDocs = relevantDocs.reduce((acc: any[], doc: any) => {
            const existingDoc = acc.find(d => d.original_file === doc.original_file);
            if (!existingDoc) {
                // If no existing doc with this original_file, add it
                return [...acc, doc];
            }
            return acc;
        }, []);

        console.log(`Filtered from ${relevantDocs.length} chunks to ${deduplicatedDocs.length} unique files`);

        // Step 4: Fetch raw content from GitHub URLs
        const docsWithRawContent = await Promise.all(
            deduplicatedDocs.map(async (doc: any) => {
                if (doc.original_file && doc.original_file.includes('github.com')) {
                    try {
                        // Convert GitHub URL to raw URL
                        const rawUrl = convertToRawGitHubUrl(doc.original_file);
                        console.log(`Fetching raw content from: ${rawUrl}`);
                        
                        const response = await fetch(rawUrl);
                        if (response.ok) {
                            const rawContent = await response.text();
                            return {
                                ...doc,
                                raw_content: rawContent
                            };
                        } else {
                            console.warn(`Failed to fetch ${rawUrl}: ${response.status}`);
                        }
                    } catch (error) {
                        console.warn(`Error fetching raw content for ${doc.original_file}:`, error);
                    }
                }
                return doc;
            })
        );

        console.log("building context");

        // Step 5: Build context for LLM
        const docsContext = docsWithRawContent
            .map((doc: any, index: number) => {
                let docText = `Document ${index + 1} (${doc.file}):\n${doc.content}`;
                
                // Add raw content if available
                if (doc.raw_content) {
                    docText += `\n\nFull file content:\n${doc.raw_content}`;
                }
                
                return docText;
            })
            .join('\n\n---\n\n');

        const systemPrompt = `You are a helpful assistant that answers user questions.

Use the retrieved documents and previous conversation context to answer the user's question. 
Base your answer on the documents, don't make up information.
If the information is not available in the documents, say so clearly.

- Do provide a clear and concise answer directly addressing the user question.
- Don't mention the retrieved documents in your answer. 
- Don't output the retrieved documents in your answer unless part of it directly answers the user question.
- Don't use triple backticks for anything else than code in your answer.

If you output code:
- Output the code in single code block at the end of your answer. D'ont include several blocks
- Surround code with triple backticks at the beginning and end of the code block.


Context: ${context}

Retrieved Documents:
${docsContext}

User question: ${query}
`;

        // Step 6: Generate response with full context
        const messages = [
            {
                role: 'system' as const,
                content: systemPrompt
            }
        ];

        const chatResponse = await mistral.chat.complete({
            model: 'mistral-medium-2505',
            messages,
            maxTokens: 1000,
            temperature: 0.1
        });

        const messageContent = chatResponse.choices?.[0]?.message?.content;
        const responseText = typeof messageContent === 'string' ? messageContent : 'I apologize, but I was unable to generate a response.';

        console.log("returning response ok");

        console.log("responseText", responseText);

        return json({
            success: true,
            response: responseText,
            sources: docsWithRawContent.map((doc: any) => ({
                file: doc.file,
                score: doc.score,
                chunk_id: doc.chunk_id,
                original_file: doc.original_file,
                has_raw_content: !!doc.raw_content
            })),
            metadata: searchMetadata
        });

    } catch (error) {
        console.error('RAG error:', error);
        return json({ 
            success: false, 
            error: 'Failed to process RAG request',
            details: error instanceof Error ? error.message : 'Unknown error'
        }, { status: 500 });
    }
}; 