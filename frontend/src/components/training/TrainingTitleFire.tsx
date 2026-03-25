import { useEffect, useRef } from 'react';

type TrainingTitleFireProps = {
  className?: string;
  text: string;
};

const FLOW_SPEED_PX_PER_SEC = 90;

function TrainingTitleFire({ className, text }: TrainingTitleFireProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const titleElement = canvas.parentElement;
    if (!titleElement) {
      return;
    }

    const context = canvas.getContext('2d', { alpha: true, willReadFrequently: true });
    if (!context) {
      return;
    }

    let cssWidth = 0;
    let cssHeight = 0;
    let isActive = true;
    const startTime = performance.now();

    const resizeCanvas = () => {
      const rect = titleElement.getBoundingClientRect();
      cssWidth = Math.max(1, Math.round(rect.width));
      cssHeight = Math.max(1, Math.round(rect.height));

      const dpr = Math.max(1, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, Math.round(cssWidth * dpr));
      canvas.height = Math.max(1, Math.round(cssHeight * dpr));
      canvas.style.width = `${cssWidth}px`;
      canvas.style.height = `${cssHeight}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const renderFrame = (timestamp: number) => {
      if (!isActive) {
        return;
      }

      context.clearRect(0, 0, cssWidth, cssHeight);

      if (cssWidth > 0 && cssHeight > 0) {
        const computedStyle = window.getComputedStyle(titleElement);
        const centerX = cssWidth / 2;
        const centerY = cssHeight / 2;
        const elapsed = (timestamp - startTime) / 1000;
        const flow = (elapsed * FLOW_SPEED_PX_PER_SEC) % cssWidth;
        const shimmer = cssWidth * ((elapsed * 0.38) % 1);

        context.save();
        context.font = computedStyle.font;
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillStyle = '#ffffff';
        context.fillText(text, centerX, centerY);
        context.globalCompositeOperation = 'source-in';

        const flameBand = context.createLinearGradient(flow - cssWidth, 0, flow + cssWidth, 0);
        flameBand.addColorStop(0, 'rgba(255, 34, 24, 0)');
        flameBand.addColorStop(0.22, 'rgba(255, 74, 52, 0.64)');
        flameBand.addColorStop(0.5, 'rgba(255, 214, 164, 0.96)');
        flameBand.addColorStop(0.78, 'rgba(255, 78, 52, 0.7)');
        flameBand.addColorStop(1, 'rgba(255, 34, 24, 0)');
        context.globalAlpha = 0.82;
        context.fillStyle = flameBand;
        context.fillRect(0, 0, cssWidth, cssHeight);

        const shimmerBand = context.createLinearGradient(
          shimmer - cssWidth * 0.35,
          0,
          shimmer + cssWidth * 0.35,
          0
        );
        shimmerBand.addColorStop(0, 'rgba(255, 255, 255, 0)');
        shimmerBand.addColorStop(0.4, 'rgba(255, 236, 205, 0.44)');
        shimmerBand.addColorStop(0.5, 'rgba(255, 255, 255, 0.78)');
        shimmerBand.addColorStop(0.6, 'rgba(255, 218, 184, 0.42)');
        shimmerBand.addColorStop(1, 'rgba(255, 255, 255, 0)');
        context.globalAlpha = 0.72;
        context.fillStyle = shimmerBand;
        context.fillRect(0, 0, cssWidth, cssHeight);

        const topMask = context.createLinearGradient(0, 0, 0, cssHeight);
        topMask.addColorStop(0, 'rgba(255, 255, 255, 1)');
        topMask.addColorStop(0.55, 'rgba(255, 255, 255, 0.84)');
        topMask.addColorStop(1, 'rgba(255, 255, 255, 0.2)');
        context.globalCompositeOperation = 'destination-in';
        context.globalAlpha = 1;
        context.fillStyle = topMask;
        context.fillRect(0, 0, cssWidth, cssHeight);

        context.restore();
      }

      animationFrameRef.current = window.requestAnimationFrame(renderFrame);
    };

    resizeCanvas();
    const resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(titleElement);
    animationFrameRef.current = window.requestAnimationFrame(renderFrame);

    return () => {
      isActive = false;
      if (animationFrameRef.current !== null) {
        window.cancelAnimationFrame(animationFrameRef.current);
      }
      resizeObserver.disconnect();
    };
  }, [text]);

  return <canvas aria-hidden className={className} ref={canvasRef} />;
}

export default TrainingTitleFire;
