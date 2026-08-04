import type {
  Message,
  MessageList,
  RegenerateResponse,
  SendMessageRequest,
  SendMessageResponse,
} from '../types/message'
import { isObject, requestJson, requestVoid } from './client'
import { isMessage, isMessageList } from './guards'

export const listMessages = (
  conversationId: number,
  options: { offset?: number; limit?: number } = {},
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams({
    offset: String(options.offset ?? 0),
    limit: String(options.limit ?? 50),
  })
  return requestJson<MessageList>(
    `/api/conversations/${conversationId}/messages?${query}`,
    isMessageList,
    { signal },
  )
}
const isSendResponse = (v: unknown): v is SendMessageResponse =>
  isObject(v) && isMessage(v.user_message) && isMessage(v.character_message)
const isRegenerate = (v: unknown): v is RegenerateResponse =>
  isObject(v) &&
  isMessage(v.character_message) &&
  typeof v.turn_count === 'number'
export const sendMessage = (
  conversationId: number,
  payload: SendMessageRequest,
  signal?: AbortSignal,
) =>
  requestJson<SendMessageResponse>(
    `/api/conversations/${conversationId}/messages`,
    isSendResponse,
    { method: 'POST', body: JSON.stringify(payload), signal },
  )
export const regenerateMessage = (conversationId: number) =>
  requestJson<RegenerateResponse>(
    `/api/conversations/${conversationId}/messages/regenerate`,
    isRegenerate,
    { method: 'POST', body: '{}' },
  )
export const editMessage = (
  conversationId: number,
  messageId: number,
  content: string,
  confirm = false,
) =>
  requestJson<Message>(
    `/api/conversations/${conversationId}/messages/${messageId}`,
    isMessage,
    {
      method: 'PATCH',
      body: JSON.stringify({
        content,
        confirm_truncate_following_messages: confirm,
      }),
    },
  )
export const deleteMessage = (
  conversationId: number,
  messageId: number,
  confirm = false,
) =>
  requestVoid(
    `/api/conversations/${conversationId}/messages/${messageId}?` +
      `confirm_truncate_following_messages=${confirm}`,
    { method: 'DELETE' },
  )
