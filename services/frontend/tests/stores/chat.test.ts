import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '@/stores/chat';
import type { Message, Conversation } from '@/types';

describe('Chat Store', () => {
  beforeEach(() => {
    useChatStore.setState({
      conversations: [],
      activeConversationId: null,
      isStreaming: false,
      streamingMessage: null,
    });
  });

  it('starts with no conversations', () => {
    expect(useChatStore.getState().conversations).toHaveLength(0);
    expect(useChatStore.getState().activeConversationId).toBeNull();
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it('creates a new conversation', () => {
    const id = useChatStore.getState().createNewConversation();
    expect(id).toBeDefined();
    const state = useChatStore.getState();
    expect(state.conversations).toHaveLength(1);
    expect(state.activeConversationId).toBe(id);
  });

  it('sets active conversation', () => {
    const store = useChatStore.getState();
    store.setActiveConversation('conv-1');
    expect(useChatStore.getState().activeConversationId).toBe('conv-1');
  });

  it('adds and removes conversations', () => {
    const conv: Conversation = {
      id: 'conv-1',
      title: 'Test Chat',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    useChatStore.getState().addConversation(conv);
    expect(useChatStore.getState().conversations).toHaveLength(1);

    useChatStore.getState().removeConversation('conv-1');
    expect(useChatStore.getState().conversations).toHaveLength(0);
  });

  it('adds a message to a conversation', () => {
    const conv: Conversation = {
      id: 'conv-1',
      title: 'Test',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    useChatStore.getState().addConversation(conv);
    useChatStore.getState().setActiveConversation('conv-1');

    const msg: Message = {
      id: 'msg-1',
      role: 'user',
      content: 'Hello!',
      createdAt: new Date().toISOString(),
    };
    useChatStore.getState().addMessage('conv-1', msg);

    const messages = useChatStore.getState().getActiveMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0].role).toBe('user');
    expect(messages[0].content).toBe('Hello!');
  });

  it('manages streaming state', () => {
    useChatStore.getState().startStreaming('stream-msg-1');
    expect(useChatStore.getState().isStreaming).toBe(true);
    expect(useChatStore.getState().streamingMessage).not.toBeNull();

    useChatStore.getState().appendStreamChunk('Hello ');
    useChatStore.getState().appendStreamChunk('World');
    expect(useChatStore.getState().streamingMessage?.content).toBe('Hello World');

    useChatStore.getState().finishStreaming();
    expect(useChatStore.getState().isStreaming).toBe(false);
    expect(useChatStore.getState().streamingMessage).toBeNull();
  });

  it('sets streaming error', () => {
    useChatStore.getState().startStreaming('msg-1');
    useChatStore.getState().setStreamingError();
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it('clears active conversation', () => {
    const conv: Conversation = {
      id: 'conv-1', title: 'Test', messages: [],
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    };
    useChatStore.getState().addConversation(conv);
    useChatStore.getState().setActiveConversation('conv-1');
    useChatStore.getState().clearConversation();
    const messages = useChatStore.getState().getActiveMessages();
    expect(messages).toHaveLength(0);
  });

  it('sends a message', () => {
    const store = useChatStore.getState();
    store.sendMessage('Hi!');
    // After sending, there should be at least one conversation with messages
    const state = useChatStore.getState();
    expect(state.conversations.length).toBeGreaterThan(0);
  });
});
