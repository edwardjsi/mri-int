import BreakoutRadar from './BreakoutRadar';

/**
 * Wrapper page component for the Breakout Radar visualization.
 * It simply forwards the `onSelectStock` prop to the underlying
 * `BreakoutRadar` component, allowing the App to render it as a
 * dedicated page while keeping navigation logic unchanged.
 */
function BreakoutRadarPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  return <BreakoutRadar onSelectStock={onSelectStock} />;
}

export default BreakoutRadarPage;
