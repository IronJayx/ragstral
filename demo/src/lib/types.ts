export type Message = {
    id: string;
    text: string;
    sender: "user" | "assistant";
    timestamp: Date;
}; 