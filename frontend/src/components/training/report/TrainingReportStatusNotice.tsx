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
        <h2>学习总结还在更新</h2>
        <p className="training-insight-empty">
          当前学习会话状态为 <strong>{status}</strong>。下面可能是进行中快照，请继续完成实训，结束后再打开本页或点「刷新读取」查看完整总结。
        </p>
      </section>
    );
  }

  if (hasSummary) {
    return null;
  }

  return (
    <section className="training-insight-section training-insight-section--state">
      <h2>小结字段暂未齐</h2>
      <p className="training-insight-empty">
        本轮学习已标记完成，但服务器还没返回完整的小结数据。你可以先看下面的能力与情境变化、回合记录；稍后再刷新，通常会出现延伸练习建议。
      </p>
    </section>
  );
}

export default TrainingReportStatusNotice;
