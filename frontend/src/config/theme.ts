import type { ThemeConfig } from 'antd';

// Ant Design 主题配置
export const themeConfig: ThemeConfig = {
  token: {
    // 主色
    colorPrimary: '#1890ff',
    // 圆角
    borderRadius: 8,
    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      headerBg: '#001529',
      headerHeight: 64,
      headerPadding: '0 24px',
    },
    Card: {
      borderRadius: 8,
      paddingLG: 24,
    },
    Button: {
      borderRadius: 8,
    },
  },
};
