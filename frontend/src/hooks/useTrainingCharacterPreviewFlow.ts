import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TrainingPortraitPreviewStatus } from '@/components/training/TrainingPortraitPreview';
import { ServiceError } from '@/services/serviceError';
import {
  createTrainingCharacter,
  createTrainingCharacterPreviewJob,
  getTrainingCharacterImages,
  listTrainingIdentityPresets,
  removeTrainingCharacterBackground,
  waitForTrainingCharacterPreviewJob,
  type TrainingIdentityPresetOption,
} from '@/services/trainingCharacterApi';

type TrainingFormDraftValue = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

type PreviewGenerationStatus = 'loading' | 'ready' | 'error';

type PersistedPreviewJobSnapshot = {
  version: 3;
  generationKey: string;
  attemptNo: number;
  idempotencyKey: string;
  jobId: string | null;
};

type PersistedPreviewJobSnapshotRaw = {
  version?: 1 | 2 | 3;
  generationKey?: unknown;
  characterId?: unknown;
  attemptNo?: unknown;
  idempotencyKey?: unknown;
  jobId?: unknown;
};

type ActivePreviewJobContext = PersistedPreviewJobSnapshot & {
  characterId: string | null;
};

type UseTrainingCharacterPreviewFlowOptions = {
  formDraft: TrainingFormDraftValue;
  onStartTraining: () => void | Promise<void>;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
};

type UseTrainingCharacterPreviewFlowResult = {
  handleConfirmTraining: () => Promise<void>;
  handleGeneratePreview: () => Promise<void>;
  identityPresetError: string | null;
  identityPresetOptions: TrainingIdentityPresetOption[];
  identityPresetStatus: PreviewGenerationStatus;
  isPersistingPortraitSelection: boolean;
  previewError: string | null;
  previewImageUrls: string[];
  previewStatus: TrainingPortraitPreviewStatus;
  selectedPreviewIndex: number | null;
  setSelectedPreviewIndex: (index: number) => void;
};

const PREVIEW_JOB_STORAGE_KEY = 'training:preview-job:v1';

class PreviewJobTerminalFailureError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PreviewJobTerminalFailureError';
  }
}

const parseAge = (rawAge: string): number | undefined => {
  const normalized = rawAge.trim();
  if (!normalized) {
    return undefined;
  }

  const age = Number.parseInt(normalized, 10);
  if (!Number.isInteger(age) || age <= 0) {
    return undefined;
  }

  return age;
};

const parsePositiveInt = (value: string): number | null => {
  const normalized = value.trim();
  if (!/^\d+$/.test(normalized)) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

const trimOrNull = (value: string): string | null => {
  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const readExistingPreviewJobId = (error: unknown): string | null => {
  if (!(error instanceof ServiceError)) {
    return null;
  }
  if (
    error.code !== 'TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT' &&
    error.status !== 409
  ) {
    return null;
  }
  if (!error.details || typeof error.details !== 'object') {
    return null;
  }

  const details = error.details as Record<string, unknown>;
  const existingJobId =
    typeof details.existing_job_id === 'string'
      ? details.existing_job_id
      : typeof details.existingJobId === 'string'
        ? details.existingJobId
        : '';
  const normalized = existingJobId.trim();
  return normalized === '' ? null : normalized;
};

const isPreviewPollTimeoutError = (error: unknown): boolean =>
  error instanceof ServiceError && error.code === 'REQUEST_TIMEOUT';

const shouldStartNewAttemptAfterError = (error: unknown): boolean =>
  error instanceof PreviewJobTerminalFailureError;

const shouldDropCurrentJobIdAfterError = (error: unknown): boolean =>
  error instanceof ServiceError && error.code === 'NOT_FOUND';

const pickPreviewImageUrls = (imageUrls: string[], limit = 2): string[] => {
  const selected: string[] = [];
  const seen = new Set<string>();

  for (const imageUrl of imageUrls) {
    if (selected.length >= limit) {
      break;
    }
    if (typeof imageUrl !== 'string') {
      continue;
    }

    const normalized = imageUrl.trim();
    if (!normalized || seen.has(normalized)) {
      continue;
    }

    seen.add(normalized);
    selected.push(normalized);
  }

  return selected;
};

const buildPreviewGenerationKey = (draft: TrainingFormDraftValue): string =>
  [
    draft.portraitPresetId.trim(),
    draft.playerName.trim(),
    draft.playerGender.trim(),
    draft.playerIdentity.trim(),
    draft.playerAge.trim(),
  ].join('|');

const hashString = (input: string): string => {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
};

const buildPreviewIdempotencyKey = (characterId: string, attemptNo: number): string => {
  const normalizedAttemptNo = Math.max(1, Math.floor(attemptNo));
  const canonicalPayload = `${characterId}|portrait|3|v2|attempt:${normalizedAttemptNo}`;
  return `training-preview-${characterId}-a${normalizedAttemptNo}-${hashString(canonicalPayload)}`;
};

const toPersistedPreviewSnapshot = (
  context: ActivePreviewJobContext
): PersistedPreviewJobSnapshot => ({
  version: 3,
  generationKey: context.generationKey,
  attemptNo: context.attemptNo,
  idempotencyKey: context.idempotencyKey,
  jobId: context.jobId,
});

const readPersistedPreviewSnapshot = (): PersistedPreviewJobSnapshot | null => {
  try {
    const raw = globalThis.localStorage?.getItem(PREVIEW_JOB_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as PersistedPreviewJobSnapshotRaw | null;
    if (!parsed || (parsed.version !== 1 && parsed.version !== 2 && parsed.version !== 3)) {
      return null;
    }

    const generationKey = typeof parsed.generationKey === 'string' ? parsed.generationKey.trim() : '';
    const attemptNo =
      typeof parsed.attemptNo === 'number' &&
      Number.isInteger(parsed.attemptNo) &&
      parsed.attemptNo > 0
        ? parsed.attemptNo
        : 1;
    const idempotencyKey =
      typeof parsed.idempotencyKey === 'string' ? parsed.idempotencyKey.trim() : '';
    const jobId = typeof parsed.jobId === 'string' ? parsed.jobId.trim() : null;
    if (!generationKey || !idempotencyKey) {
      return null;
    }
    return {
      version: 3,
      generationKey,
      attemptNo,
      idempotencyKey,
      jobId: jobId || null,
    };
  } catch {
    return null;
  }
};

const persistPreviewSnapshot = (snapshot: PersistedPreviewJobSnapshot) => {
  try {
    globalThis.localStorage?.setItem(PREVIEW_JOB_STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    // ignore local storage failures
  }
};

const clearPersistedPreviewSnapshot = () => {
  try {
    globalThis.localStorage?.removeItem(PREVIEW_JOB_STORAGE_KEY);
  } catch {
    // ignore local storage failures
  }
};

export const useTrainingCharacterPreviewFlow = ({
  formDraft,
  onStartTraining,
  updateFormDraft,
}: UseTrainingCharacterPreviewFlowOptions): UseTrainingCharacterPreviewFlowResult => {
  const [previewStatus, setPreviewStatus] = useState<TrainingPortraitPreviewStatus>('idle');
  const [previewImageUrls, setPreviewImageUrls] = useState<string[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState<number | null>(null);
  const [identityPresetStatus, setIdentityPresetStatus] = useState<PreviewGenerationStatus>('loading');
  const [identityPresetError, setIdentityPresetError] = useState<string | null>(null);
  const [identityPresetOptions, setIdentityPresetOptions] = useState<TrainingIdentityPresetOption[]>([]);
  const [isPersistingPortraitSelection, setIsPersistingPortraitSelection] = useState(false);
  const [isResumingCachedJob, setIsResumingCachedJob] = useState(false);

  const activePreviewJobRef = useRef<ActivePreviewJobContext | null>(null);
  const shouldStartNewAttemptOnRetryRef = useRef(false);
  const lastGeneratedKeyRef = useRef<string | null>(null);
  const resumedJobIdRef = useRef<string | null>(null);
  const currentPreviewGenerationKey = useMemo(
    () => buildPreviewGenerationKey(formDraft),
    [formDraft]
  );
  const hasRequiredPortraitFields = formDraft.portraitPresetId.trim() !== '';

  const resetPreviewState = useCallback((errorMessage: string | null) => {
    setPreviewStatus('idle');
    setPreviewImageUrls([]);
    setSelectedPreviewIndex(null);
    setPreviewError(errorMessage);
  }, []);

  const applyPreviewResult = useCallback(
    async (
      jobId: string,
      fallbackCharacterId: string | null = null
    ): Promise<string | null> => {
      const previewJobResult = await waitForTrainingCharacterPreviewJob(jobId, {
        timeoutMs: 180000,
        pollIntervalMs: 2000,
      });
      if (previewJobResult.status !== 'succeeded') {
        throw new PreviewJobTerminalFailureError(
          previewJobResult.errorMessage ?? '形象图生成失败，请稍后重试。'
        );
      }

      const previewCharacterId = parsePositiveInt(previewJobResult.characterId);
      const fallbackCharacterIdInt = parsePositiveInt(fallbackCharacterId ?? '');
      const resolvedCharacterId =
        previewCharacterId !== null
          ? String(previewCharacterId)
          : fallbackCharacterIdInt !== null
            ? String(fallbackCharacterIdInt)
            : null;

      let imageCandidates = [...previewJobResult.imageUrls];
      if (imageCandidates.length === 0) {
        if (!resolvedCharacterId) {
          throw new PreviewJobTerminalFailureError('预览任务缺少角色上下文，请重新生成形象图。');
        }
        const imageResponse = await getTrainingCharacterImages(resolvedCharacterId);
        imageCandidates = Array.isArray(imageResponse.images) ? imageResponse.images : [];
      }

      const resolvedImageUrls = pickPreviewImageUrls(imageCandidates, 2);
      if (resolvedImageUrls.length === 0) {
        throw new PreviewJobTerminalFailureError('后端已响应，但未返回可用图片链接。');
      }

      setPreviewImageUrls(resolvedImageUrls);
      setSelectedPreviewIndex(0);
      setPreviewStatus('ready');
      setPreviewError(null);
      shouldStartNewAttemptOnRetryRef.current = false;
      lastGeneratedKeyRef.current = currentPreviewGenerationKey;
      return resolvedCharacterId;
    },
    [currentPreviewGenerationKey]
  );

  useEffect(() => {
    let canceled = false;

    setIdentityPresetStatus('loading');
    setIdentityPresetError(null);
    setIdentityPresetOptions([]);

    void (async () => {
      try {
        const presets = await listTrainingIdentityPresets();
        if (canceled) {
          return;
        }
        setIdentityPresetOptions(presets);
        if (presets.length === 0) {
          setIdentityPresetStatus('error');
          setIdentityPresetError('当前没有可用的训练身份预设，请稍后重试。');
          return;
        }
        setIdentityPresetStatus('ready');
      } catch (error: unknown) {
        if (canceled) {
          return;
        }
        const message = error instanceof Error ? error.message : '加载身份预设失败，请稍后重试。';
        setIdentityPresetStatus('error');
        setIdentityPresetError(message);
      }
    })();

    return () => {
      canceled = true;
    };
  }, []);

  useEffect(() => {
    if (!lastGeneratedKeyRef.current) {
      return;
    }
    if (lastGeneratedKeyRef.current === currentPreviewGenerationKey) {
      return;
    }

    activePreviewJobRef.current = null;
    shouldStartNewAttemptOnRetryRef.current = false;
    resumedJobIdRef.current = null;
    clearPersistedPreviewSnapshot();
    lastGeneratedKeyRef.current = null;
    resetPreviewState('人物信息已变更，请重新生成形象图。');
  }, [currentPreviewGenerationKey, resetPreviewState]);

  useEffect(() => {
    if (isResumingCachedJob || previewStatus === 'ready') {
      return;
    }
    if (identityPresetStatus !== 'ready') {
      return;
    }
    if (!hasRequiredPortraitFields) {
      return;
    }

    const snapshot = readPersistedPreviewSnapshot();
    if (!snapshot || snapshot.generationKey !== currentPreviewGenerationKey || !snapshot.jobId) {
      return;
    }

    if (resumedJobIdRef.current === snapshot.jobId) {
      return;
    }
    resumedJobIdRef.current = snapshot.jobId;
    activePreviewJobRef.current = {
      ...snapshot,
      characterId: null,
    };

    setIsResumingCachedJob(true);
    setPreviewStatus('loading');
    setPreviewError('妫€娴嬪埌鏈畬鎴愮殑褰㈣薄鍥句换鍔★紝姝ｅ湪鎭㈠涓?..');

    void (async () => {
      try {
        const resolvedCharacterId = await applyPreviewResult(snapshot.jobId!, formDraft.characterId.trim());
        if (activePreviewJobRef.current) {
          activePreviewJobRef.current.characterId = resolvedCharacterId;
          persistPreviewSnapshot(toPersistedPreviewSnapshot(activePreviewJobRef.current));
        }
        if (formDraft.characterId.trim() === '' && resolvedCharacterId) {
          updateFormDraft('characterId', resolvedCharacterId);
        }
      } catch (error: unknown) {
        if (error instanceof ServiceError && error.code === 'NOT_FOUND') {
          activePreviewJobRef.current = null;
          shouldStartNewAttemptOnRetryRef.current = false;
          clearPersistedPreviewSnapshot();
          resetPreviewState('之前的渲染任务已失效，请重新生成形象图。');
          return;
        }

        shouldStartNewAttemptOnRetryRef.current = shouldStartNewAttemptAfterError(error);
        setPreviewStatus('error');
        setPreviewError(
          error instanceof Error ? error.message : '恢复渲染任务失败，请重新生成形象图。'
        );
      } finally {
        setIsResumingCachedJob(false);
      }
    })();
  }, [
    applyPreviewResult,
    currentPreviewGenerationKey,
    formDraft.characterId,
    hasRequiredPortraitFields,
    identityPresetStatus,
    isResumingCachedJob,
    previewStatus,
    resetPreviewState,
    updateFormDraft,
  ]);

  const handleGeneratePreview = useCallback(async () => {
    if (identityPresetStatus !== 'ready') {
      setPreviewStatus('error');
      setPreviewError(identityPresetError ?? '身份预设尚未加载完成，请稍后重试。');
      return;
    }

    if (!hasRequiredPortraitFields) {
      setPreviewStatus('error');
      setPreviewError('请先选择一个身份预设。');
      return;
    }

    const resolvedPlayerName = trimOrNull(formDraft.playerName);
    const resolvedIdentity = trimOrNull(formDraft.playerIdentity);
    const resolvedGender = trimOrNull(formDraft.playerGender);

    setPreviewStatus('loading');
    setPreviewError(null);
    setSelectedPreviewIndex(null);

    try {
      let resolvedCharacterId = formDraft.characterId.trim();
      let resolvedCharacterIdInt = parsePositiveInt(resolvedCharacterId);
      const currentContext = activePreviewJobRef.current;
      const canReuseCurrentCharacter =
        resolvedCharacterIdInt !== null &&
        resolvedCharacterId !== '' &&
        (currentContext === null ||
          (currentContext.generationKey === currentPreviewGenerationKey &&
            (currentContext.characterId === null ||
              currentContext.characterId === resolvedCharacterId)));

      if (!canReuseCurrentCharacter) {
        const createdCharacter = await createTrainingCharacter({
          identity_code: formDraft.portraitPresetId.trim(),
          name: resolvedPlayerName ?? undefined,
          gender: resolvedGender ?? undefined,
          age: parseAge(formDraft.playerAge),
          identity: resolvedIdentity ?? undefined,
        });

        resolvedCharacterId = createdCharacter.characterId.trim();
        resolvedCharacterIdInt = parsePositiveInt(resolvedCharacterId);
        if (!resolvedCharacterId || !resolvedCharacterIdInt) {
          throw new Error('创建训练角色失败：后端未返回有效 characterId。');
        }
        updateFormDraft('characterId', resolvedCharacterId);
      }

      const isRetryAfterError = previewStatus === 'error';
      const shouldStartNewAttempt =
        isRetryAfterError && shouldStartNewAttemptOnRetryRef.current;
      const baseAttemptNo = currentContext?.attemptNo ?? 1;
      const nextAttemptNo = canReuseCurrentCharacter
        ? shouldStartNewAttempt
          ? baseAttemptNo + 1
          : baseAttemptNo
        : 1;
      const idempotencyKey = buildPreviewIdempotencyKey(resolvedCharacterId, nextAttemptNo);
      const nextContext: ActivePreviewJobContext = {
        version: 3,
        generationKey: currentPreviewGenerationKey,
        characterId: resolvedCharacterId,
        attemptNo: nextAttemptNo,
        idempotencyKey,
        jobId: shouldStartNewAttempt ? null : currentContext?.jobId ?? null,
      };
      activePreviewJobRef.current = nextContext;
      persistPreviewSnapshot(toPersistedPreviewSnapshot(nextContext));

      if (
        canReuseCurrentCharacter &&
        isRetryAfterError &&
        !shouldStartNewAttempt &&
        nextContext.jobId
      ) {
        resumedJobIdRef.current = nextContext.jobId;
        const previewCharacterId = await applyPreviewResult(nextContext.jobId, resolvedCharacterId);
        nextContext.characterId = previewCharacterId;
        persistPreviewSnapshot(toPersistedPreviewSnapshot(nextContext));
        if (formDraft.characterId.trim() === '' && previewCharacterId) {
          updateFormDraft('characterId', previewCharacterId);
        }
        return;
      }

      const previewJob = await createTrainingCharacterPreviewJob({
        character_id: resolvedCharacterIdInt!,
        idempotency_key: idempotencyKey,
        image_type: 'portrait',
        group_count: 3,
      });
      if (!previewJob.jobId) {
        throw new Error('创建预览任务失败：后端未返回任务 ID。');
      }

      nextContext.jobId = previewJob.jobId;
      activePreviewJobRef.current = nextContext;
      persistPreviewSnapshot(toPersistedPreviewSnapshot(nextContext));
      resumedJobIdRef.current = previewJob.jobId;
      shouldStartNewAttemptOnRetryRef.current = false;

      const previewCharacterId = await applyPreviewResult(previewJob.jobId, resolvedCharacterId);
      nextContext.characterId = previewCharacterId;
      persistPreviewSnapshot(toPersistedPreviewSnapshot(nextContext));
      if (formDraft.characterId.trim() === '' && previewCharacterId) {
        updateFormDraft('characterId', previewCharacterId);
      }
    } catch (error: unknown) {
      const existingJobId = readExistingPreviewJobId(error);
      const resumableContext = activePreviewJobRef.current;
      if (existingJobId && resumableContext) {
        const resumedContext: ActivePreviewJobContext = {
          ...resumableContext,
          jobId: existingJobId,
        };
        activePreviewJobRef.current = resumedContext;
        persistPreviewSnapshot(toPersistedPreviewSnapshot(resumedContext));
        resumedJobIdRef.current = existingJobId;
        try {
          const previewCharacterId = await applyPreviewResult(
            existingJobId,
            resumedContext.characterId ?? formDraft.characterId.trim()
          );
          resumedContext.characterId = previewCharacterId;
          persistPreviewSnapshot(toPersistedPreviewSnapshot(resumedContext));
          if (formDraft.characterId.trim() === '' && previewCharacterId) {
            updateFormDraft('characterId', previewCharacterId);
          }
          shouldStartNewAttemptOnRetryRef.current = false;
          return;
        } catch (resumeError: unknown) {
          shouldStartNewAttemptOnRetryRef.current = shouldStartNewAttemptAfterError(resumeError);
          if (shouldDropCurrentJobIdAfterError(resumeError)) {
            resumedContext.jobId = null;
            activePreviewJobRef.current = resumedContext;
            persistPreviewSnapshot(toPersistedPreviewSnapshot(resumedContext));
          }
          if (isPreviewPollTimeoutError(resumeError)) {
            shouldStartNewAttemptOnRetryRef.current = false;
          }
          const message =
            resumeError instanceof Error
              ? resumeError.message
              : '恢复式预览任务失败，请稍后重试。';
          setPreviewStatus('error');
          setPreviewError(message);
          return;
        }
      }

      shouldStartNewAttemptOnRetryRef.current = shouldStartNewAttemptAfterError(error);
      if (shouldDropCurrentJobIdAfterError(error) && resumableContext) {
        resumableContext.jobId = null;
        activePreviewJobRef.current = resumableContext;
        persistPreviewSnapshot(toPersistedPreviewSnapshot(resumableContext));
      }
      if (isPreviewPollTimeoutError(error)) {
        shouldStartNewAttemptOnRetryRef.current = false;
      }

      const message = error instanceof Error ? error.message : '渲染失败，请稍后重试。';
      setPreviewStatus('error');
      setPreviewError(message);
    }
  }, [
    applyPreviewResult,
    currentPreviewGenerationKey,
    formDraft.characterId,
    formDraft.playerAge,
    formDraft.playerGender,
    formDraft.playerIdentity,
    formDraft.playerName,
    formDraft.portraitPresetId,
    hasRequiredPortraitFields,
    identityPresetError,
    identityPresetStatus,
    previewStatus,
    updateFormDraft,
  ]);

  const handleConfirmTraining = useCallback(async () => {
    if (identityPresetStatus !== 'ready') {
      setPreviewStatus('error');
      setPreviewError(identityPresetError ?? '身份预设尚未加载完成，请稍后重试。');
      return;
    }

    if (!hasRequiredPortraitFields) {
      setPreviewStatus('error');
      setPreviewError('请先选择身份预设，再进入训练。');
      return;
    }

    const resolvedCharacterId = formDraft.characterId.trim();
    if (!resolvedCharacterId || !parsePositiveInt(resolvedCharacterId)) {
      setPreviewStatus('error');
      setPreviewError('请先生成形象图，再进入训练。');
      return;
    }

    if (
      previewStatus !== 'ready' ||
      previewImageUrls.length === 0 ||
      selectedPreviewIndex === null ||
      !previewImageUrls[selectedPreviewIndex]
    ) {
      setPreviewStatus('error');
      setPreviewError('请选择一张形象图后再进入训练。');
      return;
    }

    setIsPersistingPortraitSelection(true);
    try {
      await removeTrainingCharacterBackground(resolvedCharacterId, {
        imageUrl: previewImageUrls[selectedPreviewIndex],
        imageUrls: previewImageUrls,
        selectedIndex: selectedPreviewIndex,
      });
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : '保存形象图选择失败，请稍后重试后再进入训练。';
      setPreviewStatus('error');
      setPreviewError(message);
      setIsPersistingPortraitSelection(false);
      return;
    }

    try {
      await onStartTraining();
      activePreviewJobRef.current = null;
      resumedJobIdRef.current = null;
      clearPersistedPreviewSnapshot();
    } finally {
      setIsPersistingPortraitSelection(false);
    }
  }, [
    formDraft.characterId,
    hasRequiredPortraitFields,
    identityPresetError,
    identityPresetStatus,
    onStartTraining,
    previewImageUrls,
    previewStatus,
    selectedPreviewIndex,
  ]);

  return {
    handleConfirmTraining,
    handleGeneratePreview,
    identityPresetError,
    identityPresetOptions,
    identityPresetStatus,
    isPersistingPortraitSelection,
    previewError,
    previewImageUrls,
    previewStatus,
    selectedPreviewIndex,
    setSelectedPreviewIndex,
  };
};

