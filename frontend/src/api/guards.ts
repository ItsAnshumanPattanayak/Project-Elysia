import type {
  ConversationDetail,
  ConversationList,
} from '../types/conversation'
import type { Message, MessageList } from '../types/message'
import type { RelationshipState } from '../types/relationship'
import type { AIStatus, HealthStatus } from '../types/system'
import type { MemoryList } from '../types/memory'
import { isObject } from './client'

export const isMessage = (v: unknown): v is Message =>
  isObject(v) &&
  (typeof v.id === 'number' || typeof v.id === 'string') &&
  typeof v.raw_content === 'string' &&
  typeof v.sender === 'string' &&
  typeof v.sequence_number === 'number'
export const isConversation = (v: unknown): v is ConversationDetail =>
  isObject(v) &&
  typeof v.id === 'number' &&
  typeof v.title === 'string' &&
  isObject(v.character) &&
  typeof v.character.display_name === 'string' &&
  typeof v.is_archived === 'boolean'
export const isConversationList = (v: unknown): v is ConversationList =>
  isObject(v) &&
  Array.isArray(v.items) &&
  v.items.every(isConversation) &&
  typeof v.total === 'number' &&
  typeof v.has_more === 'boolean'
export const isMessageList = (v: unknown): v is MessageList =>
  isObject(v) &&
  Array.isArray(v.items) &&
  v.items.every(isMessage) &&
  typeof v.total === 'number'
export const isRelationship = (v: unknown): v is RelationshipState =>
  isObject(v) &&
  typeof v.conversation_id === 'number' &&
  typeof v.mood === 'string' &&
  typeof v.trust === 'number'
export const isMemoryList = (v: unknown): v is MemoryList =>
  isObject(v) && Array.isArray(v.items) && typeof v.total === 'number'
export const isHealth = (v: unknown): v is HealthStatus =>
  isObject(v) && v.status === 'healthy' && v.database === 'connected'
export const isAIStatus = (v: unknown): v is AIStatus =>
  isObject(v) &&
  v.provider === 'ollama' &&
  typeof v.state === 'string' &&
  typeof v.model_ready === 'boolean'
