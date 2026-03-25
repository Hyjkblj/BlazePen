import { Button } from 'antd';
import TrainingTitleFire from '@/components/training/TrainingTitleFire';
import './TrainingMainHome.css';

type TrainingMainHomeProps = {
  onEnter: () => void;
};

function TrainingMainHome({ onEnter }: TrainingMainHomeProps) {
  return (
    <div className="training-mainhome">
      <h1 className="training-mainhome__title">
        烽火笔锋
        <TrainingTitleFire className="training-mainhome__title-fire" text="烽火笔锋" />
      </h1>

      <div className="training-mainhome__action">
        <Button className="training-mainhome__start" type="primary" size="large" onClick={onEnter}>
          开 始
        </Button>
      </div>
    </div>
  );
}

export default TrainingMainHome;
