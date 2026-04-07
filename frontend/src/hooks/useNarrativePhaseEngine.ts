import { useCallback, useEffect, useRef, useState } from 'react';
import type { ScriptNarrativeLine, TrainingScenario } from '@/types/training';
import type { TrainingRoundOutcomeView } from '@/flows/useTrainingMvpFlow';
import { resolveNarrativeForScenario } from '@/utils/trainingSession';
import { buildNarrativeConsequence } from '@/utils/narrativeConsequenceBuilder';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NarrativePhase =
  | 'monologue'
  | 'dialogue'
  | 'decision_pause'
  | 'choice'
  | 'consequence'
  | 'bridge'
  | 'progress';

export interface NarrativePhaseState {
  phase: NarrativePhase;
  // Phase 1
  monologueSegments: string[];
  currentSegmentIndex: number;
  // Phase 2
  dialogueLines: ScriptNarrativeLine[];
  currentDialogueIndex: number;
  // Phase 3
  decisionPrompt: string;
  // Phase 5
  consequenceLines: string[];
  // Phase 6
  bridgeSummary: string;
}

export interface UseNarrativePhaseEngineOptions {
  scenario: TrainingScenario | null;
  storyScriptPayload: unknown;
  latestOutcome: TrainingRoundOutcomeView | null;
  onPhaseComplete: (phase: NarrativePhase) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SAFETY_TIMEOUT_MS = 5000;
const DECISION_PAUSE_MS = 1500;
const CONSEQUENCE_AUTO_ADVANCE_MS = 3000;
const MONOLOGUE_SEGMENT_PAUSE_MS = 300;
const MAX_DIALOGUE_LINES = 6;

const DECISION_PROMPTS = [
  '你需要做出决定了。',
  '现在，你会怎么做？',
  '时间不多了，选择吧。',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Split monologue text into segments by sentence-ending punctuation and double newlines.
 * Segments are trimmed and empty ones are filtered out.
 */
export function splitMonologueIntoSegments(text: string): string[] {
  if (!text || text.trim() === '') {
    return [];
  }

  // First split by paragraph breaks (\n\n)
  const paragraphs = text.split(/\n\n+/);
  const segments: string[] = [];

  for (const paragraph of paragraphs) {
    if (!paragraph.trim()) continue;

    // Split each paragraph by sentence-ending punctuation
    // Keep the punctuation attached to the sentence
    const sentences = paragraph.split(/(?<=[。！？…])/);
    for (const sentence of sentences) {
      const trimmed = sentence.trim();
      if (trimmed) {
        segments.push(trimmed);
      }
    }
  }

  return segments.length > 0 ? segments : [text.trim()];
}

function pickRandomDecisionPrompt(): string {
  return DECISION_PROMPTS[Math.floor(Math.random() * DECISION_PROMPTS.length)];
}

function buildNarrativeResetKey(
  scenario: TrainingScenario | null,
  storyScriptPayload: unknown
): string {
  const scenarioId = scenario?.id ?? 'null';

  let payloadVersion = 'none';
  let payloadNarrativeCount = 0;
  if (storyScriptPayload && typeof storyScriptPayload === 'object') {
    const payload = storyScriptPayload as Record<string, unknown>;
    const maybeVersion = payload.version;
    if (typeof maybeVersion === 'string' && maybeVersion.trim() !== '') {
      payloadVersion = maybeVersion.trim();
    } else {
      payloadVersion = 'unknown';
    }

    const maybeNarratives = payload.narratives;
    if (maybeNarratives && typeof maybeNarratives === 'object') {
      payloadNarrativeCount = Object.keys(maybeNarratives as Record<string, unknown>).length;
    }
  }

  return `${scenarioId}|${payloadVersion}|${payloadNarrativeCount}`;
}

function buildOutcomeSignature(latestOutcome: TrainingRoundOutcomeView | null): string {
  if (!latestOutcome) {
    return 'none';
  }
  const riskFlags = Array.isArray(latestOutcome.evaluation?.riskFlags)
    ? latestOutcome.evaluation.riskFlags
    : [];
  return [
    String(latestOutcome.roundNo ?? ''),
    latestOutcome.isCompleted ? '1' : '0',
    riskFlags.join('|'),
  ].join('|');
}

// ---------------------------------------------------------------------------
// Initial state factory
// ---------------------------------------------------------------------------

function buildInitialState(
  scenario: TrainingScenario | null,
  storyScriptPayload: unknown
): NarrativePhaseState {
  let narrative = null;
  if (scenario) {
    try {
      narrative = resolveNarrativeForScenario(storyScriptPayload, scenario.id);
    } catch {
      // silently degrade
    }
  }

  const hasNarrative = narrative !== null;

  // Monologue segments
  const monologueSegments =
    hasNarrative && narrative !== null
      ? splitMonologueIntoSegments(narrative.monologue ?? '')
      : [];

  // Dialogue lines (max 6)
  const dialogueLines =
    hasNarrative && narrative !== null
      ? (narrative.dialogue ?? []).slice(0, MAX_DIALOGUE_LINES)
      : [];

  // Decision prompt
  const decisionPrompt = pickRandomDecisionPrompt();

  // Consequence lines from latest outcome
  const consequenceLines: string[] = [];

  // Bridge summary
  const bridgeSummary =
    hasNarrative && narrative !== null ? (narrative.bridge_summary ?? '') : '';

  // Determine starting phase
  const startPhase: NarrativePhase = hasNarrative ? 'monologue' : 'choice';

  return {
    phase: startPhase,
    monologueSegments,
    currentSegmentIndex: 0,
    dialogueLines,
    currentDialogueIndex: 0,
    decisionPrompt,
    consequenceLines,
    bridgeSummary,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useNarrativePhaseEngine(
  options: UseNarrativePhaseEngineOptions
): {
  state: NarrativePhaseState;
  advance: () => void;
  skipToChoice: () => void;
} {
  const { scenario, storyScriptPayload, latestOutcome, onPhaseComplete } = options;

  const [state, setState] = useState<NarrativePhaseState>(() =>
    buildInitialState(scenario, storyScriptPayload)
  );

  // Track the previous reset key to detect when narrative inputs have materially changed.
  const prevResetKeyRef = useRef<string>(
    buildNarrativeResetKey(scenario, storyScriptPayload)
  );
  const prevOutcomeSignatureRef = useRef<string>(
    buildOutcomeSignature(latestOutcome)
  );

  // Keep a stable ref to onPhaseComplete to avoid stale closures in timeouts
  const onPhaseCompleteRef = useRef(onPhaseComplete);
  useEffect(() => {
    onPhaseCompleteRef.current = onPhaseComplete;
  }, [onPhaseComplete]);

  // Reset state machine when scenario changes
  useEffect(() => {
    const resetKey = buildNarrativeResetKey(scenario, storyScriptPayload);
    if (resetKey === prevResetKeyRef.current) return;
    prevResetKeyRef.current = resetKey;

    setState(buildInitialState(scenario, storyScriptPayload));
  }, [scenario, storyScriptPayload]);

  // Refresh consequence payload when a new submit outcome arrives.
  useEffect(() => {
    const outcomeSignature = buildOutcomeSignature(latestOutcome);
    if (outcomeSignature === prevOutcomeSignatureRef.current) return;
    prevOutcomeSignatureRef.current = outcomeSignature;

    if (!latestOutcome) {
      return;
    }

    const consequenceLines = buildNarrativeConsequence({
      impactHint: null,
      riskFlags: latestOutcome.evaluation?.riskFlags ?? [],
      skillDelta: latestOutcome.evaluation?.skillDelta ?? {},
    });
    setState((prev) => ({
      ...prev,
      consequenceLines,
      phase: prev.phase === 'choice' ? 'consequence' : prev.phase,
    }));
  }, [latestOutcome]);

  // ---------------------------------------------------------------------------
  // advance() — core transition logic
  // ---------------------------------------------------------------------------
  const advance = useCallback(() => {
    setState((prev) => {
      const next = computeNextState(prev);
      if (next.phase !== prev.phase) {
        // Notify caller asynchronously to avoid setState-during-render issues
        setTimeout(() => onPhaseCompleteRef.current(prev.phase), 0);
      }
      return next;
    });
  }, []);

  // ---------------------------------------------------------------------------
  // skipToChoice()
  // ---------------------------------------------------------------------------
  const skipToChoice = useCallback(() => {
    setState((prev) => {
      if (prev.phase === 'choice') return prev;
      setTimeout(() => onPhaseCompleteRef.current(prev.phase), 0);
      return { ...prev, phase: 'choice' };
    });
  }, []);

  // ---------------------------------------------------------------------------
  // Safety timeout (5s) + phase-specific auto-advance timers
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const { phase } = state;

    // Phases that don't need auto-advance timers
    if (phase === 'choice' || phase === 'progress') return;

    // Phase-specific delay
    let autoAdvanceMs: number | null = null;
    if (phase === 'decision_pause') {
      autoAdvanceMs = DECISION_PAUSE_MS;
    } else if (phase === 'consequence') {
      autoAdvanceMs = CONSEQUENCE_AUTO_ADVANCE_MS;
    }

    const timers: number[] = [];

    // Auto-advance timer (phase-specific)
    if (autoAdvanceMs !== null) {
      timers.push(window.setTimeout(() => advance(), autoAdvanceMs));
    }

    // Safety timeout (5s) — always set for non-choice/progress phases
    timers.push(window.setTimeout(() => advance(), SAFETY_TIMEOUT_MS));

    // Monologue segment auto-advance (300ms between segments)
    if (phase === 'monologue' && state.monologueSegments.length > 1) {
      timers.push(window.setTimeout(() => advance(), MONOLOGUE_SEGMENT_PAUSE_MS));
    }

    return () => {
      for (const t of timers) {
        window.clearTimeout(t);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase, state.currentSegmentIndex, state.currentDialogueIndex]);

  return { state, advance, skipToChoice };
}

// ---------------------------------------------------------------------------
// State transition logic (pure function for testability)
// ---------------------------------------------------------------------------

export function computeNextState(prev: NarrativePhaseState): NarrativePhaseState {
  switch (prev.phase) {
    case 'monologue': {
      const nextSegmentIndex = prev.currentSegmentIndex + 1;
      if (nextSegmentIndex < prev.monologueSegments.length) {
        // Still more segments to show
        return { ...prev, currentSegmentIndex: nextSegmentIndex };
      }
      // Monologue done — go to dialogue or decision_pause
      if (prev.dialogueLines.length > 0) {
        return { ...prev, phase: 'dialogue', currentDialogueIndex: 0 };
      }
      return { ...prev, phase: 'decision_pause' };
    }

    case 'dialogue': {
      const nextDialogueIndex = prev.currentDialogueIndex + 1;
      if (nextDialogueIndex < prev.dialogueLines.length) {
        return { ...prev, currentDialogueIndex: nextDialogueIndex };
      }
      // All dialogue lines shown
      return { ...prev, phase: 'decision_pause' };
    }

    case 'decision_pause':
      return { ...prev, phase: 'choice' };

    case 'choice':
      // choice → consequence is triggered externally (user submits option)
      // advance() from choice goes to consequence
      return { ...prev, phase: 'consequence' };

    case 'consequence':
      // If there's a bridge summary, go to bridge; otherwise done (progress)
      if (prev.bridgeSummary && prev.bridgeSummary.trim() !== '') {
        return { ...prev, phase: 'bridge' };
      }
      return { ...prev, phase: 'progress' };

    case 'bridge':
      return { ...prev, phase: 'progress' };

    case 'progress':
      return prev;

    default:
      return prev;
  }
}
