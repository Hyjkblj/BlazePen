import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import './TrainingNewsroomIntroPage.css';

const INTRO_TITLE = '山河有难，笔亦为枪';

const INTRO_BODY = `1937年的盛夏，华夏大地早已褪去往日的安宁，山河告急，烽烟四起，战火的阴影笼罩着每一寸土地。在这风雨如晦的时代里，一间并不起眼的报馆，却如暗夜中的一束微光，亮着通宵不灭的灯火，在时代的风暴中坚守着一方阵地。报馆之内，电话的急促声、电报的滴答声、人们忙碌的脚步声与翻纸的沙沙声交织在一起，嘈杂却又透着一股不容懈怠的坚定——所有人都清楚，前线的枪声正一步步逼近城门，而后方的百姓，此刻最需要的，是真实、可靠，能为他们驱散恐慌、安定人心的消息。

就在这时，李敏抱着采访本走进了编辑部。彼时的她，还只是一个刚被委以重任的年轻记者，虽已做好面对危险的准备，却尚未真正读懂战争的重量，也未曾意识到，在这烽火连天的岁月里，一篇看似普通的报道，写下的从来不止是文字，更是无数人的信心、判断，乃至求生的希望。

陈编辑望着这个初出茅庐却眼神坚定的姑娘，语气沉稳却字字有力，将一份沉甸甸的嘱托交付于她：“从今天起，你写下的每一行字，都要对得起山河、对得起同胞、也对得起新闻人的良知。”

一旁的赵川，抬手拍了拍桌边那台饱经沧桑的老旧电报机，话语里满是坚定：“战火越急，越要稳住笔。我们要把真实告诉人民，也要把信心送到人民中间。”

正在印刷机旁忙碌的老何，缓缓抬起头，目光望向远方，声音平静却掷地有声：“纸张会旧，铅字会凉，但真正站得住的报道，能陪很多人熬过最难的夜。”

李敏郑重地点了点头，没有过多的言语。她或许还不知道，这条以笔为枪、以字为刃的道路，将会延伸至何方，将会充满多少艰难险阻，但她无比清楚，从这一夜起，从她接过这份责任的那一刻起，自己已然站进了时代的中央，与这片苦难的山河，与亿万挣扎的同胞，紧紧站在了一起。`;

const TYPING_INTERVAL_MS = 65;

function TrainingNewsroomIntroPage() {
  const navigate = useNavigate();
  const [visibleCount, setVisibleCount] = useState(
    import.meta.env.MODE === 'test' ? INTRO_BODY.length : 0
  );

  const isTypingDone = visibleCount >= INTRO_BODY.length;

  useEffect(() => {
    if (isTypingDone) {
      return;
    }
    const timerId = window.setInterval(() => {
      setVisibleCount((current) => Math.min(INTRO_BODY.length, current + 1));
    }, TYPING_INTERVAL_MS);
    return () => {
      window.clearInterval(timerId);
    };
  }, [isTypingDone]);

  const visibleBody = useMemo(() => INTRO_BODY.slice(0, visibleCount), [visibleCount]);
  const visibleParagraphs = useMemo(
    () => visibleBody.split('\n\n').filter((paragraph) => paragraph.trim() !== ''),
    [visibleBody]
  );

  const handleContinue = useCallback(() => {
    if (!isTypingDone) {
      setVisibleCount(INTRO_BODY.length);
      return;
    }
    navigate(ROUTES.TRAINING_CINEMATIC_DEMO, { replace: true });
  }, [isTypingDone, navigate]);

  return (
    <div
      className="training-newsroom-intro"
      role="button"
      tabIndex={0}
      aria-label="训练剧情序章，点击继续"
      onClick={handleContinue}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleContinue();
        }
      }}
    >
      <div className="training-newsroom-intro__content">
        <h1 className="training-newsroom-intro__title">{INTRO_TITLE}</h1>
        <div className="training-newsroom-intro__body">
          {visibleParagraphs.length > 0
            ? visibleParagraphs.map((paragraph, index) => {
                const isLastParagraph = index === visibleParagraphs.length - 1;
                return (
                  <p className="training-newsroom-intro__paragraph" key={`${index}-${paragraph.length}`}>
                    {paragraph}
                    {!isTypingDone && isLastParagraph ? (
                      <span className="training-newsroom-intro__cursor">|</span>
                    ) : null}
                  </p>
                );
              })
            : !isTypingDone ? <span className="training-newsroom-intro__cursor">|</span> : null}
        </div>
        <p className="training-newsroom-intro__hint">
          {isTypingDone ? '点击任意位置继续' : '点击任意位置跳过打字'}
        </p>
      </div>
    </div>
  );
}

export default TrainingNewsroomIntroPage;
