import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import StoryRouter from '@/router/storyRouter';

function AppStory() {
  return (
    <FeedbackProvider>
      <GameFlowProvider>
        <StoryRouter />
      </GameFlowProvider>
    </FeedbackProvider>
  );
}

export default AppStory;
