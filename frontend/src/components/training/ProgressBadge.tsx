interface ProgressBadgeProps {
  roundNo: number;
  totalRounds?: number | null;
}

function ProgressBadge({ roundNo, totalRounds }: ProgressBadgeProps) {
  const text =
    totalRounds != null && totalRounds > 0
      ? `第 ${roundNo} 轮 / 共 ${totalRounds} 轮`
      : `第 ${roundNo} 轮`;

  return (
    <div className="training-progress-badge" aria-label={text}>
      {text}
    </div>
  );
}

export default ProgressBadge;
