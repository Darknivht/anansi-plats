import { create } from "zustand";
import { generateId } from "../lib/utils";
import type { Conversation, Message, StreamingMessage } from "../types";

interface ChatState {
  // ── Conversations ──
  conversations: Conversation[];
  activeConversationId: string | null;

  setActiveConversation: (id: string) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (id: string) => void;

  // ── Messages ──
  getActiveMessages: () => Message[];
  addMessage: (conversationId: string, message: Message) => void;

  // ── Streaming ──
  isStreaming: boolean;
  streamingMessage: StreamingMessage | null;

  startStreaming: (messageId: string) => void;
  appendStreamChunk: (text: string) => void;
  finishStreaming: () => void;
  setStreamingError: () => void;

  // ── Actions ──
  sendMessage: (text: string) => void;
  clearConversation: () => void;
  createNewConversation: () => string;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // ── Conversations ──
  conversations: [],
  activeConversationId: null,

  setActiveConversation: (id) => set({ activeConversationId: id }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [...state.conversations, conversation],
    })),

  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      activeConversationId:
        state.activeConversationId === id ? null : state.activeConversationId,
    })),

  // ── Messages ──
  getActiveMessages: () => {
    const state = get();
    const conv = state.conversations.find((c) => c.id === state.activeConversationId);
    return conv?.messages ?? [];
  },

  addMessage: (conversationId, message) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === conversationId
          ? { ...c, messages: [...(c.messages ?? []), message] }
          : c,
      ),
    })),

  // ── Streaming ──
  isStreaming: false,
  streamingMessage: null,

  startStreaming: (messageId) =>
    set({
      isStreaming: true,
      streamingMessage: {
        id: messageId,
        role: "assistant",
        content: "",
        isComplete: false,
      },
    }),

  appendStreamChunk: (text) =>
    set((state) => ({
      streamingMessage: state.streamingMessage
        ? {
            ...state.streamingMessage,
            content: state.streamingMessage.content + text,
          }
        : state.streamingMessage,
    })),

  finishStreaming: () =>
    set((state) => {
      const msg = state.streamingMessage;
      if (msg) {
        const newMessage: Message = {
          id: msg.id,
          conversationId: state.activeConversationId ?? "",
          role: "assistant",
          content: msg.content,
          referencedMemoryNodes: [],
          createdAt: new Date().toISOString(),
        };

        // Add the completed message to the active conversation
        const updatedConversations = state.conversations.map((c) =>
          c.id === state.activeConversationId
            ? { ...c, messages: [...(c.messages ?? []), newMessage] }
            : c,
        );

        return {
          isStreaming: false,
          streamingMessage: null,
          conversations: updatedConversations,
        };
      }
      return { isStreaming: false, streamingMessage: null };
    }),

  setStreamingError: () =>
    set((state) => ({
      isStreaming: false,
      streamingMessage: state.streamingMessage
        ? { ...state.streamingMessage, content: "An error occurred while generating a response.", isComplete: true }
        : null,
    })),

  // ── Actions ──
  sendMessage: (text) => {
    const state = get();
    const conversationId =
      state.activeConversationId ?? state.createNewConversation();

    const userMessage: Message = {
      id: generateId(),
      conversationId,
      role: "user",
      content: text,
      referencedMemoryNodes: [],
      createdAt: new Date().toISOString(),
    };

    get().addMessage(conversationId, userMessage);

    // Start streaming a response
    const responseId = generateId();
    get().startStreaming(responseId);
  },

  clearConversation: () => {
    const state = get();
    if (state.activeConversationId) {
      set((s) => ({
        conversations: s.conversations.map((c) =>
          c.id === state.activeConversationId
            ? { ...c, messages: [] }
            : c,
        ),
      }));
    }
  },

  createNewConversation: () => {
    const id = generateId();
    const conversation: Conversation = {
      id,
      userId: "",
      channel: "web",
      title: null,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    get().addConversation(conversation);
    set({ activeConversationId: id });
    return id;
  },
}));
