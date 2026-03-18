import { Typography, App as AntdApp } from 'antd';
import { getStaticAssetUrl } from '@/services/assetUrl';

const { Text } = Typography;

export interface GameSceneBackgroundProps {
  shouldUseComposite: boolean;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  onCompositeError?: () => void;
  onSceneError?: () => void;
  onCharacterError?: () => void;
}

export default function GameSceneBackground({
  shouldUseComposite,
  compositeImageUrl,
  sceneImageUrl,
  characterImageUrl,
  onCompositeError,
  onSceneError,
  onCharacterError,
}: GameSceneBackgroundProps) {
  const { message } = AntdApp.useApp();

  if (shouldUseComposite && !compositeImageUrl) {
    message.error('合成图片加载失败，请刷新页面重试');
    return (
      <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
        <Text style={{ color: '#ff4d4f', fontSize: '24px' }}>合成图片加载失败</Text>
      </div>
    );
  }

  if (compositeImageUrl) {
    return (
      <img
        src={getStaticAssetUrl(compositeImageUrl)}
        alt="游戏场景"
        className="composite-scene-image"
        onError={(e) => {
          message.error('合成图片加载失败，请刷新页面重试');
          const target = e.target as HTMLImageElement;
          target.style.display = 'none';
          const placeholder = target.parentElement?.querySelector('.scene-placeholder-fallback') as HTMLElement;
          if (placeholder) {
            placeholder.style.display = 'flex';
            placeholder.innerHTML = '<span style="color: #ff4d4f; font-size: 24px;">合成图片加载失败</span>';
          }
          onCompositeError?.();
        }}
      />
    );
  }

  return (
    <>
      {sceneImageUrl ? (
        <img
          src={getStaticAssetUrl(sceneImageUrl)}
          alt="场景背景"
          className="scene-background-image"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const placeholder = target.parentElement?.querySelector('.scene-placeholder-fallback') as HTMLElement;
            if (placeholder) placeholder.style.display = 'flex';
            onSceneError?.();
          }}
        />
      ) : (
        <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
          <Text style={{ color: '#fff', fontSize: '24px' }}>加载场景中...</Text>
        </div>
      )}
      {characterImageUrl && (
        <img
          src={getStaticAssetUrl(characterImageUrl)}
          alt="角色"
          className="character-overlay-image"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
            onCharacterError?.();
          }}
        />
      )}
    </>
  );
}
