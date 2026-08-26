// The whole site: signed out you get the gate, signed in you get the page.
// The home page IS the sign-in — Cedar Press is a subscriber page and states
// its price of admission before it shows anything.
import { useState } from "react";

import PressPage from "./components/PressPage.jsx";
import SignIn from "./components/SignIn.jsx";
import { currentSession, signOut } from "./auth.js";

export default function App() {
  const [user, setUser] = useState(currentSession);
  return (
    <div className="teim-rd">
      {user ? (
        <PressPage
          user={user}
          onSignOut={() => {
            signOut();
            setUser(null);
          }}
        />
      ) : (
        <SignIn onSignedIn={setUser} />
      )}
    </div>
  );
}
