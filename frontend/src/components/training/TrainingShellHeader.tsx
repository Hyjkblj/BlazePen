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
      <div className="training-shell__eyebrow">训练主线</div>
      <h1 className="training-shell__title">沉浸式训练</h1>
      <Typography.Paragraph className="training-shell__description">
        场景由后端异步生成并持续推进，你只需要在关键时刻做出选择，系统会在训练结束后统一输出评估结果。
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
