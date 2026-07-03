// Animated starry-sky background shown in dark mode. Pure CSS: three parallax
// star layers (twinkling drift) + a couple of periodic shooting stars. Purely
// decorative, so it's hidden from assistive tech.
export default function StarField() {
  return (
    <div className="starfield" aria-hidden="true">
      <div className="starfield__layer starfield__layer--far" />
      <div className="starfield__layer starfield__layer--mid" />
      <div className="starfield__layer starfield__layer--near" />
      <div className="starfield__shooting starfield__shooting--1" />
      <div className="starfield__shooting starfield__shooting--2" />
      <div className="starfield__glow" />
    </div>
  );
}
