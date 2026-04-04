export type TrainingInsightEndingBadgeVariant = 'header' | 'inline';

/** 从读模型 ending 中解析可展示的类别名（兼容 type / ending_type、数字等） */
export function pickDisplayableEndingPayload(
  ending: Record<string, unknown> | null | undefined
): Record<string, unknown> | null {
  if (!ending || typeof ending !== 'object') {
    return null;
  }
  const raw = ending.type ?? ending.ending_type;
  if (typeof raw === 'string' && raw.trim()) {
    return ending;
  }
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    return { ...ending, type: String(raw) };
  }
  return null;
}

/** 结局分类展示名，供报告页主标题等使用 */
export function getEndingTypeLabel(ending: Record<string, unknown> | null | undefined): string | null {
  const resolved = pickDisplayableEndingPayload(ending);
  if (!resolved) {
    return null;
  }
  const raw = resolved.type ?? resolved.ending_type;
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim();
  }
  return null;
}

export function TrainingInsightEndingBadge({
  ending,
  variant = 'header',
  showExplanation = false,
  hideTypeLine = false,
}: {
  ending: Record<string, unknown> | null | undefined;
  variant?: TrainingInsightEndingBadgeVariant;
  /** 内联区块是否在钤印下方展示完整说明（标题栏仍用 title 悬停） */
  showExplanation?: boolean;
  /** 主标题已展示结局分类时，右侧钤印可隐藏类型行以免重复 */
  hideTypeLine?: boolean;
}) {
  const resolved = pickDisplayableEndingPayload(ending);
  if (!resolved) {
    return null;
  }
  const rawType = resolved.type ?? resolved.ending_type;
  const typeLabel = typeof rawType === 'string' && rawType.trim() ? rawType.trim() : null;
  if (!typeLabel) {
    return null;
  }
  const scoreRaw = resolved.score;
  let scoreText: string | null = null;
  if (typeof scoreRaw === 'number' && Number.isFinite(scoreRaw)) {
    scoreText = scoreRaw.toFixed(2);
  } else if (typeof scoreRaw === 'string' && scoreRaw.trim()) {
    scoreText = scoreRaw.trim();
  }
  const explanation = typeof resolved.explanation === 'string' ? resolved.explanation : '';

  return (
    <div
      className={`training-ending-badge training-ending-badge--${variant}`}
      role="status"
      title={variant === 'header' && explanation ? explanation : undefined}
    >
      <span className="training-ending-badge__eyebrow">训练结局</span>
      {hideTypeLine ? null : <span className="training-ending-badge__type">{typeLabel}</span>}
      {scoreText ? <span className="training-ending-badge__score">综合 {scoreText}</span> : null}
      {showExplanation && explanation ? (
        <p className="training-ending-badge__explain">{explanation}</p>
      ) : null}
    </div>
  );
}
