import { Outlet } from 'react-router-dom';

function Layout() {
  return (
    <main
      style={{
        width: '100%',
        minHeight: '100vh',
        padding: 0,
        background: 'transparent',
      }}
    >
      <Outlet />
    </main>
  );
}

export default Layout;
