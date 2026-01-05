import { create } from "zustand";

interface ChatState {
  messages: { role: string; content: string }[];
  addMessage: (msg: { role: string; content: string }) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
}));
