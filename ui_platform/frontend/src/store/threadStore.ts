import { create } from "zustand";

interface Thread {
  id: string;
  title: string;
  createdAt: string;
}

interface ThreadStore {
  threads: Thread[];
  activeThreadId: string | null;
  setThreads: (threads: Thread[]) => void;
  setActiveThread: (id: string) => void;
  addThread: (thread: Thread) => void;
}

export const useThreadStore = create<ThreadStore>((set) => ({
  threads: [],
  activeThreadId: null,

  setThreads: (threads) => set({ threads }),

  setActiveThread: (id) => set({ activeThreadId: id }),

  addThread: (thread) =>
    set((state) => ({
      threads: [thread, ...state.threads],
      activeThreadId: thread.id,
    })),
}));
