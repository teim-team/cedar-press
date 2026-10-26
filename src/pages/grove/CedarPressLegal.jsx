// The Terms of Service and the Privacy Policy. Public and prerendered, and
// linked from sign-in, the membership cards and every footer.
//
// The privacy statements describe what the service does today: one session
// cookie, Stripe for cards, Datadog only when configured and never with an
// email address, Cedar keeping a conversation for its follow-ups. A change to
// any of those is a change to this page, in the same commit.
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { CONTACT_EMAIL, contactHref } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import {
  LEGAL_UPDATED,
  PRESS_METHODS_PATH,
  PRESS_PRIVACY_PATH,
  PRESS_REQUEST_PATH,
  PRESS_SETTINGS_PATH,
  PRESS_TERMS_PATH,
} from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressFoot, PressMast } from "./PressChrome";

const UPDATED = new Date(`${LEGAL_UPDATED}T00:00:00`).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

function LegalPage({ title, children }) {
  useScrollToTop();
  const { user } = useAuth();
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page">
        <PressMast />
        <article className="cp-legal">
          <h1>{title}</h1>
          <p className="cp-legal__updated">Last updated {UPDATED}</p>
          {children}
        </article>
        <PressFoot nav={canReadCedarPress(user)} />
      </main>
    </div>
  );
}

const contact = (subject) => <a href={contactHref(subject)}>{CONTACT_EMAIL}</a>;

export function CedarPressTerms() {
  useDocumentTitle("Terms of Service", {
    index: true,
    description: "The terms for using Cedar Press, its collections and Cedar, the AI economic analyst.",
  });
  return (
    <LegalPage title="Terms of Service">
      <h2>Who we are</h2>
      <p>
        Cedar Press is a research publication built by Lumecon (&ldquo;we&rdquo;). These terms
        cover cedarpress.ai, app.cedarpress.ai, the collections and their downloads, and Cedar, the
        AI economic analyst. By creating an account, subscribing or using Cedar Press, you agree to
        them. If you use Cedar Press for an organization, you confirm that you can accept these
        terms on its behalf.
      </p>

      <h2>Your account</h2>
      <p>
        Each account is for one person. Keep your email address current and your password to
        yourself, and do not share your sign-in. Tell us at {contact("Cedar Press account security")} if
        you think someone else has used your account. We may suspend an account that breaks these
        terms or puts the service or other subscribers at risk.
      </p>

      <h2>Subscriptions and billing</h2>
      <ul>
        <li>
          Cedar Press and Cedar Press+ are annual subscriptions, paid upfront through Stripe. They
          renew automatically each year until you cancel. Current prices are on the{" "}
          <Link to="/subscribe">membership page</Link>.
        </li>
        <li>
          An early-access rate stays the same while your subscription remains active. If a
          subscription ends and you subscribe again, the current price applies.
        </li>
        <li>Discount codes are entered at checkout and apply as described when you enter them.</li>
        <li>
          You can cancel at any time from <Link to={PRESS_SETTINGS_PATH}>Settings</Link>. Your
          access continues to the end of the year you have paid for, and the subscription does not
          renew.
        </li>
        <li>
          You can upgrade from Settings. A move from Cedar Press+ to Cedar Press takes effect at
          renewal.
        </li>
        <li>If you think you were charged in error, contact us at {contact("Cedar Press billing")}.</li>
      </ul>

      <h2>Using the collections</h2>
      <p>
        Your subscription lets you search, analyze and download the collections your plan includes,
        and use them in your own work: research, reporting, planning, advising and publications,
        including the figures and findings you draw from them. Every download carries its own
        citation; please cite Cedar Press when you publish from it.
      </p>
      <p>You may not:</p>
      <ul>
        <li>redistribute, resell or publish the raw collections, or substantial parts of them, as a dataset;</li>
        <li>give people outside your subscription access to your account or its downloads;</li>
        <li>scrape the service or retrieve data other than through its own pages and downloads; or</li>
        <li>try to get around access limits or the service&rsquo;s security.</li>
      </ul>
      <p>
        The collections are compiled from publicly available records, and each source&rsquo;s own
        terms continue to apply to its documents. The compilations, the entity layer that connects
        them, the methods, this site and Cedar are Lumecon&rsquo;s.
      </p>

      <h2>Accuracy and Cedar&rsquo;s answers</h2>
      <p>
        We document how each collection is built on the <Link to={PRESS_METHODS_PATH}>Methods</Link>{" "}
        page and correct errors when we find them. Even so, the collections and Cedar are provided
        as they are, without a promise that they are complete or free of error, and nothing in them
        is legal, financial or investment advice. Cedar&rsquo;s answers are generated by an AI
        economic analyst and can be wrong; check them against the source records it cites before
        you rely on them.
      </p>
      <p>
        A tribal government can ask what Cedar Press holds about it, or ask for a correction,
        through a <Link to={PRESS_REQUEST_PATH}>tribal data request</Link>.
      </p>

      <h2>Liability</h2>
      <p>
        To the extent the law allows, Lumecon is not liable for indirect or consequential losses
        arising from your use of Cedar Press, and our total liability for any claim is limited to
        what you paid for Cedar Press in the twelve months before the claim.
      </p>

      <h2>Changes to these terms</h2>
      <p>
        When we change these terms we update the date at the top of this page. For a significant
        change, we email subscribers before it takes effect.
      </p>

      <h2>Contact</h2>
      <p>Questions about these terms: {contact("Cedar Press terms")}.</p>
      <p>
        See also the <Link to={PRESS_PRIVACY_PATH}>Privacy Policy</Link>.
      </p>
    </LegalPage>
  );
}

export function CedarPressPrivacy() {
  useDocumentTitle("Privacy Policy", {
    index: true,
    description: "What Cedar Press collects about its subscribers, why, who else handles it, and the choices you have.",
  });
  return (
    <LegalPage title="Privacy Policy">
      <p>
        Cedar Press is built by Lumecon. This policy explains what we collect when you use Cedar
        Press, why, and what you can do about it. We do not sell personal information, and we do
        not use advertising networks or cross-site tracking.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <b>Your account.</b> Your email address, the name you choose to add, and your password,
          which we store only as a salted one-way hash. We also record when you joined and whether
          you have confirmed your email address.
        </li>
        <li>
          <b>Your subscription.</b> Stripe processes payments, and we never receive your full card
          number. We keep Stripe&rsquo;s references to your customer record and subscription, your
          plan and its status, and your invoice amounts and dates.
        </li>
        <li>
          <b>What you tell us.</b> What you work on, if you answer that question in Settings; how
          you spend your points on research priorities, and the requests you write there; and any
          message you send us, such as a tribal data request or a research access request.
        </li>
        <li>
          <b>Your questions to Cedar.</b> Questions you ask Cedar, and its answers, go to
          Cedar&rsquo;s service so it can answer them. A conversation is kept so that your
          follow-up questions have their context.
        </li>
        <li>
          <b>How the service is used.</b> We record each download (which collection and release,
          and when), and our servers keep standard request logs, including network addresses, for
          security and troubleshooting.
        </li>
        <li>
          <b>Performance and errors.</b> Where it is enabled, Datadog measures page performance and
          errors. It receives your plan, a pseudonymous identifier and a broad type of organization
          read from your email domain (a tribal government, federal, academic or other), never your
          email address itself; what you type into forms is masked; and we do not record clicks,
          scrolling or your screen.
        </li>
      </ul>

      <h2>Cookies and browser storage</h2>
      <p>
        Cedar Press sets one cookie, which keeps you signed in for up to fourteen days. It cannot be
        read by scripts on the page and is not used to track you elsewhere. Your browser also keeps
        a few preferences on your device, such as views you save on the collections page; those stay
        in your browser and are not sent to us.
      </p>

      <h2>How we use it</h2>
      <p>
        To run your account and subscription, deliver the collections and Cedar, send the emails
        your account needs (such as confirmation links, password resets and notices about your
        account), keep the service secure, answer your messages, and decide what to build next,
        which is what research priorities are for.
      </p>

      <h2>Who else handles it</h2>
      <ul>
        <li><b>Stripe</b> processes payments and keeps your billing details.</li>
        <li><b>Amazon Web Services</b> hosts the service and its database.</li>
        <li><b>Datadog</b> receives performance and error measurements, as described above.</li>
        <li><b>Our email delivery provider</b> sends account emails.</li>
      </ul>
      <p>
        Each handles your information only to provide its service to us. We also disclose
        information when the law requires it.
      </p>

      <h2>How long we keep it</h2>
      <p>
        We keep your account information while your account exists. Billing records are kept for as
        long as accounting and tax rules require. Password reset and email confirmation links expire
        within one hour. If you ask us to delete your account, we delete or anonymize your
        information except what we must keep for those rules.
      </p>

      <h2>How we protect it</h2>
      <p>
        Connections to Cedar Press are encrypted. Passwords are stored only as salted hashes. The
        database is encrypted at rest and cannot be reached from the internet, and access to it is
        limited to the service itself.
      </p>

      <h2>Your choices</h2>
      <p>
        You can change your name, email address and password, and withdraw your answer about your
        work, in <Link to={PRESS_SETTINGS_PATH}>Settings</Link>. To get a copy of your information,
        correct it or delete your account, write to {contact("Cedar Press privacy request")}.
      </p>

      <h2>People and organizations in the collections</h2>
      <p>
        The collections are built from publicly available records about tribal nations,
        enterprises, organizations and their activity. Where a public record names a person in a
        public or business role, such as an official, a filer or a business owner, the record may
        carry that name as the source gives it. We leave out private individuals&rsquo; personal
        data. To ask about or correct a record, write to {contact("Cedar Press record correction")};
        a tribal government can also make a <Link to={PRESS_REQUEST_PATH}>tribal data request</Link>.
      </p>

      <h2>Children</h2>
      <p>
        Cedar Press is a professional research service and is not directed to children. We do not
        knowingly collect information from anyone under 13.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        When we change this policy we update the date at the top of this page. For a significant
        change, we email subscribers before it takes effect.
      </p>

      <h2>Contact</h2>
      <p>Questions about this policy: {contact("Cedar Press privacy")}.</p>
      <p>
        See also the <Link to={PRESS_TERMS_PATH}>Terms of Service</Link>.
      </p>
    </LegalPage>
  );
}
