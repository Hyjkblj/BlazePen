import { useState } from 'react';
import { getStaticAssetUrl } from '@/services/assetUrl';

export interface GameSceneBackgroundProps {
  loading: boolean;
  shouldUseComposite: boolean;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  onCompositeError?: () => void;
  onSceneError?: () => void;
  onCharacterError?: () => void;
}

interface CompositeBackgroundProps {
  loading: boolean;
  compositeImageUrl: string | null;
  onCompositeError?: () => void;
}

interface SceneBackgroundLayerProps {
  loading: boolean;
  sceneImageUrl: string | null;
  onSceneError?: () => void;
}

interface CharacterOverlayLayerProps {
  characterImageUrl: string | null;
  onCharacterError?: () => void;
}

function CompositeBackground({
  loading,
  compositeImageUrl,
  onCompositeError,
}: CompositeBackgroundProps) {
  const [failed, setFailed] = useState(false);
  const hasCompositeImage = Boolean(compositeImageUrl) && !failed;

  const placeholderText = failed
    ? '合成图片加载失败'
    : loading
      ? '场景合成中...'
      : '当前场景暂未生成合成图';

  return (
    <>
      {hasCompositeImage && compositeImageUrl ? (
        <img
          src={getStaticAssetUrl(compositeImageUrl)}
          alt="游戏场景"
          className="composite-scene-image"
          onError={() => {
            setFailed(true);
            onCompositeError?.();
          }}
        />
      ) : null}
      <div
        className="scene-placeholder-fallback"
        style={{ display: hasCompositeImage ? 'none' : 'flex' }}
      >
        <span
          className={`scene-placeholder-text ${failed ? 'scene-placeholder-text-error' : ''}`}
        >
          {placeholderText}
        </span>
      </div>
    </>
  );
}

function SceneBackgroundLayer({
  loading,
  sceneImageUrl,
  onSceneError,
}: SceneBackgroundLayerProps) {
  const [failed, setFailed] = useState(false);
  const hasSceneImage = Boolean(sceneImageUrl) && !failed;

  if (!hasSceneImage || !sceneImageUrl) {
    const placeholderText = failed
      ? '场景背景加载失败'
      : loading
        ? '加载场景中...'
        : '当前场景暂无背景';

    return (
      <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
        <span
          className={`scene-placeholder-text ${failed ? 'scene-placeholder-text-error' : ''}`}
        >
          {placeholderText}
        </span>
      </div>
    );
  }

  return (
    <img
      src={getStaticAssetUrl(sceneImageUrl)}
      alt="场景背景"
      className="scene-background-image"
      onError={() => {
        setFailed(true);
        onSceneError?.();
      }}
    />
  );
}

function CharacterOverlayLayer({
  characterImageUrl,
  onCharacterError,
}: CharacterOverlayLayerProps) {
  const [failed, setFailed] = useState(false);

  if (!characterImageUrl || failed) {
    return null;
  }

  return (
    <img
      src={getStaticAssetUrl(characterImageUrl)}
      alt="角色"
      className="character-overlay-image"
      onError={() => {
        setFailed(true);
        onCharacterError?.();
      }}
    />
  );
}

export default function GameSceneBackground({
  loading,
  shouldUseComposite,
  compositeImageUrl,
  sceneImageUrl,
  characterImageUrl,
  onCompositeError,
  onSceneError,
  onCharacterError,
}: GameSceneBackgroundProps) {
  if (shouldUseComposite) {
    return (
      <CompositeBackground
        key={`composite:${shouldUseComposite ? compositeImageUrl ?? 'empty' : 'disabled'}`}
        loading={loading}
        compositeImageUrl={compositeImageUrl}
        onCompositeError={onCompositeError}
      />
    );
  }

  return (
    <>
      <SceneBackgroundLayer
        key={`scene:${sceneImageUrl ?? 'empty'}`}
        loading={loading}
        sceneImageUrl={sceneImageUrl}
        onSceneError={onSceneError}
      />
      <CharacterOverlayLayer
        key={`character:${characterImageUrl ?? 'empty'}`}
        characterImageUrl={characterImageUrl}
        onCharacterError={onCharacterError}
      />
    </>
  );
}
