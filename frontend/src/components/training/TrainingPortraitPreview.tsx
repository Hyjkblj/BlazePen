import { Alert, Button, Card, Skeleton, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { createCharacter, getCharacterImages } from '@/services/characterApi';

type TrainingFormDraftValue = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

type TrainingPortraitPreviewProps = {
  formDraft: TrainingFormDraftValue;
};

type PreviewStatus = 'idle' | 'loading' | 'ready' | 'error';

type CharacterPreset = {
  appearanceKeywords: string[];
  personalityKeywords: string[];
  style: string;
  defaultName: string;
  defaultGender: 'male' | 'female';
};

const CHARACTER_PRESETS: Record<string, CharacterPreset> = {
  'correspondent-female': {
    appearanceKeywords: ['高挑', '干练', '文艺', '黑发', '冷白皮'],
    personalityKeywords: ['冷静', '勇敢', '有责任感', '理性', '独立'],
    style: '战地纪实风，灰暗色调，暗红火光点缀。',
    defaultName: '前线女记者',
    defaultGender: 'female',
  },
  'correspondent-male': {
    appearanceKeywords: ['成熟感', '简约风', '气场强', '短发', '干练'],
    personalityKeywords: ['冷静', '谨慎', '有主见', '可靠', '理性'],
    style: '战地纪实风，低饱和灰调，背景暗红烟尘。',
    defaultName: '前线男记者',
    defaultGender: 'male',
  },
  'frontline-photographer': {
    appearanceKeywords: ['运动感', '时尚感', '短发', '健康肤色', '干练'],
    personalityKeywords: ['行动力强', '勇敢', '好奇心强', '自信', '独立'],
    style: '镜头纪实风，强调现场张力与烟尘光影。',
    defaultName: '前线摄影记者',
    defaultGender: 'male',
  },
  'radio-operator': {
    appearanceKeywords: ['简约风', '文艺', '气质优雅', '黑发', '身材匀称'],
    personalityKeywords: ['谨慎', '可靠', '有责任感', '细腻', '冷静'],
    style: '战地通讯纪实风，突出联络设备与紧张氛围。',
    defaultName: '战地通讯员',
    defaultGender: 'female',
  },
};

const mapGender = (rawGender: string, fallbackGender: 'male' | 'female'): 'male' | 'female' => {
  const normalized = rawGender.trim().toLowerCase();
  if (normalized === '男' || normalized === 'male' || normalized === 'm' || normalized === 'man') {
    return 'male';
  }
  if (
    normalized === '女' ||
    normalized === 'female' ||
    normalized === 'f' ||
    normalized === 'woman'
  ) {
    return 'female';
  }
  return fallbackGender;
};

const parseAge = (rawAge: string): number | undefined => {
  const normalized = rawAge.trim();
  if (!normalized) {
    return undefined;
  }

  const age = Number.parseInt(normalized, 10);
  if (!Number.isInteger(age) || age <= 0) {
    return undefined;
  }

  return age;
};

const trimOrNull = (value: string): string | null => {
  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const pickFirstValidImageUrl = (imageUrls: string[]): string | null => {
  for (const imageUrl of imageUrls) {
    if (typeof imageUrl === 'string' && imageUrl.trim() !== '') {
      return imageUrl;
    }
  }
  return null;
};

const pickPreviewImageUrls = (imageUrls: string[], limit = 2): string[] => {
  const seen = new Set<string>();
  const selected: string[] = [];

  for (const imageUrl of imageUrls) {
    if (selected.length >= limit) {
      break;
    }
    if (typeof imageUrl !== 'string') {
      continue;
    }

    const normalized = imageUrl.trim();
    if (!normalized || seen.has(normalized)) {
      continue;
    }

    seen.add(normalized);
    selected.push(normalized);
  }

  return selected;
};

function TrainingPortraitPreview({ formDraft }: TrainingPortraitPreviewProps) {
  const [previewStatus, setPreviewStatus] = useState<PreviewStatus>('idle');
  const [previewImageUrls, setPreviewImageUrls] = useState<string[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const hasRequiredFields =
    formDraft.portraitPresetId.trim() !== '' && formDraft.playerIdentity.trim() !== '';

  const generationSummary = useMemo(() => {
    const characterPreset = CHARACTER_PRESETS[formDraft.portraitPresetId];
    return {
      identity: trimOrNull(formDraft.playerIdentity) ?? '未选择',
      characterPresetName: characterPreset?.defaultName ?? '未选择',
      playerName: trimOrNull(formDraft.playerName) ?? '未填写',
    };
  }, [formDraft.portraitPresetId, formDraft.playerIdentity, formDraft.playerName]);

  const handleGeneratePreview = async () => {
    if (!hasRequiredFields) {
      setPreviewStatus('error');
      setPreviewError('请先在左侧选择身份与个人形象，再生成右侧渲染图。');
      return;
    }

    const characterPreset =
      CHARACTER_PRESETS[formDraft.portraitPresetId] ?? CHARACTER_PRESETS['correspondent-female'];
    const resolvedPlayerName = trimOrNull(formDraft.playerName) ?? characterPreset.defaultName;
    const resolvedIdentity = trimOrNull(formDraft.playerIdentity) ?? '战地记者';

    setPreviewStatus('loading');
    setPreviewError(null);

    try {
      const createdCharacter = await createCharacter({
        name: resolvedPlayerName,
        gender: mapGender(formDraft.playerGender, characterPreset.defaultGender),
        age: parseAge(formDraft.playerAge),
        identity: resolvedIdentity,
        appearance: {
          keywords: characterPreset.appearanceKeywords,
          scene_tone: '1937-1945 wartime china, documentary realism',
        },
        personality: {
          keywords: characterPreset.personalityKeywords,
          identity: resolvedIdentity,
        },
        background: {
          style: characterPreset.style,
          palette: 'desaturated grayscale with dark red accents',
          lighting: 'cinematic side backlight and volumetric fog',
        },
      });

      let imageCandidates = [...createdCharacter.imageUrls];
      if (createdCharacter.imageUrl) {
        imageCandidates = [createdCharacter.imageUrl, ...imageCandidates];
      }

      if (imageCandidates.length === 0 && createdCharacter.characterId) {
        const imageResponse = await getCharacterImages(createdCharacter.characterId);
        imageCandidates = Array.isArray(imageResponse.images) ? imageResponse.images : [];
      }

      const firstImageUrl = pickFirstValidImageUrl(imageCandidates);
      if (!firstImageUrl) {
        throw new Error('后端已响应，但未返回可用图片链接。');
      }

      setPreviewImageUrls(pickPreviewImageUrls(imageCandidates, 2));
      setPreviewStatus('ready');
      setPreviewError(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '渲染失败，请稍后重试。';
      setPreviewStatus('error');
      setPreviewError(message);
    }
  };

  return (
    <div className="training-landing__preview">
      <Card className="training-landing__preview-card">
        <Typography.Title className="training-landing__preview-title" level={4}>
          形象渲染
        </Typography.Title>
        <Typography.Paragraph className="training-landing__preview-tip">
          读取左侧身份设置并调用后端生图服务，生成当前训练角色形象。
        </Typography.Paragraph>

        <div className="training-landing__preview-stage">
          {[0, 1].map((slotIndex) => {
            const imageUrl = previewImageUrls[slotIndex] ?? null;
            const slotLabel = `渲染位 ${slotIndex + 1}`;

            return (
              <div className="training-landing__preview-slot" key={slotLabel}>
                {previewStatus === 'loading' ? (
                  <Skeleton.Image className="training-landing__preview-skeleton" active />
                ) : imageUrl ? (
                  <img
                    alt={`训练身份形象渲染图-${slotIndex + 1}`}
                    className="training-landing__preview-image"
                    src={imageUrl}
                  />
                ) : (
                  <div className="training-landing__preview-placeholder">
                    <p>{slotLabel}</p>
                    <p>等待生成</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="training-landing__preview-summary">
          <p>身份：{generationSummary.identity}</p>
          <p>形象：{generationSummary.characterPresetName}</p>
          <p>姓名：{generationSummary.playerName}</p>
        </div>

        {previewError ? (
          <Alert
            className="training-landing__preview-alert"
            type="error"
            showIcon
            message="渲染失败"
            description={previewError}
          />
        ) : null}

        <div className="training-landing__preview-actions">
          <Button
            className="training-landing__preview-generate"
            type="primary"
            loading={previewStatus === 'loading'}
            disabled={!hasRequiredFields}
            onClick={() => {
              void handleGeneratePreview();
            }}
          >
            {previewStatus === 'ready' ? '重新渲染' : '生成形象图'}
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default TrainingPortraitPreview;
