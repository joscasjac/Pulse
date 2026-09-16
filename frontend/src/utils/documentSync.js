import * as Y from 'yjs'

export function encodeState(doc) {
  const bytes = Y.encodeStateAsUpdate(doc)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary)
}
export function applyStates(doc, states) {
  for (const state of states) {
    Y.applyUpdate(doc, Uint8Array.from(atob(state), char => char.charCodeAt(0)), 'remote')
  }
}
