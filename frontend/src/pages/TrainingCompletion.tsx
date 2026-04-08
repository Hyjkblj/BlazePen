import { useMemo } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { buildTrainingReportRoute, ROUTES } from '@/config/routes';
import { useTrainingReport } from '@/hooks/useTrainingReport';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import { useTypewriter } from '@/hooks/useTypewriter';
import './Training.css';

const readEndingNarrativeText = (ending: Record<string, unknown> | null | undefined): string | null => {
  if (!ending || typeof ending !== 'object') return null;

  const directCandidates = ['ending_text', 'endingText', 'description', 'explanation', 'title'] as const;
  for (const key of directCandidates) {
    const value = ending[key];
    if (typeof value === 'string' && value.trim() !== '') {
      return value.trim();
    }
  }

  const nestedCandidates = ['article', 'story', 'narrative'] as const;
  for (const key of nestedCandidates) {
    const value = ending[key];
    if (!value || typeof value !== 'object') continue;
    const record = value as Record<string, unknown>;
    for (const subKey of ['text', 'content', 'summary', 'description'] as const) {
      const subValue = record[subKey];
      if (typeof subValue === 'string' && subValue.trim() !== '') {
        return subValue.trim();
      }
    }
  }

  return null;
};

const resolveEndingTypeLabel = (ending: Record<string, unknown> | null | undefined): string | null => {
  if (!ending || typeof ending !== 'object') return null;
  const raw = ending.type ?? ending.ending_type;
  if (typeof raw === 'string' && raw.trim() !== '') return raw.trim();
  if (typeof raw === 'number' && Number.isFinite(raw)) return String(raw);
  return null;
};

const sanitizeCompletionNarrativeText = (text: string): string => {
  return text
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) return true;
      return !/^综合能力评分/.test(trimmed) && !/^综合加权分/.test(trimmed);
    })
    .join('\n')
    .trim();
};

const buildEndingFallbackNarrative = (endingType: string | null): string => {
  const normalizedType = (endingType ?? '').toLowerCase();
  let lead = '任务暂告一段落。你在高压信息环境下完成了取舍与发布，后续影响仍在持续扩散。';

  if (normalizedType.includes('excellent') || normalizedType.includes('卓越')) {
    lead = '你在保护线索人物与公共利益之间取得了稳健平衡，报道克制且可信。';
  } else if (normalizedType.includes('recovery') || normalizedType.includes('修复')) {
    lead = '你在不利局面下及时修正策略，降低了扩散风险并守住了关键底线。';
  } else if (normalizedType.includes('steady') || normalizedType.includes('稳健')) {
    lead = '你维持了稳定推进，信息发布节奏与风险控制保持在可接受区间。';
  } else if (normalizedType.includes('costly') || normalizedType.includes('代价')) {
    lead = '你完成了核心目标，但关键节点的代价偏高，后续影响仍需持续跟进。';
  } else if (normalizedType.includes('fail') || normalizedType.includes('失败')) {
    lead = '关键节点处理出现失衡，线索保护与信息发布目标都受到明显冲击。';
  }

  return `${lead}\n\n点击下方“查看可视化评估报告”，查看完整能力雷达与回合轨迹。`;
};

function TrainingCompletion() {
  const [searchParams] = useSearchParams();
  const explicitSessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload } = useTrainingReport(explicitSessionId);
  const sessionId = sessionTarget.sessionId ?? explicitSessionId;

  const completionStoryText = useMemo(() => {
    const endingPayload = data?.ending && typeof data.ending === 'object' ? data.ending : null;
    const endingText = readEndingNarrativeText(endingPayload);
    const endingType = resolveEndingTypeLabel(endingPayload);

    if (endingText) {
      const sanitizedEndingText = sanitizeCompletionNarrativeText(endingText);
      if (sanitizedEndingText) {
        if (endingType && !sanitizedEndingText.includes(endingType)) {
          return `[${endingType}]\n${sanitizedEndingText}`;
        }
        return sanitizedEndingText;
      }
    }

    return buildEndingFallbackNarrative(endingType);
  }, [data?.ending]);

  const { displayedText: completionStoryDisplayedText, isDone: completionStoryDone } = useTypewriter(
    completionStoryText,
    {
      charIntervalMs: 28,
      autoStart: status !== 'loading',
    }
  );

  if (!sessionId && status !== 'loading') {
    return <Navigate to={ROUTES.TRAINING_MAINHOME} replace />;
  }

  return (
    <div className="training-page training-page--simplified">
      <section className="training-simplified" aria-live="polite">
        <div className="training-simplified__scene-frame">
          <div className="training-simplified__scene-placeholder" aria-hidden="true" />
          {completionStoryText ? (
            <div className="training-simplified__completion-story" aria-live="polite">
              <p className="training-simplified__completion-story-text">
                {completionStoryDisplayedText}
                {!completionStoryDone ? (
                  <span className="training-simplified__narration-cursor" aria-hidden="true" />
                ) : null}
              </p>
            </div>
          ) : null}
        </div>

        <div className="training-simplified__feedback-stack">
          {status === 'loading' ? (
            <div className="training-simplified__feedback training-simplified__feedback--notice">
              <span>正在整理训练结局…</span>
            </div>
          ) : null}
          {hasStaleData ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>结局读取失败，正在展示最近一次可用结果。</span>
              <button type="button" onClick={reload}>
                重试读取
              </button>
            </div>
          ) : null}
          {errorMessage && !hasStaleData ? (
            <div className="training-simplified__feedback training-simplified__feedback--error">
              <span>{errorMessage}</span>
              <button type="button" onClick={reload}>
                重试读取
              </button>
            </div>
          ) : null}
        </div>

        {sessionId ? (
          <Link className="training-simplified__report-link" to={buildTrainingReportRoute(sessionId)}>
            查看可视化评估报告
          </Link>
        ) : null}
      </section>
    </div>
  );
}

export default TrainingCompletion;
