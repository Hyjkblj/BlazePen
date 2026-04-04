/** 与产品文档《抗战记者 KT 训练系统方案》等口径对齐的展示名。未知 code 回退为原字符串。 */

export const TRAINING_K_SKILL_LABELS: Record<string, string> = {
  K1: '史实核验',
  K2: '来源可信评估',
  K3: '时效-准确平衡',
  K4: '风险沟通表达',
  K5: '伦理与安全边界',
  K6: '反谣与纠偏',
  K7: '公共行动指引',
  K8: '沟通闭环管理',
};

/** S 状态维度（剧情态势），与架构设计文档命名一致。 */
export const TRAINING_S_STATE_LABELS: Record<string, string> = {
  credibility: '公信力',
  accuracy: '报道准确性',
  public_panic: '公众恐慌度',
  source_safety: '线人与来源安全',
  editor_trust: '编辑部信任',
  actionability: '行动指引有效性',
};

const K_PREFIX = /^K\d+$/i;

export function resolveTrainingMetricDisplayLabel(code: string): {
  primary: string;
  /** 有中文主名时附带技术编码，便于对照 API。 */
  codeLine: string | null;
} {
  const trimmed = code.trim();
  if (!trimmed) {
    return { primary: '—', codeLine: null };
  }

  const kLabel = TRAINING_K_SKILL_LABELS[trimmed];
  if (kLabel) {
    return { primary: kLabel, codeLine: trimmed.toUpperCase() };
  }

  const sLabel = TRAINING_S_STATE_LABELS[trimmed];
  if (sLabel) {
    return { primary: sLabel, codeLine: trimmed };
  }

  if (K_PREFIX.test(trimmed)) {
    return { primary: trimmed.toUpperCase(), codeLine: null };
  }

  return { primary: trimmed, codeLine: null };
}

/** 进度页 stateBar（camelCase）与 UI 条目的展示名。 */
export const TRAINING_STATE_BAR_LABELS: Record<string, string> = {
  editorTrust: '编辑部信任',
  publicStability: '舆情稳定度',
  sourceSafety: '线人与来源安全',
};

export const TRAINING_RUNTIME_FLAG_LABELS: Record<string, string> = {
  panicTriggered: '恐慌已触发',
  sourceExposed: '来源已暴露',
  editorLocked: '编务锁定',
  highRiskPath: '高风险路径',
};

export const TRAINING_DECISION_CONTEXT_LABELS: Record<string, string> = {
  selectionSource: '选择来源',
  recommendedScenarioId: '推荐场景',
  selectedScenarioId: '选中场景',
  candidatePool: '候选池规模',
};

export function resolveTrainingLabeledField(
  field: string,
  map: Record<string, string>
): { primary: string; codeLine: string | null } {
  const trimmed = field.trim();
  if (!trimmed) {
    return { primary: '—', codeLine: null };
  }
  const label = map[trimmed];
  if (label) {
    return { primary: label, codeLine: trimmed };
  }
  return { primary: trimmed, codeLine: null };
}
