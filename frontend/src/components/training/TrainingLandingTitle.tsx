import TrainingTitleFire from '@/components/training/TrainingTitleFire';

type TrainingLandingTitleProps = {
  title?: string;
};

const DEFAULT_TITLE = '烽火笔锋';

function TrainingLandingTitle({ title = DEFAULT_TITLE }: TrainingLandingTitleProps) {
  return (
    <h1 className="training-landing__title">
      {title}
      <TrainingTitleFire className="training-landing__title-fire" text={title} />
    </h1>
  );
}

export default TrainingLandingTitle;
