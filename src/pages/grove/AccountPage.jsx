import { Link } from "react-router";
import "../../styles/grove/accountPages.css";

export function AccountPage({ children, wide = false }) {
  return <div className="teim-rd teim-rd--paper cp-account-page">
    <header className="cp-account-page__header">
      <Link className="cp-account-page__brand" to="/"><img src="/brand/lumecon-logo-mark-teal.png" alt="" />Cedar Press</Link>
      <nav aria-label="Public navigation"><Link to="/data">Explore</Link><Link to="/articles">Research</Link><Link to="/methods">Methods</Link></nav>
      <div className="cp-account-page__actions"><Link to="/login">Sign in</Link><Link className="cp-btn cp-btn--primary" to="/subscribe">Subscribe</Link></div>
    </header>
    <main className={`cp-account-page__main${wide ? " cp-account-page__main--wide" : ""}`} id="cp-main">{children}</main>
  </div>;
}
