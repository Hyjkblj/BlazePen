import { useNavigate } from 'react-router-dom';
import { Result, Button } from 'antd';
import { HomeOutlined } from '@ant-design/icons';

function NotFound() {
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="404"
      subTitle="抱歉，您访问的页面不存在。"
      extra={
        <Button type="primary" icon={<HomeOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>
      }
    />
  );
}

export default NotFound;

