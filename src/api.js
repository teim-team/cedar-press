/**
 * PURPOSE
 * The standalone site's stand-in for the app's API module.
 *
 * Only the calls the press surface names exist here. Activation is gated off
 * in the gate (pressSignup.PRESS_ACTIVATION_AVAILABLE is false) exactly as it
 * is in the app while the server routes do not exist, so these stubs are
 * unreachable today; they reject with the server's own error shape so the
 * gate's copy renders correctly if the flag flips before the real API lands.
 */

function pressError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

export async function validatePressCode() {
  throw pressError(
    "PRESS_CODE_INVALID",
    "Activation is not available in this preview. Sign in with the preview account instead.",
  );
}

export async function activatePressAccount() {
  throw pressError(
    "PRESS_CODE_INVALID",
    "Activation is not available in this preview. Sign in with the preview account instead.",
  );
}
