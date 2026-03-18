import AppRouter from './router';
import { App as AntdApp } from 'antd';
import { GameFlowProvider } from '@/contexts';
import './App.css';

function App() {
  return (
    <AntdApp>
      <GameFlowProvider>
        <AppRouter />
      </GameFlowProvider>
    </AntdApp>
  );
}

export default App;
