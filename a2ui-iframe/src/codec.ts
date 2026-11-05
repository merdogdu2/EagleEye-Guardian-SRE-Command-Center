// Copyright 2026 EagleEye Guardian Contributors
// SPDX-License-Identifier: Apache-2.0

import { DEFAULT_WORKBENCH_STATE } from './demoData';
import { WorkbenchHydratedState } from './types';

function base64UrlToUint8Array(base64Url: string): Uint8Array {
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const padLength = (4 - (base64.length % 4)) % 4;
  const padded = base64 + '='.repeat(padLength);
  const binary = window.atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Inflate #s=z.<base64url> in-browser using native DecompressionStream('deflate-raw').
 * Falls back cleanly to DEFAULT_WORKBENCH_STATE when opened standalone.
 */
export async function hydrateStateFromHash(hashFragment: string): Promise<{
  state: WorkbenchHydratedState;
  hydrationSource: 'deflate-raw-hash' | 'standalone-demo';
}> {
  try {
    const trimmed = hashFragment.replace(/^#/, '');
    const params = new URLSearchParams(trimmed);
    const token = params.get('s');
    if (!token || !token.startsWith('z.')) {
      return { state: DEFAULT_WORKBENCH_STATE, hydrationSource: 'standalone-demo' };
    }

    const compressedBytes = base64UrlToUint8Array(token.slice(2));
    if (typeof DecompressionStream === 'undefined') {
      return { state: DEFAULT_WORKBENCH_STATE, hydrationSource: 'standalone-demo' };
    }

    const ds = new DecompressionStream('deflate-raw');
    const writer = ds.writable.getWriter();
    await writer.write(new Uint8Array(compressedBytes));
    await writer.close();

    const decompressedBuffer = await new Response(ds.readable).arrayBuffer();
    const jsonText = new TextDecoder('utf-8').decode(decompressedBuffer);
    const parsed = JSON.parse(jsonText) as Partial<WorkbenchHydratedState>;

    return {
      state: {
        ...DEFAULT_WORKBENCH_STATE,
        ...parsed,
        hyperdiskDefaults: {
          ...DEFAULT_WORKBENCH_STATE.hyperdiskDefaults,
          ...(parsed.hyperdiskDefaults ?? {}),
        },
        incident: {
          ...DEFAULT_WORKBENCH_STATE.incident,
          ...(parsed.incident ?? {}),
        },
      },
      hydrationSource: 'deflate-raw-hash',
    };
  } catch {
    return { state: DEFAULT_WORKBENCH_STATE, hydrationSource: 'standalone-demo' };
  }
}

/**
 * Bidirectional A2UI v0.9 postMessage bridge to the parent Gemini Enterprise window.
 */
export function dispatchA2UIAction(
  actionName: string,
  humanReadablePrompt: string,
  payload: Record<string, unknown> = {},
): { type: 'a2ui_action'; action: string; data: { prompt: string; [k: string]: unknown } } {
  const params = new URLSearchParams(window.location.search);
  const rawOrigin = params.get('origin');
  const targetOrigin =
    rawOrigin && rawOrigin !== 'REPLACE_WITH_PARENT_ORIGIN' ? rawOrigin : '*';

  const message = {
    type: 'a2ui_action' as const,
    action: actionName,
    data: {
      prompt: humanReadablePrompt,
      ...payload,
    },
  };

  if (typeof window !== 'undefined' && window.parent) {
    window.parent.postMessage(message, targetOrigin);
  }
  return message;
}
