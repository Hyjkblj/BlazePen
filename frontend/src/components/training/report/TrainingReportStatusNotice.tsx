import type { TrainingReportResult } from '@/types/training';

interface TrainingReportStatusNoticeProps {
  status: TrainingReportResult['status'];
  hasSummary: boolean;
}

function TrainingReportStatusNotice({
  status,
  hasSummary,
}: TrainingReportStatusNoticeProps) {
  if (status !== 'completed') {
    return (
      <section className="training-insight-section training-insight-section--state">
        <h2>报告仍在生成中</h2>
        <p className="training-insight-empty">
          当前训练会话状态为 <strong>{status}</strong>。以下内容是阶段性快照，建议继续训练并在完成后刷新报告以查看最终结论。
        </p>
      </section>
    );
  }

  if (hasSummary) {
    return null;
  }

  return (
    <section className="training-insight-section training-insight-section--state">
      <h2>摘要暂未就绪</h2>
      <p className="training-insight-empty">
        当前会话已完成，但服务端尚未返回完整摘要字段。你仍可先查看能力/状态变化和回合历史，稍后刷新可获取完整复盘建议。
      </p>
    </section>
  );
}

export default TrainingReportStatusNotice;
