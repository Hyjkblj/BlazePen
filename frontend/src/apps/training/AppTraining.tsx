import { FeedbackProvider, TrainingFlowProvider } from '@/contexts';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';
import TrainingRouter from '@/router/trainingRouter';

function AppTraining() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#c92b2b',
          colorInfo: '#c92b2b',
          borderRadius: 12,
          fontFamily:
            '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", "Segoe UI", sans-serif',
        },
      }}
    >
      <FeedbackProvider>
        <TrainingFlowProvider>
          <TrainingRouter />
        </TrainingFlowProvider>
      </FeedbackProvider>
    </ConfigProvider>
  );
}

export default AppTraining;
