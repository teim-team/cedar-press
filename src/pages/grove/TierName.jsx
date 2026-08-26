// REVIEW OWNER: Havala
//
// "Cedar Press+" with the plus raised, everywhere the name renders.
//
// The whole name is ONE inline span. The first version returned a fragment,
// and inside a flex parent (the Get button, any inline-flex link) the
// fragment's pieces became separate flex items, where vertical-align does
// nothing, so the plus sat full-size beside the name instead of above it.
// Wrapping the name keeps the superscript inside normal inline layout no
// matter what container it lands in.
export function TierName({ name }) {
  if (!name?.endsWith("+")) return name;
  return (
    <span className="cp-tname">
      {name.slice(0, -1)}
      <span className="cp-plus">+</span>
    </span>
  );
}
