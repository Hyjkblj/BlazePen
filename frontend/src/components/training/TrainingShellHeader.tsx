import { Link } from 'react-router-dom';
import {
  ROUTES,
  buildTrainingDiagnosticsRoute,
  buildTrainingProgressRoute,
  buildTrainingReportRoute,
} from '@/config/routes';

interface TrainingShellHeaderProps {
  hasInsightEntry: boolean;
  insightSessionId: string | null;
  onClearWorkspace: () => void;
}

const insightLinks = (sessionId: string | null) => [
  {
    label: '查看训练进度',
    to: buildTrainingProgressRoute(sessionId),
  },
  {
    label: '查看训练报告',
    to: buildTrainingReportRoute(sessionId),
  },
  {
    label: '查看训练诊断',
    to: buildTrainingDiagnosticsRoute(sessionId),
  },
];

function TrainingShellHeader({
  hasInsightEntry,
  insightSessionId,
  onClearWorkspace,
}: TrainingShellHeaderProps) {
  return (
    <>
      <div className="training-shell__eyebrow">PR-07</div>
      <h1 className="training-shell__title">Training Frontend MVP</h1>
      <p className="training-shell__description">
        训练主线通过独立 `sessionId` 驱动。初始化、回合提交、刷新恢复都收口到训练专用
        `services / hooks / flow`，页面层不直接兼容后端脏字段，也不复用 story 会话实现。
      </p>

      <div className="training-shell__actions">
        <Link className="training-shell__link" to={ROUTES.HOME}>
          返回首页
        </Link>
        {hasInsightEntry ? (
          <button className="training-shell__clear-button" type="button" onClick={onClearWorkspace}>
            清空训练入口
          </button>
        ) : null}
      </div>

      {hasInsightEntry ? (
        <div className="training-shell__subnav" aria-label="训练结果导航">
          {insightLinks(insightSessionId).map((item) => (
            <Link key={item.label} className="training-shell__subnav-link" to={item.to}>
              {item.label}
            </Link>
          ))}
        </div>
      ) : null}
    </>
  );
}

export default TrainingShellHeader;
