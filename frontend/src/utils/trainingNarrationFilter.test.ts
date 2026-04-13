import { describe, expect, it } from 'vitest';
import { filterTrainingNarrationText } from './trainingNarrationFilter';

describe('filterTrainingNarrationText', () => {
  it('removes storyline metadata and mission directives before rendering', () => {
    const raw =
      '主线第1/6幕，承接“序章”。固定角色协同：赵川(前线通讯员)、老何(印刷与发布)。夜战突然升级，谣言已在街头流动。你必须用克制措辞写出第一版快讯，避免标题化放大恐慌。任务：在时间压力下决定首条快讯的发布策略，兼顾时效与核验。（完成后进入本幕小场景，且每个小场景都参与测评）';

    expect(filterTrainingNarrationText(raw)).toBe(
      '夜战突然升级，谣言已在街头流动。你必须用克制措辞写出第一版快讯，避免标题化放大恐慌'
    );
  });

  it('cleans fallback brief/mission multi-line narration text', () => {
    const raw = [
      '主线第2/6幕，承接上一幕。',
      '',
      '固定角色协同：赵川。',
      '',
      '前线电话突然中断，编辑部陷入短暂沉默。',
      '',
      '任务：在五分钟内发布核验声明。',
    ].join('\n');

    expect(filterTrainingNarrationText(raw)).toBe('前线电话突然中断，编辑部陷入短暂沉默');
  });

  it('keeps normal narrative text unchanged', () => {
    expect(filterTrainingNarrationText('雨夜里，报馆灯火未熄。')).toBe('雨夜里，报馆灯火未熄');
  });
});

