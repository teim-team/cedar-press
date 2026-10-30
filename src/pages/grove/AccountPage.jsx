import { Link } from "react-router";
import "../../styles/grove/accountPages.css";

export function AccountPage({ children, wide = false }) {
  return <div className="teim-rd teim-rd--paper cp-account-page">
    <header className="cp-account-page__header">
      <div className="cp-account-page__identity"><Link className="cp-account-page__brand" to="/"><img src="/brand/lumecon-logo-mark-teal.png" alt="" />Cedar Press</Link><span className="cp-account-page__tagline">Trusted intelligence for Indian Country</span></div>
      <nav aria-label="Public navigation"><Link to="/data">Explore</Link><Link to="/articles">Research</Link><Link to="/methods">Methods</Link></nav>
      <div className="cp-account-page__actions"><Link className="cp-btn cp-btn--quiet" to="/subscribe">Early access</Link><Link className="cp-btn cp-btn--primary" to="/login">Sign in</Link></div>
    </header>
    <main className={`cp-account-page__main${wide ? " cp-account-page__main--wide" : ""}`} id="cp-main">{children}</main>
  </div>;
}
