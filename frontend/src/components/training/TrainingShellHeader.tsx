import { Button, Space, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();

  return (
    <>
      <div className="training-shell__eyebrow">PR-07</div>
      <h1 className="training-shell__title">Training Frontend MVP</h1>
      <Typography.Paragraph className="training-shell__description">
        训练主线通过独立 <code>sessionId</code> 驱动。初始化、回合提交、刷新恢复都收口到训练专用
        <code>services / hooks / flow</code>，页面层不直接兼容后端脏字段，也不复用 story 会话实现。
      </Typography.Paragraph>

      <Space className="training-shell__actions" wrap>
        <Button
          className="training-shell__link"
          type="primary"
          onClick={() => {
            navigate(ROUTES.HOME);
          }}
        >
          返回首页
        </Button>
        {hasInsightEntry ? (
          <Button className="training-shell__clear-button" onClick={onClearWorkspace}>
            清空训练入口
          </Button>
        ) : null}
      </Space>

      {hasInsightEntry ? (
        <Space className="training-shell__subnav" wrap aria-label="训练结果导航">
          {insightLinks(insightSessionId).map((item) => (
            <Button
              key={item.label}
              className="training-shell__subnav-link"
              onClick={() => {
                navigate(item.to);
              }}
            >
              {item.label}
            </Button>
          ))}
        </Space>
      ) : null}
    </>
  );
}

export default TrainingShellHeader;
