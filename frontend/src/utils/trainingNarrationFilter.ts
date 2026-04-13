const META_SEGMENT_PATTERNS: ReadonlyArray<RegExp> = [
  /主线第\s*\d+\s*\/\s*\d+\s*幕[^。！？!?]*(?:[。！？!?]|$)/g,
  /固定角色协同[:：][^。！？!?]*(?:[。！？!?]|$)/g,
  /任务[:：][\s\S]*$/g,
  /[（(][^）)]*(?:本幕小场景|参与测评|完成后进入|测评引导)[^）)]*[）)]/g,
];

const META_LINE_PATTERNS: ReadonlyArray<RegExp> = [
  /^主线第\s*\d+\s*\/\s*\d+\s*幕/,
  /^固定角色协同[:：]/,
  /^任务[:：]/,
];

export const filterTrainingNarrationText = (value: string): string => {
  const normalizedInput = String(value ?? '')
    .replace(/\r\n?/g, '\n')
    .trim();
  if (!normalizedInput) return '';

  let filtered = normalizedInput;
  for (const pattern of META_SEGMENT_PATTERNS) {
    filtered = filtered.replace(pattern, '');
  }

  const lines = filtered
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
    .filter((line) => META_LINE_PATTERNS.every((pattern) => !pattern.test(line)));

  return lines
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/^[，,。；;：:\s]+/, '')
    .replace(/[，,。；;：:\s]+$/g, '')
    .trim();
};

