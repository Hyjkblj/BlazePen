import { Button, Card, Space, Typography } from 'antd';
import { getStaticAssetUrl } from '@/services/assetUrl';
import type {
  TrainingMediaTaskStatus,
  TrainingReportResult,
  TrainingScenario,
} from '@/types/training';
import TrainingCinematicChoiceBand from './TrainingCinematicChoiceBand';

type SceneImageStatus = TrainingMediaTaskStatus | 'idle';
type CompletionReportStatus = 'idle' | 'loading' | 'ready' | 'error';

interface TrainingRoundPanelProps {
  isCompleted: boolean;
  currentScenario: TrainingScenario | null;
  sessionProgressLabel: string | null;
  sceneImageStatus: SceneImageStatus;
  sceneImageUrl: string | null;
  sceneImageErrorMessage: string | null;
  completionReportStatus: CompletionReportStatus;
  completionReport: TrainingReportResult | null;
  completionReportErrorMessage: string | null;
  selectedOptionId: string | null;
  selectOption: (optionId: string) => void;
  submissionPreview: string | null;
  canSubmitRound: boolean;
  submitCurrentRound: () => void;
  retryRestore: () => void;
  clearWorkspace: () => void;
  completedEnding: Record<string, unknown> | null;
}

const SCENE_IMAGE_LOADING_STATUSES = new Set<SceneImageStatus>(['pending', 'running']);
const SCENE_IMAGE_FAILED_STATUSES = new Set<SceneImageStatus>(['failed', 'timeout']);

const readEndingSummary = (ending: Record<string, unknown> | null): string | null => {
  if (!ending) {
    return null;
  }

  const candidates = ['summary', 'ending_text', 'endingText', 'description', 'title'];
  for (const key of candidates) {
    const value = ending[key];
    if (typeof value === 'string' && value.trim() !== '') {
      return value.trim();
    }
  }

  return null;
};

const formatScoreDelta = (value: number | null | undefined): string => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
};

function TrainingRoundPanel({
  isCompleted,
  currentScenario,
  sessionProgressLabel,
  sceneImageStatus,
  sceneImageUrl,
  sceneImageErrorMessage,
  completionReportStatus,
  completionReport,
  completionReportErrorMessage,
  selectedOptionId,
  selectOption,
  submissionPreview,
  canSubmitRound,
  submitCurrentRound,
  retryRestore,
  clearWorkspace,
  completedEnding,
}: TrainingRoundPanelProps) {
  const completionSummary = completionReport?.summary ?? null;
  const reviewSuggestions = completionSummary?.reviewSuggestions ?? [];
  const endingSummary = readEndingSummary(completedEnding);

  return (
    <Card
      className="training-shell__panel training-shell__panel--primary training-shell__panel--antd"
      variant="borderless"
    >
      {isCompleted ? (
        <>
          <Typography.Title level={4}>训练完成</Typography.Title>
          <Typography.Paragraph className="training-shell__empty">
            本次训练流程已完成，以下为统一汇总结果。
          </Typography.Paragraph>

          {completionReportStatus === 'loading' ? (
            <Typography.Paragraph className="training-shell__completion-loading">
              正在汇总最终训练报告...
            </Typography.Paragraph>
          ) : null}

          {completionReportErrorMessage ? (
            <Typography.Paragraph className="training-shell__completion-error">
              {completionReportErrorMessage}
            </Typography.Paragraph>
          ) : null}

          {completionReport ? (
            <div className="training-shell__completion-grid">
              <div>
                <Typography.Text type="secondary">完成回合</Typography.Text>
                <Typography.Paragraph>{completionReport.rounds}</Typography.Paragraph>
              </div>
              <div>
                <Typography.Text type="secondary">综合提升</Typography.Text>
                <Typography.Paragraph>
                  {formatScoreDelta(completionSummary?.weightedScoreDelta ?? null)}
                </Typography.Paragraph>
              </div>
              <div>
                <Typography.Text type="secondary">高风险回合</Typography.Text>
                <Typography.Paragraph>{completionSummary?.highRiskRoundCount ?? 0}</Typography.Paragraph>
              </div>
              <div>
                <Typography.Text type="secondary">主要风险标签</Typography.Text>
                <Typography.Paragraph>{completionSummary?.dominantRiskFlag ?? '无'}</Typography.Paragraph>
              </div>
            </div>
          ) : null}

          {endingSummary ? (
            <Typography.Paragraph className="training-shell__completion-ending">
              {endingSummary}
            </Typography.Paragraph>
          ) : null}

          {reviewSuggestions.length > 0 ? (
            <div className="training-shell__completion-suggestions">
              <Typography.Title level={5}>后续建议</Typography.Title>
              <ul className="training-shell__metric-list">
                {reviewSuggestions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <Space className="training-shell__stack-actions">
            <Button className="training-shell__primary-button" type="primary" onClick={clearWorkspace}>
              开始新训练
            </Button>
          </Space>
        </>
      ) : currentScenario ? (
        <>
          <Typography.Title level={4}>{currentScenario.title}</Typography.Title>
          <Typography.Paragraph className="training-shell__scenario-meta">
            {(currentScenario.eraDate || '未标注时间') +
              ' · ' +
              (currentScenario.location || '未标注地点')}
          </Typography.Paragraph>
          {sessionProgressLabel ? (
            <Typography.Paragraph className="training-shell__scenario-progress">
              当前进度：{sessionProgressLabel}
            </Typography.Paragraph>
          ) : null}
          <Typography.Paragraph className="training-shell__scenario-brief">
            {currentScenario.brief || '当前场景暂无背景说明。'}
          </Typography.Paragraph>

          <section className="training-shell__scene-frame" aria-live="polite">
            {sceneImageUrl ? (
              <img
                className="training-shell__scene-image"
                src={getStaticAssetUrl(sceneImageUrl)}
                alt={`${currentScenario.title} 场景图`}
              />
            ) : (
              <div className="training-shell__scene-placeholder">场景影像生成中...</div>
            )}
            {SCENE_IMAGE_LOADING_STATUSES.has(sceneImageStatus) ? (
              <p className="training-shell__scene-caption">后端正在生成本场景影像</p>
            ) : null}
            {SCENE_IMAGE_FAILED_STATUSES.has(sceneImageStatus) && sceneImageErrorMessage ? (
              <p className="training-shell__scene-warning">{sceneImageErrorMessage}</p>
            ) : null}
          </section>

          <div className="training-shell__scenario-grid">
            <div>
              <Typography.Title level={5}>任务目标</Typography.Title>
              <Typography.Paragraph>
                {currentScenario.mission || '保持训练目标可持续推进。'}
              </Typography.Paragraph>
            </div>
            <div>
              <Typography.Title level={5}>决策焦点</Typography.Title>
              <Typography.Paragraph>
                {currentScenario.decisionFocus || '根据现场状态完成判断。'}
              </Typography.Paragraph>
            </div>
          </div>

          {currentScenario.options.length > 0 ? (
            <TrainingCinematicChoiceBand
              options={currentScenario.options}
              selectedOptionId={selectedOptionId}
              onSelectOption={selectOption}
            />
          ) : (
            <Typography.Paragraph className="training-shell__empty">
              当前场景缺少可选项，请尝试恢复会话。
            </Typography.Paragraph>
          )}

          {submissionPreview ? (
            <Typography.Paragraph className="training-shell__submission-preview">
              已选择：{submissionPreview}
            </Typography.Paragraph>
          ) : null}

          <Space className="training-shell__stack-actions" wrap>
            <Button
              className="training-shell__primary-button"
              type="primary"
              disabled={!canSubmitRound}
              onClick={submitCurrentRound}
            >
              提交本轮决策
            </Button>
            <Button className="training-shell__secondary-button" onClick={retryRestore}>
              按服务端进度恢复
            </Button>
          </Space>
        </>
      ) : (
        <>
          <Typography.Title level={4}>训练恢复待确认</Typography.Title>
          <Typography.Paragraph className="training-shell__empty">
            当前会话没有可继续的场景，请按服务端会话状态恢复。
          </Typography.Paragraph>
          <Space className="training-shell__stack-actions">
            <Button className="training-shell__primary-button" type="primary" onClick={retryRestore}>
              恢复当前训练
            </Button>
          </Space>
        </>
      )}
    </Card>
  );
}

export default TrainingRoundPanel;
