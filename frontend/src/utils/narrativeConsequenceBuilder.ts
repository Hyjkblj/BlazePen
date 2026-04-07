export interface NarrativeConsequenceInput {
  impactHint: string | null;
  riskFlags: string[];
  skillDelta: Record<string, number>;
}

const RISK_FLAG_NARRATIVES: Record<string, string> = {
  panic: '⚠ 一些未经核实的信息引发了公众恐慌。',
  source_exposed: '⚠ 消息来源已经暴露，后续报道将面临压力。',
  editor_locked: '⚠ 编辑部对你的判断产生了质疑。',
  high_risk_path: '⚠ 你选择了一条充满风险的道路。',
};

const RISK_FLAG_FALLBACK = (flag: string) => `⚠ 检测到风险：${flag}。`;

const SKILL_DELTA_NARRATIVES: Record<string, { positive: string; negative: string }> = {
  verify_skill: {
    positive: '编辑对你的信任有所提升。',
    negative: '你的核实能力受到了质疑。',
  },
};

const SKILL_DELTA_THRESHOLD = 0.05;

const SKILL_DELTA_GENERIC_POSITIVE = '你在这次决策中展现出了更强的判断力。';
const SKILL_DELTA_GENERIC_NEGATIVE = '这次决策让你意识到还有需要改进的地方。';

/**
 * 将评估数据转化为叙事句子数组。
 * 输出字符串中禁止出现原始数值格式或原始字段名。
 */
export function buildNarrativeConsequence(input: NarrativeConsequenceInput): string[] {
  const lines: string[] = [];

  // impactHint 非空 → 包装为叙事句子
  if (input.impactHint && input.impactHint.trim() !== '') {
    lines.push(`你按下了发送键。几分钟后，${input.impactHint.trim()}。`);
  }

  // riskFlags 每条 → 转化为后果描述
  for (const flag of input.riskFlags) {
    const narrative = RISK_FLAG_NARRATIVES[flag] ?? RISK_FLAG_FALLBACK(flag);
    lines.push(narrative);
  }

  // skillDelta 中 |delta| > 0.05 的项 → 转化为隐性提示
  for (const [skill, delta] of Object.entries(input.skillDelta)) {
    if (Math.abs(delta) <= SKILL_DELTA_THRESHOLD) {
      continue;
    }

    const mapping = SKILL_DELTA_NARRATIVES[skill];
    if (mapping) {
      lines.push(delta > 0 ? mapping.positive : mapping.negative);
    } else {
      lines.push(delta > 0 ? SKILL_DELTA_GENERIC_POSITIVE : SKILL_DELTA_GENERIC_NEGATIVE);
    }
  }

  return lines;
}
